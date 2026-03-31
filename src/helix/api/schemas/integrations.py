"""Pydantic schemas for integration operations."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class IntegrationCreate(BaseModel):
    """Request to add an integration."""

    provider: str = Field(min_length=1, max_length=64)
    connector_type: Literal["composio", "nango", "custom"] = "composio"
    config: dict = Field(default_factory=dict)
    rate_limit_per_hour: int = Field(default=1000, ge=1)


class IntegrationResponse(BaseModel):
    """Integration response."""

    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    provider: str
    connector_type: str
    enabled: bool
    rate_limit_per_hour: int
    created_at: datetime
    updated_at: datetime


class ApprovalRequestResponse(BaseModel):
    """Approval request response."""

    model_config = {"from_attributes": True}

    id: UUID
    workflow_id: UUID
    org_id: UUID
    action_description: str
    risk_level: str
    status: str
    decided_by: UUID | None
    decision_reason: str | None
    sla_deadline: datetime | None
    created_at: datetime
    decided_at: datetime | None


class ApprovalDecision(BaseModel):
    """Request to approve or reject an approval request."""

    decision: Literal["APPROVED", "REJECTED"]
    reason: str = Field(default="", max_length=1024)
