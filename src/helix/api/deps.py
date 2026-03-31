"""FastAPI dependencies for auth, tenant isolation, and database sessions."""

from uuid import UUID

from pydantic import BaseModel


class CurrentUser(BaseModel):
    """Authenticated user context injected into request handlers."""

    user_id: UUID
    org_id: UUID
    roles: list[str]
    email: str


class TenantContext(BaseModel):
    """Tenant context for multi-tenant isolation.

    Every database query is scoped with org_id from this context.
    RLS at the database layer provides defense-in-depth (arch decision #6).
    """

    org_id: UUID
