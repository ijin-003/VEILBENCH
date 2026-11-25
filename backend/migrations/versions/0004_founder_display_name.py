"""Allow duplicate founder display names without changing login identities."""
from alembic import op
import sqlalchemy as sa

revision = "0004_founder_display_name"
down_revision = "0003_account_created_at"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("accounts", sa.Column("display_name", sa.String(80), nullable=True))

def downgrade():
    op.drop_column("accounts", "display_name")
