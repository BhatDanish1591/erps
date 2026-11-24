from __future__ import annotations

import math
import secrets
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException, AuthorizationException, BadRequestException, ConflictException, NotFoundException
from app.core.logging import get_logger
from app.models.academic import (
    SchoolClass,
    Section,
    StudentParent,
    StudentProfile,
    Subject,
    TeacherAssignment,
    TeacherAttendance,
    TeacherLeave,
    TeacherProfile,
)
from app.models.attendance import (
    AttendanceCorrectionLog,
    AttendanceDeviceLog,
    StudentAttendanceEntry,
    StudentAttendanceSession,
)
from app.models.audit import AuditLog
from app.models.user import User
from app.repositories.attendance import AttendanceRepository
from app.services.notification_service import NotificationService
from app.schemas.attendance import (
    AdminAttendanceOverviewResponse,
    AttendanceCorrectionLogResponse,
    AttendanceRosterResponse,
    BiometricSyncBatchRequest,
    CollegeCohortAttendanceResponse,
    CollegeStudentAttendanceItem,
    DeviceSyncResultResponse,
    LowAttendanceAlertItem,
    QRCodeAttendanceResponse,
    QRCodeGenerateRequest,
    QRCodeScanSubmitRequest,
    RFIDSwipeRequest,
    StudentAttendanceCorrectionRequest,
    StudentAttendanceEntryResponse,
    StudentAttendanceSessionCreate,
    StudentAttendanceSessionResponse,
    StudentAttendanceSummaryResponse,
    StudentMonthlyAttendanceReport,
    TeacherAttendanceResponse,
    TeacherCheckInRequest,
    TeacherCheckOutRequest,
    TeacherLeaveActionRequest,
    TeacherLeaveApplyRequest,
    TeacherLeaveResponse,
)

logger = get_logger(__name__)


