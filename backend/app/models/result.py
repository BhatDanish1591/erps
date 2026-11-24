from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantBaseModel

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
    from app.models.examination import Examination
    from app.models.user import User


class GradingScale(TenantBaseModel):
    """
    Configurable grading system supporting school letter scales (CBSE, state boards)
    and college 10-point / 4-point GPA and CGPA systems.
    """
    __tablename__ = "grading_scales"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    scale_type: Mapped[str] = mapped_column(String(50), default="CBSE_9_POINT", nullable=False)
    # CBSE_9_POINT, CGPA_10_POINT, GPA_4_POINT, PERCENTAGE_PASS_FAIL, CUSTOM
    grades: Mapped[Any] = mapped_column(JSONB, default=list, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class StudentSubjectResult(TenantBaseModel):
    """
    Subject-wise assessment entry breaking down theory, practical, internal,
    and assignment marks, with automated grade point & credit calculation.
    """
    __tablename__ = "student_subject_results"
    __table_args__ = (
        UniqueConstraint("tenant_id", "student_id", "exam_id", "subject_id", name="uq_student_exam_subject_result"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("examinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
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

    theory_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), nullable=False)
    theory_max_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("70.00"), nullable=False)
    practical_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), nullable=False)
    practical_max_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("20.00"), nullable=False)
    internal_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), nullable=False)
    internal_max_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("10.00"), nullable=False)
    assignment_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), nullable=False)
    assignment_max_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), nullable=False)

    total_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), nullable=False)
    max_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("100.00"), nullable=False)
    percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    grade_point: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.00"), nullable=False)
    credits: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=Decimal("3.0"), nullable=False)
    credit_points: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), nullable=False)
    is_passed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    status: Mapped[str] = mapped_column(String(30), default="DRAFT", nullable=False, index=True)
    # DRAFT, SUBMITTED, IN_REVIEW, APPROVED, PUBLISHED
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entered_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    student: Mapped["StudentProfile"] = relationship(foreign_keys=[student_id], lazy="selectin")
    exam: Mapped["Examination"] = relationship(foreign_keys=[exam_id], lazy="selectin")
    subject: Mapped["Subject"] = relationship(foreign_keys=[subject_id], lazy="selectin")
    revisions: Mapped[List["ResultRevisionHistory"]] = relationship(
        back_populates="subject_result",
        cascade="all, delete-orphan",
        order_by="ResultRevisionHistory.modified_at.desc()",
        lazy="selectin",
    )


class StudentTermResult(TenantBaseModel):
    """
    Cumulative examination/term performance card.
    Computes total obtained marks, overall percentage, CGPA/SGPA, rank, and attendance summary.
    """
    __tablename__ = "student_term_results"
    __table_args__ = (
        UniqueConstraint("tenant_id", "student_id", "exam_id", name="uq_student_term_result"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("examinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="RESTRICT"),
        nullable=False,
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

    total_obtained: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=Decimal("0.00"), nullable=False)
    total_max: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=Decimal("100.00"), nullable=False)
    overall_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    overall_grade: Mapped[str] = mapped_column(String(10), default="F", nullable=False)
    cgpa: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2), nullable=True)
    sgpa: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2), nullable=True)
    total_credits: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=Decimal("0.0"), nullable=False)
    earned_credits: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=Decimal("0.0"), nullable=False)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_passed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    attendance_percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    total_attendance_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    present_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    approval_status: Mapped[str] = mapped_column(String(30), default="DRAFT", nullable=False, index=True)
    # DRAFT, SUBMITTED, IN_REVIEW, APPROVED, PUBLISHED
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    student: Mapped["StudentProfile"] = relationship(foreign_keys=[student_id], lazy="selectin")
    exam: Mapped["Examination"] = relationship(foreign_keys=[exam_id], lazy="selectin")
    academic_session: Mapped["AcademicSession"] = relationship(foreign_keys=[academic_session_id], lazy="selectin")


class ResultRevisionHistory(Base):
    """
    Immutable audit ledger tracking every marks revision post-submission/publication,
    recording previous values, new values, modification reason, and authorized reviewer.
    """
    __tablename__ = "result_revision_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_subject_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_marks: Mapped[Any] = mapped_column(JSONB, nullable=False)
    new_marks: Mapped[Any] = mapped_column(JSONB, nullable=False)
    revision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    modified_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    subject_result: Mapped["StudentSubjectResult"] = relationship(back_populates="revisions")
    modifier: Mapped["User"] = relationship(foreign_keys=[modified_by], lazy="selectin")
    approver: Mapped[Optional["User"]] = relationship(foreign_keys=[approved_by], lazy="selectin")


class ReEvaluationRequest(TenantBaseModel):
    """
    Student or parent appeal for marks re-checking and scrutiny.
    """
    __tablename__ = "re_evaluation_requests"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_subject_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False, index=True)
    # PENDING, UNDER_REVIEW, APPROVED_UPDATED, REJECTED
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewer_remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    subject_result: Mapped["StudentSubjectResult"] = relationship(lazy="selectin")
    student: Mapped["StudentProfile"] = relationship(lazy="selectin")
    requester: Mapped["User"] = relationship(foreign_keys=[requested_by], lazy="selectin")
    reviewer: Mapped[Optional["User"]] = relationship(foreign_keys=[reviewer_id], lazy="selectin")


class ReportCardTemplate(TenantBaseModel):
    """
    Institution-branded template configurations for downloadable PDF report cards.
    """
    __tablename__ = "report_card_templates"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    header_title: Mapped[str] = mapped_column(String(255), default="ACADEMIC REPORT CARD", nullable=False)
    show_attendance: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_signatures: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_ranks: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    custom_footer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
