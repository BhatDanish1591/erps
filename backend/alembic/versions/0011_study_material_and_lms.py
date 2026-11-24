"""study_material_and_lms

Revision ID: 0011_study_material_and_lms
Revises: 0010_results_and_report_cards
Create Date: 2026-11-19 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0011_study_material_and_lms"
down_revision: Union[str, None] = "0010_results_and_report_cards"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create study_materials ─────────────────────────────────────────────
    op.create_table(
        "study_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id", ondelete="CASCADE"), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=True),
        sa.Column("semester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_semesters.id", ondelete="CASCADE"), nullable=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_batches.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("chapter", sa.String(150), nullable=True),
        sa.Column("material_type", sa.String(50), nullable=False, server_default="PDF"),
        sa.Column("category", sa.String(50), nullable=False, server_default="GENERAL"),
        sa.Column("file_key", sa.String(512), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("external_url", sa.String(1024), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tags", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_study_materials_tenant_id", "study_materials", ["tenant_id"])
    op.create_index("ix_study_materials_session_id", "study_materials", ["academic_session_id"])
    op.create_index("ix_study_materials_subject_id", "study_materials", ["subject_id"])
    op.create_index("ix_study_materials_class_id", "study_materials", ["class_id"])
    op.create_index("ix_study_materials_is_published", "study_materials", ["is_published"])

    op.execute("ALTER TABLE study_materials ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_study_materials ON study_materials
        FOR ALL USING (
            tenant_id::text = current_setting('app.current_tenant_id', true)
            OR current_setting('app.is_super_admin', true) = 'true'
        );
        """
    )

    # ── 2. Create study_material_versions ─────────────────────────────────────
    op.create_table(
        "study_material_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("study_materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_key", sa.String(512), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("change_summary", sa.String(500), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_study_material_versions_tenant_id", "study_material_versions", ["tenant_id"])
    op.create_index("ix_study_material_versions_material_id", "study_material_versions", ["material_id"])

    op.execute("ALTER TABLE study_material_versions ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_study_material_versions ON study_material_versions
        FOR ALL USING (
            tenant_id::text = current_setting('app.current_tenant_id', true)
            OR current_setting('app.is_super_admin', true) = 'true'
        );
        """
    )

    # ── 3. Create assignments ─────────────────────────────────────────────────
    op.create_table(
        "assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id", ondelete="CASCADE"), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=True),
        sa.Column("semester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_semesters.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("instructions_file_key", sa.String(512), nullable=True),
        sa.Column("instructions_file_name", sa.String(255), nullable=True),
        sa.Column("instructions_file_size", sa.BigInteger(), nullable=True),
        sa.Column("due_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("allow_late_submission", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("late_penalty_percent", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("total_marks", sa.Numeric(6, 2), nullable=False, server_default="100.00"),
        sa.Column("passing_marks", sa.Numeric(6, 2), nullable=False, server_default="40.00"),
        sa.Column("status", sa.String(30), nullable=False, server_default="PUBLISHED"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_assignments_tenant_id", "assignments", ["tenant_id"])
    op.create_index("ix_assignments_session_id", "assignments", ["academic_session_id"])
    op.create_index("ix_assignments_subject_id", "assignments", ["subject_id"])
    op.create_index("ix_assignments_class_id", "assignments", ["class_id"])
    op.create_index("ix_assignments_status", "assignments", ["status"])
    op.create_index("ix_assignments_due_datetime", "assignments", ["due_datetime"])

    op.execute("ALTER TABLE assignments ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_assignments ON assignments
        FOR ALL USING (
            tenant_id::text = current_setting('app.current_tenant_id', true)
            OR current_setting('app.is_super_admin', true) = 'true'
        );
        """
    )

    # ── 4. Create assignment_submissions ──────────────────────────────────────
    op.create_table(
        "assignment_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("submission_text", sa.Text(), nullable=True),
        sa.Column("attachment_file_key", sa.String(512), nullable=True),
        sa.Column("attachment_file_name", sa.String(255), nullable=True),
        sa.Column("attachment_file_size", sa.BigInteger(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_late", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("marks_obtained", sa.Numeric(6, 2), nullable=True),
        sa.Column("grade", sa.String(20), nullable=True),
        sa.Column("teacher_feedback", sa.Text(), nullable=True),
        sa.Column("evaluated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="SUBMITTED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.UniqueConstraint("tenant_id", "assignment_id", "student_id", name="uq_assignment_student_submission"),
    )
    op.create_index("ix_assignment_submissions_tenant_id", "assignment_submissions", ["tenant_id"])
    op.create_index("ix_assignment_submissions_assignment_id", "assignment_submissions", ["assignment_id"])
    op.create_index("ix_assignment_submissions_student_id", "assignment_submissions", ["student_id"])
    op.create_index("ix_assignment_submissions_status", "assignment_submissions", ["status"])

    op.execute("ALTER TABLE assignment_submissions ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_assignment_submissions ON assignment_submissions
        FOR ALL USING (
            tenant_id::text = current_setting('app.current_tenant_id', true)
            OR current_setting('app.is_super_admin', true) = 'true'
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_assignment_submissions ON assignment_submissions;")
    op.drop_table("assignment_submissions")

    op.execute("DROP POLICY IF EXISTS tenant_isolation_assignments ON assignments;")
    op.drop_table("assignments")

    op.execute("DROP POLICY IF EXISTS tenant_isolation_study_material_versions ON study_material_versions;")
    op.drop_table("study_material_versions")

    op.execute("DROP POLICY IF EXISTS tenant_isolation_study_materials ON study_materials;")
    op.drop_table("study_materials")
