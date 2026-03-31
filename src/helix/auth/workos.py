"""WorkOS SSO and SCIM integration.

Handles enterprise SSO login flow and user provisioning/deprovisioning
via SCIM webhooks. Claude Code has no enterprise auth (single-user);
this is required for enterprise customers.
"""

from uuid import UUID

import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


class SSOProfile(BaseModel):
    """User profile returned from WorkOS SSO callback."""

    workos_user_id: str
    email: str
    display_name: str | None = None
    org_id: str | None = None  # WorkOS organization ID


class AuthResult(BaseModel):
    """Result of an SSO authentication flow."""

    user_id: UUID
    org_id: UUID
    email: str
    display_name: str
    roles: list[str]
    is_new_user: bool = False
    access_token: str = ""


async def get_authorization_url(
    org_slug: str,
    redirect_uri: str,
    client_id: str,
) -> str:
    """Generate WorkOS SSO authorization URL.

    In production, this calls workos.client.sso.get_authorization_url().
    Returns the URL to redirect the user's browser to.
    """
    # In production:
    # from workos import WorkOSClient
    # client = WorkOSClient(api_key=settings.workos_api_key)
    # url = client.sso.get_authorization_url(
    #     organization=org_slug,
    #     redirect_uri=redirect_uri,
    #     client_id=client_id,
    # )
    logger.info("workos.auth_url_generated", org_slug=org_slug)
    return f"https://api.workos.com/sso/authorize?organization={org_slug}&redirect_uri={redirect_uri}&client_id={client_id}"


async def handle_sso_callback(
    code: str,
    client_id: str,
) -> SSOProfile:
    """Exchange authorization code for user profile.

    In production, this calls workos.client.sso.get_profile_and_token().
    """
    # In production:
    # profile_and_token = client.sso.get_profile_and_token(code)
    # profile = profile_and_token.profile
    logger.info("workos.sso_callback", code=code[:8] + "...")

    # Stub: return a profile for development
    return SSOProfile(
        workos_user_id=f"workos_{code[:8]}",
        email="user@example.com",
        display_name="SSO User",
    )


async def handle_scim_event(
    event_type: str,
    payload: dict,
) -> dict:
    """Process SCIM webhook events from WorkOS.

    Handles user provisioning (create), updates, and deprovisioning (delete).
    """
    logger.info("workos.scim_event", event_type=event_type)

    if event_type == "dsync.user.created":
        return {"action": "provision", "email": payload.get("email", "")}
    elif event_type == "dsync.user.deleted":
        return {"action": "deprovision", "email": payload.get("email", "")}
    elif event_type == "dsync.user.updated":
        return {"action": "update", "email": payload.get("email", "")}
    else:
        logger.warning("workos.unknown_scim_event", event_type=event_type)
        return {"action": "ignored", "event_type": event_type}
