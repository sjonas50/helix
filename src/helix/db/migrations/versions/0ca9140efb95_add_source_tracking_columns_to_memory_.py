"""add source tracking columns to memory_records

Revision ID: 0ca9140efb95
Revises: af7e018444fe
Create Date: 2026-03-31 19:36:11.477068

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0ca9140efb95"
down_revision: str | Sequence[str] | None = "af7e018444fe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add content_hash, source_system, source_id, source_url for ambient memory."""
    op.add_column("memory_records", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column("memory_records", sa.Column("source_system", sa.String(length=64), nullable=True))
    op.add_column("memory_records", sa.Column("source_id", sa.String(length=512), nullable=True))
    op.add_column("memory_records", sa.Column("source_url", sa.Text(), nullable=True))
    op.create_unique_constraint("uq_memory_source", "memory_records", ["org_id", "source_system", "source_id"])


def downgrade() -> None:
    """Remove source tracking columns."""
    op.drop_constraint("uq_memory_source", "memory_records", type_="unique")
    op.drop_column("memory_records", "source_url")
    op.drop_column("memory_records", "source_id")
    op.drop_column("memory_records", "source_system")
    op.drop_column("memory_records", "content_hash")
