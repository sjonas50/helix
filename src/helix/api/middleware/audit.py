"""Audit logging middleware.

Logs all state-changing requests (POST, PUT, PATCH, DELETE) to the
audit_events table. Claude Code has no audit trail (single-user);
this is required for SOC 2 compliance (arch decision #9).
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()

# Methods that represent state changes
_AUDITABLE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditEntry(BaseModel):
    """An audit event to be persisted."""

    id: UUID = Field(default_factory=uuid4)
    org_id: UUID
    user_id: UUID | None = None
    agent_id: UUID | None = None
    event_type: str
    resource_type: str | None = None
    resource_id: UUID | None = None
    payload: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


def should_audit(method: str) -> bool:
    """Check if an HTTP method should be audited."""
    return method.upper() in _AUDITABLE_METHODS


def create_audit_entry(
    org_id: UUID,
    event_type: str,
    user_id: UUID | None = None,
    agent_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    payload: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditEntry:
    """Create an audit entry for persistence.

    In production, this is written to audit_events table via SQLAlchemy.
    The table is append-only (DELETE/UPDATE revoked from app role).
    """
    entry = AuditEntry(
        org_id=org_id,
        user_id=user_id,
        agent_id=agent_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    logger.info(
        "audit.event",
        event_type=event_type,
        org_id=str(org_id),
        user_id=str(user_id) if user_id else None,
        resource_type=resource_type,
    )

    return entry
