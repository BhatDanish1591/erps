from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, List, Optional
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModel, TenantBaseModel

if TYPE_CHECKING:
    from app.models.academic import (
        AcademicSession,
        CollegeBatch,
        CollegeSemester,
        Course,
        SchoolClass,
        Section,
        StudentProfile,
        Subject,
    )
    from app.models.user import User


class QuestionBank(TenantBaseModel):
    """
    Reusable question bank supporting multi-format questions:
    MCQ, MULTIPLE_SELECT, TRUE_FALSE, SHORT_ANSWER, LONG_ANSWER,
    FILL_IN_THE_BLANKS, MATCHING, NUMERICAL, FILE_UPLOAD.
    """
    __tablename__ = "question_bank"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(100), default="General", nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)  # EASY, MEDIUM, HARD
    question_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    correct_answer: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rubric: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    default_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("1.00"), nullable=False)
    default_negative_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    subject: Mapped[Optional["Subject"]] = relationship(foreign_keys=[subject_id], lazy="selectin")
    creator: Mapped[Optional["User"]] = relationship(foreign_keys=[created_by], lazy="selectin")


class Examination(TenantBaseModel):
    """
    Scheduled or ad-hoc examination entity for schools and colleges.
    Handles scheduling, target class/section/course, passing criteria, duration, and status.
    """
    __tablename__ = "examinations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    exam_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # DAILY_TEST, WEEKLY_TEST, MONTHLY_TEST, UNIT_TEST, MID_TERM, FINAL_EXAM, SEMESTER_EXAM, PRACTICAL, MOCK_TEST, ONLINE_MCQ, OFFLINE
    mode: Mapped[str] = mapped_column(String(20), default="ONLINE", nullable=False)  # ONLINE, OFFLINE, HYBRID

    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
    )
    class_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("school_classes.id", ondelete="CASCADE"),
        nullable=True,
    )
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=True,
    )
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True,
    )
    semester_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_semesters.id", ondelete="CASCADE"),
        nullable=True,
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_batches.id", ondelete="CASCADE"),
        nullable=True,
    )

    total_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("100.00"), nullable=False)
    passing_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("40.00"), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    start_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    shuffle_options: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_late_submission: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    late_submission_grace_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False, index=True)
    # DRAFT, SCHEDULED, ONGOING, COMPLETED, ARCHIVED
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_results_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    results_published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    academic_session: Mapped["AcademicSession"] = relationship(foreign_keys=[academic_session_id], lazy="selectin")
    subject: Mapped[Optional["Subject"]] = relationship(foreign_keys=[subject_id], lazy="selectin")
    school_class: Mapped[Optional["SchoolClass"]] = relationship(foreign_keys=[class_id], lazy="selectin")
    section: Mapped[Optional["Section"]] = relationship(foreign_keys=[section_id], lazy="selectin")
    course: Mapped[Optional["Course"]] = relationship(foreign_keys=[course_id], lazy="selectin")
    semester: Mapped[Optional["CollegeSemester"]] = relationship(foreign_keys=[semester_id], lazy="selectin")
    batch: Mapped[Optional["CollegeBatch"]] = relationship(foreign_keys=[batch_id], lazy="selectin")
    questions: Mapped[List["ExaminationQuestion"]] = relationship(
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="ExaminationQuestion.order_index",
        lazy="selectin",
    )
    attempts: Mapped[List["StudentExamAttempt"]] = relationship(back_populates="exam", cascade="all, delete-orphan")


class ExaminationQuestion(TenantBaseModel):
    """
    Associates questions (from question_bank or custom defined) with an examination.
    Contains marks, negative_marks, and order_index for this specific exam.
    """
    __tablename__ = "examination_questions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("examinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("question_bank.id", ondelete="SET NULL"),
        nullable=True,
    )
    custom_question_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_options: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    custom_correct_answer: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    custom_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    question_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("1.00"), nullable=False)
    negative_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    exam: Mapped["Examination"] = relationship(back_populates="questions")
    bank_question: Mapped[Optional["QuestionBank"]] = relationship(foreign_keys=[question_id], lazy="selectin")

    @property
    def effective_question_text(self) -> str:
        if self.custom_question_text:
            return self.custom_question_text
        if self.bank_question:
            return self.bank_question.question_text
        return ""

    @property
    def effective_options(self) -> Optional[Any]:
        if self.custom_options is not None:
            return self.custom_options
        if self.bank_question:
            return self.bank_question.options
        return None

    @property
    def effective_correct_answer(self) -> Optional[Any]:
        if self.custom_correct_answer is not None:
            return self.custom_correct_answer
        if self.bank_question:
            return self.bank_question.correct_answer
        return None

    @property
    def effective_explanation(self) -> Optional[str]:
        if self.custom_explanation is not None:
            return self.custom_explanation
        if self.bank_question:
            return self.bank_question.explanation
        return None

    @property
    def effective_question_type(self) -> str:
        if self.question_type:
            return self.question_type
        if self.bank_question:
            return self.bank_question.question_type
        return "MCQ"


class StudentExamAttempt(TenantBaseModel):
    """
    Student test session lifecycle.
    Tracks server-side countdown timer, autosave, submission, idempotency, and grading.
    """
    __tablename__ = "student_exam_attempts"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("examinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="IN_PROGRESS", nullable=False, index=True)
    # IN_PROGRESS, SUBMITTED, EVALUATED, EXPIRED, CANCELLED

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    total_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    is_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submission_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    question_order: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    # Relationships
    exam: Mapped["Examination"] = relationship(back_populates="attempts", lazy="selectin")
    student: Mapped["StudentProfile"] = relationship(foreign_keys=[student_id], lazy="selectin")
    answers: Mapped[List["StudentExamAnswer"]] = relationship(
        back_populates="attempt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    audit_logs: Mapped[List["ExamAuditLog"]] = relationship(
        back_populates="attempt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class StudentExamAnswer(TenantBaseModel):
    """
    Individual question response by a student, with auto-graded or manual-graded score.
    """
    __tablename__ = "student_exam_answers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "attempt_id", "exam_question_id", name="uq_attempt_question_answer"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_exam_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exam_question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("examination_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_answer: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    marks_awarded: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    teacher_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_evaluated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evaluated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_autosaved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    # Relationships
    attempt: Mapped["StudentExamAttempt"] = relationship(back_populates="answers")
    exam_question: Mapped["ExaminationQuestion"] = relationship(foreign_keys=[exam_question_id], lazy="selectin")


class ExamAuditLog(Base):
    """
    Security audit trails for online exam sessions:
    records start, autosave checkpoints, tab switch warnings, timeouts, and grading actions.
    """
    __tablename__ = "exam_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_exam_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_payload: Mapped[Any] = mapped_column(JSONB, default=dict, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    attempt: Mapped["StudentExamAttempt"] = relationship(back_populates="audit_logs")
