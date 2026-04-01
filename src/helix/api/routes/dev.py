"""Development-only routes. Disabled in production."""

import uuid

from fastapi import APIRouter, HTTPException

from helix.auth.tokens import create_token_claims, encode_token
from helix.config import get_settings

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/token")
async def create_dev_token() -> dict:
    """Issue a real signed JWT for development. Disabled in production."""
    settings = get_settings()
    if settings.environment == "production":
        raise HTTPException(status_code=404, detail="Not found")

    claims = create_token_claims(
        subject_id=uuid.uuid4(),
        org_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        roles=["admin", "operator"],
        email="dev@helix.local",
        display_name="Dev User",
    )
    token = encode_token(claims)
    return {"token": token}
