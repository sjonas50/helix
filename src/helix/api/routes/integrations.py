"""Integration management API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from helix.api.deps import CurrentUser
from helix.api.middleware.auth import get_current_user
from helix.api.schemas.integrations import IntegrationCreate, IntegrationResponse

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/", response_model=IntegrationResponse, status_code=201)
async def add_integration(
    body: IntegrationCreate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Add a new integration for the current org."""
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.get("/", response_model=list[IntegrationResponse])
async def list_integrations(
    user: CurrentUser = Depends(get_current_user),
) -> list:
    """List all integrations for the current org."""
    return []


@router.get("/providers")
async def list_providers(
    user: CurrentUser = Depends(get_current_user),
) -> list[str]:
    """List all supported integration providers."""
    from helix.integrations.registry import ToolRegistry

    return ToolRegistry().get_all_providers()


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Get a specific integration."""
    raise HTTPException(status_code=404, detail="Integration not found")


@router.delete("/{integration_id}", status_code=204)
async def remove_integration(
    integration_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> None:
    """Remove an integration."""
    raise HTTPException(status_code=404, detail="Integration not found")


@router.get("/{integration_id}/tools")
async def list_integration_tools(
    integration_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> list:
    """List available tools for an integration."""
    return []
