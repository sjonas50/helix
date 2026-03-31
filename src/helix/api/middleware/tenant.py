"""Tenant isolation middleware.

Sets PostgreSQL session variable `app.current_org_id` per request so that
Row Level Security policies can enforce tenant isolation at the DB layer.
This is defense-in-depth (arch decision #6) — application-layer WHERE
clauses are the primary defense, RLS is the backstop.
"""

from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


async def set_tenant_context(session: AsyncSession, org_id: UUID) -> None:
    """Set the PostgreSQL session variable for RLS tenant isolation.

    Must be called at the start of every request that accesses tenant data.
    Uses SET LOCAL so the setting is scoped to the current transaction only.
    """
    # SET LOCAL doesn't support bind params in asyncpg.
    # UUID is validated by the type system — safe to interpolate.
    safe_org_id = str(org_id)
    await session.execute(text(f"SET LOCAL app.current_org_id = '{safe_org_id}'"))
    logger.debug("tenant.context_set", org_id=str(org_id))


async def clear_tenant_context(session: AsyncSession) -> None:
    """Clear the tenant context. Called at end of request or on error."""
    await session.execute(text("RESET app.current_org_id"))
