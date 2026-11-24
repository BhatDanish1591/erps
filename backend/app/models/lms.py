from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBaseModel

if TYPE_CHECKING:
    from app.models.academic import (
        Department,
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


class StudyMaterial(TenantBaseModel):
    """
    Learning Management System study material resource.
    Supports PDF uploads, Word documents, PowerPoint presentations, Images,
    Video links, Recorded lectures, Reference materials, and Previous question papers.
    """
    __tablename__ = "study_materials"

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
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    class_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("school_classes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    semester_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_semesters.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_batches.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chapter: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, index=True)

    # Material classification
    material_type: Mapped[str] = mapped_column(
        String(50),
        default="PDF",
        nullable=False,
        index=True,
    )
    # PDF, WORD, POWERPOINT, IMAGE, VIDEO_LINK, RECORDED_LECTURE, REFERENCE_MATERIAL, PREVIOUS_PAPER, OTHER

    category: Mapped[str] = mapped_column(
        String(50),
        default="GENERAL",
        nullable=False,
        index=True,
    )
    # LECTURE_NOTE, SYLLABUS, PAST_PAPER, READING, REFERENCE, LAB_MANUAL, GENERAL

    # Storage fields (S3 / R2 / local)
    file_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    external_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tags: Mapped[Optional[Any]] = mapped_column(JSONB, default=list, nullable=True)

    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Relationships
    uploader: Mapped["User"] = relationship("User", foreign_keys=[uploaded_by], lazy="selectin")
    subject: Mapped[Optional["Subject"]] = relationship("Subject", lazy="selectin")
    academic_session: Mapped["AcademicSession"] = relationship("AcademicSession", lazy="selectin")
    versions: Mapped[List["StudyMaterialVersion"]] = relationship(
        "StudyMaterialVersion",
        back_populates="material",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_materials_tenant_published", "tenant_id", "is_published"),
        Index("ix_materials_tenant_subject", "tenant_id", "subject_id"),
        Index("ix_materials_tenant_class", "tenant_id", "class_id"),
    )


class StudyMaterialVersion(TenantBaseModel):
    """
    Version audit history for revised study materials.
    """
    __tablename__ = "study_material_versions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("study_materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    change_summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    material: Mapped["StudyMaterial"] = relationship("StudyMaterial", back_populates="versions")
    uploader: Mapped["User"] = relationship("User", foreign_keys=[uploaded_by], lazy="selectin")


class Assignment(TenantBaseModel):
    """
    LMS Assignment created by teacher/admin with deadline, file attachments,
    passing criteria, and late submission rules.
    """
    __tablename__ = "assignments"

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
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    class_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("school_classes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    semester_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_semesters.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    instructions_file_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    instructions_file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    instructions_file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    due_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    allow_late_submission: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    late_penalty_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)

    total_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("100.00"), nullable=False)
    passing_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("40.00"), nullable=False)

    status: Mapped[str] = mapped_column(String(30), default="PUBLISHED", nullable=False, index=True)
    # DRAFT, PUBLISHED, CLOSED, ARCHIVED

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Relationships
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by], lazy="selectin")
    subject: Mapped[Optional["Subject"]] = relationship("Subject", lazy="selectin")
    academic_session: Mapped["AcademicSession"] = relationship("AcademicSession", lazy="selectin")
    submissions: Mapped[List["AssignmentSubmission"]] = relationship(
        "AssignmentSubmission",
        back_populates="assignment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_assignments_tenant_status", "tenant_id", "status"),
        Index("ix_assignments_tenant_due", "tenant_id", "due_datetime"),
    )


class AssignmentSubmission(TenantBaseModel):
    """
    Student response to an assignment, including text content, uploaded files,
    late flags, teacher score, and evaluation feedback.
    """
    __tablename__ = "assignment_submissions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    submission_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attachment_file_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    attachment_file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    attachment_file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    marks_obtained: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    teacher_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    evaluated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="SUBMITTED", nullable=False, index=True)
    # SUBMITTED, EVALUATED, RESUBMISSION_REQUESTED

    # Relationships
    assignment: Mapped["Assignment"] = relationship("Assignment", back_populates="submissions")
    student: Mapped["StudentProfile"] = relationship("StudentProfile", lazy="selectin")
    evaluator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[evaluated_by], lazy="selectin")

    __table_args__ = (
        UniqueConstraint("tenant_id", "assignment_id", "student_id", name="uq_assignment_student_submission"),
        Index("ix_submissions_tenant_assignment", "tenant_id", "assignment_id"),
        Index("ix_submissions_tenant_student", "tenant_id", "student_id"),
    )
