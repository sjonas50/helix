"""Approval management API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from helix.api.deps import CurrentUser
from helix.api.middleware.auth import get_current_user
from helix.api.schemas.integrations import ApprovalDecision, ApprovalRequestResponse

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/", response_model=list[ApprovalRequestResponse])
async def list_pending_approvals(
    user: CurrentUser = Depends(get_current_user),
) -> list:
    """List pending approval requests for the current org."""
    return []


@router.post("/{approval_id}/decide", response_model=ApprovalRequestResponse)
async def decide_approval(
    approval_id: UUID,
    body: ApprovalDecision,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Approve or reject an approval request."""
    raise HTTPException(status_code=404, detail="Approval request not found")
