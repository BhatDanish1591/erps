"""Create Timetable Management tables and enhancements

Revision ID: 0012_timetable_management
Revises: 0011_study_material_and_lms
Create Date: 2026-11-19 16:45:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0012_timetable_management"
down_revision: Union[str, None] = "0011_study_material_and_lms"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create timetable_settings ─────────────────────────────────────────
    op.create_table(
        "timetable_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("working_days", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='["MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY"]'),
        sa.Column("periods_per_day", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("period_duration_minutes", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("break_duration_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("lunch_duration_minutes", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("school_start_time", sa.String(10), nullable=False, server_default="08:30"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "academic_session_id", name="uq_timetable_settings_tenant_session"),
    )
    op.create_index("ix_timetable_settings_tenant_id", "timetable_settings", ["tenant_id"])
    op.execute("ALTER TABLE timetable_settings ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY timetable_settings_tenant_isolation ON timetable_settings
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 2. Create timetable_periods ──────────────────────────────────────────
    op.create_table(
        "timetable_periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("period_type", sa.String(30), nullable=False, server_default="ACADEMIC"),
        sa.Column("start_time", sa.String(10), nullable=False),
        sa.Column("end_time", sa.String(10), nullable=False),
        sa.Column("is_break", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_timetable_periods_tenant_session", "timetable_periods", ["tenant_id", "academic_session_id", "period_number"])
    op.execute("ALTER TABLE timetable_periods ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY timetable_periods_tenant_isolation ON timetable_periods
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 3. Create timetable_holidays ─────────────────────────────────────────
    op.create_table(
        "timetable_holidays",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("holiday_type", sa.String(50), nullable=False, server_default="NATIONAL"),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_half_day", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_timetable_holidays_tenant_date", "timetable_holidays", ["tenant_id", "holiday_date"])
    op.execute("ALTER TABLE timetable_holidays ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY timetable_holidays_tenant_isolation ON timetable_holidays
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 4. Create timetable_schedules ────────────────────────────────────────
    op.create_table(
        "timetable_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("institution_type", sa.String(20), nullable=False, server_default="SCHOOL"),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_timetable_schedules_tenant_status", "timetable_schedules", ["tenant_id", "status"])
    op.execute("ALTER TABLE timetable_schedules ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY timetable_schedules_tenant_isolation ON timetable_schedules
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 5. Add enhancements to timetable_entries ──────────────────────────────
    op.add_column("timetable_entries", sa.Column("schedule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("timetable_schedules.id", ondelete="CASCADE"), nullable=True))
    op.add_column("timetable_entries", sa.Column("period_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("timetable_periods.id", ondelete="SET NULL"), nullable=True))
    op.add_column("timetable_entries", sa.Column("entry_type", sa.String(30), nullable=False, server_default="THEORY"))
    op.add_column("timetable_entries", sa.Column("is_practical", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("timetable_entries", sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_batches.id", ondelete="SET NULL"), nullable=True))
    op.add_column("timetable_entries", sa.Column("semester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_semesters.id", ondelete="SET NULL"), nullable=True))
    op.add_column("timetable_entries", sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True))
    op.add_column("timetable_entries", sa.Column("capacity", sa.Integer(), nullable=True))
    op.add_column("timetable_entries", sa.Column("notes", sa.String(255), nullable=True))

    op.create_index("ix_timetable_entries_schedule_id", "timetable_entries", ["schedule_id"])
    op.create_index("ix_timetable_entries_class_section_day", "timetable_entries", ["class_id", "section_id", "day_of_week"])
    op.create_index("ix_timetable_entries_room_day", "timetable_entries", ["room_number", "day_of_week"])

    # ── 6. Create substitute_teacher_assignments ─────────────────────────────
    op.create_table(
        "substitute_teacher_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timetable_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("timetable_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_date", sa.Date(), nullable=False),
        sa.Column("original_teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teacher_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("substitute_teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teacher_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="ASSIGNED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_substitute_assignments_tenant_date", "substitute_teacher_assignments", ["tenant_id", "assignment_date"])
    op.create_index("ix_substitute_assignments_sub_teacher", "substitute_teacher_assignments", ["substitute_teacher_id", "assignment_date"])
    op.execute("ALTER TABLE substitute_teacher_assignments ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY substitute_teacher_assignments_tenant_isolation ON substitute_teacher_assignments
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)


def downgrade() -> None:
    op.drop_table("substitute_teacher_assignments")
    op.drop_index("ix_timetable_entries_room_day", table_name="timetable_entries")
    op.drop_index("ix_timetable_entries_class_section_day", table_name="timetable_entries")
    op.drop_index("ix_timetable_entries_schedule_id", table_name="timetable_entries")

    op.drop_column("timetable_entries", "notes")
    op.drop_column("timetable_entries", "capacity")
    op.drop_column("timetable_entries", "department_id")
    op.drop_column("timetable_entries", "semester_id")
    op.drop_column("timetable_entries", "batch_id")
    op.drop_column("timetable_entries", "is_practical")
    op.drop_column("timetable_entries", "entry_type")
    op.drop_column("timetable_entries", "period_id")
    op.drop_column("timetable_entries", "schedule_id")

    op.drop_table("timetable_schedules")
    op.drop_table("timetable_holidays")
    op.drop_table("timetable_periods")
    op.drop_table("timetable_settings")
