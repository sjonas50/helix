"""JWT token issuance and verification.

Agent tokens are short-lived (15-min TTL) per architecture spec.
User tokens are longer-lived (24hr) with refresh support.

Uses python-jose for RS256/HS256 signing. In production, use RS256 with
a real key pair. In development, falls back to HS256 with SECRET_KEY.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from jose import JWTError, jwt
from pydantic import BaseModel

from helix.config import get_settings

logger = structlog.get_logger()

# HS256 for development simplicity; RS256 in production with JWT_PUBLIC_KEY_PATH
_ALGORITHM = "HS256"


class TokenClaims(BaseModel):
    """JWT token claims."""

    sub: str  # user_id or agent_id
    org_id: str
    roles: list[str]
    token_type: str  # user | agent
    exp: datetime
    iat: datetime


def _get_signing_key() -> str:
    """Get the signing key from settings."""
    settings = get_settings()
    return settings.secret_key


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

    now = datetime.now(tz=UTC)
    return TokenClaims(
        sub=str(subject_id),
        org_id=str(org_id),
        roles=roles,
        token_type=token_type,
        exp=now + timedelta(minutes=ttl_minutes),
        iat=now,
    )


def encode_token(claims: TokenClaims) -> str:
    """Encode claims into a signed JWT string."""
    payload = {
        "sub": claims.sub,
        "org_id": claims.org_id,
        "roles": claims.roles,
        "token_type": claims.token_type,
        "exp": claims.exp,
        "iat": claims.iat,
    }
    token = jwt.encode(payload, _get_signing_key(), algorithm=_ALGORITHM)
    logger.debug(
        "token.encoded",
        sub=claims.sub,
        token_type=claims.token_type,
    )
    return token


def decode_token(token: str) -> TokenClaims:
    """Decode and verify a JWT string. Raises ValueError on failure."""
    try:
        payload = jwt.decode(token, _get_signing_key(), algorithms=[_ALGORITHM])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e

    return TokenClaims(
        sub=payload["sub"],
        org_id=payload["org_id"],
        roles=payload["roles"],
        token_type=payload["token_type"],
        exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
        iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
    )


def is_token_expired(claims: TokenClaims) -> bool:
    """Check if a token has expired."""
    return datetime.now(tz=UTC) > claims.exp


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
