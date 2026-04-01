"""Workflow generation API route."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from helix.api.deps import CurrentUser
from helix.api.middleware.auth import get_current_user
from helix.orchestration.workflow_generator import GeneratedWorkflow, generate_workflow

router = APIRouter(prefix="/generate", tags=["generate"])


class GenerateRequest(BaseModel):
    """Request to generate a workflow from natural language."""

    description: str = Field(min_length=10, max_length=2000)


@router.post("/workflow", response_model=GeneratedWorkflow)
async def generate_workflow_from_description(
    body: GenerateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> GeneratedWorkflow:
    """Generate a workflow graph from a natural language description.

    Uses Claude to understand intent, map to available integrations,
    and produce a structured graph for the canvas editor.
    """
    return await generate_workflow(body.description)
