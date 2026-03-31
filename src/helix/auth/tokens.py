"""JWT token issuance and verification.

Agent tokens are short-lived (15-min TTL) per architecture spec.
User tokens are longer-lived (24hr) with refresh support.
"""

from datetime import datetime, timedelta
from uuid import UUID

import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


class TokenClaims(BaseModel):
    """JWT token claims."""

    sub: str  # user_id or agent_id
    org_id: str
    roles: list[str]
    token_type: str  # user | agent
    exp: datetime
    iat: datetime


def create_token_claims(
    subject_id: UUID,
    org_id: UUID,
    roles: list[str],
    token_type: str = "user",
    ttl_minutes: int | None = None,
) -> TokenClaims:
    """Create JWT claims for a user or agent token.

    Agent tokens: 15-min TTL (never issue long-lived agent credentials).
    User tokens: 24-hour TTL with refresh.
    """
    if ttl_minutes is None:
        ttl_minutes = 15 if token_type == "agent" else 1440  # 24 hours

    now = datetime.now()
    return TokenClaims(
        sub=str(subject_id),
        org_id=str(org_id),
        roles=roles,
        token_type=token_type,
        exp=now + timedelta(minutes=ttl_minutes),
        iat=now,
    )


def is_token_expired(claims: TokenClaims) -> bool:
    """Check if a token has expired."""
    return datetime.now() > claims.exp


def validate_token_claims(
    claims: TokenClaims,
    required_org_id: UUID | None = None,
) -> tuple[bool, str]:
    """Validate token claims.

    Returns (is_valid, error_message).
    """
    if is_token_expired(claims):
        return False, "Token expired"

    if required_org_id and claims.org_id != str(required_org_id):
        return False, "Org ID mismatch"

    if not claims.roles:
        return False, "No roles assigned"

    return True, ""
