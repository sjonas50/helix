"""Tests for database migrations, RLS, and tenant isolation.

Requires a running PostgreSQL instance (docker compose up -d postgres).
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from helix.config import get_settings

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def db_session():
    """Create a test database session."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


class TestMigrationState:
    async def test_all_tables_exist(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
            "ORDER BY table_name"
        ))
        tables = {row[0] for row in result.fetchall()}
        expected = {
            "orgs", "users", "role_permissions",
            "workflows", "workflow_templates", "agents", "agent_messages",
            "approval_policies", "approval_requests",
            "memory_records", "dream_configs", "dream_runs",
            "integrations", "integration_tool_executions",
            "llm_policies", "token_usage_events", "workflow_compaction_snapshots",
            "speculative_executions", "audit_events",
            "alembic_version",
        }
        assert expected.issubset(tables), f"Missing tables: {expected - tables}"

    async def test_pgvector_extension_exists(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(text(
            "SELECT extname FROM pg_extension WHERE extname = 'vector'"
        ))
        assert result.fetchone() is not None

    async def test_embedding_column_is_vector(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'memory_records' AND column_name = 'embedding'"
        ))
        row = result.fetchone()
        assert row is not None
        assert row[0] == "USER-DEFINED"  # pgvector type

    async def test_ivfflat_index_exists(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'memory_records' AND indexname = 'idx_memory_embedding'"
        ))
        assert result.fetchone() is not None


class TestRLS:
    # Tables that should have RLS (all tenant-scoped tables with org_id)
    TENANT_TABLES = {
        "users", "role_permissions", "workflows", "workflow_templates",
        "agents", "agent_messages", "approval_policies", "approval_requests",
        "memory_records", "dream_configs", "dream_runs", "integrations",
        "integration_tool_executions", "llm_policies", "token_usage_events",
        "speculative_executions", "audit_events",
    }

    async def test_rls_enabled_on_tenant_tables(self, db_session: AsyncSession) -> None:
        for table in self.TENANT_TABLES:
            result = await db_session.execute(text(
                "SELECT relrowsecurity FROM pg_class WHERE relname = :tbl"
            ), {"tbl": table})
            row = result.fetchone()
            assert row is not None and row[0] is True, f"RLS not enabled on {table}"

    async def test_rls_not_on_orgs(self, db_session: AsyncSession) -> None:
        """orgs is the parent table — no org_id to filter on, RLS not applied."""
        result = await db_session.execute(text(
            "SELECT relrowsecurity FROM pg_class WHERE relname = 'orgs'"
        ))
        row = result.fetchone()
        assert row is not None and row[0] is False

    async def test_rls_policies_count(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(text(
            "SELECT count(*) FROM pg_catalog.pg_policy "
            "WHERE polname LIKE 'tenant_isolation_%'"
        ))
        count = result.scalar()
        assert count >= len(self.TENANT_TABLES), (
            f"Expected {len(self.TENANT_TABLES)}+ RLS policies, got {count}"
        )


class TestTenantIsolation:
    """Test RLS with a non-superuser role (superusers bypass RLS)."""

    @pytest.fixture
    async def app_session(self):
        """Session as helix_app (non-superuser) for RLS testing."""
        app_url = get_settings().database_url.replace(
            "postgres:postgres", "helix_app:helix_app"
        )
        engine = create_async_engine(app_url, echo=False)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            yield session
        await engine.dispose()

    async def test_insert_and_isolate(
        self, db_session: AsyncSession, app_session: AsyncSession
    ) -> None:
        """Insert data as org A, verify org B can't see it via RLS."""
        org_a = uuid.uuid4()
        org_b = uuid.uuid4()

        # Create orgs + data as superuser (bypasses RLS)
        await db_session.execute(text(
            "INSERT INTO orgs (id, name, slug) VALUES (:id, :name, :slug)"
        ), {"id": org_a, "name": "Org A", "slug": f"org-a-{org_a.hex[:8]}"})
        await db_session.execute(text(
            "INSERT INTO orgs (id, name, slug) VALUES (:id, :name, :slug)"
        ), {"id": org_b, "name": "Org B", "slug": f"org-b-{org_b.hex[:8]}"})
        await db_session.execute(text(
            "INSERT INTO dream_configs (org_id) VALUES (:org_id)"
        ), {"org_id": org_a})
        await db_session.commit()

        try:
            # Query as org A via non-superuser — should see the row
            await app_session.execute(text(
                f"SET LOCAL app.current_org_id = '{org_a}'"
            ))
            result = await app_session.execute(text("SELECT * FROM dream_configs"))
            rows_a = result.fetchall()
            assert len(rows_a) == 1

            await app_session.commit()  # Reset SET LOCAL

            # Query as org B via non-superuser — RLS should block
            await app_session.execute(text(
                f"SET LOCAL app.current_org_id = '{org_b}'"
            ))
            result = await app_session.execute(text("SELECT * FROM dream_configs"))
            rows_b = result.fetchall()
            assert len(rows_b) == 0, f"RLS failed: org B saw {len(rows_b)} rows"
        finally:
            # Cleanup as superuser
            await app_session.rollback()
            await db_session.execute(text(
                "DELETE FROM dream_configs WHERE org_id = :id"
            ), {"id": org_a})
            await db_session.execute(text(
                "DELETE FROM orgs WHERE id = :a OR id = :b"
            ), {"a": org_a, "b": org_b})
            await db_session.commit()
