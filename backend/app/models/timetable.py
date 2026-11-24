from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TenantBaseModel


class TimetableSetting(BaseModel):
    """
    Institution-wide or session-level timetable parameters:
    working days, bell schedules, period lengths, break and lunch timings.
    """
    __tablename__ = "timetable_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    working_days: Mapped[List[str]] = mapped_column(
        JSONB,
        default=lambda: ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"],
        nullable=False,
    )
    periods_per_day: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    period_duration_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    break_duration_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    lunch_duration_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    school_start_time: Mapped[str] = mapped_column(String(10), default="08:30", nullable=False)

    academic_session: Mapped["AcademicSession"] = relationship("AcademicSession")

    __table_args__ = (
        UniqueConstraint("tenant_id", "academic_session_id", name="uq_timetable_settings_tenant_session"),
    )


class TimetablePeriod(BaseModel):
    """
    Configured period / bell slot (e.g. Period 1, Assembly, Recess, Lunch, Practical Block).
    """
    __tablename__ = "timetable_periods"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    period_type: Mapped[str] = mapped_column(
        String(30), default="ACADEMIC", nullable=False
    )  # ACADEMIC, PRACTICAL, ASSEMBLY, BREAK, LUNCH, EXAM
    start_time: Mapped[str] = mapped_column(String(10), nullable=False)
    end_time: Mapped[str] = mapped_column(String(10), nullable=False)
    is_break: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    academic_session: Mapped["AcademicSession"] = relationship("AcademicSession")


class TimetableHoliday(BaseModel):
    """
    Institutional, national, or vacation calendar event.
    """
    __tablename__ = "timetable_holidays"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    holiday_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    holiday_type: Mapped[str] = mapped_column(
        String(50), default="NATIONAL", nullable=False
    )  # NATIONAL, FESTIVAL, VACATION, INSTITUTIONAL
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_half_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    academic_session: Mapped["AcademicSession"] = relationship("AcademicSession")


class TimetableSchedule(TenantBaseModel):
    """
    Timetable schedule version container for school/college.
    Lifecycle: DRAFT -> PUBLISHED -> ARCHIVED.
    """
    __tablename__ = "timetable_schedules"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    institution_type: Mapped[str] = mapped_column(String(20), default="SCHOOL", nullable=False)  # SCHOOL, COLLEGE
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="DRAFT", nullable=False, index=True
    )  # DRAFT, PUBLISHED, ARCHIVED
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    academic_session: Mapped["AcademicSession"] = relationship("AcademicSession")
    publisher: Mapped[Optional["User"]] = relationship("User")
    entries: Mapped[List["TimetableEntry"]] = relationship("TimetableEntry", back_populates="schedule", cascade="all, delete-orphan")


class SubstituteTeacherAssignment(BaseModel):
    """
    Daily substitute teacher assignment for an absent faculty member on a specific slot.
    """
    __tablename__ = "substitute_teacher_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timetable_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("timetable_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    original_teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    substitute_teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="ASSIGNED", nullable=False
    )  # ASSIGNED, CONFIRMED, CANCELLED

    timetable_entry: Mapped["TimetableEntry"] = relationship("TimetableEntry", back_populates="substitute_assignments")
    original_teacher: Mapped["TeacherProfile"] = relationship("TeacherProfile", foreign_keys=[original_teacher_id])
    substitute_teacher: Mapped["TeacherProfile"] = relationship("TeacherProfile", foreign_keys=[substitute_teacher_id])
    assigner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_by])
