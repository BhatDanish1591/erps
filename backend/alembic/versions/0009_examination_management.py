"""examination_management

Revision ID: 0009_examination_management
Revises: 0008_attendance_management
Create Date: 2026-11-19 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0009_examination_management"
down_revision: Union[str, None] = "0008_attendance_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create question_bank ───────────────────────────────────────────────
    op.create_table(
        "question_bank",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category", sa.String(100), nullable=False, server_default="General"),
        sa.Column("difficulty", sa.String(20), nullable=False, server_default="MEDIUM"),  # EASY, MEDIUM, HARD
        sa.Column("question_type", sa.String(30), nullable=False),  # MCQ, MULTIPLE_SELECT, TRUE_FALSE, SHORT_ANSWER, LONG_ANSWER, FILL_IN_THE_BLANKS, MATCHING, NUMERICAL, FILE_UPLOAD
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(), nullable=True),
        sa.Column("correct_answer", postgresql.JSONB(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("rubric", postgresql.JSONB(), nullable=True),
        sa.Column("default_marks", sa.Numeric(6, 2), nullable=False, server_default="1.00"),
        sa.Column("default_negative_marks", sa.Numeric(6, 2), nullable=False, server_default="0.00"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_question_bank_tenant", "question_bank", ["tenant_id"])
    op.create_index("ix_question_bank_subject", "question_bank", ["tenant_id", "subject_id"])
    op.create_index("ix_question_bank_category", "question_bank", ["tenant_id", "category"])
    op.create_index("ix_question_bank_type", "question_bank", ["tenant_id", "question_type"])
    op.execute("ALTER TABLE question_bank ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY question_bank_tenant_isolation ON question_bank
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 2. Create examinations ───────────────────────────────────────────────
    op.create_table(
        "examinations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("exam_type", sa.String(50), nullable=False),  # DAILY_TEST, WEEKLY_TEST, MONTHLY_TEST, UNIT_TEST, MID_TERM, FINAL_EXAM, SEMESTER_EXAM, PRACTICAL, MOCK_TEST, ONLINE_MCQ, OFFLINE
        sa.Column("mode", sa.String(20), nullable=False, server_default="ONLINE"),  # ONLINE, OFFLINE, HYBRID
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id", ondelete="CASCADE"), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=True),
        sa.Column("semester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_semesters.id", ondelete="CASCADE"), nullable=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_batches.id", ondelete="CASCADE"), nullable=True),
        sa.Column("total_marks", sa.Numeric(6, 2), nullable=False, server_default="100.00"),
        sa.Column("passing_marks", sa.Numeric(6, 2), nullable=False, server_default="40.00"),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("start_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shuffle_questions", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("shuffle_options", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("allow_late_submission", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("late_submission_grace_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),  # DRAFT, SCHEDULED, ONGOING, COMPLETED, ARCHIVED
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_results_published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("results_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_examinations_tenant", "examinations", ["tenant_id"])
    op.create_index("ix_examinations_session", "examinations", ["tenant_id", "academic_session_id"])
    op.create_index("ix_examinations_type", "examinations", ["tenant_id", "exam_type"])
    op.create_index("ix_examinations_status", "examinations", ["tenant_id", "status"])
    op.execute("ALTER TABLE examinations ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY examinations_tenant_isolation ON examinations
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 3. Create examination_questions ───────────────────────────────────────
    op.create_table(
        "examination_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("question_bank.id", ondelete="SET NULL"), nullable=True),
        sa.Column("custom_question_text", sa.Text(), nullable=True),
        sa.Column("custom_options", postgresql.JSONB(), nullable=True),
        sa.Column("custom_correct_answer", postgresql.JSONB(), nullable=True),
        sa.Column("custom_explanation", sa.Text(), nullable=True),
        sa.Column("question_type", sa.String(30), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("marks", sa.Numeric(6, 2), nullable=False, server_default="1.00"),
        sa.Column("negative_marks", sa.Numeric(6, 2), nullable=False, server_default="0.00"),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_exam_questions_tenant", "examination_questions", ["tenant_id"])
    op.create_index("ix_exam_questions_exam", "examination_questions", ["tenant_id", "exam_id"])
    op.execute("ALTER TABLE examination_questions ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY exam_questions_tenant_isolation ON examination_questions
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 4. Create student_exam_attempts ───────────────────────────────────────
    op.create_table(
        "student_exam_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="IN_PROGRESS"),  # IN_PROGRESS, SUBMITTED, EVALUATED, EXPIRED, CANCELLED
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("is_passed", sa.Boolean(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("submission_hash", sa.String(64), nullable=True),
        sa.Column("question_order", postgresql.JSONB(), nullable=True),  # randomized question IDs order for this attempt
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_exam_attempts_tenant", "student_exam_attempts", ["tenant_id"])
    op.create_index("ix_exam_attempts_exam_student", "student_exam_attempts", ["tenant_id", "exam_id", "student_id"])
    op.create_index("ix_exam_attempts_status", "student_exam_attempts", ["tenant_id", "status"])
    op.execute("ALTER TABLE student_exam_attempts ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY exam_attempts_tenant_isolation ON student_exam_attempts
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 5. Create student_exam_answers ────────────────────────────────────────
    op.create_table(
        "student_exam_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_exam_attempts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_question_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("examination_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_answer", postgresql.JSONB(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("marks_awarded", sa.Numeric(6, 2), nullable=True),
        sa.Column("teacher_feedback", sa.Text(), nullable=True),
        sa.Column("is_evaluated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("evaluated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_autosaved_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_exam_answers_tenant", "student_exam_answers", ["tenant_id"])
    op.create_index("ix_exam_answers_attempt", "student_exam_answers", ["tenant_id", "attempt_id"])
    op.create_index("ix_exam_answers_attempt_q", "student_exam_answers", ["tenant_id", "attempt_id", "exam_question_id"], unique=True)
    op.execute("ALTER TABLE student_exam_answers ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY exam_answers_tenant_isolation ON student_exam_answers
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 6. Create exam_audit_logs ─────────────────────────────────────────────
    op.create_table(
        "exam_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_exam_attempts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_exam_audit_logs_tenant", "exam_audit_logs", ["tenant_id"])
    op.create_index("ix_exam_audit_logs_attempt", "exam_audit_logs", ["tenant_id", "attempt_id"])
    op.execute("ALTER TABLE exam_audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY exam_audit_logs_tenant_isolation ON exam_audit_logs
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)


def downgrade() -> None:
    op.drop_table("exam_audit_logs")
    op.drop_table("student_exam_answers")
    op.drop_table("student_exam_attempts")
    op.drop_table("examination_questions")
    op.drop_table("examinations")
    op.drop_table("question_bank")
