"""Agent management API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from helix.api.deps import CurrentUser
from helix.api.middleware.auth import get_current_user
from helix.api.schemas.workflows import AgentResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/workflow/{workflow_id}", response_model=list[AgentResponse])
async def list_agents_for_workflow(
    workflow_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> list:
    """List all agents in a workflow."""
    return []


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Get agent details including trace and messages."""
    raise HTTPException(status_code=404, detail="Agent not found")


@router.get("/{agent_id}/messages")
async def get_agent_messages(
    agent_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> list:
    """Get messages sent/received by an agent."""
    return []
