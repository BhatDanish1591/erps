"""Create Parent and Guardian Portal tables and extensions

Revision ID: 0014_parent_guardian_portal
Revises: 0013_student_fees_and_finance
Create Date: 2026-11-19 18:50:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0014_parent_guardian_portal"
down_revision: Union[str, None] = "0013_student_fees_and_finance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Enhance student_parents with verification & governance columns ───
    op.add_column("student_parents", sa.Column("status", sa.String(30), nullable=False, server_default="VERIFIED"))
    op.add_column("student_parents", sa.Column("verification_method", sa.String(50), nullable=True, server_default="ADMIN_INVITATION"))
    op.add_column("student_parents", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("student_parents", sa.Column("verified_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.add_column("student_parents", sa.Column("verification_notes", sa.Text(), nullable=True))
    op.add_column("student_parents", sa.Column("verification_token", sa.String(100), nullable=True))
    op.add_column("student_parents", sa.Column("emergency_contact", sa.Boolean(), nullable=False, server_default="false"))

    op.create_index("ix_student_parents_tenant_status", "student_parents", ["tenant_id", "status"])
    op.create_index("ix_student_parents_parent_status", "student_parents", ["tenant_id", "parent_user_id", "status"])

    # ── 2. Create student_link_verification_codes table ───────────────────────
    op.create_table(
        "student_link_verification_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("generated_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("used_by_parent_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_link_codes_tenant_code", "student_link_verification_codes", ["tenant_id", "code"])
    op.create_index("ix_link_codes_tenant_student", "student_link_verification_codes", ["tenant_id", "student_id"])

    op.execute("ALTER TABLE student_link_verification_codes ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY link_codes_tenant_isolation ON student_link_verification_codes "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # ── 3. Create parent_teacher_messages table ──────────────────────────────
    op.create_table(
        "parent_teacher_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("sender_role", sa.String(20), nullable=False),  # PARENT | TEACHER
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("parent_message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parent_teacher_messages.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_pt_messages_tenant_student", "parent_teacher_messages", ["tenant_id", "student_id"])
    op.create_index("ix_pt_messages_tenant_parent", "parent_teacher_messages", ["tenant_id", "parent_user_id"])
    op.create_index("ix_pt_messages_tenant_teacher", "parent_teacher_messages", ["tenant_id", "teacher_user_id"])

    op.execute("ALTER TABLE parent_teacher_messages ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY pt_messages_tenant_isolation ON parent_teacher_messages "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )


def downgrade() -> None:
    op.drop_table("parent_teacher_messages")
    op.drop_table("student_link_verification_codes")
    op.drop_index("ix_student_parents_parent_status", table_name="student_parents")
    op.drop_index("ix_student_parents_tenant_status", table_name="student_parents")
    op.drop_column("student_parents", "emergency_contact")
    op.drop_column("student_parents", "verification_token")
    op.drop_column("student_parents", "verification_notes")
    op.drop_column("student_parents", "verified_by_user_id")
    op.drop_column("student_parents", "verified_at")
    op.drop_column("student_parents", "verification_method")
    op.drop_column("student_parents", "status")
