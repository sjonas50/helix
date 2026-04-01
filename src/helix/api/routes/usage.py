"""Usage and billing API routes."""

from fastapi import APIRouter, Depends

from helix.api.deps import CurrentUser
from helix.api.middleware.auth import get_current_user

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/stats")
async def get_usage_stats(
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Get token usage statistics for the current org.

    In production: queries token_usage_events table aggregated by model and workflow.
    For now: returns structure matching frontend UsageStats type.
    """
    return {
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cost_usd": 0.0,
        "by_model": {},
        "by_workflow": {},
    }
