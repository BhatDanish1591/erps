"""academic_management

Revision ID: 0007_academic_management
Revises: 0006_teacher_management
Create Date: 2026-11-19 14:30:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007_academic_management"
down_revision: Union[str, None] = "0006_teacher_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create academic_faculties ──────────────────────────────────────────
    op.create_table(
        "academic_faculties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("dean_teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teacher_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_academic_faculties_tenant_code"),
    )
    op.create_index("ix_academic_faculties_tenant_id", "academic_faculties", ["tenant_id"])
    op.execute("ALTER TABLE academic_faculties ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY academic_faculties_tenant_isolation ON academic_faculties
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 2. Create academic_degrees ────────────────────────────────────────────
    op.create_table(
        "academic_degrees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("level", sa.String(50), server_default="UNDERGRADUATE", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_academic_degrees_tenant_code"),
    )
    op.create_index("ix_academic_degrees_tenant_id", "academic_degrees", ["tenant_id"])
    op.execute("ALTER TABLE academic_degrees ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY academic_degrees_tenant_isolation ON academic_degrees
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 3. Enhance departments ────────────────────────────────────────────────
    op.add_column("departments", sa.Column("faculty_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_faculties.id", ondelete="SET NULL"), nullable=True))
    op.add_column("departments", sa.Column("hod_teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teacher_profiles.id", ondelete="SET NULL"), nullable=True))

    # ── 4. Enhance school_classes ─────────────────────────────────────────────
    op.add_column("school_classes", sa.Column("class_teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teacher_profiles.id", ondelete="SET NULL"), nullable=True))
    op.add_column("school_classes", sa.Column("category", sa.String(50), nullable=False, server_default="GENERAL"))

    # ── 5. Enhance courses ────────────────────────────────────────────────────
    op.add_column("courses", sa.Column("degree_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_degrees.id", ondelete="SET NULL"), nullable=True))
    op.add_column("courses", sa.Column("duration_years", sa.Numeric(3, 1), nullable=False, server_default="4.0"))
    op.add_column("courses", sa.Column("coordinator_teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teacher_profiles.id", ondelete="SET NULL"), nullable=True))

    # ── 6. Create college_semesters ───────────────────────────────────────────
    op.create_table(
        "college_semesters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("semester_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("credits_required", sa.Integer(), server_default="20", nullable=False),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "course_id", "semester_number", name="uq_college_semesters_tenant_course_sem"),
    )
    op.create_index("ix_college_semesters_tenant_id", "college_semesters", ["tenant_id"])
    op.execute("ALTER TABLE college_semesters ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY college_semesters_tenant_isolation ON college_semesters
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 7. Create college_batches ─────────────────────────────────────────────
    op.create_table(
        "college_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("start_year", sa.Integer(), nullable=False),
        sa.Column("end_year", sa.Integer(), nullable=False),
        sa.Column("current_semester_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "course_id", "name", name="uq_college_batches_tenant_course_name"),
    )
    op.create_index("ix_college_batches_tenant_id", "college_batches", ["tenant_id"])
    op.execute("ALTER TABLE college_batches ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY college_batches_tenant_isolation ON college_batches
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 8. Enhance sections ───────────────────────────────────────────────────
    op.alter_column("sections", "class_id", nullable=True)
    op.add_column("sections", sa.Column("room_number", sa.String(50), nullable=True))
    op.add_column("sections", sa.Column("class_teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teacher_profiles.id", ondelete="SET NULL"), nullable=True))
    op.add_column("sections", sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=True))
    op.add_column("sections", sa.Column("semester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_semesters.id", ondelete="CASCADE"), nullable=True))
    op.add_column("sections", sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_batches.id", ondelete="CASCADE"), nullable=True))

    # ── 9. Enhance subjects ───────────────────────────────────────────────────
    op.add_column("subjects", sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True))
    op.add_column("subjects", sa.Column("hours_per_week", sa.Integer(), nullable=False, server_default="4"))
    op.add_column("subjects", sa.Column("is_elective", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("subjects", sa.Column("description", sa.Text(), nullable=True))

    # ── 10. Create academic_subject_mappings ──────────────────────────────────
    op.create_table(
        "academic_subject_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=True),
        sa.Column("semester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_semesters.id", ondelete="CASCADE"), nullable=True),
        sa.Column("semester_number", sa.Integer(), nullable=True),
        sa.Column("is_elective", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("credits", sa.Integer(), server_default="3", nullable=False),
        sa.Column("weekly_hours", sa.Integer(), server_default="4", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_academic_subj_map_tenant", "academic_subject_mappings", ["tenant_id"])
    op.create_index("ix_academic_subj_map_session", "academic_subject_mappings", ["tenant_id", "academic_session_id"])
    op.execute("ALTER TABLE academic_subject_mappings ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY academic_subj_map_tenant_isolation ON academic_subject_mappings
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 11. Create teacher_subject_mappings ───────────────────────────────────
    op.create_table(
        "teacher_subject_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teacher_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id", ondelete="CASCADE"), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=True),
        sa.Column("semester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_semesters.id", ondelete="CASCADE"), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_teacher_subj_map_tenant", "teacher_subject_mappings", ["tenant_id"])
    op.create_index("ix_teacher_subj_map_teacher", "teacher_subject_mappings", ["tenant_id", "teacher_id"])
    op.execute("ALTER TABLE teacher_subject_mappings ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY teacher_subj_map_tenant_isolation ON teacher_subject_mappings
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 12. Create student_academic_enrollments (Common Enrollment Model) ─────
    op.create_table(
        "student_academic_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("enrollment_type", sa.String(20), nullable=False),  # SCHOOL | COLLEGE
        sa.Column("enrollment_number", sa.String(100), nullable=False),
        sa.Column("enrollment_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(30), server_default="ACTIVE", nullable=False),
        sa.Column("roll_number", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "enrollment_number", name="uq_student_acad_enr_tenant_number"),
    )
    op.create_index("ix_student_acad_enr_tenant_id", "student_academic_enrollments", ["tenant_id"])
    op.create_index("ix_student_acad_enr_student_session", "student_academic_enrollments", ["tenant_id", "student_id", "academic_session_id"])
    op.execute("ALTER TABLE student_academic_enrollments ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY student_acad_enr_tenant_isolation ON student_academic_enrollments
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 13. Create school_enrollment_details ──────────────────────────────────
    op.create_table(
        "school_enrollment_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enrollment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_academic_enrollments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stream", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "enrollment_id", name="uq_school_enr_det_tenant_enr"),
    )
    op.create_index("ix_school_enr_det_tenant_id", "school_enrollment_details", ["tenant_id"])
    op.execute("ALTER TABLE school_enrollment_details ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY school_enr_det_tenant_isolation ON school_enrollment_details
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 14. Create college_enrollment_details ─────────────────────────────────
    op.create_table(
        "college_enrollment_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enrollment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_academic_enrollments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("faculty_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_faculties.id", ondelete="SET NULL"), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("degree_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_degrees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("semester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_semesters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("year_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("semester_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("specialization", sa.String(150), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "enrollment_id", name="uq_college_enr_det_tenant_enr"),
    )
    op.create_index("ix_college_enr_det_tenant_id", "college_enrollment_details", ["tenant_id"])
    op.execute("ALTER TABLE college_enrollment_details ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY college_enr_det_tenant_isolation ON college_enrollment_details
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 15. Create student_promotions ─────────────────────────────────────────
    op.create_table(
        "student_promotions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("to_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("from_enrollment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_academic_enrollments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("to_enrollment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_academic_enrollments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(30), server_default="PROMOTED", nullable=False),
        sa.Column("promotion_date", sa.Date(), nullable=False),
        sa.Column("remarks", sa.String(500), nullable=True),
        sa.Column("performed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_student_promotions_tenant_id", "student_promotions", ["tenant_id"])
    op.create_index("ix_student_promotions_student", "student_promotions", ["tenant_id", "student_id"])
    op.execute("ALTER TABLE student_promotions ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY student_promotions_tenant_isolation ON student_promotions
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 16. Create academic_hierarchies ───────────────────────────────────────
    op.create_table(
        "academic_hierarchies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution_type", sa.String(30), server_default="SCHOOL", nullable=False),
        sa.Column("academic_system", sa.String(30), server_default="ANNUAL", nullable=False),
        sa.Column("has_departments", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("has_faculties", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("has_batches", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("has_sections", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("grading_system", sa.String(30), server_default="PERCENTAGE", nullable=False),
        sa.Column("pass_percentage", sa.Numeric(5, 2), server_default="40.0", nullable=False),
        sa.Column("allow_cross_department_electives", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("max_electives_per_student", sa.Integer(), server_default="2", nullable=False),
        sa.Column("settings", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", name="uq_academic_hierarchies_tenant"),
    )
    op.create_index("ix_academic_hierarchies_tenant_id", "academic_hierarchies", ["tenant_id"])
    op.execute("ALTER TABLE academic_hierarchies ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY academic_hierarchies_tenant_isolation ON academic_hierarchies
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)


def downgrade() -> None:
    op.drop_table("academic_hierarchies")
    op.drop_table("student_promotions")
    op.drop_table("college_enrollment_details")
    op.drop_table("school_enrollment_details")
    op.drop_table("student_academic_enrollments")
    op.drop_table("teacher_subject_mappings")
    op.drop_table("academic_subject_mappings")
    op.drop_column("subjects", "description")
    op.drop_column("subjects", "is_elective")
    op.drop_column("subjects", "hours_per_week")
    op.drop_column("subjects", "department_id")
    op.drop_column("sections", "batch_id")
    op.drop_column("sections", "semester_id")
    op.drop_column("sections", "course_id")
    op.drop_column("sections", "class_teacher_id")
    op.drop_column("sections", "room_number")
    op.drop_table("college_batches")
    op.drop_table("college_semesters")
    op.drop_column("courses", "coordinator_teacher_id")
    op.drop_column("courses", "duration_years")
    op.drop_column("courses", "degree_id")
    op.drop_column("school_classes", "category")
    op.drop_column("school_classes", "class_teacher_id")
    op.drop_column("departments", "hod_teacher_id")
    op.drop_column("departments", "faculty_id")
    op.drop_table("academic_degrees")
    op.drop_table("academic_faculties")
