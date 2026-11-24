from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.academic import (
    AcademicSession,
    CollegeEnrollmentDetail,
    CollegeSemester,
    Course,
    Department,
    SchoolClass,
    SchoolEnrollmentDetail,
    Section,
    StudentAcademicEnrollment,
    StudentProfile,
    Subject,
    TeacherAttendance,
    TeacherProfile,
)
from app.models.attendance import (
    AttendanceCorrectionLog,
    AttendanceDeviceLog,
    StudentAttendanceEntry,
    StudentAttendanceSession,
)
from app.models.user import User

logger = get_logger(__name__)


class AttendanceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_cohort_report(
        self, tenant_id: uuid.UUID, academic_session_id: uuid.UUID, *,
        class_id: Optional[uuid.UUID], section_id: Optional[uuid.UUID],
        course_id: Optional[uuid.UUID], semester_id: Optional[uuid.UUID],
    ) -> Dict[str, Any]:
        _, roster = await self.get_roster_for_marking(
            tenant_id, academic_session_id, date.today(), class_id=class_id,
            section_id=section_id, course_id=course_id, semester_id=semester_id,
        )
        totals = {row["student_id"]: [0, 0] for row in roster}
        names = {row["student_id"]: row for row in roster}
        conditions = [
            StudentAttendanceSession.tenant_id == tenant_id,
            StudentAttendanceEntry.tenant_id == tenant_id,
            StudentAttendanceSession.academic_session_id == academic_session_id,
            StudentAttendanceSession.status == "SUBMITTED",
            StudentAttendanceSession.class_id == class_id,
            StudentAttendanceSession.course_id == course_id,
            StudentAttendanceSession.semester_id == semester_id,
            StudentAttendanceEntry.student_id.in_(totals),
        ]
        if section_id:
            conditions.append(StudentAttendanceSession.section_id == section_id)
        subject_id = StudentAttendanceSession.subject_id
        grouped = (
            select(
                subject_id, Subject.name.label("subject_name"), StudentAttendanceEntry.student_id,
                func.count().label("total"), func.count().filter(
                    StudentAttendanceEntry.status.in_(("PRESENT", "LATE"))
                ).label("attended"),
            )
            .select_from(StudentAttendanceEntry)
            .join(StudentAttendanceSession, StudentAttendanceSession.id == StudentAttendanceEntry.session_id)
            .outerjoin(Subject, and_(Subject.id == subject_id, Subject.tenant_id == tenant_id))
            .where(*conditions)
            .group_by(subject_id, Subject.name, StudentAttendanceEntry.student_id)
            .order_by(Subject.name, subject_id)
        )
        sessions = (
            select(subject_id, func.count(func.distinct(StudentAttendanceSession.id)))
            .select_from(StudentAttendanceEntry)
            .join(StudentAttendanceSession, StudentAttendanceSession.id == StudentAttendanceEntry.session_id)
            .where(*conditions).group_by(subject_id)
        )
        class_counts = dict((await self.session.execute(sessions)).tuples().all())
        subjects: Dict[Any, Dict[str, Any]] = {}

        def counts(total: int, attended: int) -> Dict[str, Any]:
            return {"total": total, "attended": attended, "percentage": round(attended * 100 / total, 1) if total else None}

        def student_row(student_id: uuid.UUID, total: int, attended: int) -> Dict[str, Any]:
            student = names[student_id]
            return {"id": student_id, "name": student["full_name"],
                    "admission_number": student["admission_number"], **counts(total, attended)}

        for record in (await self.session.execute(grouped)).all():
            totals[record.student_id][0] += record.total
            totals[record.student_id][1] += record.attended
            subject = subjects.setdefault(record.subject_id, {
                "id": record.subject_id, "name": record.subject_name or "Daily roll call",
                "classes": class_counts[record.subject_id], "total": 0, "attended": 0, "students": [],
            })
            subject["total"] += record.total
            subject["attended"] += record.attended
            subject["students"].append(student_row(record.student_id, record.total, record.attended))

        students = [student_row(student_id, *values) for student_id, values in totals.items()]
        return {
            "students": students,
            "subjects": [{**subject, **counts(subject["total"], subject["attended"])} for subject in subjects.values()],
            "overview": counts(sum(values[0] for values in totals.values()), sum(values[1] for values in totals.values())),
        }

    async def find_existing_session(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: uuid.UUID,
        session_date: date,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        semester_id: Optional[uuid.UUID] = None,
        subject_id: Optional[uuid.UUID] = None,
        period_number: Optional[int] = None,
        session_type: str = "DAILY",
    ) -> Optional[StudentAttendanceSession]:
        """
        Check if an attendance session already exists for the given slot.
        """
        stmt = select(StudentAttendanceSession).where(
            StudentAttendanceSession.tenant_id == tenant_id,
            StudentAttendanceSession.academic_session_id == academic_session_id,
            StudentAttendanceSession.session_date == session_date,
            StudentAttendanceSession.session_type == session_type,
            StudentAttendanceSession.class_id == class_id,
            StudentAttendanceSession.section_id == section_id,
            StudentAttendanceSession.course_id == course_id,
            StudentAttendanceSession.semester_id == semester_id,
            StudentAttendanceSession.subject_id == subject_id,
            StudentAttendanceSession.period_number == period_number,
        )

        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_session_by_id(
        self,
        tenant_id: uuid.UUID,
        session_id: uuid.UUID,
        load_entries: bool = True,
    ) -> Optional[StudentAttendanceSession]:
        stmt = (
            select(StudentAttendanceSession)
            .where(
                StudentAttendanceSession.tenant_id == tenant_id,
                StudentAttendanceSession.id == session_id,
            )
            .options(
                selectinload(StudentAttendanceSession.school_class),
                selectinload(StudentAttendanceSession.section),
                selectinload(StudentAttendanceSession.subject),
                selectinload(StudentAttendanceSession.conducted_by).selectinload(TeacherProfile.user),
            )
        )
        if load_entries:
            stmt = stmt.options(
                selectinload(StudentAttendanceSession.entries)
                .selectinload(StudentAttendanceEntry.student)
                .selectinload(StudentProfile.user)
            )

        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def create_attendance_session(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: uuid.UUID,
        session_date: date,
        session_type: str,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        semester_id: Optional[uuid.UUID] = None,
        subject_id: Optional[uuid.UUID] = None,
        period_number: Optional[int] = None,
        conducted_by_teacher_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
    ) -> StudentAttendanceSession:
        attendance_session = StudentAttendanceSession(
            tenant_id=tenant_id,
            academic_session_id=academic_session_id,
            session_date=session_date,
            session_type=session_type,
            class_id=class_id,
            section_id=section_id,
            course_id=course_id,
            semester_id=semester_id,
            subject_id=subject_id,
            period_number=period_number,
            conducted_by_teacher_id=conducted_by_teacher_id,
            remarks=remarks,
            status="SUBMITTED",
        )
        self.session.add(attendance_session)
        await self.session.flush()
        return attendance_session

    async def record_entries(
        self,
        tenant_id: uuid.UUID,
        session_id: uuid.UUID,
        entries_data: List[Dict[str, Any]],
    ) -> StudentAttendanceSession:
        att_session = await self.get_session_by_id(tenant_id, session_id, load_entries=True)
        if not att_session:
            raise ValueError("Attendance session not found")

        # Map existing entries
        existing_map = {e.student_id: e for e in att_session.entries}

        present = 0
        absent = 0
        late = 0
        leave = 0

        for item in entries_data:
            s_id = item["student_id"]
            status = item.get("status", "PRESENT").upper()
            remarks = item.get("remarks")
            method = item.get("marked_via", "WEB")

            if status == "PRESENT":
                present += 1
            elif status == "ABSENT":
                absent += 1
            elif status == "LATE":
                late += 1
            elif status in ("LEAVE", "HALF_DAY", "EXCUSED"):
                leave += 1

            if s_id in existing_map:
                entry = existing_map[s_id]
                entry.status = status
                entry.remarks = remarks
                entry.check_in_method = method
            else:
                entry = StudentAttendanceEntry(
                    tenant_id=tenant_id,
                    session_id=session_id,
                    student_id=s_id,
                    status=status,
                    remarks=remarks,
                    check_in_method=method,
                )
                self.session.add(entry)
                att_session.entries.append(entry)

        total = len(entries_data)
        att_session.total_students = total
        att_session.present_count = present
        att_session.absent_count = absent
        att_session.late_count = late
        att_session.leave_count = leave
        att_session.status = "SUBMITTED"

        await self.session.flush()
        return att_session

    async def correct_entry(
        self,
        tenant_id: uuid.UUID,
        entry_id: uuid.UUID,
        new_status: str,
        reason: str,
        corrected_by_user_id: uuid.UUID,
    ) -> StudentAttendanceEntry:
        stmt = (
            select(StudentAttendanceEntry)
            .where(
                StudentAttendanceEntry.tenant_id == tenant_id,
                StudentAttendanceEntry.id == entry_id,
            )
            .options(
                selectinload(StudentAttendanceEntry.session),
                selectinload(StudentAttendanceEntry.student).selectinload(StudentProfile.user),
            )
        )
        res = await self.session.execute(stmt)
        entry = res.scalars().first()
        if not entry:
            raise ValueError("Attendance entry not found")

        old_status = entry.status
        new_status = new_status.upper()

        if old_status != new_status:
            # Create correction log
            log = AttendanceCorrectionLog(
                tenant_id=tenant_id,
                entry_id=entry_id,
                previous_status=old_status,
                new_status=new_status,
                reason=reason,
                corrected_by_user_id=corrected_by_user_id,
            )
            self.session.add(log)

            # Update entry
            entry.status = new_status
            entry.remarks = f"[CORRECTED: {reason}]" if not entry.remarks else f"{entry.remarks} [CORRECTED: {reason}]"
            await self.session.flush()

            # Recalculate session counts
            att_session = entry.session
            if att_session:
                stmt_counts = select(
                    func.count().filter(StudentAttendanceEntry.status == "PRESENT"),
                    func.count().filter(StudentAttendanceEntry.status == "ABSENT"),
                    func.count().filter(StudentAttendanceEntry.status == "LATE"),
                    func.count().filter(StudentAttendanceEntry.status.in_(["LEAVE", "HALF_DAY", "EXCUSED"])),
                    func.count(),
                ).where(
                    StudentAttendanceEntry.session_id == att_session.id,
                    StudentAttendanceEntry.tenant_id == tenant_id,
                )
                counts_res = await self.session.execute(stmt_counts)
                row = counts_res.one()
                att_session.present_count = row[0] or 0
                att_session.absent_count = row[1] or 0
                att_session.late_count = row[2] or 0
                att_session.leave_count = row[3] or 0
                att_session.total_students = row[4] or 0
                await self.session.flush()

        return entry

    async def get_correction_logs(
        self,
        tenant_id: uuid.UUID,
        entry_id: Optional[uuid.UUID] = None,
        limit: int = 50,
    ) -> List[AttendanceCorrectionLog]:
        stmt = (
            select(AttendanceCorrectionLog)
            .where(AttendanceCorrectionLog.tenant_id == tenant_id)
            .order_by(desc(AttendanceCorrectionLog.corrected_at))
            .limit(limit)
        )
        if entry_id:
            stmt = stmt.where(AttendanceCorrectionLog.entry_id == entry_id)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_roster_for_marking(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: uuid.UUID,
        session_date: date,
        session_type: str = "DAILY",
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        semester_id: Optional[uuid.UUID] = None,
        subject_id: Optional[uuid.UUID] = None,
        period_number: Optional[int] = None,
    ) -> Tuple[Optional[StudentAttendanceSession], List[Dict[str, Any]]]:
        """
        Loads roster of students enrolled in the class/section or course/semester.
        If an attendance session already exists, maps their recorded status.
        """
        # Find existing session if already conducted
        existing_session = await self.find_existing_session(
            tenant_id=tenant_id,
            academic_session_id=academic_session_id,
            session_date=session_date,
            class_id=class_id,
            section_id=section_id,
            course_id=course_id,
            semester_id=semester_id,
            subject_id=subject_id,
            period_number=period_number,
            session_type=session_type,
        )

        existing_entries: Dict[uuid.UUID, StudentAttendanceEntry] = {}
        if existing_session:
            sess_with_entries = await self.get_session_by_id(tenant_id, existing_session.id, load_entries=True)
            if sess_with_entries:
                existing_entries = {e.student_id: e for e in sess_with_entries.entries}

        # Query enrolled students
        # Join StudentAcademicEnrollment with StudentProfile
        stmt = (
            select(StudentProfile, StudentAcademicEnrollment)
            .options(selectinload(StudentProfile.user))
            .join(StudentAcademicEnrollment, StudentAcademicEnrollment.student_id == StudentProfile.id)
            .where(
                StudentProfile.tenant_id == tenant_id,
                StudentProfile.is_deleted.is_(False),
                StudentProfile.status == "ACTIVE",
                StudentAcademicEnrollment.tenant_id == tenant_id,
                StudentAcademicEnrollment.academic_session_id == academic_session_id,
                StudentAcademicEnrollment.is_deleted.is_(False),
                StudentAcademicEnrollment.status == "ACTIVE",
            )
        )

        if course_id or semester_id:
            stmt = stmt.join(CollegeEnrollmentDetail, CollegeEnrollmentDetail.enrollment_id == StudentAcademicEnrollment.id)
            if course_id:
                stmt = stmt.where(CollegeEnrollmentDetail.course_id == course_id)
            if semester_id:
                stmt = stmt.where(CollegeEnrollmentDetail.semester_id == semester_id)
            if section_id:
                stmt = stmt.where(CollegeEnrollmentDetail.section_id == section_id)
        elif class_id or section_id:
            stmt = stmt.join(SchoolEnrollmentDetail, SchoolEnrollmentDetail.enrollment_id == StudentAcademicEnrollment.id)
            if class_id:
                stmt = stmt.where(SchoolEnrollmentDetail.class_id == class_id)
            if section_id:
                stmt = stmt.where(SchoolEnrollmentDetail.section_id == section_id)

        stmt = stmt.order_by(StudentProfile.admission_number.asc())
        res = await self.session.execute(stmt)
        rows = res.all()

        # Admissions created through Student Management store their placement on
        # the profile. Prefer formal enrollment whenever one exists for the session.
        existing_enrollment = select(StudentAcademicEnrollment.id).where(
            StudentAcademicEnrollment.tenant_id == tenant_id,
            StudentAcademicEnrollment.student_id == StudentProfile.id,
            StudentAcademicEnrollment.academic_session_id == academic_session_id,
            StudentAcademicEnrollment.is_deleted.is_(False),
        ).exists()
        selected_session = await self.session.scalar(select(AcademicSession).where(
            AcademicSession.id == academic_session_id, AcademicSession.tenant_id == tenant_id,
            AcademicSession.is_deleted.is_(False),
        ))
        active_session_count = await self.session.scalar(select(func.count()).select_from(AcademicSession).where(
            AcademicSession.tenant_id == tenant_id, AcademicSession.is_deleted.is_(False),
        ))
        session_match = StudentProfile.academic_session_id == academic_session_id
        if selected_session and (selected_session.is_current or active_session_count == 1):
            session_match = or_(session_match, StudentProfile.academic_session_id.is_(None))
        legacy = select(StudentProfile).options(selectinload(StudentProfile.user)).where(
            StudentProfile.tenant_id == tenant_id, StudentProfile.is_deleted.is_(False),
            StudentProfile.status == "ACTIVE", session_match, ~existing_enrollment,
        )
        if course_id:
            legacy = legacy.where(StudentProfile.course_id == course_id)
            if semester_id:
                semester_number = select(CollegeSemester.semester_number).where(
                    CollegeSemester.id == semester_id, CollegeSemester.tenant_id == tenant_id,
                    CollegeSemester.course_id == course_id, CollegeSemester.is_deleted.is_(False),
                ).scalar_subquery()
                legacy = legacy.where(StudentProfile.semester == semester_number)
        elif class_id:
            legacy = legacy.where(StudentProfile.class_id == class_id)
        else:
            legacy = legacy.where(False)
        if section_id:
            legacy = legacy.where(StudentProfile.section_id == section_id)
        legacy_students = (await self.session.scalars(legacy)).all()

        roster = []
        for student in [*(row[0] for row in rows), *legacy_students]:
            entry = existing_entries.get(student.id)
            roster.append({
                "student_id": student.id,
                "full_name": student.full_name,
                "admission_number": student.admission_number,
                "roll_number": student.roll_number,
                "current_status": entry.status if entry else None,
                "remarks": entry.remarks if entry else None,
                "parent_phone": student.parent_phone,
                "parent_email": student.parent_email,
            })

        roster.sort(key=lambda student: student["admission_number"] or "")
        return existing_session, roster

    async def get_student_attendance_summary(
        self,
        tenant_id: uuid.UUID,
        student_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Calculates student attendance percentage from valid conducted sessions and attendance records.
        """
        student = (await self.session.execute(
            select(StudentProfile)
            .options(selectinload(StudentProfile.user))
            .where(
                StudentProfile.tenant_id == tenant_id,
                StudentProfile.id == student_id,
            )
        )).scalar_one_or_none()

        if not student:
            raise ValueError("Student not found")

        # Query all submitted sessions where student had an entry
        stmt = (
            select(
                func.count(StudentAttendanceEntry.id).label("total_entries"),
                func.count().filter(StudentAttendanceEntry.status == "PRESENT").label("present"),
                func.count().filter(StudentAttendanceEntry.status == "ABSENT").label("absent"),
                func.count().filter(StudentAttendanceEntry.status == "LATE").label("late"),
                func.count().filter(StudentAttendanceEntry.status.in_(["LEAVE", "HALF_DAY", "EXCUSED"])).label("leave"),
            )
            .join(StudentAttendanceSession, StudentAttendanceSession.id == StudentAttendanceEntry.session_id)
            .where(
                StudentAttendanceEntry.tenant_id == tenant_id,
                StudentAttendanceEntry.student_id == student_id,
                StudentAttendanceSession.status == "SUBMITTED",
            )
        )
        if academic_session_id:
            stmt = stmt.where(StudentAttendanceSession.academic_session_id == academic_session_id)

        res = await self.session.execute(stmt)
        row = res.one()

        total = row.total_entries or 0
        present = row.present or 0
        absent = row.absent or 0
        late = row.late or 0
        leave = row.leave or 0

        attended = present + late
        pct = round((attended / total * 100.0), 2) if total > 0 else 100.0

        return {
            "student_id": student.id,
            "full_name": student.full_name,
            "admission_number": student.admission_number,
            "total_conducted": total,
            "total_attended": attended,
            "present_count": present,
            "absent_count": absent,
            "late_count": late,
            "leave_count": leave,
            "attendance_percentage": pct,
            "is_low_attendance": pct < 75.0,
        }

    async def get_low_attendance_students(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        threshold: float = 75.0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Finds students with attendance rate below threshold (e.g. 75%).
        """
        # Aggregate by student
        stmt = (
            select(
                StudentProfile.id,
                User.full_name,
                StudentProfile.admission_number,
                StudentProfile.parent_name,
                StudentProfile.parent_phone,
                func.count(StudentAttendanceEntry.id).label("total_sessions"),
                func.count().filter(StudentAttendanceEntry.status.in_(["PRESENT", "LATE"])).label("attended_sessions"),
            )
            .join(User, User.id == StudentProfile.user_id)
            .join(StudentAttendanceEntry, StudentAttendanceEntry.student_id == StudentProfile.id)
            .join(StudentAttendanceSession, StudentAttendanceSession.id == StudentAttendanceEntry.session_id)
            .where(
                StudentProfile.tenant_id == tenant_id,
                StudentProfile.status == "ACTIVE",
                StudentAttendanceSession.status == "SUBMITTED",
            )
            .group_by(
                StudentProfile.id,
                User.full_name,
                StudentProfile.admission_number,
                StudentProfile.parent_name,
                StudentProfile.parent_phone,
            )
            .having(func.count(StudentAttendanceEntry.id) > 0)
        )
        if academic_session_id:
            stmt = stmt.where(StudentAttendanceSession.academic_session_id == academic_session_id)

        res = await self.session.execute(stmt)
        rows = res.all()

        low_students = []
        for row in rows:
            total = row.total_sessions or 0
            attended = row.attended_sessions or 0
            pct = round((attended / total * 100.0), 2) if total > 0 else 100.0
            if pct < threshold:
                low_students.append({
                    "student_id": row.id,
                    "full_name": row.full_name,
                    "admission_number": row.admission_number,
                    "total_sessions": total,
                    "attended_sessions": attended,
                    "attendance_percentage": pct,
                    "parent_name": row.parent_name,
                    "parent_phone": row.parent_phone,
                })

        return low_students[:limit]

    async def get_monthly_attendance_report(
        self,
        tenant_id: uuid.UUID,
        student_id: uuid.UUID,
        year: int,
        month: int,
    ) -> Dict[str, Any]:
        """
        Generates day-by-day attendance report for a specific student and month.
        """
        student = (await self.session.execute(
            select(StudentProfile)
            .options(selectinload(StudentProfile.user))
            .where(
                StudentProfile.tenant_id == tenant_id,
                StudentProfile.id == student_id,
            )
        )).scalar_one_or_none()

        if not student:
            raise ValueError("Student not found")

        stmt = (
            select(
                StudentAttendanceSession.session_date,
                StudentAttendanceSession.period_number,
                StudentAttendanceEntry.status,
                Subject.name.label("subject_name"),
            )
            .join(StudentAttendanceSession, StudentAttendanceSession.id == StudentAttendanceEntry.session_id)
            .outerjoin(Subject, Subject.id == StudentAttendanceSession.subject_id)
            .where(
                StudentAttendanceEntry.tenant_id == tenant_id,
                StudentAttendanceEntry.student_id == student_id,
                func.extract("year", StudentAttendanceSession.session_date) == year,
                func.extract("month", StudentAttendanceSession.session_date) == month,
                StudentAttendanceSession.status == "SUBMITTED",
            )
            .order_by(StudentAttendanceSession.session_date.asc())
        )
        res = await self.session.execute(stmt)
        records_raw = res.all()

        records = []
        present_count = 0
        absent_count = 0
        late_count = 0
        leave_count = 0

        for r in records_raw:
            records.append({
                "date": r.session_date,
                "status": r.status,
                "period_number": r.period_number,
                "subject_name": r.subject_name,
            })
            if r.status == "PRESENT":
                present_count += 1
            elif r.status == "ABSENT":
                absent_count += 1
            elif r.status == "LATE":
                late_count += 1
            elif r.status in ("LEAVE", "HALF_DAY", "EXCUSED"):
                leave_count += 1

        conducted = len(records)
        attended = present_count + late_count
        pct = round((attended / conducted * 100.0), 2) if conducted > 0 else 100.0

        return {
            "student_id": student.id,
            "full_name": student.full_name,
            "admission_number": student.admission_number,
            "year": year,
            "month": month,
            "total_days": 31,  # Calendar days
            "conducted_days": conducted,
            "present_days": present_count,
            "absent_days": absent_count,
            "late_days": late_count,
            "leave_days": leave_count,
            "percentage": pct,
            "records": records,
        }

    async def get_admin_attendance_overview(
        self,
        tenant_id: uuid.UUID,
        target_date: date,
    ) -> Dict[str, Any]:
        """
        Dashboard statistics for Admin Attendance View.
        """
        # Count total active students enrolled
        tot_students_stmt = select(func.count(StudentProfile.id)).where(
            StudentProfile.tenant_id == tenant_id,
            StudentProfile.status == "ACTIVE",
        )
        tot_students = (await self.session.execute(tot_students_stmt)).scalar() or 0

        # Today's sessions & entries
        today_entries_stmt = (
            select(
                func.count(StudentAttendanceEntry.id).label("total_marked"),
                func.count().filter(StudentAttendanceEntry.status == "PRESENT").label("present"),
                func.count().filter(StudentAttendanceEntry.status == "ABSENT").label("absent"),
                func.count().filter(StudentAttendanceEntry.status == "LATE").label("late"),
                func.count().filter(StudentAttendanceEntry.status.in_(["LEAVE", "HALF_DAY", "EXCUSED"])).label("leave"),
            )
            .join(StudentAttendanceSession, StudentAttendanceSession.id == StudentAttendanceEntry.session_id)
            .where(
                StudentAttendanceSession.tenant_id == tenant_id,
                StudentAttendanceSession.session_date == target_date,
                StudentAttendanceSession.status == "SUBMITTED",
            )
        )
        row = (await self.session.execute(today_entries_stmt)).one()
        marked = row.total_marked or 0
        present = row.present or 0
        absent = row.absent or 0
        late = row.late or 0
        leave = row.leave or 0

        # Sessions conducted today
        sess_count_stmt = select(func.count(StudentAttendanceSession.id)).where(
            StudentAttendanceSession.tenant_id == tenant_id,
            StudentAttendanceSession.session_date == target_date,
            StudentAttendanceSession.status == "SUBMITTED",
        )
        sessions_today = (await self.session.execute(sess_count_stmt)).scalar() or 0

        # Low attendance count
        low_att_list = await self.get_low_attendance_students(tenant_id=tenant_id, threshold=75.0, limit=1000)

        rate = round(((present + late) / marked * 100.0), 2) if marked > 0 else 0.0

        return {
            "today": target_date,
            "total_students_enrolled": tot_students,
            "total_marked_today": marked,
            "overall_attendance_rate_today": rate,
            "total_present_today": present,
            "total_absent_today": absent,
            "total_late_today": late,
            "total_leave_today": leave,
            "low_attendance_students_count": len(low_att_list),
            "sessions_conducted_today": sessions_today,
        }

    async def log_device_event(
        self,
        tenant_id: uuid.UUID,
        device_id: str,
        device_type: str,
        identifier_tag: str,
        payload: Dict[str, Any],
        user_type: Optional[str] = None,
        matched_id: Optional[uuid.UUID] = None,
    ) -> AttendanceDeviceLog:
        log = AttendanceDeviceLog(
            tenant_id=tenant_id,
            device_id=device_id,
            device_type=device_type,
            identifier_tag=identifier_tag,
            user_type=user_type,
            matched_id=matched_id,
            payload=payload,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def find_student_by_rfid_or_admission(
        self,
        tenant_id: uuid.UUID,
        tag: str,
    ) -> Optional[StudentProfile]:
        stmt = (
            select(StudentProfile)
            .where(
                StudentProfile.tenant_id == tenant_id,
                or_(
                    StudentProfile.rfid_tag == tag,
                    StudentProfile.admission_number == tag,
                ),
            )
            .options(selectinload(StudentProfile.user))
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def find_teacher_by_rfid_or_employee_id(
        self,
        tenant_id: uuid.UUID,
        tag: str,
    ) -> Optional[TeacherProfile]:
        stmt = (
            select(TeacherProfile)
            .where(
                TeacherProfile.tenant_id == tenant_id,
                or_(
                    TeacherProfile.rfid_tag == tag,
                    TeacherProfile.employee_id == tag,
                ),
            )
            .options(selectinload(TeacherProfile.user))
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_college_cohort_attendance(
        self,
        tenant_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        semester_id: Optional[uuid.UUID] = None,
        academic_session_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all students enrolled in a college department/course/semester
        along with their overall attendance percentage across all subjects.
        """
        stmt = (
            select(
                StudentProfile.id.label("student_id"),
                StudentProfile.admission_number,
                StudentProfile.roll_number,
                StudentProfile.full_name,
                Department.id.label("department_id"),
                Department.name.label("department_name"),
                Course.id.label("course_id"),
                Course.name.label("course_name"),
                Course.code.label("course_code"),
                CollegeSemester.id.label("semester_id"),
                CollegeSemester.name.label("semester_name"),
                CollegeSemester.semester_number.label("semester_number"),
            )
            .join(StudentAcademicEnrollment, StudentAcademicEnrollment.student_id == StudentProfile.id)
            .join(CollegeEnrollmentDetail, CollegeEnrollmentDetail.enrollment_id == StudentAcademicEnrollment.id)
            .join(Course, Course.id == CollegeEnrollmentDetail.course_id)
            .outerjoin(Department, Department.id == Course.department_id)
            .outerjoin(CollegeSemester, CollegeSemester.id == CollegeEnrollmentDetail.semester_id)
            .where(
                StudentProfile.tenant_id == tenant_id,
                StudentProfile.is_deleted.is_(False),
                StudentAcademicEnrollment.tenant_id == tenant_id,
                StudentAcademicEnrollment.status == "ACTIVE",
            )
        )

        if department_id:
            stmt = stmt.where(
                or_(
                    Course.department_id == department_id,
                    CollegeEnrollmentDetail.department_id == department_id,
                )
            )
        if course_id:
            stmt = stmt.where(CollegeEnrollmentDetail.course_id == course_id)
        if semester_id:
            stmt = stmt.where(CollegeEnrollmentDetail.semester_id == semester_id)
        if academic_session_id:
            stmt = stmt.where(StudentAcademicEnrollment.academic_session_id == academic_session_id)
        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    StudentProfile.full_name.ilike(term),
                    StudentProfile.admission_number.ilike(term),
                    StudentProfile.roll_number.ilike(term),
                )
            )

        stmt = stmt.order_by(StudentProfile.admission_number.asc())
        res = await self.session.execute(stmt)
        students = res.all()

        if not students:
            # Fallback query if enrollment status is not strictly marked active
            alt_stmt = (
                select(
                    StudentProfile.id.label("student_id"),
                    StudentProfile.admission_number,
                    StudentProfile.roll_number,
                    StudentProfile.full_name,
                    Department.id.label("department_id"),
                    Department.name.label("department_name"),
                    Course.id.label("course_id"),
                    Course.name.label("course_name"),
                    Course.code.label("course_code"),
                    CollegeSemester.id.label("semester_id"),
                    CollegeSemester.name.label("semester_name"),
                    CollegeSemester.semester_number.label("semester_number"),
                )
                .join(StudentAcademicEnrollment, StudentAcademicEnrollment.student_id == StudentProfile.id)
                .join(CollegeEnrollmentDetail, CollegeEnrollmentDetail.enrollment_id == StudentAcademicEnrollment.id)
                .join(Course, Course.id == CollegeEnrollmentDetail.course_id)
                .outerjoin(Department, Department.id == Course.department_id)
                .outerjoin(CollegeSemester, CollegeSemester.id == CollegeEnrollmentDetail.semester_id)
                .where(
                    StudentProfile.tenant_id == tenant_id,
                    StudentProfile.is_deleted.is_(False),
                )
            )
            if department_id:
                alt_stmt = alt_stmt.where(or_(Course.department_id == department_id, CollegeEnrollmentDetail.department_id == department_id))
            if course_id:
                alt_stmt = alt_stmt.where(CollegeEnrollmentDetail.course_id == course_id)
            if semester_id:
                alt_stmt = alt_stmt.where(CollegeEnrollmentDetail.semester_id == semester_id)
            if search and search.strip():
                term = f"%{search.strip()}%"
                alt_stmt = alt_stmt.where(or_(StudentProfile.full_name.ilike(term), StudentProfile.admission_number.ilike(term), StudentProfile.roll_number.ilike(term)))
            alt_stmt = alt_stmt.order_by(StudentProfile.admission_number.asc())
            alt_res = await self.session.execute(alt_stmt)
            students = alt_res.all()

        if not students:
            return []

        student_ids = [s.student_id for s in students]

        # Aggregate attendance entries across ALL subjects for these students
        att_stmt = (
            select(
                StudentAttendanceEntry.student_id,
                func.count(StudentAttendanceEntry.id).label("total_classes"),
                func.count().filter(StudentAttendanceEntry.status == "PRESENT").label("present_count"),
                func.count().filter(StudentAttendanceEntry.status == "LATE").label("late_count"),
                func.count().filter(StudentAttendanceEntry.status == "ABSENT").label("absent_count"),
                func.count().filter(StudentAttendanceEntry.status.in_(["LEAVE", "HALF_DAY", "EXCUSED"])).label("leave_count"),
            )
            .join(StudentAttendanceSession, StudentAttendanceSession.id == StudentAttendanceEntry.session_id)
            .where(
                StudentAttendanceEntry.tenant_id == tenant_id,
                StudentAttendanceEntry.student_id.in_(student_ids),
                StudentAttendanceSession.status == "SUBMITTED",
            )
        )
        if academic_session_id:
            att_stmt = att_stmt.where(StudentAttendanceSession.academic_session_id == academic_session_id)
        att_stmt = att_stmt.group_by(StudentAttendanceEntry.student_id)

        att_res = await self.session.execute(att_stmt)
        att_map = {row.student_id: row for row in att_res.all()}

        results = []
        for s in students:
            att = att_map.get(s.student_id)
            total = att.total_classes if att else 0
            present = att.present_count if att else 0
            late = att.late_count if att else 0
            absent = att.absent_count if att else 0
            leave = att.leave_count if att else 0
            attended = present + late
            pct = round((attended / total * 100.0), 1) if total > 0 else 100.0

            results.append({
                "student_id": s.student_id,
                "admission_number": s.admission_number or "—",
                "roll_number": s.roll_number or "—",
                "full_name": s.full_name,
                "department_id": s.department_id,
                "department_name": s.department_name or "General",
                "course_id": s.course_id,
                "course_name": s.course_name,
                "course_code": s.course_code,
                "semester_id": s.semester_id,
                "semester_name": s.semester_name or (f"Semester {s.semester_number}" if s.semester_number else "N/A"),
                "semester_number": s.semester_number or 1,
                "total_classes": total,
                "attended_classes": attended,
                "present_count": present,
                "late_count": late,
                "absent_count": absent,
                "leave_count": leave,
                "attendance_percentage": pct,
                "status": "CRITICAL" if pct < 75.0 and total > 0 else "AVERAGE" if pct < 85.0 and total > 0 else "EXCELLENT",
            })

        return results
