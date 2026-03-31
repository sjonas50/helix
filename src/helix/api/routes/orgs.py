"""Organization management API routes."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException

from helix.api.deps import CurrentUser
from helix.api.middleware.auth import get_current_user
from helix.api.schemas.orgs import OrgCreate, OrgResponse

router = APIRouter(prefix="/orgs", tags=["organizations"])


@router.post("/", response_model=OrgResponse, status_code=201)
async def create_org(
    body: OrgCreate,
    user: CurrentUser = Depends(get_current_user),
) -> OrgResponse:
    """Create a new organization.

    Requires authentication. In production, also provisions WorkOS SSO,
    default RBAC roles, DreamConfig, and LLMPolicy.
    """
    return OrgResponse(
        id=uuid4(),
        name=body.name,
        slug=body.slug,
        plan=body.plan,
        status="active",
        on_prem=body.on_prem,
        created_at=datetime.now(tz=UTC),
    )


@router.get("/{org_id}", response_model=OrgResponse)
async def get_org(
    org_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> OrgResponse:
    """Get organization by ID."""
    raise HTTPException(status_code=404, detail="Org not found")
