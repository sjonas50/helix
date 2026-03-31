"""Pydantic schemas for org operations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OrgCreate(BaseModel):
    """Request to create a new organization."""

    name: str = Field(min_length=1, max_length=256)
    slug: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9-]+$")
    plan: str = "enterprise"
    on_prem: bool = False


class OrgResponse(BaseModel):
    """Organization response."""

    model_config = {"from_attributes": True}

    id: UUID
    name: str
    slug: str
    plan: str
    status: str
    on_prem: bool
    created_at: datetime
