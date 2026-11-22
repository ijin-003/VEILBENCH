"""Create metadata-only benchmark sessions.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "benchmark_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_party_ids", sa.JSON(), nullable=False),
        sa.Column("aggregate_sum", sa.BigInteger(), nullable=True),
        sa.Column("average_salary", sa.Float(), nullable=True),
        sa.Column("failure_reason", sa.String(length=160), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_benchmark_sessions_expires_at",
        "benchmark_sessions",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_benchmark_sessions_expires_at", table_name="benchmark_sessions")
    op.drop_table("benchmark_sessions")
