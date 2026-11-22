"""Add account login and participant assignments."""
from alembic import op
import sqlalchemy as sa

revision = "0002_accounts"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("accounts",
        sa.Column("username", sa.String(80), primary_key=True),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("password_hash", sa.String(256)),
        sa.Column("invitation_hash", sa.String(64)),
        sa.Column("invitation_expiry", sa.BigInteger(), nullable=False),
        sa.Column("benchmark_id", sa.String(36), sa.ForeignKey("benchmark_sessions.id")),
        sa.Column("party_id", sa.Integer()),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("benchmark_id", "party_id"),
    )
    op.create_table("login_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("username", sa.String(80), sa.ForeignKey("accounts.username"), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
    )


def downgrade():
    op.drop_table("login_sessions")
    op.drop_table("accounts")
