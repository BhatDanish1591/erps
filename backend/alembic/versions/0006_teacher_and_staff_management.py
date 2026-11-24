"""teacher_and_staff_management

Revision ID: 0006_teacher_management
Revises: 0005_student_management
Create Date: 2026-11-19 14:05:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_teacher_management"
down_revision: Union[str, None] = "0005_student_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Add extra columns to teacher_profiles ──────────────────────────────
    op.add_column("teacher_profiles", sa.Column("specialization", sa.String(150), nullable=True))
    op.add_column("teacher_profiles", sa.Column("experience_years", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("teacher_profiles", sa.Column("address_line1", sa.String(255), nullable=True))
    op.add_column("teacher_profiles", sa.Column("address_line2", sa.String(255), nullable=True))
    op.add_column("teacher_profiles", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("teacher_profiles", sa.Column("state", sa.String(100), nullable=True))
    op.add_column("teacher_profiles", sa.Column("postal_code", sa.String(20), nullable=True))
    op.add_column("teacher_profiles", sa.Column("country", sa.String(100), nullable=False, server_default="India"))
    op.add_column("teacher_profiles", sa.Column("emergency_contact_name", sa.String(150), nullable=True))
    op.add_column("teacher_profiles", sa.Column("emergency_contact_phone", sa.String(50), nullable=True))
    op.add_column("teacher_profiles", sa.Column("pan_number", sa.String(20), nullable=True))
    op.add_column("teacher_profiles", sa.Column("aadhar_number", sa.String(20), nullable=True))
    op.add_column("teacher_profiles", sa.Column("bank_name", sa.String(100), nullable=True))
    op.add_column("teacher_profiles", sa.Column("bank_account_number", sa.String(50), nullable=True))
    op.add_column("teacher_profiles", sa.Column("bank_ifsc", sa.String(20), nullable=True))
    op.add_column("teacher_profiles", sa.Column("employment_type", sa.String(50), nullable=False, server_default="FULL_TIME"))
    op.add_column("teacher_profiles", sa.Column("photo_url", sa.String(1024), nullable=True))
    op.add_column("teacher_profiles", sa.Column("custom_fields", postgresql.JSONB(), nullable=False, server_default="{}"))

    # ── 2. Create teacher_assignments ─────────────────────────────────────────
    op.create_table(
        "teacher_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teacher_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id", ondelete="CASCADE"), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("semester", sa.Integer(), nullable=True),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("is_class_teacher", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_teacher_assignments_tenant_id", "teacher_assignments", ["tenant_id"])
    op.create_index("ix_teacher_assignments_teacher_id", "teacher_assignments", ["teacher_id"])
    op.create_index("ix_teacher_assignments_subject_id", "teacher_assignments", ["subject_id"])
    op.execute("ALTER TABLE teacher_assignments ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY teacher_assignments_tenant_isolation ON teacher_assignments
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 3. Create timetable_entries ───────────────────────────────────────────
    op.create_table(
        "timetable_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teacher_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id", ondelete="CASCADE"), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("semester", sa.Integer(), nullable=True),
        sa.Column("day_of_week", sa.String(20), nullable=False),
        sa.Column("period_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("start_time", sa.String(10), nullable=False),
        sa.Column("end_time", sa.String(10), nullable=False),
        sa.Column("room_number", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_timetable_entries_tenant_id", "timetable_entries", ["tenant_id"])
    op.create_index("ix_timetable_entries_teacher_day", "timetable_entries", ["teacher_id", "day_of_week"])
    op.execute("ALTER TABLE timetable_entries ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY timetable_entries_tenant_isolation ON timetable_entries
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 4. Create teacher_attendances ─────────────────────────────────────────
    op.create_table(
        "teacher_attendances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teacher_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PRESENT"),
        sa.Column("check_in_time", sa.String(10), nullable=True),
        sa.Column("check_out_time", sa.String(10), nullable=True),
        sa.Column("remarks", sa.String(255), nullable=True),
        sa.Column("recorded_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "teacher_id", "attendance_date", name="uq_teacher_attendance_tenant_date"),
    )
    op.create_index("ix_teacher_attendances_tenant_id", "teacher_attendances", ["tenant_id"])
    op.execute("ALTER TABLE teacher_attendances ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY teacher_attendances_tenant_isolation ON teacher_attendances
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 5. Create teacher_leaves ──────────────────────────────────────────────
    op.create_table(
        "teacher_leaves",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teacher_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leave_type", sa.String(30), nullable=False, server_default="CASUAL"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("days_count", sa.Numeric(4, 1), nullable=False, server_default="1.0"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rejection_reason", sa.String(255), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_teacher_leaves_tenant_id", "teacher_leaves", ["tenant_id"])
    op.create_index("ix_teacher_leaves_teacher_status", "teacher_leaves", ["teacher_id", "status"])
    op.execute("ALTER TABLE teacher_leaves ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY teacher_leaves_tenant_isolation ON teacher_leaves
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 6. Create teacher_documents ───────────────────────────────────────────
    op.create_table(
        "teacher_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teacher_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("document_name", sa.String(255), nullable=False),
        sa.Column("file_url", sa.String(1024), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_teacher_documents_tenant_id", "teacher_documents", ["tenant_id"])
    op.create_index("ix_teacher_documents_teacher_id", "teacher_documents", ["teacher_id"])
    op.execute("ALTER TABLE teacher_documents ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY teacher_documents_tenant_isolation ON teacher_documents
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)


def downgrade() -> None:
    op.drop_table("teacher_documents")
    op.drop_table("teacher_leaves")
    op.drop_table("teacher_attendances")
    op.drop_table("timetable_entries")
    op.drop_table("teacher_assignments")
    op.drop_column("teacher_profiles", "custom_fields")
    op.drop_column("teacher_profiles", "photo_url")
    op.drop_column("teacher_profiles", "employment_type")
    op.drop_column("teacher_profiles", "bank_ifsc")
    op.drop_column("teacher_profiles", "bank_account_number")
    op.drop_column("teacher_profiles", "bank_name")
    op.drop_column("teacher_profiles", "aadhar_number")
    op.drop_column("teacher_profiles", "pan_number")
    op.drop_column("teacher_profiles", "emergency_contact_phone")
    op.drop_column("teacher_profiles", "emergency_contact_name")
    op.drop_column("teacher_profiles", "country")
    op.drop_column("teacher_profiles", "postal_code")
    op.drop_column("teacher_profiles", "state")
    op.drop_column("teacher_profiles", "city")
    op.drop_column("teacher_profiles", "address_line2")
    op.drop_column("teacher_profiles", "address_line1")
    op.drop_column("teacher_profiles", "experience_years")
    op.drop_column("teacher_profiles", "specialization")
