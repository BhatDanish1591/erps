from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestException, NotFoundException, ValidationException
from app.core.logging import get_logger
from app.dependencies.tenant import registered_institution_type
from app.models.academic import (
    Course,
    SchoolClass,
    SchoolEnrollmentDetail,
    Section,
    StudentAcademicEnrollment,
    StudentProfile,
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
from app.repositories.timetable import TimetableRepository
from app.schemas.timetable import (
    ConflictCheckResponse,
    ConflictItem,
    DayScheduleResponse,
    SubstituteAssignmentResponse,
    TimetableEntryResponse,
    TimetableHolidayResponse,
    TimetablePeriodResponse,
    TimetableScheduleResponse,
    TimetableSettingResponse,
    WeeklyTimetableResponse,
)

logger = get_logger(__name__)

DAYS_ORDER = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]


class TimetableService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TimetableRepository(session)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Conflict Detection Engine
    # ─────────────────────────────────────────────────────────────────────────

    async def detect_conflicts(
        self,
        tenant_id: uuid.UUID,
        day_of_week: str,
        start_time: str,
        end_time: str,
        teacher_id: Optional[uuid.UUID] = None,
        room_number: Optional[str] = None,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        semester: Optional[int] = None,
        batch_id: Optional[uuid.UUID] = None,
        schedule_id: Optional[uuid.UUID] = None,
        exclude_entry_id: Optional[uuid.UUID] = None,
    ) -> List[ConflictItem]:
        """
        Comprehensive conflict detection engine checking teacher, classroom, and class overlaps.
        """
        conflicts: List[ConflictItem] = []
        clean_day = day_of_week.upper()

        # Validate time format
        if start_time >= end_time:
            conflicts.append(
                ConflictItem(
                    conflict_type="INVALID_TIME",
                    severity="ERROR",
                    message=f"Start time ({start_time}) must be earlier than end time ({end_time}).",
                    day_of_week=clean_day,
                    start_time=start_time,
                    end_time=end_time,
                    entity_name="Time Slot",
                )
            )
            return conflicts

        overlaps = await self.repo.find_overlapping_entries(
            tenant_id=tenant_id,
            day_of_week=clean_day,
            start_time=start_time,
            end_time=end_time,
            exclude_id=exclude_entry_id,
            schedule_id=schedule_id,
            teacher_id=teacher_id,
            room_number=room_number,
            class_id=class_id,
            section_id=section_id,
            course_id=course_id,
            semester=semester,
            batch_id=batch_id,
        )

        for other in overlaps:
            # 1. Teacher Overlap
            if teacher_id and other.teacher_id == teacher_id:
                t_name = other.teacher.user.full_name if (other.teacher and other.teacher.user) else "Teacher"
                cls_desc = other.school_class.name if other.school_class else (other.course.name if other.course else "Class")
                conflicts.append(
                    ConflictItem(
                        conflict_type="TEACHER_OVERLAP",
                        severity="ERROR",
                        message=f"{t_name} is already scheduled for {cls_desc} on {clean_day} between {other.start_time} and {other.end_time}.",
                        day_of_week=clean_day,
                        start_time=start_time,
                        end_time=end_time,
                        conflicting_entry_id=other.id,
                        entity_name=t_name,
                    )
                )

            # 2. Classroom Overlap
            if room_number and other.room_number and other.room_number.strip().upper() == room_number.strip().upper():
                cls_desc = other.school_class.name if other.school_class else (other.course.name if other.course else "Class")
                conflicts.append(
                    ConflictItem(
                        conflict_type="ROOM_OVERLAP",
                        severity="ERROR",
                        message=f"Room {room_number} is already occupied by {cls_desc} on {clean_day} ({other.start_time}-{other.end_time}).",
                        day_of_week=clean_day,
                        start_time=start_time,
                        end_time=end_time,
                        conflicting_entry_id=other.id,
                        entity_name=f"Room {room_number}",
                    )
                )

            # 3. Class / Section Overlap
            if class_id and other.class_id == class_id:
                is_same_section = (section_id is None or other.section_id is None or other.section_id == section_id)
                if is_same_section:
                    cls_name = other.school_class.name if other.school_class else "This Class"
                    subj_name = other.subject.name if other.subject else "Subject"
                    conflicts.append(
                        ConflictItem(
                            conflict_type="CLASS_OVERLAP",
                            severity="ERROR",
                            message=f"{cls_name} already has a scheduled class ({subj_name}) on {clean_day} ({other.start_time}-{other.end_time}).",
                            day_of_week=clean_day,
                            start_time=start_time,
                            end_time=end_time,
                            conflicting_entry_id=other.id,
                            entity_name=cls_name,
                        )
                    )

            # 4. College Course / Semester / Batch Overlap
            if course_id and other.course_id == course_id and other.semester == semester:
                is_same_batch = (batch_id is None or other.batch_id is None or other.batch_id == batch_id)
                if is_same_batch:
                    c_name = other.course.name if other.course else "This Course"
                    conflicts.append(
                        ConflictItem(
                            conflict_type="CLASS_OVERLAP",
                            severity="ERROR",
                            message=f"{c_name} (Sem {semester}) already has a lecture on {clean_day} ({other.start_time}-{other.end_time}).",
                            day_of_week=clean_day,
                            start_time=start_time,
                            end_time=end_time,
                            conflicting_entry_id=other.id,
                            entity_name=c_name,
                        )
                    )

        return conflicts

    async def check_schedule_conflicts(
        self, tenant_id: uuid.UUID, schedule_id: uuid.UUID
    ) -> ConflictCheckResponse:
        """
        Audit the entire schedule for any internal overlapping conflicts.
        """
        entries = await self.repo.list_entries(tenant_id=tenant_id, schedule_id=schedule_id)
        all_conflicts: List[ConflictItem] = []

        for i, entry in enumerate(entries):
            conflicts = await self.detect_conflicts(
                tenant_id=tenant_id,
                day_of_week=entry.day_of_week,
                start_time=entry.start_time,
                end_time=entry.end_time,
                teacher_id=entry.teacher_id,
                room_number=entry.room_number,
                class_id=entry.class_id,
                section_id=entry.section_id,
                course_id=entry.course_id,
                semester=entry.semester,
                batch_id=entry.batch_id,
                schedule_id=schedule_id,
                exclude_entry_id=entry.id,
            )
            for c in conflicts:
                # Deduplicate mirrored conflict pairs
                exists = any(
                    x.conflicting_entry_id == entry.id and x.conflict_type == c.conflict_type
                    for x in all_conflicts
                )
                if not exists:
                    all_conflicts.append(c)

        return ConflictCheckResponse(
            has_conflicts=len(all_conflicts) > 0,
            total_conflicts=len(all_conflicts),
            conflicts=all_conflicts,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Settings & Periods
    # ─────────────────────────────────────────────────────────────────────────

    async def get_settings(
        self, tenant_id: uuid.UUID, academic_session_id: uuid.UUID
    ) -> TimetableSettingResponse:
        setting = await self.repo.get_or_create_settings(tenant_id, academic_session_id)
        return TimetableSettingResponse.model_validate(setting)

    async def update_settings(
        self, tenant_id: uuid.UUID, academic_session_id: uuid.UUID, data: Dict[str, Any]
    ) -> TimetableSettingResponse:
        setting = await self.repo.update_settings(tenant_id, academic_session_id, data)
        return TimetableSettingResponse.model_validate(setting)

    async def create_period(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> TimetablePeriodResponse:
        period = await self.repo.create_period(tenant_id, data)
        return TimetablePeriodResponse.model_validate(period)

    async def list_periods(
        self, tenant_id: uuid.UUID, academic_session_id: uuid.UUID
    ) -> List[TimetablePeriodResponse]:
        periods = await self.repo.list_periods(tenant_id, academic_session_id)
        return [TimetablePeriodResponse.model_validate(p) for p in periods]

    async def delete_period(self, tenant_id: uuid.UUID, period_id: uuid.UUID) -> bool:
        return await self.repo.delete_period(tenant_id, period_id)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Holidays & Institutional Calendar
    # ─────────────────────────────────────────────────────────────────────────

    async def create_holiday(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> TimetableHolidayResponse:
        holiday = await self.repo.create_holiday(tenant_id, data)
        return TimetableHolidayResponse.model_validate(holiday)

    async def list_holidays(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[TimetableHolidayResponse]:
        holidays = await self.repo.list_holidays(tenant_id, academic_session_id, from_date, to_date)
        return [TimetableHolidayResponse.model_validate(h) for h in holidays]

    async def delete_holiday(self, tenant_id: uuid.UUID, holiday_id: uuid.UUID) -> bool:
        return await self.repo.delete_holiday(tenant_id, holiday_id)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Schedules
    # ─────────────────────────────────────────────────────────────────────────

    async def create_schedule(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> TimetableScheduleResponse:
        institution_type = (await registered_institution_type(self.session, tenant_id)).value
        if data.get("institution_type") not in (None, institution_type):
            raise BadRequestException("Schedule type must match the registered institution type.")
        schedule = await self.repo.create_schedule(tenant_id, {**data, "institution_type": institution_type})
        detailed = await self.repo.get_schedule(tenant_id, schedule.id)
        return self._format_schedule_response(detailed or schedule)

    async def get_schedule(
        self, tenant_id: uuid.UUID, schedule_id: uuid.UUID
    ) -> TimetableScheduleResponse:
        schedule = await self.repo.get_schedule(tenant_id, schedule_id)
        if not schedule:
            raise NotFoundException("Timetable schedule not found.")
        return self._format_schedule_response(schedule)

    async def update_schedule(
        self, tenant_id: uuid.UUID, schedule_id: uuid.UUID, data: Dict[str, Any]
    ) -> TimetableScheduleResponse:
        schedule = await self.repo.update_schedule(tenant_id, schedule_id, data)
        detailed = await self.repo.get_schedule(tenant_id, schedule.id)
        return self._format_schedule_response(detailed or schedule)

    async def publish_schedule(
        self, tenant_id: uuid.UUID, schedule_id: uuid.UUID, user_id: uuid.UUID, force: bool = False
    ) -> TimetableScheduleResponse:
        # Run conflict audit before publishing
        conflict_report = await self.check_schedule_conflicts(tenant_id, schedule_id)
        if conflict_report.has_conflicts and not force:
            errors = [c.message for c in conflict_report.conflicts if c.severity == "ERROR"]
            if errors:
                raise ValidationException(
                    message=f"Cannot publish schedule with {len(errors)} active scheduling conflicts.",
                    details=[{"field": "conflicts", "message": error} for error in errors],
                )

        schedule = await self.repo.publish_schedule(tenant_id, schedule_id, user_id)
        detailed = await self.repo.get_schedule(tenant_id, schedule.id)
        return self._format_schedule_response(detailed or schedule)

    async def list_schedules(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
    ) -> List[TimetableScheduleResponse]:
        items = await self.repo.list_schedules(tenant_id, academic_session_id, status)
        return [self._format_schedule_response(s) for s in items]

    def _format_schedule_response(self, schedule: TimetableSchedule) -> TimetableScheduleResponse:
        pub_name = schedule.publisher.full_name if schedule.publisher else None
        sess_name = schedule.academic_session.name if schedule.academic_session else None
        entries_cnt = len(schedule.entries) if schedule.entries else 0

        return TimetableScheduleResponse(
            id=schedule.id,
            tenant_id=schedule.tenant_id,
            academic_session_id=schedule.academic_session_id,
            academic_session_name=sess_name,
            name=schedule.name,
            institution_type=schedule.institution_type,
            effective_from=schedule.effective_from,
            effective_to=schedule.effective_to,
            status=schedule.status,
            published_at=schedule.published_at,
            published_by=schedule.published_by,
            publisher_name=pub_name,
            entries_count=entries_cnt,
            description=schedule.description,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Timetable Entries
    # ─────────────────────────────────────────────────────────────────────────

    async def create_entry(
        self, tenant_id: uuid.UUID, data: Dict[str, Any], ignore_conflicts: bool = False
    ) -> TimetableEntryResponse:
        # Pre-save conflict validation
        conflicts = await self.detect_conflicts(
            tenant_id=tenant_id,
            day_of_week=data["day_of_week"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            teacher_id=data.get("teacher_id"),
            room_number=data.get("room_number"),
            class_id=data.get("class_id"),
            section_id=data.get("section_id"),
            course_id=data.get("course_id"),
            semester=data.get("semester"),
            batch_id=data.get("batch_id"),
            schedule_id=data.get("schedule_id"),
        )
        if conflicts and (not ignore_conflicts or any(conflict.conflict_type == "INVALID_TIME" for conflict in conflicts)):
            err_msgs = "; ".join(c.message for c in conflicts)
            raise BadRequestException(f"Scheduling conflict detected: {err_msgs}")

        entry = await self.repo.create_entry(tenant_id, data)
        detailed = await self.repo.get_entry(tenant_id, entry.id)
        return self._format_entry_response(detailed or entry)

    async def update_entry(
        self, tenant_id: uuid.UUID, entry_id: uuid.UUID, data: Dict[str, Any]
    ) -> TimetableEntryResponse:
        current = await self.repo.get_entry(tenant_id, entry_id)
        if not current:
            raise NotFoundException("Timetable entry not found.")

        # Check conflicts for updated parameters
        day = data.get("day_of_week", current.day_of_week)
        start = data.get("start_time", current.start_time)
        end = data.get("end_time", current.end_time)
        teacher = data.get("teacher_id", current.teacher_id)
        room = data.get("room_number", current.room_number)
        cid = data.get("class_id", current.class_id)
        sec = data.get("section_id", current.section_id)

        conflicts = await self.detect_conflicts(
            tenant_id=tenant_id,
            day_of_week=day,
            start_time=start,
            end_time=end,
            teacher_id=teacher,
            room_number=room,
            class_id=cid,
            section_id=sec,
            course_id=data.get("course_id", current.course_id),
            semester=data.get("semester", current.semester),
            batch_id=data.get("batch_id", current.batch_id),
            schedule_id=current.schedule_id,
            exclude_entry_id=entry_id,
        )
        if conflicts:
            err_msgs = "; ".join(c.message for c in conflicts)
            raise BadRequestException(f"Scheduling conflict detected: {err_msgs}")

        updated = await self.repo.update_entry(tenant_id, entry_id, data)
        detailed = await self.repo.get_entry(tenant_id, updated.id)
        return self._format_entry_response(detailed or updated)

    async def delete_entry(self, tenant_id: uuid.UUID, entry_id: uuid.UUID) -> bool:
        return await self.repo.delete_entry(tenant_id, entry_id)

    async def list_entries(
        self,
        tenant_id: uuid.UUID,
        schedule_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        teacher_id: Optional[uuid.UUID] = None,
        room_number: Optional[str] = None,
        day_of_week: Optional[str] = None,
    ) -> List[TimetableEntryResponse]:
        entries = await self.repo.list_entries(
            tenant_id=tenant_id,
            schedule_id=schedule_id,
            class_id=class_id,
            section_id=section_id,
            teacher_id=teacher_id,
            room_number=room_number,
            day_of_week=day_of_week,
        )
        return [self._format_entry_response(e) for e in entries]

    def _format_entry_response(
        self, entry: TimetableEntry, substitute_date: Optional[date] = None
    ) -> TimetableEntryResponse:
        t_name = entry.teacher.user.full_name if (entry.teacher and entry.teacher.user) else None
        emp_id = entry.teacher.employee_id if entry.teacher else None
        s_name = entry.subject.name if entry.subject else None
        s_code = entry.subject.code if entry.subject else None
        c_name = entry.school_class.name if entry.school_class else None
        sec_name = entry.section.name if entry.section else None
        course_name = entry.course.name if entry.course else None

        sub_teacher_id = None
        sub_teacher_name = None
        if entry.substitute_assignments:
            for sub in entry.substitute_assignments:
                if sub.status != "CANCELLED" and (substitute_date is None or sub.assignment_date == substitute_date):
                    sub_teacher_id = sub.substitute_teacher_id
                    if sub.substitute_teacher and sub.substitute_teacher.user:
                        sub_teacher_name = sub.substitute_teacher.user.full_name
                    break

        return TimetableEntryResponse(
            id=entry.id,
            tenant_id=entry.tenant_id,
            academic_session_id=entry.academic_session_id,
            schedule_id=entry.schedule_id,
            period_id=entry.period_id,
            teacher_id=entry.teacher_id,
            teacher_name=t_name,
            employee_id=emp_id,
            subject_id=entry.subject_id,
            subject_name=s_name,
            subject_code=s_code,
            class_id=entry.class_id,
            class_name=c_name,
            section_id=entry.section_id,
            section_name=sec_name,
            course_id=entry.course_id,
            course_name=course_name,
            semester=entry.semester,
            batch_id=entry.batch_id,
            batch_name=None,
            department_id=entry.department_id,
            day_of_week=entry.day_of_week,
            period_number=entry.period_number,
            start_time=entry.start_time,
            end_time=entry.end_time,
            room_number=entry.room_number,
            entry_type=entry.entry_type,
            is_practical=entry.is_practical,
            capacity=entry.capacity,
            notes=entry.notes,
            substitute_teacher_id=sub_teacher_id,
            substitute_teacher_name=sub_teacher_name,
            created_at=entry.created_at,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Weekly Matrix / Views
    # ─────────────────────────────────────────────────────────────────────────

    async def get_weekly_view(
        self,
        tenant_id: uuid.UUID,
        schedule_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        teacher_id: Optional[uuid.UUID] = None,
        room_number: Optional[str] = None,
        target_date: Optional[date] = None,
    ) -> WeeklyTimetableResponse:
        ref_date = target_date or date.today()
        entries = await self.repo.list_entries(
            tenant_id=tenant_id,
            schedule_id=schedule_id,
            class_id=class_id,
            section_id=section_id,
            teacher_id=teacher_id,
            room_number=room_number,
        )

        # Get settings for active working days
        setting_stmt = select(TimetableSetting).where(TimetableSetting.tenant_id == tenant_id)
        setting = (await self.session.execute(setting_stmt)).scalars().first()
        active_days = setting.working_days if setting else DAYS_ORDER[:6]

        # Get holidays
        holidays = await self.repo.list_holidays(tenant_id=tenant_id, from_date=ref_date, to_date=ref_date)
        holiday_map = {h.holiday_date: TimetableHolidayResponse.model_validate(h) for h in holidays}

        days_resp: List[DayScheduleResponse] = []
        for d in DAYS_ORDER:
            day_entries = [e for e in entries if e.day_of_week.upper() == d]
            formatted_entries = [self._format_entry_response(e, substitute_date=ref_date) for e in day_entries]
            days_resp.append(
                DayScheduleResponse(
                    day_of_week=d,
                    is_working_day=d in active_days,
                    holiday=holiday_map.get(ref_date),
                    entries=formatted_entries,
                )
            )

        entity_type = "CLASS"
        entity_name = "Class Timetable"
        if teacher_id:
            entity_type = "TEACHER"
            t_stmt = (
                select(TeacherProfile)
                .where(TeacherProfile.id == teacher_id)
                .options(selectinload(TeacherProfile.user))
            )
            teacher = (await self.session.execute(t_stmt)).scalars().first()
            entity_name = teacher.user.full_name if (teacher and teacher.user) else "Teacher Timetable"
        elif room_number:
            entity_type = "ROOM"
            entity_name = f"Room {room_number}"
        elif class_id:
            c_stmt = select(SchoolClass).where(SchoolClass.id == class_id)
            cls = (await self.session.execute(c_stmt)).scalars().first()
            entity_name = cls.name if cls else "Class Timetable"

        sched_name = None
        if schedule_id:
            sched = await self.repo.get_schedule(tenant_id, schedule_id)
            sched_name = sched.name if sched else None

        return WeeklyTimetableResponse(
            schedule_id=schedule_id,
            schedule_name=sched_name,
            entity_type=entity_type,
            entity_name=entity_name,
            days=days_resp,
        )

    async def get_my_timetable(
        self, tenant_id: uuid.UUID, user: User, user_role: str, target_date: Optional[date] = None
    ) -> WeeklyTimetableResponse:
        ref_date = target_date or date.today()

        if user_role == "TEACHER":
            t_stmt = select(TeacherProfile).where(TeacherProfile.tenant_id == tenant_id, TeacherProfile.user_id == user.id)
            t_prof = (await self.session.execute(t_stmt)).scalars().first()
            if not t_prof:
                raise NotFoundException("Teacher profile not found.")
            return await self.get_weekly_view(tenant_id=tenant_id, teacher_id=t_prof.id, target_date=ref_date)

        elif user_role in ("STUDENT", "PARENT"):
            s_stmt = select(StudentProfile).where(StudentProfile.tenant_id == tenant_id, StudentProfile.user_id == user.id)
            s_prof = (await self.session.execute(s_stmt)).scalars().first()
            if not s_prof:
                raise NotFoundException("Student profile not found.")

            # Find active enrollment details
            enr_stmt = (
                select(StudentAcademicEnrollment)
                .where(
                    StudentAcademicEnrollment.tenant_id == tenant_id,
                    StudentAcademicEnrollment.student_id == s_prof.id,
                    StudentAcademicEnrollment.status == "ACTIVE",
                )
                .options(selectinload(StudentAcademicEnrollment.school_detail))
            )
            enrollment = (await self.session.execute(enr_stmt)).scalars().first()

            if enrollment and enrollment.school_detail:
                return await self.get_weekly_view(
                    tenant_id=tenant_id,
                    class_id=enrollment.school_detail.class_id,
                    section_id=enrollment.school_detail.section_id,
                    target_date=ref_date,
                )
            elif s_prof.class_id:
                return await self.get_weekly_view(
                    tenant_id=tenant_id,
                    class_id=s_prof.class_id,
                    section_id=s_prof.section_id,
                    target_date=ref_date,
                )
            else:
                return await self.get_weekly_view(tenant_id=tenant_id, target_date=ref_date)

        # Fallback for Admin
        return await self.get_weekly_view(tenant_id=tenant_id, target_date=ref_date)

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Substitute Teacher Assignment
    # ─────────────────────────────────────────────────────────────────────────

    async def assign_substitute(
        self,
        tenant_id: uuid.UUID,
        timetable_entry_id: uuid.UUID,
        assignment_date: date,
        substitute_teacher_id: uuid.UUID,
        assigned_by: uuid.UUID,
        reason: Optional[str] = None,
    ) -> SubstituteAssignmentResponse:
        entry = await self.repo.get_entry(tenant_id, timetable_entry_id)
        if not entry:
            raise NotFoundException("Timetable entry slot not found.")

        # Check if substitute teacher is already booked on that day & time
        conflicts = await self.detect_conflicts(
            tenant_id=tenant_id,
            day_of_week=entry.day_of_week,
            start_time=entry.start_time,
            end_time=entry.end_time,
            teacher_id=substitute_teacher_id,
            exclude_entry_id=timetable_entry_id,
        )
        if conflicts:
            err = "; ".join(c.message for c in conflicts)
            raise BadRequestException(f"Substitute teacher cannot be assigned due to schedule conflict: {err}")

        sub = await self.repo.create_substitute_assignment(
            tenant_id=tenant_id,
            timetable_entry_id=timetable_entry_id,
            assignment_date=assignment_date,
            original_teacher_id=entry.teacher_id,
            substitute_teacher_id=substitute_teacher_id,
            assigned_by=assigned_by,
            reason=reason,
        )
        return self._format_substitute_response(sub)

    async def list_substitutes(
        self,
        tenant_id: uuid.UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        teacher_id: Optional[uuid.UUID] = None,
    ) -> List[SubstituteAssignmentResponse]:
        subs = await self.repo.list_substitutes(tenant_id, from_date, to_date, teacher_id)
        return [self._format_substitute_response(s) for s in subs]

    def _format_substitute_response(self, sub: SubstituteTeacherAssignment) -> SubstituteAssignmentResponse:
        orig_name = sub.original_teacher.user.full_name if (sub.original_teacher and sub.original_teacher.user) else None
        sub_name = sub.substitute_teacher.user.full_name if (sub.substitute_teacher and sub.substitute_teacher.user) else None
        assigner_name = sub.assigner.full_name if sub.assigner else None

        return SubstituteAssignmentResponse(
            id=sub.id,
            tenant_id=sub.tenant_id,
            timetable_entry_id=sub.timetable_entry_id,
            assignment_date=sub.assignment_date,
            original_teacher_id=sub.original_teacher_id,
            original_teacher_name=orig_name,
            substitute_teacher_id=sub.substitute_teacher_id,
            substitute_teacher_name=sub_name,
            assigned_by=sub.assigned_by,
            assigner_name=assigner_name,
            reason=sub.reason,
            status=sub.status,
            created_at=sub.created_at,
            updated_at=sub.updated_at,
        )
