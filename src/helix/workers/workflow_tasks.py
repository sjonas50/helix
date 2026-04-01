"""Celery tasks for workflow execution."""

import asyncio

import structlog

from helix.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    name="helix.workers.workflow_tasks.execute_workflow_task",
    queue="workflow",
    bind=True,
    max_retries=0,
)
def execute_workflow_task(self, workflow_id: str, org_id: str, workflow_json: str) -> dict:  # noqa: ANN001
    """Execute a workflow asynchronously via Celery.

    Deserializes the GeneratedWorkflow from JSON and runs it through the
    executor engine inside an async DB session.
    """

    async def _inner() -> dict:
        from helix.db.engine import get_session_factory
        from helix.orchestration.executor import execute_workflow
        from helix.orchestration.workflow_generator import GeneratedWorkflow

        workflow = GeneratedWorkflow.model_validate_json(workflow_json)
        session_factory = get_session_factory()

        async with session_factory() as session:
            result = await execute_workflow(session, workflow_id, org_id, workflow)
            return result

    logger.info(
        "workflow_task.started",
        workflow_id=workflow_id,
        org_id=org_id,
    )
    try:
        result = asyncio.run(_inner())
        logger.info(
            "workflow_task.completed",
            workflow_id=workflow_id,
            status=result.get("status"),
        )
        return result
    except Exception as e:
        logger.error(
            "workflow_task.failed",
            workflow_id=workflow_id,
            error=str(e),
        )
        return {"status": "FAILED", "workflow_id": workflow_id, "error": str(e)}


@celery_app.task(
    name="helix.workers.workflow_tasks.resume_workflow_task",
    queue="workflow",
    bind=True,
    max_retries=0,
)
def resume_workflow_task(  # noqa: ANN001
    self,
    workflow_id: str,
    org_id: str,
    workflow_json: str,
    paused_at_node: str,
    previous_results_json: str,
    approval_decision: str,
) -> dict:
    """Resume a paused workflow after an approval decision via Celery.

    Picks up execution from the node after the approval gate.
    """
    import json

    async def _inner() -> dict:
        from helix.db.engine import get_session_factory
        from helix.orchestration.executor import resume_workflow
        from helix.orchestration.workflow_generator import GeneratedWorkflow

        workflow = GeneratedWorkflow.model_validate_json(workflow_json)
        previous_results = json.loads(previous_results_json)
        session_factory = get_session_factory()

        async with session_factory() as session:
            result = await resume_workflow(
                session,
                workflow_id,
                org_id,
                workflow,
                paused_at_node,
                previous_results,
                approval_decision,
            )
            return result

    logger.info(
        "workflow_task.resuming",
        workflow_id=workflow_id,
        org_id=org_id,
        decision=approval_decision,
    )
    try:
        result = asyncio.run(_inner())
        logger.info(
            "workflow_task.resume_completed",
            workflow_id=workflow_id,
            status=result.get("status"),
        )
        return result
    except Exception as e:
        logger.error(
            "workflow_task.resume_failed",
            workflow_id=workflow_id,
            error=str(e),
        )
        return {"status": "FAILED", "workflow_id": workflow_id, "error": str(e)}
