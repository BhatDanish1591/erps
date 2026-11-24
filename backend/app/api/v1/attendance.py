from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException, AuthorizationException, BadRequestException
from app.dependencies.tenant import get_registered_institution_type
from app.models.academic import AcademicSession, CollegeSemester, Course, SchoolClass, Section
from app.models.enums import InstitutionType
from app.models.attendance import StudentAttendanceEntry, StudentAttendanceSession
from app.models.user import User
from app.permissions.rbac import get_active_tenant_id, get_current_user, get_teacher_scope_user, require_any_role, require_permission
from app.schemas.attendance import (
    AdminAttendanceOverviewResponse,
    AttendanceCorrectionLogResponse,
    AttendanceRosterResponse,
    BiometricSyncBatchRequest,
    CollegeCohortAttendanceResponse,
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
from app.services.attendance_service import AttendanceService
from app.repositories.attendance import AttendanceRepository
from app.services.staff_access_service import require_teaching_assignment

router = APIRouter(prefix="/attendance", tags=["Attendance Management"])


@router.get("/cohort-report")
async def get_cohort_report(
    academic_session_id: uuid.UUID,
    department_id: Optional[uuid.UUID] = None,
    course_id: Optional[uuid.UUID] = None,
    semester_id: Optional[uuid.UUID] = None,
    class_id: Optional[uuid.UUID] = None,
    section_id: Optional[uuid.UUID] = None,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    institution_type: InstitutionType = Depends(get_registered_institution_type),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if not await session.scalar(select(AcademicSession.id).where(
        AcademicSession.id == academic_session_id, AcademicSession.tenant_id == tenant_id,
        AcademicSession.is_deleted.is_(False),
    )):
        raise BadRequestException("Select an academic session in this institution.")
    if institution_type == InstitutionType.COLLEGE:
        if not (department_id and course_id and semester_id) or class_id or section_id:
            raise BadRequestException("Select a department, course, and semester.")
        matches = await session.scalar(
            select(CollegeSemester.id).join(Course, Course.id == CollegeSemester.course_id).where(
                CollegeSemester.id == semester_id, CollegeSemester.tenant_id == tenant_id,
                CollegeSemester.is_deleted.is_(False), Course.id == course_id, Course.tenant_id == tenant_id,
                Course.department_id == department_id, Course.is_deleted.is_(False),
            )
        )
        if not matches:
            raise BadRequestException("The semester must belong to the selected course and department.")
    elif not class_id or department_id or course_id or semester_id:
        raise BadRequestException("Select a school class and optionally a section.")
    elif not await session.scalar(select(SchoolClass.id).where(
        SchoolClass.id == class_id, SchoolClass.tenant_id == tenant_id, SchoolClass.is_deleted.is_(False),
    )):
        raise BadRequestException("Select a class in this school.")
    elif section_id and not await session.scalar(select(Section.id).where(
        Section.id == section_id, Section.class_id == class_id, Section.tenant_id == tenant_id,
        Section.is_deleted.is_(False),
    )):
        raise BadRequestException("The section must belong to the selected class.")
    report = await AttendanceRepository(session).get_cohort_report(
        tenant_id, academic_session_id, class_id=class_id, section_id=section_id,
        course_id=course_id, semester_id=semester_id,
    )
    return {"success": True, "data": report}


# ── Admin Attendance Dashboard Overview ────────────────────────────────────────
@router.get("/overview", response_model=Dict[str, Any])
async def get_attendance_overview(
    target_date: Optional[date] = Query(None, description="Overview date (default: today)"),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = AttendanceService(session)
    overview = await service.get_admin_overview(tenant_id=tenant_id, target_date=target_date)
    return {"success": True, "data": overview.model_dump()}


# ── College Cohort Attendance Directory ───────────────────────────────────────
@router.get("/college/cohort-attendance", response_model=Dict[str, Any])
async def get_college_cohort_attendance(
    department_id: Optional[uuid.UUID] = Query(None, description="Department ID filter"),
    course_id: Optional[uuid.UUID] = Query(None, description="Course ID filter"),
    semester_id: Optional[uuid.UUID] = Query(None, description="Semester ID filter"),
    academic_session_id: Optional[uuid.UUID] = Query(None, description="Academic Session ID"),
    search: Optional[str] = Query(None, description="Search student by name, admission no, or roll no"),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = AttendanceService(session)
    result = await service.get_college_cohort_attendance(
        tenant_id=tenant_id,
        department_id=department_id,
        course_id=course_id,
        semester_id=semester_id,
        academic_session_id=academic_session_id,
        search=search,
    )
    return {"success": True, "data": result.model_dump()}


# ── Teacher Roster for Marking Attendance ─────────────────────────────────────
@router.get("/roster", response_model=Dict[str, Any])
async def get_attendance_roster(
    academic_session_id: uuid.UUID = Query(..., description="Active academic session ID"),
    session_date: date = Query(..., description="Attendance date"),
    session_type: str = Query("DAILY", description="DAILY, PERIOD_WISE, SUBJECT_WISE"),
    class_id: Optional[uuid.UUID] = Query(None),
    section_id: Optional[uuid.UUID] = Query(None),
    course_id: Optional[uuid.UUID] = Query(None),
    semester_id: Optional[uuid.UUID] = Query(None),
    subject_id: Optional[uuid.UUID] = Query(None),
    period_number: Optional[int] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["TEACHER", "INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    teacher_user_id: Optional[uuid.UUID] = Depends(get_teacher_scope_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await require_teaching_assignment(
        session, tenant_id, teacher_user_id, academic_session_id,
        class_id=class_id, section_id=section_id, course_id=course_id, semester_id=semester_id, subject_id=subject_id,
    )
    service = AttendanceService(session)
    roster = await service.get_marking_roster(
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
    return {"success": True, "data": roster.model_dump()}


# ── Submit Student Attendance Session ─────────────────────────────────────────
@router.post("/sessions", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def submit_attendance_session(
    payload: StudentAttendanceSessionCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["TEACHER", "INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    teacher_user_id: Optional[uuid.UUID] = Depends(get_teacher_scope_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await require_teaching_assignment(
        session, tenant_id, teacher_user_id, payload.academic_session_id,
        class_id=payload.class_id, section_id=payload.section_id, course_id=payload.course_id,
        semester_id=payload.semester_id, subject_id=payload.subject_id,
    )
    service = AttendanceService(session)
    if teacher_user_id is not None:
        roster = await service.get_marking_roster(
            tenant_id, payload.academic_session_id, payload.session_date, payload.session_type,
            payload.class_id, payload.section_id, payload.course_id, payload.semester_id,
            payload.subject_id, payload.period_number,
        )
        roster_ids = {student.student_id for student in roster.students}
        if any(entry.student_id not in roster_ids for entry in payload.entries):
            raise AuthorizationException("Attendance can only be recorded for students in this roster.")
    result = await service.submit_student_attendance(
        tenant_id=tenant_id,
        current_user=current_user,
        data=payload,
    )
    return {"success": True, "data": result.model_dump(), "message": "Attendance recorded successfully"}


# ── Attendance Correction ──────────────────────────────────────────────────────
@router.post("/entries/correct", response_model=Dict[str, Any])
async def correct_attendance_entry(
    payload: StudentAttendanceCorrectionRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    teacher_user_id: Optional[uuid.UUID] = Depends(get_teacher_scope_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if teacher_user_id is not None:
        recorded = await session.scalar(
            select(StudentAttendanceSession)
            .join(StudentAttendanceEntry, StudentAttendanceEntry.session_id == StudentAttendanceSession.id)
            .where(
                StudentAttendanceEntry.id == payload.entry_id,
                StudentAttendanceEntry.tenant_id == tenant_id,
                StudentAttendanceSession.tenant_id == tenant_id,
                StudentAttendanceSession.is_deleted.is_(False),
            )
        )
        if not recorded:
            raise AuthorizationException("This entry is outside your teaching assignments.")
        await require_teaching_assignment(
            session, tenant_id, teacher_user_id, recorded.academic_session_id,
            class_id=recorded.class_id, section_id=recorded.section_id, course_id=recorded.course_id,
            semester_id=recorded.semester_id, subject_id=recorded.subject_id,
        )
    service = AttendanceService(session)
    entry = await service.correct_attendance(
        tenant_id=tenant_id,
        current_user=current_user,
        data=payload,
    )
    return {"success": True, "data": entry.model_dump(), "message": "Attendance corrected successfully"}


# ── Correction Audit Trail ─────────────────────────────────────────────────────
@router.get("/corrections", response_model=Dict[str, Any])
async def get_correction_audit_logs(
    entry_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = AttendanceService(session)
    logs = await service.get_correction_audit_logs(tenant_id=tenant_id, entry_id=entry_id, limit=limit)
    return {"success": True, "data": [l.model_dump() for l in logs]}


# ── Low Attendance Alerts ──────────────────────────────────────────────────────
@router.get("/low-attendance", response_model=Dict[str, Any])
async def get_low_attendance_alerts(
    threshold: float = Query(75.0, ge=0.0, le=100.0, description="Attendance threshold percentage"),
    academic_session_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = AttendanceService(session)
    alerts = await service.get_low_attendance_alerts(
        tenant_id=tenant_id,
        academic_session_id=academic_session_id,
        threshold=threshold,
        limit=limit,
    )
    return {"success": True, "data": [a.model_dump() for a in alerts]}


# ── Student Attendance Summary (Student / Parent / Staff) ──────────────────────
@router.get("/students/{student_id}/summary", response_model=Dict[str, Any])
async def get_student_attendance_summary(
    student_id: uuid.UUID,
    academic_session_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["STUDENT", "PARENT", "TEACHER", "INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = AttendanceService(session)
    summary = await service.get_student_summary(
        tenant_id=tenant_id,
        student_id=student_id,
        academic_session_id=academic_session_id,
    )
    return {"success": True, "data": summary.model_dump()}


# ── Monthly Attendance Calendar / Report ──────────────────────────────────────
@router.get("/students/{student_id}/monthly", response_model=Dict[str, Any])
async def get_student_monthly_report(
    student_id: uuid.UUID,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["STUDENT", "PARENT", "TEACHER", "INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = AttendanceService(session)
    report = await service.get_monthly_report(
        tenant_id=tenant_id,
        student_id=student_id,
        year=year,
        month=month,
    )
    return {"success": True, "data": report.model_dump()}


# ── QR Code Attendance ─────────────────────────────────────────────────────────
@router.post("/qr/generate", response_model=Dict[str, Any])
async def generate_qr_attendance(
    payload: QRCodeGenerateRequest,
    academic_session_id: uuid.UUID = Query(..., description="Active academic session ID"),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["TEACHER", "INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    teacher_user_id: Optional[uuid.UUID] = Depends(get_teacher_scope_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await require_teaching_assignment(
        session, tenant_id, teacher_user_id, academic_session_id,
        class_id=payload.class_id, section_id=payload.section_id, course_id=payload.course_id,
        semester_id=payload.semester_id, subject_id=payload.subject_id,
    )
    service = AttendanceService(session)
    qr_data = await service.generate_qr_attendance_session(
        tenant_id=tenant_id,
        current_user=current_user,
        academic_session_id=academic_session_id,
        req=payload,
    )
    return {"success": True, "data": qr_data.model_dump()}


@router.post("/qr/scan", response_model=Dict[str, Any])
async def scan_qr_attendance(
    payload: QRCodeScanSubmitRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["STUDENT", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = AttendanceService(session)
    entry = await service.submit_qr_scan(
        tenant_id=tenant_id,
        current_user=current_user,
        scan_req=payload,
    )
    return {"success": True, "data": entry.model_dump(), "message": "Attendance marked successfully via QR scan"}


# ── Hardware Integrations (RFID & Biometric Webhooks) ──────────────────────────
@router.post("/hardware/rfid-swipe", response_model=Dict[str, Any])
async def handle_rfid_swipe(
    payload: RFIDSwipeRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = AttendanceService(session)
    res = await service.process_rfid_swipe(tenant_id=tenant_id, req=payload)
    return {"success": True, "data": res}


@router.post("/hardware/biometric-sync", response_model=Dict[str, Any])
async def handle_biometric_sync(
    payload: BiometricSyncBatchRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = AttendanceService(session)
    res = await service.process_biometric_sync(tenant_id=tenant_id, batch_req=payload)
    return {"success": True, "data": res.model_dump()}


# ── Teacher Check-in / Check-out ──────────────────────────────────────────────
@router.post("/teacher/check-in", response_model=Dict[str, Any])
async def teacher_check_in(
    payload: TeacherCheckInRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["TEACHER", "INSTITUTION_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = AttendanceService(session)
    record = await service.teacher_check_in(tenant_id=tenant_id, current_user=current_user, req=payload)
    return {"success": True, "data": record.model_dump(), "message": "Checked in successfully"}


@router.post("/teacher/check-out", response_model=Dict[str, Any])
async def teacher_check_out(
    payload: TeacherCheckOutRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["TEACHER", "INSTITUTION_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = AttendanceService(session)
    record = await service.teacher_check_out(tenant_id=tenant_id, current_user=current_user, req=payload)
    return {"success": True, "data": record.model_dump(), "message": "Checked out successfully"}


# ── Teacher Leave Applications & Approvals ────────────────────────────────────
@router.post("/teacher/leaves", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def apply_teacher_leave(
    payload: TeacherLeaveApplyRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = AttendanceService(session)
    leave = await service.apply_teacher_leave(tenant_id=tenant_id, current_user=current_user, req=payload)
    return {"success": True, "data": leave.model_dump(), "message": "Leave application submitted"}


@router.put("/teacher/leaves/{leave_id}", response_model=Dict[str, Any])
async def action_teacher_leave(
    leave_id: uuid.UUID,
    payload: TeacherLeaveActionRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = AttendanceService(session)
    leave = await service.action_teacher_leave(
        tenant_id=tenant_id,
        leave_id=leave_id,
        current_user=current_user,
        req=payload,
    )
    return {"success": True, "data": leave.model_dump(), "message": f"Leave {payload.action} successfully"}
