"""Workflow execution engine.

Takes a GeneratedWorkflow (from NL generation or templates) and executes
each node sequentially, calling real integrations, pausing at approval
gates, and emitting status events.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from helix.api.events import emit_agent_activity, emit_approval_request, emit_workflow_status
from helix.integrations.nango import execute_tool
from helix.llm.gateway import LLMRequest, call_llm
from helix.orchestration.workflow_generator import GeneratedWorkflow, WorkflowNode

logger = structlog.get_logger()


class ExecutionContext:
    """Tracks state during workflow execution."""

    def __init__(self, workflow_id: str, org_id: str, session: AsyncSession):
        self.workflow_id = workflow_id
        self.org_id = org_id
        self.session = session
        self.results: dict[str, Any] = {}  # node_id -> result
        self.status = "EXECUTING"
        self.current_node: str | None = None
        self.error: str | None = None


async def execute_workflow(
    session: AsyncSession,
    workflow_id: str,
    org_id: str,
    workflow: GeneratedWorkflow,
) -> dict:
    """Execute a workflow by walking through nodes in edge order.

    For each node:
    - trigger: log start, continue
    - action: call execute_tool() with the provider/tool from the node
    - agent: call LLM for research/analysis/verification
    - approval: create approval request, pause, return pending status
    - condition: evaluate based on previous results

    Returns execution result dict.
    """
    ctx = ExecutionContext(workflow_id, org_id, session)

    # Build execution order from edges (topological sort)
    node_map = {n.id: n for n in workflow.nodes}
    execution_order = _topological_sort(workflow)

    # Update workflow status to EXECUTING
    await _update_workflow_status(session, workflow_id, "EXECUTING")
    await emit_workflow_status(org_id, workflow_id, "EXECUTING", "started")

    for node_id in execution_order:
        node = node_map.get(node_id)
        if not node:
            continue

        ctx.current_node = node_id
        logger.info(
            "executor.node_start",
            workflow_id=workflow_id,
            node_id=node_id,
            type=node.type,
            label=node.label,
        )

        try:
            if node.type == "trigger":
                result = await _execute_trigger(ctx, node)
            elif node.type == "action":
                result = await _execute_action(ctx, node)
            elif node.type == "agent":
                result = await _execute_agent(ctx, node)
            elif node.type == "approval":
                result = await _execute_approval(ctx, node)
                if result.get("status") == "AWAITING_APPROVAL":
                    # Workflow pauses here -- will resume when approval decision arrives
                    await _update_workflow_status(session, workflow_id, "AWAITING_APPROVAL")
                    await emit_workflow_status(
                        org_id, workflow_id, "AWAITING_APPROVAL", node.label
                    )
                    return {
                        "status": "AWAITING_APPROVAL",
                        "workflow_id": workflow_id,
                        "paused_at_node": node_id,
                        "approval_id": result.get("approval_id"),
                        "results": ctx.results,
                    }
            elif node.type == "condition":
                result = await _execute_condition(ctx, node)
            else:
                result = {"status": "skipped", "reason": f"Unknown node type: {node.type}"}

            ctx.results[node_id] = result

            await emit_agent_activity(
                org_id,
                node_id,
                workflow_id,
                f"completed_{node.type}",
                f"{node.label}: {result.get('status', 'done')}",
            )

        except Exception as e:
            logger.error("executor.node_failed", node_id=node_id, error=str(e))
            ctx.error = str(e)
            await _update_workflow_status(session, workflow_id, "FAILED")
            await emit_workflow_status(org_id, workflow_id, "FAILED", str(e))
            return {
                "status": "FAILED",
                "workflow_id": workflow_id,
                "failed_at_node": node_id,
                "error": str(e),
                "results": ctx.results,
            }

    # All nodes completed
    await _update_workflow_status(session, workflow_id, "COMPLETE")
    await emit_workflow_status(org_id, workflow_id, "COMPLETE", "all nodes completed")

    return {
        "status": "COMPLETE",
        "workflow_id": workflow_id,
        "results": ctx.results,
    }


async def resume_workflow(
    session: AsyncSession,
    workflow_id: str,
    org_id: str,
    workflow: GeneratedWorkflow,
    paused_at_node: str,
    previous_results: dict[str, Any],
    approval_decision: str,
) -> dict:
    """Resume a workflow that was paused at an approval node.

    Picks up execution from the node after the approval gate.
    If the approval was REJECTED, marks the workflow as FAILED.
    """
    if approval_decision == "REJECTED":
        await _update_workflow_status(session, workflow_id, "FAILED")
        await emit_workflow_status(org_id, workflow_id, "FAILED", "Approval rejected")
        return {
            "status": "FAILED",
            "workflow_id": workflow_id,
            "failed_at_node": paused_at_node,
            "error": "Approval rejected",
            "results": previous_results,
        }

    ctx = ExecutionContext(workflow_id, org_id, session)
    ctx.results = previous_results

    node_map = {n.id: n for n in workflow.nodes}
    execution_order = _topological_sort(workflow)

    # Find where to resume: skip nodes up to and including the paused node
    resume_from = False
    await _update_workflow_status(session, workflow_id, "EXECUTING")
    await emit_workflow_status(org_id, workflow_id, "EXECUTING", "resumed after approval")

    for node_id in execution_order:
        if node_id == paused_at_node:
            resume_from = True
            continue
        if not resume_from:
            continue

        node = node_map.get(node_id)
        if not node:
            continue

        ctx.current_node = node_id
        logger.info(
            "executor.node_start",
            workflow_id=workflow_id,
            node_id=node_id,
            type=node.type,
            label=node.label,
        )

        try:
            if node.type == "trigger":
                result = await _execute_trigger(ctx, node)
            elif node.type == "action":
                result = await _execute_action(ctx, node)
            elif node.type == "agent":
                result = await _execute_agent(ctx, node)
            elif node.type == "approval":
                result = await _execute_approval(ctx, node)
                if result.get("status") == "AWAITING_APPROVAL":
                    await _update_workflow_status(session, workflow_id, "AWAITING_APPROVAL")
                    await emit_workflow_status(
                        org_id, workflow_id, "AWAITING_APPROVAL", node.label
                    )
                    return {
                        "status": "AWAITING_APPROVAL",
                        "workflow_id": workflow_id,
                        "paused_at_node": node_id,
                        "approval_id": result.get("approval_id"),
                        "results": ctx.results,
                    }
            elif node.type == "condition":
                result = await _execute_condition(ctx, node)
            else:
                result = {"status": "skipped", "reason": f"Unknown node type: {node.type}"}

            ctx.results[node_id] = result

            await emit_agent_activity(
                org_id,
                node_id,
                workflow_id,
                f"completed_{node.type}",
                f"{node.label}: {result.get('status', 'done')}",
            )

        except Exception as e:
            logger.error("executor.node_failed", node_id=node_id, error=str(e))
            ctx.error = str(e)
            await _update_workflow_status(session, workflow_id, "FAILED")
            await emit_workflow_status(org_id, workflow_id, "FAILED", str(e))
            return {
                "status": "FAILED",
                "workflow_id": workflow_id,
                "failed_at_node": node_id,
                "error": str(e),
                "results": ctx.results,
            }

    # All remaining nodes completed
    await _update_workflow_status(session, workflow_id, "COMPLETE")
    await emit_workflow_status(org_id, workflow_id, "COMPLETE", "all nodes completed")

    return {
        "status": "COMPLETE",
        "workflow_id": workflow_id,
        "results": ctx.results,
    }


async def _execute_trigger(ctx: ExecutionContext, node: WorkflowNode) -> dict:
    """Execute a trigger node -- marks workflow as started."""
    return {
        "status": "triggered",
        "trigger_type": node.trigger_type or "manual",
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }


async def _execute_action(ctx: ExecutionContext, node: WorkflowNode) -> dict:
    """Execute an action node -- calls the real integration tool."""
    if not node.provider or not node.tool_name:
        return {"status": "skipped", "reason": "No provider or tool specified"}

    # Build arguments from previous node results
    arguments = _build_arguments_from_context(ctx, node)

    result = await execute_tool(
        provider=node.provider,
        tool_name=node.tool_name,
        arguments=arguments,
    )

    return {
        "status": "success" if result.success else "failed",
        "provider": node.provider,
        "tool": node.tool_name,
        "output": result.output,
        "duration_ms": result.duration_ms,
        "error": result.error,
    }


async def _execute_agent(ctx: ExecutionContext, node: WorkflowNode) -> dict:
    """Execute an agent node -- calls LLM for research/analysis/verification."""
    role = node.agent_role or "researcher"

    # Build prompt from context
    context_summary = "\n".join(
        f"- {nid}: {r.get('status', '?')} -- {str(r.get('output', ''))[:200]}"
        for nid, r in ctx.results.items()
    )

    if role == "researcher":
        task_instruction = "gather relevant information and provide a summary"
    elif role == "verifier":
        task_instruction = (
            "verify all previous steps completed successfully and provide a status report"
        )
    else:
        task_instruction = "execute the required task and report results"

    prompt = (
        f"You are a {role} agent in an automated workflow.\n\n"
        f"Workflow: {node.label}\n"
        f"Task: {node.description}\n\n"
        f"Previous steps completed:\n"
        f"{context_summary or '(this is the first step)'}\n\n"
        f"Based on the workflow context, {task_instruction}."
    )

    try:
        request = LLMRequest(
            messages=[{"role": "user", "content": prompt}],
            model="claude-haiku-4-5",  # Use Haiku for speed in workflow execution
            org_id=uuid.UUID(ctx.org_id),
            workflow_id=uuid.UUID(ctx.workflow_id),
            max_tokens=1024,
        )
        response = await call_llm(request)
        return {
            "status": "complete",
            "role": role,
            "output": response.content,
            "model": response.model_used,
            "tokens": response.input_tokens + response.output_tokens,
        }
    except Exception as e:
        # Agent failure is not workflow failure -- log and continue
        logger.warning("executor.agent_failed", role=role, error=str(e))
        return {
            "status": "degraded",
            "role": role,
            "output": f"Agent could not complete: {str(e)[:200]}",
            "error": str(e),
        }


async def _execute_approval(ctx: ExecutionContext, node: WorkflowNode) -> dict:
    """Execute an approval node -- creates request and pauses workflow."""
    approval_id = str(uuid.uuid4())
    sla_minutes = node.sla_minutes or 60

    # Persist approval request to DB
    await ctx.session.execute(
        text(
            """INSERT INTO approval_requests
            (id, workflow_id, org_id, requested_by_agent_id, action_description,
             risk_level, payload, sla_deadline)
            VALUES (:id, :workflow_id, :org_id, :agent_id, :description,
                    :risk, :payload::jsonb, now() + interval '1 minute' * :sla)"""
        ),
        {
            "id": approval_id,
            "workflow_id": ctx.workflow_id,
            "org_id": ctx.org_id,
            "agent_id": ctx.workflow_id,  # Use workflow_id as agent placeholder
            "description": node.description or node.label,
            "risk": node.risk_level or "MEDIUM",
            "payload": "{}",
            "sla": sla_minutes,
        },
    )
    await ctx.session.commit()

    # Emit WebSocket notification
    await emit_approval_request(
        ctx.org_id,
        approval_id,
        ctx.workflow_id,
        node.description or node.label,
        node.risk_level or "MEDIUM",
    )

    return {
        "status": "AWAITING_APPROVAL",
        "approval_id": approval_id,
        "risk_level": node.risk_level,
        "sla_minutes": sla_minutes,
    }


async def _execute_condition(ctx: ExecutionContext, node: WorkflowNode) -> dict:
    """Execute a condition node -- evaluates to true/false."""
    # Simple: check if all previous steps succeeded
    all_ok = all(
        r.get("status") in ("success", "complete", "triggered") for r in ctx.results.values()
    )
    return {
        "status": "evaluated",
        "condition": node.condition_text or "all_previous_succeeded",
        "result": all_ok,
    }


def _build_arguments_from_context(ctx: ExecutionContext, node: WorkflowNode) -> dict:
    """Build tool arguments from workflow context."""
    # Pass previous results as context for the tool call
    return {
        "workflow_context": {
            nid: r.get("output", {}) if isinstance(r.get("output"), dict) else {"text": str(r.get("output", ""))}
            for nid, r in ctx.results.items()
        }
    }


def _topological_sort(workflow: GeneratedWorkflow) -> list[str]:
    """Sort nodes in execution order based on edges."""
    # Build adjacency list
    adj: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}
    in_degree: dict[str, int] = {n.id: 0 for n in workflow.nodes}

    for edge in workflow.edges:
        if edge.source in adj:
            adj[edge.source].append(edge.target)
        if edge.target in in_degree:
            in_degree[edge.target] += 1

    # Kahn's algorithm
    queue = [n for n, d in in_degree.items() if d == 0]
    result: list[str] = []

    while queue:
        node = queue.pop(0)
        result.append(node)
        for neighbor in adj.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return result


async def _update_workflow_status(
    session: AsyncSession, workflow_id: str, status: str
) -> None:
    """Update workflow status in the database."""
    await session.execute(
        text("UPDATE workflows SET status = :status, updated_at = now() WHERE id = :id"),
        {"id": workflow_id, "status": status},
    )
    if status in ("COMPLETE", "FAILED"):
        await session.execute(
            text("UPDATE workflows SET completed_at = now() WHERE id = :id"),
            {"id": workflow_id},
        )
    await session.commit()
