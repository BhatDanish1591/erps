"""student_management

Revision ID: 0005_student_management
Revises: 0004_subscription_billing
Create Date: 2026-11-19 13:35:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_student_management"
down_revision: Union[str, None] = "0004_subscription_billing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Add extra columns to student_profiles ──────────────────────────────
    op.add_column("student_profiles", sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="SET NULL"), nullable=True))
    op.add_column("student_profiles", sa.Column("semester", sa.Integer(), nullable=True))
    op.add_column("student_profiles", sa.Column("batch_year", sa.Integer(), nullable=True))
    op.add_column("student_profiles", sa.Column("admission_date", sa.Date(), nullable=True))
    op.add_column("student_profiles", sa.Column("blood_group", sa.String(10), nullable=True))
    op.add_column("student_profiles", sa.Column("address_line1", sa.String(255), nullable=True))
    op.add_column("student_profiles", sa.Column("address_line2", sa.String(255), nullable=True))
    op.add_column("student_profiles", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("student_profiles", sa.Column("state", sa.String(100), nullable=True))
    op.add_column("student_profiles", sa.Column("postal_code", sa.String(20), nullable=True))
    op.add_column("student_profiles", sa.Column("country", sa.String(100), nullable=False, server_default="India"))
    op.add_column("student_profiles", sa.Column("father_name", sa.String(150), nullable=True))
    op.add_column("student_profiles", sa.Column("father_phone", sa.String(50), nullable=True))
    op.add_column("student_profiles", sa.Column("father_occupation", sa.String(100), nullable=True))
    op.add_column("student_profiles", sa.Column("mother_name", sa.String(150), nullable=True))
    op.add_column("student_profiles", sa.Column("mother_phone", sa.String(50), nullable=True))
    op.add_column("student_profiles", sa.Column("mother_occupation", sa.String(100), nullable=True))
    op.add_column("student_profiles", sa.Column("guardian_name", sa.String(150), nullable=True))
    op.add_column("student_profiles", sa.Column("guardian_phone", sa.String(50), nullable=True))
    op.add_column("student_profiles", sa.Column("guardian_relation", sa.String(50), nullable=True))
    op.add_column("student_profiles", sa.Column("emergency_contact_name", sa.String(150), nullable=True))
    op.add_column("student_profiles", sa.Column("emergency_contact_phone", sa.String(50), nullable=True))
    op.add_column("student_profiles", sa.Column("previous_school_name", sa.String(255), nullable=True))
    op.add_column("student_profiles", sa.Column("previous_grade", sa.String(50), nullable=True))
    op.add_column("student_profiles", sa.Column("transfer_certificate_number", sa.String(100), nullable=True))
    op.add_column("student_profiles", sa.Column("photo_url", sa.String(1024), nullable=True))
    op.add_column("student_profiles", sa.Column("custom_fields", postgresql.JSONB(), nullable=False, server_default="{}"))

    op.create_index("ix_student_profiles_tenant_session", "student_profiles", ["tenant_id", "academic_session_id"])
    op.create_index("ix_student_profiles_tenant_course_sem", "student_profiles", ["tenant_id", "course_id", "semester"])

    # ── 2. Create student_documents table ─────────────────────────────────────
    op.create_table(
        "student_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("document_name", sa.String(255), nullable=False),
        sa.Column("file_url", sa.String(1024), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_student_documents_tenant_student", "student_documents", ["tenant_id", "student_id"])
    op.create_index("ix_student_documents_tenant_type", "student_documents", ["tenant_id", "document_type"])

    # Enable RLS on student_documents
    op.execute("ALTER TABLE student_documents ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY student_documents_tenant_isolation ON student_documents "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # ── 3. Create student_enrollment_history table ────────────────────────────
    op.create_table(
        "student_enrollment_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("semester", sa.Integer(), nullable=True),
        sa.Column("roll_number", sa.String(50), nullable=True),
        sa.Column("enrollment_status", sa.String(30), nullable=False, server_default="ENROLLED"),
        sa.Column("promoted_to_enrollment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("remarks", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_student_enrollments_tenant_student", "student_enrollment_history", ["tenant_id", "student_id"])
    op.create_index("ix_student_enrollments_tenant_session", "student_enrollment_history", ["tenant_id", "academic_session_id"])

    # Enable RLS on student_enrollment_history
    op.execute("ALTER TABLE student_enrollment_history ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY student_enrollments_tenant_isolation ON student_enrollment_history "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # ── 4. Create student_parents table ───────────────────────────────────────
    op.create_table(
        "student_parents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation_type", sa.String(50), nullable=False, server_default="GUARDIAN"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("can_view_grades", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("can_pay_fees", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_student_parents_tenant_student", "student_parents", ["tenant_id", "student_id"])
    op.create_index("ix_student_parents_tenant_user", "student_parents", ["tenant_id", "parent_user_id"])
    op.create_unique_constraint("uq_student_parents_tenant_student_user", "student_parents", ["tenant_id", "student_id", "parent_user_id"])

    # Enable RLS on student_parents
    op.execute("ALTER TABLE student_parents ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY student_parents_tenant_isolation ON student_parents "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )


def downgrade() -> None:
    op.drop_table("student_parents")
    op.drop_table("student_enrollment_history")
    op.drop_table("student_documents")
    op.drop_index("ix_student_profiles_tenant_course_sem", table_name="student_profiles")
    op.drop_index("ix_student_profiles_tenant_session", table_name="student_profiles")
    op.drop_column("student_profiles", "custom_fields")
    op.drop_column("student_profiles", "photo_url")
    op.drop_column("student_profiles", "transfer_certificate_number")
    op.drop_column("student_profiles", "previous_grade")
    op.drop_column("student_profiles", "previous_school_name")
    op.drop_column("student_profiles", "emergency_contact_phone")
    op.drop_column("student_profiles", "emergency_contact_name")
    op.drop_column("student_profiles", "guardian_relation")
    op.drop_column("student_profiles", "guardian_phone")
    op.drop_column("student_profiles", "guardian_name")
    op.drop_column("student_profiles", "mother_occupation")
    op.drop_column("student_profiles", "mother_phone")
    op.drop_column("student_profiles", "mother_name")
    op.drop_column("student_profiles", "father_occupation")
    op.drop_column("student_profiles", "father_phone")
    op.drop_column("student_profiles", "father_name")
    op.drop_column("student_profiles", "country")
    op.drop_column("student_profiles", "postal_code")
    op.drop_column("student_profiles", "state")
    op.drop_column("student_profiles", "city")
    op.drop_column("student_profiles", "address_line2")
    op.drop_column("student_profiles", "address_line1")
    op.drop_column("student_profiles", "blood_group")
    op.drop_column("student_profiles", "admission_date")
    op.drop_column("student_profiles", "batch_year")
    op.drop_column("student_profiles", "semester")
    op.drop_column("student_profiles", "academic_session_id")
