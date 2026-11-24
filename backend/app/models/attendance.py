from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModel, TenantBaseModel

if TYPE_CHECKING:
    from app.models.academic import AcademicSession, CollegeSemester, Course, SchoolClass, Section, StudentProfile, Subject, TeacherProfile
    from app.models.user import User


class StudentAttendanceSession(TenantBaseModel):
    """
    Conducted attendance roll call session for a class, section, subject, or period.
    Prevents duplicate sessions via unique constraints and handles total/present/absent metrics.
    """
    __tablename__ = "student_attendance_sessions"

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
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    session_type: Mapped[str] = mapped_column(String(30), default="DAILY", nullable=False)  # DAILY, PERIOD_WISE, SUBJECT_WISE
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
    )
    semester_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_semesters.id", ondelete="CASCADE"),
        nullable=True,
    )
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    period_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    conducted_by_teacher_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    total_students: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    present_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    absent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    late_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leave_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qr_token: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    qr_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="SUBMITTED", nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    academic_session: Mapped["AcademicSession"] = relationship("AcademicSession")
    school_class: Mapped[Optional["SchoolClass"]] = relationship("SchoolClass")
    section: Mapped[Optional["Section"]] = relationship("Section")
    course: Mapped[Optional["Course"]] = relationship("Course")
    semester: Mapped[Optional["CollegeSemester"]] = relationship("CollegeSemester")
    subject: Mapped[Optional["Subject"]] = relationship("Subject")
    conducted_by: Mapped[Optional["TeacherProfile"]] = relationship("TeacherProfile")
    entries: Mapped[List["StudentAttendanceEntry"]] = relationship(
        "StudentAttendanceEntry", back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_student_att_sess_tenant_date", "tenant_id", "session_date"),
        Index("ix_student_att_sess_class_sec", "tenant_id", "class_id", "section_id"),
    )


class StudentAttendanceEntry(BaseModel):
    """
    Individual student attendance record for an attendance session.
    Tracks check-in method (Manual, QR, RFID, Biometric, GPS) and audit trail.
    """
    __tablename__ = "student_attendance_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_attendance_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), default="PRESENT", nullable=False)  # PRESENT, ABSENT, LATE, LEAVE
    late_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    check_in_method: Mapped[str] = mapped_column(String(30), default="MANUAL", nullable=False)  # MANUAL, QR, RFID, BIOMETRIC, GPS
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(9, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    session: Mapped["StudentAttendanceSession"] = relationship("StudentAttendanceSession", back_populates="entries")
    student: Mapped["StudentProfile"] = relationship("StudentProfile")
    correction_logs: Mapped[List["AttendanceCorrectionLog"]] = relationship(
        "AttendanceCorrectionLog", back_populates="entry", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "session_id", "student_id", name="uq_student_att_entry_sess_stu"),
    )


class AttendanceCorrectionLog(Base):
    """
    Audit trail recording changes/corrections made to attendance entries.
    """
    __tablename__ = "attendance_correction_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_attendance_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_status: Mapped[str] = mapped_column(String(20), nullable=False)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    corrected_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    corrected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    entry: Mapped["StudentAttendanceEntry"] = relationship("StudentAttendanceEntry", back_populates="correction_logs")
    corrected_by: Mapped[Optional["User"]] = relationship("User")


class AttendanceDeviceLog(Base):
    """
    Raw hardware and device scans (RFID cards, Biometric terminals, QR scanners, GPS check-ins).
    """
    __tablename__ = "attendance_device_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)  # RFID, BIOMETRIC, QR_SCANNER, GPS
    identifier_tag: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    user_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # STUDENT, TEACHER
    matched_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
