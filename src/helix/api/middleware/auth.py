"""Authentication middleware — JWT validation on every request.

Extracts Bearer token from Authorization header, decodes + verifies,
and populates CurrentUser dependency for route handlers.
"""

from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from helix.api.deps import CurrentUser
from helix.auth.tokens import decode_token, validate_token_claims

logger = structlog.get_logger()

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    """FastAPI dependency: extract and verify JWT, return CurrentUser.

    Raises 401 if token is missing, invalid, or expired.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    try:
        claims = decode_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    is_valid, error = validate_token_claims(claims)
    if not is_valid:
        raise HTTPException(status_code=401, detail=error)

    return CurrentUser(
        user_id=UUID(claims.sub),
        org_id=UUID(claims.org_id),
        roles=claims.roles,
        email="",  # Populated from DB in production
    )


def require_roles(*required_roles: str):
    """Factory for role-checking dependencies.

    Usage: Depends(require_roles("admin", "operator"))
    Returns a FastAPI dependency function (not a coroutine).
    """
    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not any(role in user.roles for role in required_roles):
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of: {', '.join(required_roles)}",
            )
        return user
    return _check
