"""attendance_management

Revision ID: 0008_attendance_management
Revises: 0007_academic_management
Create Date: 2026-11-19 15:00:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008_attendance_management"
down_revision: Union[str, None] = "0007_academic_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Add rfid_tag to student_profiles and teacher_profiles ──────────────
    op.add_column("student_profiles", sa.Column("rfid_tag", sa.String(100), nullable=True))
    op.create_index("ix_student_profiles_rfid", "student_profiles", ["tenant_id", "rfid_tag"])

    op.add_column("teacher_profiles", sa.Column("rfid_tag", sa.String(100), nullable=True))
    op.create_index("ix_teacher_profiles_rfid", "teacher_profiles", ["tenant_id", "rfid_tag"])

    # ── 2. Create student_attendance_sessions ─────────────────────────────────
    op.create_table(
        "student_attendance_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("session_type", sa.String(30), server_default="DAILY", nullable=False),  # DAILY, PERIOD_WISE, SUBJECT_WISE
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id", ondelete="CASCADE"), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=True),
        sa.Column("semester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_semesters.id", ondelete="CASCADE"), nullable=True),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("period_number", sa.Integer(), nullable=True),
        sa.Column("conducted_by_teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teacher_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("total_students", sa.Integer(), server_default="0", nullable=False),
        sa.Column("present_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("absent_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("late_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("leave_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("qr_token", sa.String(100), nullable=True),
        sa.Column("qr_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="SUBMITTED", nullable=False),
        sa.Column("remarks", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_student_att_sess_tenant", "student_attendance_sessions", ["tenant_id"])
    op.create_index("ix_student_att_sess_date", "student_attendance_sessions", ["tenant_id", "session_date"])
    op.create_index("ix_student_att_sess_class_sec", "student_attendance_sessions", ["tenant_id", "class_id", "section_id"])
    op.execute("ALTER TABLE student_attendance_sessions ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY student_att_sess_tenant_isolation ON student_attendance_sessions
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 3. Create student_attendance_entries ──────────────────────────────────
    op.create_table(
        "student_attendance_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_attendance_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), server_default="PRESENT", nullable=False),  # PRESENT, ABSENT, LATE, LEAVE
        sa.Column("late_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("remarks", sa.String(255), nullable=True),
        sa.Column("check_in_method", sa.String(30), server_default="MANUAL", nullable=False),  # MANUAL, QR, RFID, BIOMETRIC, GPS
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "session_id", "student_id", name="uq_student_att_entry_sess_stu"),
    )
    op.create_index("ix_student_att_entries_tenant", "student_attendance_entries", ["tenant_id"])
    op.create_index("ix_student_att_entries_sess", "student_attendance_entries", ["tenant_id", "session_id"])
    op.create_index("ix_student_att_entries_stu", "student_attendance_entries", ["tenant_id", "student_id"])
    op.execute("ALTER TABLE student_attendance_entries ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY student_att_entries_tenant_isolation ON student_attendance_entries
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 4. Create attendance_correction_logs ──────────────────────────────────
    op.create_table(
        "attendance_correction_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_attendance_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_status", sa.String(20), nullable=False),
        sa.Column("new_status", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("corrected_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("corrected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_att_corr_logs_tenant", "attendance_correction_logs", ["tenant_id"])
    op.create_index("ix_att_corr_logs_entry", "attendance_correction_logs", ["tenant_id", "entry_id"])
    op.execute("ALTER TABLE attendance_correction_logs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY att_corr_logs_tenant_isolation ON attendance_correction_logs
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 5. Create attendance_device_logs ──────────────────────────────────────
    op.create_table(
        "attendance_device_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.String(100), nullable=False),
        sa.Column("device_type", sa.String(50), nullable=False),  # RFID, BIOMETRIC, QR_SCANNER, GPS
        sa.Column("identifier_tag", sa.String(150), nullable=False),
        sa.Column("user_type", sa.String(30), nullable=True),  # STUDENT, TEACHER
        sa.Column("matched_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scanned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
    )
    op.create_index("ix_att_device_logs_tenant", "attendance_device_logs", ["tenant_id"])
    op.create_index("ix_att_device_logs_tag", "attendance_device_logs", ["tenant_id", "identifier_tag"])
    op.execute("ALTER TABLE attendance_device_logs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY att_device_logs_tenant_isolation ON attendance_device_logs
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)


def downgrade() -> None:
    op.drop_table("attendance_device_logs")
    op.drop_table("attendance_correction_logs")
    op.drop_table("student_attendance_entries")
    op.drop_table("student_attendance_sessions")
    op.drop_column("teacher_profiles", "rfid_tag")
    op.drop_column("student_profiles", "rfid_tag")
