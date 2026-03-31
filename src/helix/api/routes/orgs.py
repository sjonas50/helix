"""Organization management API routes."""

from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from helix.api.schemas.orgs import OrgCreate, OrgResponse

router = APIRouter(prefix="/orgs", tags=["organizations"])


@router.post("/", response_model=OrgResponse, status_code=201)
async def create_org(body: OrgCreate) -> OrgResponse:
    """Create a new organization.

    In production, this also:
    - Provisions WorkOS SSO connection
    - Creates default RBAC roles
    - Provisions Redis namespaces
    - Creates DreamConfig with default params
    - Creates LLMPolicy with default models
    """
    return OrgResponse(
        id=uuid4(),
        name=body.name,
        slug=body.slug,
        plan=body.plan,
        status="active",
        on_prem=body.on_prem,
        created_at="2026-03-31T00:00:00Z",
    )


@router.get("/{org_id}", response_model=OrgResponse)
async def get_org(org_id: UUID) -> OrgResponse:
    """Get organization by ID."""
    raise HTTPException(status_code=404, detail="Org not found")