def calculate_haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two lat/lon coordinates."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class AttendanceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AttendanceRepository(session)

    async def get_marking_roster(
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
    ) -> AttendanceRosterResponse:
        existing_session, roster_students = await self.repo.get_roster_for_marking(
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
        )

        return AttendanceRosterResponse(
            academic_session_id=academic_session_id,
            session_date=session_date,
            session_type=session_type,
            class_id=class_id,
            section_id=section_id,
            subject_id=subject_id,
            period_number=period_number,
            existing_session_id=existing_session.id if existing_session else None,
            is_submitted=bool(existing_session and existing_session.status == "SUBMITTED"),
            students=roster_students,
        )

    async def submit_student_attendance(
        self,
        tenant_id: uuid.UUID,
        current_user: User,
        data: StudentAttendanceSessionCreate,
    ) -> StudentAttendanceSessionResponse:
        # Check if caller is teacher or admin
        teacher_profile: Optional[TeacherProfile] = None
        stmt_tp = select(TeacherProfile).where(
            TeacherProfile.tenant_id == tenant_id,
            TeacherProfile.user_id == current_user.id,
        )
        res_tp = await self.session.execute(stmt_tp)
        teacher_profile = res_tp.scalars().first()

        # Check for duplicate session
        existing = await self.repo.find_existing_session(
            tenant_id=tenant_id,
            academic_session_id=data.academic_session_id,
            session_date=data.session_date,
            class_id=data.class_id,
            section_id=data.section_id,
            course_id=data.course_id,
            semester_id=data.semester_id,
            subject_id=data.subject_id,
            period_number=data.period_number,
            session_type=data.session_type,
        )

        if existing:
            # Update existing session
            session_obj = existing
            session_obj.remarks = data.remarks or session_obj.remarks
        else:
            session_obj = await self.repo.create_attendance_session(
                tenant_id=tenant_id,
                academic_session_id=data.academic_session_id,
                session_date=data.session_date,
                session_type=data.session_type,
                class_id=data.class_id,
                section_id=data.section_id,
                course_id=data.course_id,
                semester_id=data.semester_id,
                subject_id=data.subject_id,
                period_number=data.period_number,
                conducted_by_teacher_id=teacher_profile.id if teacher_profile else None,
                remarks=data.remarks,
            )

        # Record entries
        entries_dicts = [entry.model_dump() for entry in data.entries]
        updated_session = await self.repo.record_entries(
            tenant_id=tenant_id,
            session_id=session_obj.id,
            entries_data=entries_dicts,
        )

        # Audit Log
        audit = AuditLog(
            tenant_id=tenant_id,
            user_id=current_user.id,
            action="SUBMIT_ATTENDANCE",
            entity_type="STUDENT_ATTENDANCE_SESSION",
            entity_id=str(updated_session.id),
            changes={
                "session_date": str(data.session_date),
                "total": updated_session.total_students,
                "present": updated_session.present_count,
                "absent": updated_session.absent_count,
                "late": updated_session.late_count,
                "leave": updated_session.leave_count,
            },
        )
        self.session.add(audit)

        # Handle absent parent notifications if requested
        if data.notify_absent_parents and updated_session.absent_count > 0:
            absent_student_ids = [e["student_id"] for e in entries_dicts if e.get("status") == "ABSENT"]
            await self._queue_absence_notifications(tenant_id, updated_session.id, data.session_date, absent_student_ids)

        await self.session.commit()

        # Reload with joined info
        full_session = await self.repo.get_session_by_id(tenant_id, updated_session.id, load_entries=True)
        return self._format_session_response(full_session)

    async def _queue_absence_notifications(
        self, tenant_id: uuid.UUID, session_id: uuid.UUID, session_date: date, student_ids: list[uuid.UUID],
    ) -> None:
        student_user = User.__table__.alias("absence_student_user")
        rows = await self.session.execute(
            select(StudentParent.student_id, student_user.c.full_name, User.id, User.email, User.phone)
            .select_from(StudentParent)
            .join(User, User.id == StudentParent.parent_user_id)
            .join(StudentProfile, StudentProfile.id == StudentParent.student_id)
            .join(student_user, student_user.c.id == StudentProfile.user_id)
            .where(
                StudentParent.tenant_id == tenant_id,
                StudentParent.student_id.in_(student_ids),
                StudentParent.status == "VERIFIED",
                StudentParent.is_deleted.is_(False),
                StudentProfile.tenant_id == tenant_id,
                StudentProfile.is_deleted.is_(False),
                User.is_active.is_(True),
                User.is_deleted.is_(False),
            )
        )
        notifications = NotificationService(self.session)
        for student_id, student_name, parent_id, email, phone in rows:
            await notifications.emit_event(
                tenant_id, "STUDENT_ABSENT",
                {
                    "title": "Student absence",
                    "message": f"{student_name} was marked absent on {session_date:%d %b %Y}.",
                    "student_name": student_name,
                    "date": session_date.isoformat(),
                    "student_id": str(student_id),
                    "attendance_session_id": str(session_id),
                    "recipients": [{"user_id": str(parent_id), "email": email, "phone": phone}],
                },
                idempotency_key=f"absence:{session_id}:{student_id}:{parent_id}",
            )

    async def correct_attendance(
        self,
        tenant_id: uuid.UUID,
        current_user: User,
        data: StudentAttendanceCorrectionRequest,
    ) -> StudentAttendanceEntryResponse:
        entry = await self.repo.correct_entry(
            tenant_id=tenant_id,
            entry_id=data.entry_id,
            new_status=data.new_status,
            reason=data.reason,
            corrected_by_user_id=current_user.id,
        )

        audit = AuditLog(
            tenant_id=tenant_id,
            user_id=current_user.id,
            action="CORRECT_ATTENDANCE_ENTRY",
            entity_type="STUDENT_ATTENDANCE_ENTRY",
            entity_id=str(entry.id),
            changes={
                "new_status": data.new_status,
                "reason": data.reason,
            },
        )
        self.session.add(audit)
        await self.session.commit()

        return StudentAttendanceEntryResponse(
            id=entry.id,
            session_id=entry.session_id,
            student_id=entry.student_id,
            student_name=entry.student.full_name if entry.student else None,
            admission_number=entry.student.admission_number if entry.student else None,
            roll_number=entry.student.roll_number if entry.student else None,
            status=entry.status,
            remarks=entry.remarks,
            marked_via=entry.check_in_method,
            marked_at=entry.created_at,
            is_corrected=True,
            corrected_at=entry.updated_at,
            correction_reason=data.reason,
        )

    async def get_correction_audit_logs(
        self,
        tenant_id: uuid.UUID,
        entry_id: Optional[uuid.UUID] = None,
        limit: int = 50,
    ) -> List[AttendanceCorrectionLogResponse]:
        logs = await self.repo.get_correction_logs(tenant_id=tenant_id, entry_id=entry_id, limit=limit)
        return [AttendanceCorrectionLogResponse.model_validate(l) for l in logs]

    async def get_student_summary(
        self,
        tenant_id: uuid.UUID,
        student_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
    ) -> StudentAttendanceSummaryResponse:
        summary = await self.repo.get_student_attendance_summary(
            tenant_id=tenant_id,
            student_id=student_id,
            academic_session_id=academic_session_id,
        )
        return StudentAttendanceSummaryResponse(**summary)

    async def get_low_attendance_alerts(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        threshold: float = 75.0,
        limit: int = 50,
    ) -> List[LowAttendanceAlertItem]:
        students = await self.repo.get_low_attendance_students(
            tenant_id=tenant_id,
            academic_session_id=academic_session_id,
            threshold=threshold,
            limit=limit,
        )
        return [LowAttendanceAlertItem(**s) for s in students]

    async def get_monthly_report(
        self,
        tenant_id: uuid.UUID,
        student_id: uuid.UUID,
        year: int,
        month: int,
    ) -> StudentMonthlyAttendanceReport:
        report = await self.repo.get_monthly_attendance_report(
            tenant_id=tenant_id,
            student_id=student_id,
            year=year,
            month=month,
        )
        return StudentMonthlyAttendanceReport(**report)

    async def get_admin_overview(
        self,
        tenant_id: uuid.UUID,
        target_date: Optional[date] = None,
    ) -> AdminAttendanceOverviewResponse:
        target = target_date or datetime.now(timezone.utc).date()
        overview = await self.repo.get_admin_attendance_overview(tenant_id=tenant_id, target_date=target)
        return AdminAttendanceOverviewResponse(**overview)

    async def get_college_cohort_attendance(
        self,
        tenant_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        semester_id: Optional[uuid.UUID] = None,
        academic_session_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
    ) -> CollegeCohortAttendanceResponse:
        records = await self.repo.get_college_cohort_attendance(
            tenant_id=tenant_id,
            department_id=department_id,
            course_id=course_id,
            semester_id=semester_id,
            academic_session_id=academic_session_id,
            search=search,
        )
        student_items = [CollegeStudentAttendanceItem(**r) for r in records]
        total_stus = len(student_items)
        avg_att = (
            round(sum(s.attendance_percentage for s in student_items) / total_stus, 1)
            if total_stus > 0
            else 0.0
        )
        critical_count = sum(1 for s in student_items if s.attendance_percentage < 75.0 and s.total_classes > 0)
        excellent_count = sum(1 for s in student_items if s.attendance_percentage >= 85.0)

        return CollegeCohortAttendanceResponse(
            department_id=department_id,
            course_id=course_id,
            semester_id=semester_id,
            total_students=total_stus,
            average_attendance=avg_att,
            critical_attendance_count=critical_count,
            excellent_attendance_count=excellent_count,
            students=student_items,
        )

    # -----------------------------------------------------------------------
    # Advanced QR Code Attendance
    # -----------------------------------------------------------------------

    async def generate_qr_attendance_session(
        self,
        tenant_id: uuid.UUID,
        current_user: User,
        academic_session_id: uuid.UUID,
        req: QRCodeGenerateRequest,
    ) -> QRCodeAttendanceResponse:
        qr_token = f"QR-ATT-{secrets.token_urlsafe(16)}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=req.validity_minutes)

        teacher_profile = (await self.session.execute(
            select(TeacherProfile).where(
                TeacherProfile.tenant_id == tenant_id,
                TeacherProfile.user_id == current_user.id,
            )
        )).scalars().first()

        today = datetime.now(timezone.utc).date()
        existing = await self.repo.find_existing_session(
            tenant_id=tenant_id,
            academic_session_id=academic_session_id,
            session_date=today,
            class_id=req.class_id,
            section_id=req.section_id,
            course_id=req.course_id,
            semester_id=req.semester_id,
            subject_id=req.subject_id,
            period_number=req.period_number,
            session_type="PERIOD_WISE" if req.period_number else "DAILY",
        )

        if not existing:
            session_obj = await self.repo.create_attendance_session(
                tenant_id=tenant_id,
                academic_session_id=academic_session_id,
                session_date=today,
                session_type="PERIOD_WISE" if req.period_number else "DAILY",
                class_id=req.class_id,
                section_id=req.section_id,
                course_id=req.course_id,
                semester_id=req.semester_id,
                subject_id=req.subject_id,
                period_number=req.period_number,
                conducted_by_teacher_id=teacher_profile.id if teacher_profile else None,
                remarks=f"QR Attendance Session (expires {expires_at.isoformat()})",
            )
        else:
            session_obj = existing

        session_obj.qr_token = qr_token
        session_obj.qr_expires_at = expires_at
        await self.session.commit()

        return QRCodeAttendanceResponse(
            qr_token=qr_token,
            session_id=session_obj.id,
            expires_at=expires_at,
            geo_fence_enabled=bool(req.latitude and req.longitude),
            allowed_radius_meters=req.allowed_radius_meters,
        )

    async def submit_qr_scan(
        self,
        tenant_id: uuid.UUID,
        current_user: User,
        scan_req: QRCodeScanSubmitRequest,
    ) -> StudentAttendanceEntryResponse:
        # Find session by qr_token
        stmt = select(StudentAttendanceSession).where(
            StudentAttendanceSession.tenant_id == tenant_id,
            StudentAttendanceSession.qr_token == scan_req.qr_token,
        )
        res = await self.session.execute(stmt)
        session_obj = res.scalars().first()
        if not session_obj:
            raise NotFoundException("Invalid or inactive QR code")

        now = datetime.now(timezone.utc)
        if session_obj.qr_expires_at and session_obj.qr_expires_at < now:
            raise BadRequestException("QR code has expired. Please ask the instructor to regenerate.")

        # Find student profile for user
        stmt_stu = (
            select(StudentProfile)
            .where(
                StudentProfile.tenant_id == tenant_id,
                StudentProfile.user_id == current_user.id,
            )
            .options(selectinload(StudentProfile.user))
        )
        stu_res = await self.session.execute(stmt_stu)
        student = stu_res.scalars().first()
        if not student:
            raise AuthorizationException("User is not enrolled as a student")

        _, roster = await self.repo.get_roster_for_marking(
            tenant_id=tenant_id,
            academic_session_id=session_obj.academic_session_id,
            session_date=session_obj.session_date,
            session_type=session_obj.session_type,
            class_id=session_obj.class_id,
            section_id=session_obj.section_id,
            course_id=session_obj.course_id,
            semester_id=session_obj.semester_id,
            subject_id=session_obj.subject_id,
            period_number=session_obj.period_number,
        )
        if not any(row["student_id"] == student.id for row in roster):
            raise AuthorizationException("You are not enrolled in this attendance group.")

        # Record entry
        updated_sess = await self.repo.record_entries(
            tenant_id=tenant_id,
            session_id=session_obj.id,
            entries_data=[{
                "student_id": student.id,
                "status": "PRESENT",
                "remarks": "Marked via QR Code Scan",
                "marked_via": "QR",
            }],
        )
        await self.session.commit()

        # Return entry
        stmt_entry = select(StudentAttendanceEntry).where(
            StudentAttendanceEntry.tenant_id == tenant_id,
            StudentAttendanceEntry.session_id == session_obj.id,
            StudentAttendanceEntry.student_id == student.id,
        )
        entry = (await self.session.execute(stmt_entry)).scalars().first()

        return StudentAttendanceEntryResponse(
            id=entry.id,
            session_id=entry.session_id,
            student_id=student.id,
            student_name=current_user.full_name,
            admission_number=student.admission_number,
            roll_number=student.roll_number,
            status=entry.status,
            remarks=entry.remarks,
            marked_via=entry.check_in_method,
            marked_at=entry.created_at,
        )

    # -----------------------------------------------------------------------
    # RFID & Biometric Integration
    # -----------------------------------------------------------------------

    async def process_rfid_swipe(
        self,
        tenant_id: uuid.UUID,
        req: RFIDSwipeRequest,
    ) -> Dict[str, Any]:
        tag = req.rfid_tag.strip()
        student = await self.repo.find_student_by_rfid_or_admission(tenant_id, tag)
        teacher = await self.repo.find_teacher_by_rfid_or_employee_id(tenant_id, tag) if not student else None

        user_type = "STUDENT" if student else ("TEACHER" if teacher else "UNKNOWN")
        matched_id = student.id if student else (teacher.id if teacher else None)

        device_log = await self.repo.log_device_event(
            tenant_id=tenant_id,
            device_id=req.device_id,
            device_type="RFID",
            identifier_tag=tag,
            user_type=user_type,
            matched_id=matched_id,
            payload=req.model_dump(mode="json"),
        )

        today = datetime.now(timezone.utc).date()
        result_msg = "Device log recorded"

        if student:
            result_msg = f"RFID swipe recorded for {student.full_name} ({student.admission_number})"
        elif teacher:
            # Teacher daily check-in
            now_time = datetime.now(timezone.utc).time()
            time_str = now_time.strftime("%H:%M:%S")
            stmt_t_att = select(TeacherAttendance).where(
                TeacherAttendance.tenant_id == tenant_id,
                TeacherAttendance.teacher_id == teacher.id,
                TeacherAttendance.attendance_date == today,
            )
            t_att = (await self.session.execute(stmt_t_att)).scalars().first()
            if not t_att:
                t_att = TeacherAttendance(
                    tenant_id=tenant_id,
                    teacher_id=teacher.id,
                    attendance_date=today,
                    status="PRESENT",
                    check_in_time=time_str,
                    remarks="RFID Check-in",
                )
                self.session.add(t_att)
            else:
                t_att.check_out_time = time_str
            result_msg = f"Teacher {teacher.user.full_name if teacher.user else teacher.employee_id} ({teacher.employee_id}) check-in recorded via RFID"

        await self.session.commit()
        return {
            "status": "SUCCESS",
            "device_log_id": device_log.id,
            "user_type": user_type,
            "matched_id": matched_id,
            "message": result_msg,
        }

    async def process_biometric_sync(
        self,
        tenant_id: uuid.UUID,
        batch_req: BiometricSyncBatchRequest,
    ) -> DeviceSyncResultResponse:
        success = 0
        failure = 0
        failures_list = []

        for record in batch_req.records:
            try:
                student = await self.repo.find_student_by_rfid_or_admission(tenant_id, record.user_identifier)
                teacher = await self.repo.find_teacher_by_rfid_or_employee_id(tenant_id, record.user_identifier) if not student else None
                user_type = "STUDENT" if student else ("TEACHER" if teacher else "UNKNOWN")
                matched_id = student.id if student else (teacher.id if teacher else None)

                await self.repo.log_device_event(
                    tenant_id=tenant_id,
                    device_id=record.device_id,
                    device_type="BIOMETRIC",
                    identifier_tag=record.user_identifier,
                    user_type=user_type,
                    matched_id=matched_id,
                    payload=record.model_dump(mode="json"),
                )
                success += 1
            except Exception as e:
                failure += 1
                failures_list.append({"identifier": record.user_identifier, "error": str(e)})

        await self.session.commit()
        return DeviceSyncResultResponse(
            processed_count=len(batch_req.records),
            success_count=success,
            failure_count=failure,
            failures=failures_list,
        )

    # -----------------------------------------------------------------------
    # Teacher Attendance & Leave
    # -----------------------------------------------------------------------

    async def teacher_check_in(
        self,
        tenant_id: uuid.UUID,
        current_user: User,
        req: TeacherCheckInRequest,
    ) -> TeacherAttendanceResponse:
        teacher = (await self.session.execute(
            select(TeacherProfile).where(
                TeacherProfile.tenant_id == tenant_id,
                TeacherProfile.user_id == current_user.id,
            )
        )).scalars().first()
        if not teacher:
            raise NotFoundException("Teacher profile not found for user")

        today = datetime.now(timezone.utc).date()
        now_time = datetime.now(timezone.utc).time()
        time_str = now_time.strftime("%H:%M:%S")

        stmt = select(TeacherAttendance).where(
            TeacherAttendance.tenant_id == tenant_id,
            TeacherAttendance.teacher_id == teacher.id,
            TeacherAttendance.attendance_date == today,
        )
        record = (await self.session.execute(stmt)).scalars().first()

        if record and record.check_in_time:
            raise ConflictException("Teacher has already checked in for today")

        note_str = f"Method: {req.check_in_method} | Notes: {req.notes or ''}"
        if not record:
            record = TeacherAttendance(
                tenant_id=tenant_id,
                teacher_id=teacher.id,
                attendance_date=today,
                status="PRESENT",
                check_in_time=time_str,
                remarks=note_str,
                recorded_by_user_id=current_user.id,
            )
            self.session.add(record)
        else:
            record.check_in_time = time_str
            record.status = "PRESENT"
            record.remarks = note_str

        await self.session.commit()
        return TeacherAttendanceResponse(
            id=record.id,
            teacher_id=teacher.id,
            teacher_name=current_user.full_name,
            employee_id=teacher.employee_id,
            attendance_date=record.attendance_date,
            status=record.status,
            check_in_time=record.check_in_time,
            check_out_time=record.check_out_time,
            working_hours=None,
            check_in_method=req.check_in_method,
            notes=record.remarks,
        )

    async def teacher_check_out(
        self,
        tenant_id: uuid.UUID,
        current_user: User,
        req: TeacherCheckOutRequest,
    ) -> TeacherAttendanceResponse:
        teacher = (await self.session.execute(
            select(TeacherProfile).where(
                TeacherProfile.tenant_id == tenant_id,
                TeacherProfile.user_id == current_user.id,
            )
        )).scalars().first()
        if not teacher:
            raise NotFoundException("Teacher profile not found for user")

        today = datetime.now(timezone.utc).date()
        now_time = datetime.now(timezone.utc).time()
        time_str = now_time.strftime("%H:%M:%S")

        stmt = select(TeacherAttendance).where(
            TeacherAttendance.tenant_id == tenant_id,
            TeacherAttendance.teacher_id == teacher.id,
            TeacherAttendance.attendance_date == today,
        )
        record = (await self.session.execute(stmt)).scalars().first()
        if not record or not record.check_in_time:
            raise BadRequestException("Cannot check out without checking in first")

        record.check_out_time = time_str
        if req.notes:
            record.remarks = f"{record.remarks or ''} | Out: {req.notes}"

        await self.session.commit()
        return TeacherAttendanceResponse(
            id=record.id,
            teacher_id=teacher.id,
            teacher_name=current_user.full_name,
            employee_id=teacher.employee_id,
            attendance_date=record.attendance_date,
            status=record.status,
            check_in_time=record.check_in_time,
            check_out_time=record.check_out_time,
            working_hours=None,
            check_in_method="WEB",
            notes=record.remarks,
        )

    async def apply_teacher_leave(
        self,
        tenant_id: uuid.UUID,
        current_user: User,
        req: TeacherLeaveApplyRequest,
    ) -> TeacherLeaveResponse:
        teacher = (await self.session.execute(
            select(TeacherProfile).where(
                TeacherProfile.tenant_id == tenant_id,
                TeacherProfile.user_id == current_user.id,
            )
        )).scalars().first()
        if not teacher:
            raise NotFoundException("Teacher profile not found")

        total_days = max(1, (req.end_date - req.start_date).days + 1)
        leave = TeacherLeave(
            tenant_id=tenant_id,
            teacher_id=teacher.id,
            leave_type=req.leave_type.upper(),
            start_date=req.start_date,
            end_date=req.end_date,
            days_count=float(total_days),
            reason=req.reason,
            status="PENDING",
        )
        self.session.add(leave)
        await self.session.commit()

        return TeacherLeaveResponse(
            id=leave.id,
            teacher_id=teacher.id,
            teacher_name=current_user.full_name,
            employee_id=teacher.employee_id,
            leave_type=leave.leave_type,
            start_date=leave.start_date,
            end_date=leave.end_date,
            total_days=int(leave.days_count),
            reason=leave.reason,
            status=leave.status,
            rejection_reason=leave.rejection_reason,
            created_at=leave.created_at,
        )

    async def action_teacher_leave(
        self,
        tenant_id: uuid.UUID,
        leave_id: uuid.UUID,
        current_user: User,
        req: TeacherLeaveActionRequest,
    ) -> TeacherLeaveResponse:
        stmt = (
            select(TeacherLeave)
            .where(
                TeacherLeave.tenant_id == tenant_id,
                TeacherLeave.id == leave_id,
            )
            .options(selectinload(TeacherLeave.teacher).selectinload(TeacherProfile.user))
        )
        res = await self.session.execute(stmt)
        leave = res.scalars().first()
        if not leave:
            raise NotFoundException("Leave request not found")

        action = req.action.upper()
        if action == "APPROVE":
            leave.status = "APPROVED"
            leave.approved_by_user_id = current_user.id
        elif action == "REJECT":
            leave.status = "REJECTED"
            leave.rejection_reason = req.rejection_reason or "Rejected by administrator"
        else:
            raise BadRequestException("Action must be APPROVE or REJECT")

        await self.session.commit()
        return TeacherLeaveResponse(
            id=leave.id,
            teacher_id=leave.teacher_id,
            teacher_name=leave.teacher.user.full_name if leave.teacher and leave.teacher.user else None,
            employee_id=leave.teacher.employee_id if leave.teacher else None,
            leave_type=leave.leave_type,
            start_date=leave.start_date,
            end_date=leave.end_date,
            total_days=int(leave.days_count),
            reason=leave.reason,
            status=leave.status,
            rejection_reason=leave.rejection_reason,
            created_at=leave.created_at,
        )

    # -----------------------------------------------------------------------
    # Helper formatters
    # -----------------------------------------------------------------------

    def _format_session_response(self, sess: StudentAttendanceSession) -> StudentAttendanceSessionResponse:
        tot = sess.total_students
        rate = round(((sess.present_count + sess.late_count) / tot * 100.0), 2) if tot > 0 else 0.0

        entry_responses = []
        if sess.entries:
            for e in sess.entries:
                entry_responses.append(
                    StudentAttendanceEntryResponse(
                        id=e.id,
                        session_id=e.session_id,
                        student_id=e.student_id,
                        student_name=e.student.full_name if e.student else None,
                        admission_number=e.student.admission_number if e.student else None,
                        roll_number=e.student.roll_number if e.student else None,
                        status=e.status,
                        remarks=e.remarks,
                        marked_via=e.check_in_method,
                        marked_at=e.created_at,
                    )
                )

        return StudentAttendanceSessionResponse(
            id=sess.id,
            tenant_id=sess.tenant_id,
            academic_session_id=sess.academic_session_id,
            session_date=sess.session_date,
            session_type=sess.session_type,
            class_id=sess.class_id,
            section_id=sess.section_id,
            course_id=sess.course_id,
            semester_id=sess.semester_id,
            subject_id=sess.subject_id,
            period_number=sess.period_number,
            conducted_by_teacher_id=sess.conducted_by_teacher_id,
            teacher_name=sess.conducted_by.user.full_name if sess.conducted_by and sess.conducted_by.user else None,
            class_name=sess.school_class.name if sess.school_class else None,
            section_name=sess.section.name if sess.section else None,
            subject_name=sess.subject.name if sess.subject else None,
            status=sess.status,
            total_students=sess.total_students,
            present_count=sess.present_count,
            absent_count=sess.absent_count,
            late_count=sess.late_count,
            leave_count=sess.leave_count,
            attendance_rate=rate,
            remarks=sess.remarks,
            submitted_at=sess.updated_at,
            entries=entry_responses,
        )
