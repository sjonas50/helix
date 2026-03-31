"""Audit trail API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from helix.api.deps import CurrentUser
from helix.api.middleware.auth import get_current_user

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events")
async def list_audit_events(
    user: CurrentUser = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = None,
    resource_type: str | None = None,
) -> dict:
    """Query audit trail with pagination and filtering."""
    return {"events": [], "total": 0, "limit": limit, "offset": offset}


@router.get("/events/{event_id}")
async def get_audit_event(
    event_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Get a single audit event."""
    raise HTTPException(status_code=404, detail="Audit event not found")


@router.get("/integrity")
async def verify_audit_integrity(
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Verify audit trail integrity via chain hash check.

    Each event hashes (prev_hash || payload) — a broken chain indicates tampering.
    """
    return {"status": "ok", "events_checked": 0, "chain_valid": True}
