"""Approval management API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from helix.api.schemas.integrations import ApprovalDecision, ApprovalRequestResponse

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/", response_model=list[ApprovalRequestResponse])
async def list_pending_approvals() -> list:
    """List pending approval requests for the current org."""
    return []


@router.post("/{approval_id}/decide", response_model=ApprovalRequestResponse)
async def decide_approval(approval_id: UUID, body: ApprovalDecision) -> dict:
    """Approve or reject an approval request.

    On approval: releases DB savepoint if speculation was running,
    applies queued writes immediately.
    On rejection: rolls back savepoint, discards speculative state.
    """
    raise HTTPException(status_code=404, detail="Approval request not found")
