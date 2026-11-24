from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import (
    AcademicSession,
    CollegeBatch,
    CollegeSemester,
    Course,
    Department,
    SchoolClass,
    Section,
    TeacherProfile,
    TimetableEntry,
)
from app.models.timetable import (
    SubstituteTeacherAssignment,
    TimetableHoliday,
    TimetablePeriod,
    TimetableSchedule,
    TimetableSetting,
)
from app.models.user import User


class TimetableRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Settings & Periods
    # ─────────────────────────────────────────────────────────────────────────

    async def get_or_create_settings(
        self, tenant_id: uuid.UUID, academic_session_id: uuid.UUID
    ) -> TimetableSetting:
        stmt = select(TimetableSetting).where(
            TimetableSetting.tenant_id == tenant_id,
            TimetableSetting.academic_session_id == academic_session_id,
        )
        setting = (await self.session.execute(stmt)).scalars().first()
        if not setting:
            setting = TimetableSetting(
                tenant_id=tenant_id,
                academic_session_id=academic_session_id,
                working_days=["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"],
                periods_per_day=8,
                period_duration_minutes=45,
                break_duration_minutes=15,
                lunch_duration_minutes=45,
                school_start_time="08:30",
            )
            self.session.add(setting)
            await self.session.flush()
            await self.session.refresh(setting)
        return setting

    async def update_settings(
        self, tenant_id: uuid.UUID, academic_session_id: uuid.UUID, data: Dict[str, Any]
    ) -> TimetableSetting:
        setting = await self.get_or_create_settings(tenant_id, academic_session_id)
        for k, v in data.items():
            if v is not None and hasattr(setting, k):
                setattr(setting, k, v)
        setting.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(setting)
        return setting

    async def create_period(self, tenant_id: uuid.UUID, data: Dict[str, Any]) -> TimetablePeriod:
        period = TimetablePeriod(
            tenant_id=tenant_id,
            academic_session_id=data["academic_session_id"],
            period_number=data["period_number"],
            name=data["name"],
            period_type=data.get("period_type", "ACADEMIC"),
            start_time=data["start_time"],
            end_time=data["end_time"],
            is_break=data.get("is_break", False),
        )
        self.session.add(period)
        await self.session.flush()
        await self.session.refresh(period)
        return period

    async def list_periods(
        self, tenant_id: uuid.UUID, academic_session_id: uuid.UUID
    ) -> List[TimetablePeriod]:
        stmt = (
            select(TimetablePeriod)
            .where(
                TimetablePeriod.tenant_id == tenant_id,
                TimetablePeriod.academic_session_id == academic_session_id,
            )
            .order_by(TimetablePeriod.period_number.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_period(self, tenant_id: uuid.UUID, period_id: uuid.UUID) -> bool:
        stmt = select(TimetablePeriod).where(
            TimetablePeriod.tenant_id == tenant_id,
            TimetablePeriod.id == period_id,
        )
        period = (await self.session.execute(stmt)).scalars().first()
        if not period:
            return False
        await self.session.delete(period)
        await self.session.flush()
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Holiday Calendar
    # ─────────────────────────────────────────────────────────────────────────

    async def create_holiday(self, tenant_id: uuid.UUID, data: Dict[str, Any]) -> TimetableHoliday:
        holiday = TimetableHoliday(
            tenant_id=tenant_id,
            academic_session_id=data["academic_session_id"],
            title=data["title"],
            holiday_date=data["holiday_date"],
            holiday_type=data.get("holiday_type", "NATIONAL"),
            description=data.get("description"),
            is_half_day=data.get("is_half_day", False),
        )
        self.session.add(holiday)
        await self.session.flush()
        await self.session.refresh(holiday)
        return holiday

    async def list_holidays(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[TimetableHoliday]:
        stmt = select(TimetableHoliday).where(TimetableHoliday.tenant_id == tenant_id)
        if academic_session_id:
            stmt = stmt.where(TimetableHoliday.academic_session_id == academic_session_id)
        if from_date:
            stmt = stmt.where(TimetableHoliday.holiday_date >= from_date)
        if to_date:
            stmt = stmt.where(TimetableHoliday.holiday_date <= to_date)
        stmt = stmt.order_by(TimetableHoliday.holiday_date.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_holiday(self, tenant_id: uuid.UUID, holiday_id: uuid.UUID) -> bool:
        stmt = select(TimetableHoliday).where(
            TimetableHoliday.tenant_id == tenant_id,
            TimetableHoliday.id == holiday_id,
        )
        holiday = (await self.session.execute(stmt)).scalars().first()
        if not holiday:
            return False
        await self.session.delete(holiday)
        await self.session.flush()
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Timetable Schedules
    # ─────────────────────────────────────────────────────────────────────────

    async def create_schedule(self, tenant_id: uuid.UUID, data: Dict[str, Any]) -> TimetableSchedule:
        schedule = TimetableSchedule(
            tenant_id=tenant_id,
            academic_session_id=data["academic_session_id"],
            name=data["name"],
            institution_type=data.get("institution_type", "SCHOOL"),
            effective_from=data["effective_from"],
            effective_to=data["effective_to"],
            status="DRAFT",
            description=data.get("description"),
        )
        self.session.add(schedule)
        await self.session.flush()
        return schedule

    async def get_schedule(
        self, tenant_id: uuid.UUID, schedule_id: uuid.UUID
    ) -> Optional[TimetableSchedule]:
        stmt = (
            select(TimetableSchedule)
            .where(
                TimetableSchedule.tenant_id == tenant_id,
                TimetableSchedule.id == schedule_id,
                TimetableSchedule.is_deleted == False,
            )
            .options(
                selectinload(TimetableSchedule.academic_session),
                selectinload(TimetableSchedule.publisher),
                selectinload(TimetableSchedule.entries),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def update_schedule(
        self, tenant_id: uuid.UUID, schedule_id: uuid.UUID, data: Dict[str, Any]
    ) -> TimetableSchedule:
        stmt = select(TimetableSchedule).where(
            TimetableSchedule.tenant_id == tenant_id,
            TimetableSchedule.id == schedule_id,
            TimetableSchedule.is_deleted == False,
        )
        schedule = (await self.session.execute(stmt)).scalars().first()
        if not schedule:
            raise ValueError("Schedule not found.")
        for k, v in data.items():
            if v is not None and hasattr(schedule, k):
                setattr(schedule, k, v)
        await self.session.flush()
        return schedule

    async def publish_schedule(
        self, tenant_id: uuid.UUID, schedule_id: uuid.UUID, published_by: uuid.UUID
    ) -> TimetableSchedule:
        stmt = select(TimetableSchedule).where(
            TimetableSchedule.tenant_id == tenant_id,
            TimetableSchedule.id == schedule_id,
            TimetableSchedule.is_deleted == False,
        )
        schedule = (await self.session.execute(stmt)).scalars().first()
        if not schedule:
            raise ValueError("Schedule not found.")
        schedule.status = "PUBLISHED"
        schedule.published_at = datetime.now(timezone.utc)
        schedule.published_by = published_by
        await self.session.flush()
        return schedule

    async def list_schedules(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
    ) -> List[TimetableSchedule]:
        stmt = (
            select(TimetableSchedule)
            .where(
                TimetableSchedule.tenant_id == tenant_id,
                TimetableSchedule.is_deleted == False,
            )
            .options(
                selectinload(TimetableSchedule.academic_session),
                selectinload(TimetableSchedule.publisher),
                selectinload(TimetableSchedule.entries),
            )
            .order_by(TimetableSchedule.created_at.desc())
        )
        if academic_session_id:
            stmt = stmt.where(TimetableSchedule.academic_session_id == academic_session_id)
        if status:
            stmt = stmt.where(TimetableSchedule.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Timetable Entries
    # ─────────────────────────────────────────────────────────────────────────

    async def create_entry(self, tenant_id: uuid.UUID, data: Dict[str, Any]) -> TimetableEntry:
        entry = TimetableEntry(
            tenant_id=tenant_id,
            academic_session_id=data.get("academic_session_id"),
            schedule_id=data.get("schedule_id"),
            period_id=data.get("period_id"),
            teacher_id=data["teacher_id"],
            subject_id=data.get("subject_id"),
            class_id=data.get("class_id"),
            section_id=data.get("section_id"),
            course_id=data.get("course_id"),
            semester=data.get("semester"),
            semester_id=data.get("semester_id"),
            batch_id=data.get("batch_id"),
            department_id=data.get("department_id"),
            day_of_week=data["day_of_week"].upper(),
            period_number=data.get("period_number", 1),
            start_time=data["start_time"],
            end_time=data["end_time"],
            room_number=data.get("room_number"),
            entry_type=data.get("entry_type", "THEORY"),
            is_practical=data.get("is_practical", False),
            capacity=data.get("capacity"),
            notes=data.get("notes"),
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get_entry(self, tenant_id: uuid.UUID, entry_id: uuid.UUID) -> Optional[TimetableEntry]:
        stmt = (
            select(TimetableEntry)
            .where(TimetableEntry.tenant_id == tenant_id, TimetableEntry.id == entry_id)
            .options(
                selectinload(TimetableEntry.teacher).selectinload(TeacherProfile.user),
                selectinload(TimetableEntry.subject),
                selectinload(TimetableEntry.school_class),
                selectinload(TimetableEntry.section),
                selectinload(TimetableEntry.course),
                selectinload(TimetableEntry.substitute_assignments).selectinload(SubstituteTeacherAssignment.substitute_teacher).selectinload(TeacherProfile.user),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def update_entry(
        self, tenant_id: uuid.UUID, entry_id: uuid.UUID, data: Dict[str, Any]
    ) -> TimetableEntry:
        stmt = select(TimetableEntry).where(TimetableEntry.tenant_id == tenant_id, TimetableEntry.id == entry_id)
        entry = (await self.session.execute(stmt)).scalars().first()
        if not entry:
            raise ValueError("Timetable entry not found.")
        for k, v in data.items():
            if v is not None and hasattr(entry, k):
                if k == "day_of_week":
                    v = str(v).upper()
                setattr(entry, k, v)
        await self.session.flush()
        return entry

    async def delete_entry(self, tenant_id: uuid.UUID, entry_id: uuid.UUID) -> bool:
        stmt = select(TimetableEntry).where(TimetableEntry.tenant_id == tenant_id, TimetableEntry.id == entry_id)
        entry = (await self.session.execute(stmt)).scalars().first()
        if not entry:
            return False
        await self.session.delete(entry)
        await self.session.flush()
        return True

    async def list_entries(
        self,
        tenant_id: uuid.UUID,
        schedule_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        teacher_id: Optional[uuid.UUID] = None,
        room_number: Optional[str] = None,
        day_of_week: Optional[str] = None,
        course_id: Optional[uuid.UUID] = None,
        semester: Optional[int] = None,
        batch_id: Optional[uuid.UUID] = None,
    ) -> List[TimetableEntry]:
        stmt = (
            select(TimetableEntry)
            .where(TimetableEntry.tenant_id == tenant_id)
            .options(
                selectinload(TimetableEntry.teacher).selectinload(TeacherProfile.user),
                selectinload(TimetableEntry.subject),
                selectinload(TimetableEntry.school_class),
                selectinload(TimetableEntry.section),
                selectinload(TimetableEntry.course),
                selectinload(TimetableEntry.substitute_assignments).selectinload(SubstituteTeacherAssignment.substitute_teacher).selectinload(TeacherProfile.user),
            )
            .order_by(TimetableEntry.day_of_week.asc(), TimetableEntry.start_time.asc())
        )
        if schedule_id:
            stmt = stmt.where(TimetableEntry.schedule_id == schedule_id)
        if class_id:
            stmt = stmt.where(TimetableEntry.class_id == class_id)
        if section_id:
            stmt = stmt.where(or_(TimetableEntry.section_id == section_id, TimetableEntry.section_id.is_(None)))
        if teacher_id:
            stmt = stmt.where(TimetableEntry.teacher_id == teacher_id)
        if room_number:
            stmt = stmt.where(TimetableEntry.room_number == room_number)
        if day_of_week:
            stmt = stmt.where(TimetableEntry.day_of_week == day_of_week.upper())
        if course_id:
            stmt = stmt.where(TimetableEntry.course_id == course_id)
        if semester:
            stmt = stmt.where(TimetableEntry.semester == semester)
        if batch_id:
            stmt = stmt.where(TimetableEntry.batch_id == batch_id)

        return list((await self.session.execute(stmt)).scalars().all())

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Overlap & Conflict Queries
    # ─────────────────────────────────────────────────────────────────────────

    async def find_overlapping_entries(
        self,
        tenant_id: uuid.UUID,
        day_of_week: str,
        start_time: str,
        end_time: str,
        exclude_id: Optional[uuid.UUID] = None,
        schedule_id: Optional[uuid.UUID] = None,
        teacher_id: Optional[uuid.UUID] = None,
        room_number: Optional[str] = None,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        semester: Optional[int] = None,
        batch_id: Optional[uuid.UUID] = None,
    ) -> List[TimetableEntry]:
        """
        Detect any slot on same day where start_time < other.end_time AND end_time > other.start_time.
        """
        stmt = (
            select(TimetableEntry)
            .where(
                TimetableEntry.tenant_id == tenant_id,
                TimetableEntry.day_of_week == day_of_week.upper(),
                TimetableEntry.start_time < end_time,
                TimetableEntry.end_time > start_time,
            )
            .options(
                selectinload(TimetableEntry.teacher).selectinload(TeacherProfile.user),
                selectinload(TimetableEntry.subject),
                selectinload(TimetableEntry.school_class),
                selectinload(TimetableEntry.section),
            )
        )
        if exclude_id:
            stmt = stmt.where(TimetableEntry.id != exclude_id)
        if schedule_id:
            stmt = stmt.where(TimetableEntry.schedule_id == schedule_id)

        conditions = []
        if teacher_id:
            conditions.append(TimetableEntry.teacher_id == teacher_id)
        if room_number and room_number.strip():
            conditions.append(TimetableEntry.room_number == room_number.strip())
        if class_id:
            if section_id:
                conditions.append(
                    and_(
                        TimetableEntry.class_id == class_id,
                        or_(TimetableEntry.section_id == section_id, TimetableEntry.section_id.is_(None)),
                    )
                )
            else:
                conditions.append(TimetableEntry.class_id == class_id)
        if course_id:
            if batch_id:
                conditions.append(
                    and_(
                        TimetableEntry.course_id == course_id,
                        or_(TimetableEntry.batch_id == batch_id, TimetableEntry.batch_id.is_(None)),
                    )
                )
            elif semester:
                conditions.append(
                    and_(
                        TimetableEntry.course_id == course_id,
                        TimetableEntry.semester == semester,
                    )
                )
            else:
                conditions.append(TimetableEntry.course_id == course_id)

        if not conditions:
            return []

        stmt = stmt.where(or_(*conditions))
        return list((await self.session.execute(stmt)).scalars().all())

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Substitute Assignments
    # ─────────────────────────────────────────────────────────────────────────

    async def get_substitute_assignment(
        self, tenant_id: uuid.UUID, assignment_id: uuid.UUID
    ) -> Optional[SubstituteTeacherAssignment]:
        stmt = (
            select(SubstituteTeacherAssignment)
            .where(
                SubstituteTeacherAssignment.tenant_id == tenant_id,
                SubstituteTeacherAssignment.id == assignment_id,
            )
            .options(
                selectinload(SubstituteTeacherAssignment.original_teacher).selectinload(TeacherProfile.user),
                selectinload(SubstituteTeacherAssignment.substitute_teacher).selectinload(TeacherProfile.user),
                selectinload(SubstituteTeacherAssignment.assigner),
                selectinload(SubstituteTeacherAssignment.timetable_entry).selectinload(TimetableEntry.subject),
                selectinload(SubstituteTeacherAssignment.timetable_entry).selectinload(TimetableEntry.school_class),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def create_substitute_assignment(
        self,
        tenant_id: uuid.UUID,
        timetable_entry_id: uuid.UUID,
        assignment_date: date,
        original_teacher_id: uuid.UUID,
        substitute_teacher_id: uuid.UUID,
        assigned_by: Optional[uuid.UUID] = None,
        reason: Optional[str] = None,
    ) -> SubstituteTeacherAssignment:
        assignment = SubstituteTeacherAssignment(
            tenant_id=tenant_id,
            timetable_entry_id=timetable_entry_id,
            assignment_date=assignment_date,
            original_teacher_id=original_teacher_id,
            substitute_teacher_id=substitute_teacher_id,
            assigned_by=assigned_by,
            reason=reason,
            status="ASSIGNED",
        )
        self.session.add(assignment)
        await self.session.flush()
        detailed = await self.get_substitute_assignment(tenant_id, assignment.id)
        return detailed or assignment

    async def list_substitutes(
        self,
        tenant_id: uuid.UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        teacher_id: Optional[uuid.UUID] = None,
    ) -> List[SubstituteTeacherAssignment]:
        stmt = (
            select(SubstituteTeacherAssignment)
            .where(SubstituteTeacherAssignment.tenant_id == tenant_id)
            .options(
                selectinload(SubstituteTeacherAssignment.original_teacher).selectinload(TeacherProfile.user),
                selectinload(SubstituteTeacherAssignment.substitute_teacher).selectinload(TeacherProfile.user),
                selectinload(SubstituteTeacherAssignment.assigner),
                selectinload(SubstituteTeacherAssignment.timetable_entry).selectinload(TimetableEntry.subject),
                selectinload(SubstituteTeacherAssignment.timetable_entry).selectinload(TimetableEntry.school_class),
            )
            .order_by(SubstituteTeacherAssignment.assignment_date.desc())
        )
        if from_date:
            stmt = stmt.where(SubstituteTeacherAssignment.assignment_date >= from_date)
        if to_date:
            stmt = stmt.where(SubstituteTeacherAssignment.assignment_date <= to_date)
        if teacher_id:
            stmt = stmt.where(
                or_(
                    SubstituteTeacherAssignment.original_teacher_id == teacher_id,
                    SubstituteTeacherAssignment.substitute_teacher_id == teacher_id,
                )
            )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_active_substitute(
        self, tenant_id: uuid.UUID, timetable_entry_id: uuid.UUID, check_date: date
    ) -> Optional[SubstituteTeacherAssignment]:
        stmt = (
            select(SubstituteTeacherAssignment)
            .where(
                SubstituteTeacherAssignment.tenant_id == tenant_id,
                SubstituteTeacherAssignment.timetable_entry_id == timetable_entry_id,
                SubstituteTeacherAssignment.assignment_date == check_date,
                SubstituteTeacherAssignment.status != "CANCELLED",
            )
            .options(
                selectinload(SubstituteTeacherAssignment.substitute_teacher).selectinload(TeacherProfile.user),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()
