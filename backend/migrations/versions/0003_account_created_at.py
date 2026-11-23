"""Record account creation time without making up legacy signup dates.

Revision ID: 0003_account_created_at
Revises: 0002_accounts
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_account_created_at"
down_revision = "0002_accounts"
branch_labels = None
depends_on = None


def upgrade():
    # Nullable for existing accounts: the actual earlier invitation time is unknown.
    op.add_column("accounts", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("accounts", "created_at")
