"""Create Scheduled Reports and Analytics tables

Revision ID: 0017_analytics_reporting
Revises: 0016_advanced_modules
Create Date: 2026-11-19 22:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0017_analytics_reporting"
down_revision: Union[str, None] = "0016_advanced_modules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. scheduled_reports
    op.create_table(
        "scheduled_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("frequency", sa.String(20), nullable=False, server_default="WEEKLY"),
        sa.Column("format", sa.String(20), nullable=False, server_default="PDF"),
        sa.Column("recipients", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("filters", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_scheduled_reports_tenant_type", "scheduled_reports", ["tenant_id", "report_type"])
    op.create_index("ix_scheduled_reports_user_id", "scheduled_reports", ["user_id"])
    op.create_index("ix_scheduled_reports_is_active", "scheduled_reports", ["is_active"])

    op.execute("ALTER TABLE scheduled_reports ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY scheduled_reports_isolation ON scheduled_reports "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id IS NULL OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS scheduled_reports_isolation ON scheduled_reports;")
    op.drop_table("scheduled_reports")
