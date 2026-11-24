"""Align examinations and LMS tables with their soft-delete models."""

from alembic import op

revision = "0021_academic_soft_delete"
down_revision = "0020_staff_documents_timestamp"


def upgrade() -> None:
    op.execute(
        "ALTER TABLE examinations ADD COLUMN IF NOT EXISTS is_deleted boolean NOT NULL DEFAULT false"
    )
    for table in ("examinations", "assignments", "assignment_submissions"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS deleted_at timestamptz")


def downgrade() -> None:
    # Preserve deletion history and columns preinstalled by older deployments.
    pass
