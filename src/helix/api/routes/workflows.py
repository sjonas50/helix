"""Workflow management API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from helix.api.deps import CurrentUser
from helix.api.middleware.auth import get_current_user
from helix.api.schemas.workflows import WorkflowCreate, WorkflowResponse

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    body: WorkflowCreate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Create and start a new workflow. Requires authentication."""
    raise HTTPException(status_code=501, detail="Workflow creation not yet implemented")


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Get workflow status and results."""
    raise HTTPException(status_code=404, detail="Workflow not found")


@router.get("/", response_model=list[WorkflowResponse])
async def list_workflows(
    user: CurrentUser = Depends(get_current_user),
) -> list:
    """List workflows for the current org."""
    return []
