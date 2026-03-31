"""Pydantic schemas for memory operations."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

AccessLevel = Literal["PUBLIC", "ROLE_RESTRICTED", "CONFIDENTIAL"]


class MemoryCreate(BaseModel):
    """Request to create a memory record."""

    topic: str = Field(min_length=1, max_length=256)
    content: str = Field(min_length=1, max_length=65536)  # 64KB max
    tags: list[str] = Field(default_factory=list)
    access_level: AccessLevel = "PUBLIC"
    allowed_roles: list[str] = Field(default_factory=list)


class MemoryQuery(BaseModel):
    """Request to query memory by semantic similarity."""

    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)
    access_level: AccessLevel | None = None
    topic_filter: str | None = None


class MemoryResponse(BaseModel):
    """Memory record response."""

    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    topic: str
    content: str
    tags: list[str] | None
    access_level: str
    version: int
    valid_from: datetime
    valid_until: datetime | None
    created_at: datetime


class DreamRunResponse(BaseModel):
    """Dream cycle run response."""

    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    triggered_by: str | None
    phase: str
    sessions_processed: int | None
    records_created: int | None
    records_updated: int | None
    records_pruned: int | None
    tokens_used: int | None
    started_at: datetime
    completed_at: datetime | None
