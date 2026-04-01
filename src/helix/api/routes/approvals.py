"""Approval management API routes."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from helix.api.deps import CurrentUser
from helix.api.middleware.auth import get_current_user
from helix.api.schemas.integrations import ApprovalDecision, ApprovalRequestResponse
from helix.db.engine import get_session_factory

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/", response_model=list[ApprovalRequestResponse])
async def list_pending_approvals(
    user: CurrentUser = Depends(get_current_user),
) -> list:
    """List pending approval requests for the current org."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """SELECT id, workflow_id, org_id, action_description, risk_level,
                       status, decided_by, decision_reason, sla_deadline, created_at, decided_at
                FROM approval_requests
                WHERE org_id = :org_id AND status = 'PENDING'
                ORDER BY created_at DESC LIMIT 50"""
            ),
            {"org_id": str(user.org_id)},
        )
        rows = result.fetchall()

    return [
        {
            "id": str(r[0]),
            "workflow_id": str(r[1]),
            "org_id": str(r[2]),
            "action_description": r[3],
            "risk_level": r[4],
            "status": r[5],
            "decided_by": str(r[6]) if r[6] else None,
            "decision_reason": r[7],
            "sla_deadline": r[8].isoformat() if r[8] else None,
            "created_at": r[9].isoformat() if r[9] else None,
            "decided_at": r[10].isoformat() if r[10] else None,
        }
        for r in rows
    ]


@router.post("/{approval_id}/decide", response_model=ApprovalRequestResponse)
async def decide_approval(
    approval_id: UUID,
    body: ApprovalDecision,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Approve or reject an approval request.

    On APPROVED: updates approval status, resumes the paused workflow via Celery.
    On REJECTED: updates approval status, marks the workflow as FAILED.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        # Find the approval request
        result = await session.execute(
            text(
                """SELECT id, workflow_id, org_id, action_description, risk_level,
                       status, sla_deadline, created_at
                FROM approval_requests WHERE id = :id"""
            ),
            {"id": str(approval_id)},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Approval request not found")

        if row[5] != "PENDING":
            raise HTTPException(
                status_code=409,
                detail=f"Approval already decided: {row[5]}",
            )

        workflow_id = str(row[1])
        org_id = str(row[2])

        # Update approval status
        await session.execute(
            text(
                """UPDATE approval_requests
                SET status = :decision, decided_by = :decided_by,
                    decision_reason = :reason, decided_at = now()
                WHERE id = :id"""
            ),
            {
                "id": str(approval_id),
                "decision": body.decision,
                "decided_by": str(user.user_id),
                "reason": body.reason,
            },
        )

        # Get the workflow context to retrieve workflow JSON for resumption
        wf_result = await session.execute(
            text("SELECT initial_context, status FROM workflows WHERE id = :id"),
            {"id": workflow_id},
        )
        wf_row = wf_result.fetchone()

        if wf_row and wf_row[1] == "AWAITING_APPROVAL":
            context = wf_row[0] or {}
            workflow_json = context.get("workflow", "{}")

            if body.decision == "APPROVED":
                # Resume the workflow via Celery
                from helix.workers.workflow_tasks import resume_workflow_task

                # The paused_at_node info would need to be stored; for now we use
                # a convention of storing it in the workflow result or context.
                # We pass the approval node info so the executor can find where to resume.
                resume_workflow_task.delay(
                    workflow_id,
                    org_id,
                    workflow_json,
                    str(approval_id),  # paused_at_node placeholder
                    json.dumps({}),  # previous_results
                    "APPROVED",
                )
            else:
                # REJECTED: mark workflow as FAILED
                await session.execute(
                    text(
                        """UPDATE workflows SET status = 'FAILED',
                           updated_at = now(), completed_at = now()
                        WHERE id = :id"""
                    ),
                    {"id": workflow_id},
                )

        await session.commit()

        return {
            "id": str(row[0]),
            "workflow_id": workflow_id,
            "org_id": org_id,
            "action_description": row[3],
            "risk_level": row[4],
            "status": body.decision,
            "decided_by": str(user.user_id),
            "decision_reason": body.reason,
            "sla_deadline": row[6].isoformat() if row[6] else None,
            "created_at": row[7].isoformat() if row[7] else None,
            "decided_at": None,  # Just set, not yet read back
        }
