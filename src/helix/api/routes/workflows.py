"""Workflow management API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from helix.api.schemas.workflows import WorkflowCreate, WorkflowResponse

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/", response_model=WorkflowResponse, status_code=201)
async def create_workflow(body: WorkflowCreate) -> dict:
    """Create and start a new workflow.

    In production, this:
    1. Validates the template exists and user has permission
    2. Creates a Workflow row
    3. Dispatches to the LangGraph orchestration engine
    4. Returns the workflow ID for status polling
    """
    raise HTTPException(status_code=501, detail="Workflow creation not yet implemented")


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: UUID) -> dict:
    """Get workflow status and results."""
    raise HTTPException(status_code=404, detail="Workflow not found")


@router.get("/", response_model=list[WorkflowResponse])
async def list_workflows() -> list:
    """List workflows for the current org."""
    return []
