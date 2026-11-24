"""results_and_report_cards

Revision ID: 0010_results_and_report_cards
Revises: 0009_examination_management
Create Date: 2026-11-19 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0010_results_and_report_cards"
down_revision: Union[str, None] = "0009_examination_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create grading_scales ──────────────────────────────────────────────
    op.create_table(
        "grading_scales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("scale_type", sa.String(50), nullable=False, server_default="CBSE_9_POINT"),  # CBSE_9_POINT, CGPA_10_POINT, GPA_4_POINT, PERCENTAGE_PASS_FAIL, CUSTOM
        sa.Column("grades", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_grading_scales_tenant", "grading_scales", ["tenant_id"])
    op.execute("ALTER TABLE grading_scales ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY grading_scales_tenant_isolation ON grading_scales
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 2. Create student_subject_results ─────────────────────────────────────
    op.create_table(
        "student_subject_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id", ondelete="CASCADE"), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=True),
        sa.Column("semester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_semesters.id", ondelete="CASCADE"), nullable=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_batches.id", ondelete="CASCADE"), nullable=True),
        sa.Column("theory_marks", sa.Numeric(6, 2), nullable=False, server_default="0.00"),
        sa.Column("theory_max_marks", sa.Numeric(6, 2), nullable=False, server_default="70.00"),
        sa.Column("practical_marks", sa.Numeric(6, 2), nullable=False, server_default="0.00"),
        sa.Column("practical_max_marks", sa.Numeric(6, 2), nullable=False, server_default="20.00"),
        sa.Column("internal_marks", sa.Numeric(6, 2), nullable=False, server_default="0.00"),
        sa.Column("internal_max_marks", sa.Numeric(6, 2), nullable=False, server_default="10.00"),
        sa.Column("assignment_marks", sa.Numeric(6, 2), nullable=False, server_default="0.00"),
        sa.Column("assignment_max_marks", sa.Numeric(6, 2), nullable=False, server_default="0.00"),
        sa.Column("total_marks", sa.Numeric(6, 2), nullable=False, server_default="0.00"),
        sa.Column("max_marks", sa.Numeric(6, 2), nullable=False, server_default="100.00"),
        sa.Column("percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("grade", sa.String(10), nullable=True),
        sa.Column("grade_point", sa.Numeric(4, 2), nullable=False, server_default="0.00"),
        sa.Column("credits", sa.Numeric(4, 1), nullable=False, server_default="3.0"),
        sa.Column("credit_points", sa.Numeric(6, 2), nullable=False, server_default="0.00"),
        sa.Column("is_passed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),  # DRAFT, SUBMITTED, IN_REVIEW, APPROVED, PUBLISHED
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("entered_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "student_id", "exam_id", "subject_id", name="uq_student_exam_subject_result"),
    )
    op.create_index("ix_stu_subj_res_tenant", "student_subject_results", ["tenant_id"])
    op.create_index("ix_stu_subj_res_exam", "student_subject_results", ["tenant_id", "exam_id"])
    op.create_index("ix_stu_subj_res_student", "student_subject_results", ["tenant_id", "student_id"])
    op.create_index("ix_stu_subj_res_status", "student_subject_results", ["tenant_id", "status"])
    op.execute("ALTER TABLE student_subject_results ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY stu_subj_res_tenant_isolation ON student_subject_results
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 3. Create student_term_results ────────────────────────────────────────
    op.create_table(
        "student_term_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id", ondelete="CASCADE"), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=True),
        sa.Column("semester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_semesters.id", ondelete="CASCADE"), nullable=True),
        sa.Column("total_obtained", sa.Numeric(7, 2), nullable=False, server_default="0.00"),
        sa.Column("total_max", sa.Numeric(7, 2), nullable=False, server_default="100.00"),
        sa.Column("overall_percentage", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("overall_grade", sa.String(10), nullable=False, server_default="F"),
        sa.Column("cgpa", sa.Numeric(4, 2), nullable=True),
        sa.Column("sgpa", sa.Numeric(4, 2), nullable=True),
        sa.Column("total_credits", sa.Numeric(5, 1), nullable=False, server_default="0.0"),
        sa.Column("earned_credits", sa.Numeric(5, 1), nullable=False, server_default="0.0"),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("is_passed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("attendance_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("total_attendance_days", sa.Integer(), nullable=True),
        sa.Column("present_days", sa.Integer(), nullable=True),
        sa.Column("approval_status", sa.String(30), nullable=False, server_default="DRAFT"),  # DRAFT, SUBMITTED, IN_REVIEW, APPROVED, PUBLISHED
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "student_id", "exam_id", name="uq_student_term_result"),
    )
    op.create_index("ix_stu_term_res_tenant", "student_term_results", ["tenant_id"])
    op.create_index("ix_stu_term_res_exam", "student_term_results", ["tenant_id", "exam_id"])
    op.create_index("ix_stu_term_res_student", "student_term_results", ["tenant_id", "student_id"])
    op.create_index("ix_stu_term_res_status", "student_term_results", ["tenant_id", "approval_status"])
    op.execute("ALTER TABLE student_term_results ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY stu_term_res_tenant_isolation ON student_term_results
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 4. Create result_revision_history ─────────────────────────────────────
    op.create_table(
        "result_revision_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_subject_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_marks", postgresql.JSONB(), nullable=False),
        sa.Column("new_marks", postgresql.JSONB(), nullable=False),
        sa.Column("revision_reason", sa.Text(), nullable=False),
        sa.Column("modified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_res_rev_hist_tenant", "result_revision_history", ["tenant_id"])
    op.create_index("ix_res_rev_hist_result", "result_revision_history", ["tenant_id", "subject_result_id"])
    op.execute("ALTER TABLE result_revision_history ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY res_rev_hist_tenant_isolation ON result_revision_history
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 5. Create re_evaluation_requests ──────────────────────────────────────
    op.create_table(
        "re_evaluation_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_subject_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),  # PENDING, UNDER_REVIEW, APPROVED_UPDATED, REJECTED
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewer_remarks", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_reeval_req_tenant", "re_evaluation_requests", ["tenant_id"])
    op.create_index("ix_reeval_req_student", "re_evaluation_requests", ["tenant_id", "student_id"])
    op.create_index("ix_reeval_req_status", "re_evaluation_requests", ["tenant_id", "status"])
    op.execute("ALTER TABLE re_evaluation_requests ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY reeval_req_tenant_isolation ON re_evaluation_requests
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 6. Create report_card_templates ───────────────────────────────────────
    op.create_table(
        "report_card_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("header_title", sa.String(255), nullable=False, server_default="ACADEMIC REPORT CARD"),
        sa.Column("show_attendance", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("show_signatures", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("show_ranks", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("custom_footer", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_report_card_temp_tenant", "report_card_templates", ["tenant_id"])
    op.execute("ALTER TABLE report_card_templates ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY report_card_temp_tenant_isolation ON report_card_templates
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)


def downgrade() -> None:
    op.drop_table("report_card_templates")
    op.drop_table("re_evaluation_requests")
    op.drop_table("result_revision_history")
    op.drop_table("student_term_results")
    op.drop_table("student_subject_results")
    op.drop_table("grading_scales")
