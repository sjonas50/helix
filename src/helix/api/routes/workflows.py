"""Workflow management API routes."""

import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from helix.api.deps import CurrentUser
from helix.api.middleware.auth import get_current_user
from helix.api.schemas.workflows import WorkflowCreate
from helix.db.engine import get_session_factory

router = APIRouter(prefix="/workflows", tags=["workflows"])


class DeployWorkflowRequest(BaseModel):
    """Request to deploy a generated workflow."""

    name: str
    description: str = ""
    workflow_json: str  # JSON-serialized GeneratedWorkflow


class RunWorkflowResponse(BaseModel):
    """Response when a workflow is dispatched for execution."""

    workflow_id: str
    status: str
    message: str


@router.post("/", status_code=201)
async def create_workflow(
    body: WorkflowCreate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Create and start a new workflow. Requires authentication.

    Accepts a WorkflowCreate with initial_context. Saves to DB with PLANNING status.
    """
    workflow_id = str(uuid4())

    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(
            text(
                """INSERT INTO workflows (id, org_id, status, initial_context, created_by, created_at, updated_at)
                VALUES (:id, :org_id, 'PLANNING', :context::jsonb, :user_id, now(), now())"""
            ),
            {
                "id": workflow_id,
                "org_id": str(user.org_id),
                "context": json.dumps(body.initial_context),
                "user_id": str(user.user_id),
            },
        )
        await session.commit()

    return {
        "id": workflow_id,
        "org_id": str(user.org_id),
        "status": "PLANNING",
        "template_id": str(body.template_id) if body.template_id else None,
    }


@router.post("/deploy", status_code=201)
async def deploy_workflow(
    body: DeployWorkflowRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Deploy a generated workflow -- saves to DB with workflow graph JSON."""
    workflow_id = str(uuid4())

    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(
            text(
                """INSERT INTO workflows (id, org_id, status, initial_context, created_by, created_at, updated_at)
                VALUES (:id, :org_id, 'PLANNING', :context::jsonb, :user_id, now(), now())"""
            ),
            {
                "id": workflow_id,
                "org_id": str(user.org_id),
                "context": json.dumps(
                    {
                        "name": body.name,
                        "description": body.description,
                        "workflow": body.workflow_json,
                    }
                ),
                "user_id": str(user.user_id),
            },
        )
        await session.commit()

    return {"id": workflow_id, "status": "PLANNING", "name": body.name}


@router.post("/{workflow_id}/run")
async def run_workflow(
    workflow_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> RunWorkflowResponse:
    """Run a deployed workflow -- dispatches to Celery for async execution."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            text("SELECT id, org_id, status, initial_context FROM workflows WHERE id = :id"),
            {"id": str(workflow_id)},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Workflow not found")

        if row[2] in ("EXECUTING", "AWAITING_APPROVAL"):
            raise HTTPException(status_code=409, detail=f"Workflow already {row[2]}")

        # Get the workflow JSON from initial_context
        context = row[3] or {}
        workflow_json = context.get("workflow", "{}")

        # Dispatch to Celery
        from helix.workers.workflow_tasks import execute_workflow_task

        execute_workflow_task.delay(str(workflow_id), str(user.org_id), workflow_json)

        # Update status
        await session.execute(
            text(
                "UPDATE workflows SET status = 'EXECUTING', updated_at = now() WHERE id = :id"
            ),
            {"id": str(workflow_id)},
        )
        await session.commit()

    return RunWorkflowResponse(
        workflow_id=str(workflow_id),
        status="EXECUTING",
        message="Workflow dispatched for execution",
    )


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Get workflow status and details."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """SELECT id, org_id, status, initial_context, created_at, updated_at, completed_at
                FROM workflows WHERE id = :id"""
            ),
            {"id": str(workflow_id)},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Workflow not found")

        context = row[3] or {}
        return {
            "id": str(row[0]),
            "org_id": str(row[1]),
            "status": row[2],
            "name": context.get("name", "Untitled"),
            "description": context.get("description", ""),
            "created_at": row[4].isoformat() if row[4] else None,
            "updated_at": row[5].isoformat() if row[5] else None,
            "completed_at": row[6].isoformat() if row[6] else None,
        }


@router.get("/")
async def list_workflows(
    user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    """List workflows for the current org."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """SELECT id, org_id, status, initial_context, created_at, updated_at, completed_at
                FROM workflows WHERE org_id = :org_id ORDER BY created_at DESC LIMIT 50"""
            ),
            {"org_id": str(user.org_id)},
        )
        rows = result.fetchall()

    return [
        {
            "id": str(r[0]),
            "org_id": str(r[1]),
            "status": r[2],
            "name": (r[3] or {}).get("name", "Untitled"),
            "description": (r[3] or {}).get("description", ""),
            "created_at": r[4].isoformat() if r[4] else None,
            "updated_at": r[5].isoformat() if r[5] else None,
            "completed_at": r[6].isoformat() if r[6] else None,
        }
        for r in rows
    ]
