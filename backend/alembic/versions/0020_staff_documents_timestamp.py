"""Align faculty documents with the timestamped ORM model."""

import sqlalchemy as sa
from alembic import op

revision = "0020_staff_documents_timestamp"
down_revision = "0019_college_staff_roles"


def upgrade() -> None:
    op.execute(sa.text(
        "ALTER TABLE teacher_documents "
        "ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()"
    ))


def downgrade() -> None:
    # Some installations added this timestamp before this revision.
    pass
