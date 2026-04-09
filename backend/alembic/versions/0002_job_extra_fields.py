"""Add filename_prefix and profile_id to jobs table.

Revision ID: 0002
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE jobs ADD COLUMN filename_prefix TEXT")
    op.execute("ALTER TABLE jobs ADD COLUMN profile_id TEXT")


def downgrade() -> None:
    # SQLite does not support DROP COLUMN in older versions; omit for simplicity.
    pass
