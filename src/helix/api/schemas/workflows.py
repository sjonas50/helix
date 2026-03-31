"""Pydantic schemas for workflow operations."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

WorkflowStatus = Literal[
    "PLANNING", "EXECUTING", "AWAITING_APPROVAL", "VERIFYING", "COMPLETE", "FAILED"
]


class WorkflowCreate(BaseModel):
    """Request to create a new workflow."""

    template_id: UUID | None = None
    initial_context: dict = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    """Workflow response."""

    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    template_id: UUID | None
    status: str
    coordinator_agent_id: UUID | None
    token_usage: dict | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class AgentResponse(BaseModel):
    """Agent response."""

    model_config = {"from_attributes": True}

    id: UUID
    workflow_id: UUID
    role: str
    model_id: str
    status: str
    spawned_by: UUID | None
    hierarchy_depth: int
    token_usage: dict | None
    created_at: datetime
    terminated_at: datetime | None
