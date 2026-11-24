from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException, AuthorizationException
from app.core.logging import get_logger
from app.models.academic import (
    AcademicSession,
    Course,
    Department,
    SchoolClass,
    Section,
    Subject,
    TeacherAssignment,
    TeacherAttendance,
    TeacherDocument,
    TeacherLeave,
    TeacherProfile,
    TimetableEntry,
)
from app.models.tenant import Tenant
from app.models.auth import Membership, Role
from app.models.attendance import StudentAttendanceSession
from app.models.enums import MembershipStatus
from app.models.examination import Examination
from app.models.lms import Assignment, AssignmentSubmission
from app.models.user import User
from app.repositories.teacher import TeacherRepository
from app.repositories.notification import NotificationRepository
from app.schemas.teacher import (
    TeacherAssignmentCreateRequest,
    TeacherAssignmentSchema,
    TeacherAttendanceRecordRequest,
    TeacherAttendanceResponse,
    TeacherCreateRequest,
    TeacherDashboardSummary,
    TeacherDocumentCreateRequest,
    TeacherDocumentResponse,
    TeacherLeaveApplyRequest,
    TeacherLeaveResponse,
    TeacherLeaveReviewRequest,
    TeacherResponse,
    TeacherUpdateRequest,
    TeacherWorkloadResponse,
    TimetableEntryCreateRequest,
    TimetableEntrySchema,
)
from app.services.entitlement_service import EntitlementService
from app.services.staff_access_service import StaffAccess, staff_role_query

logger = get_logger(__name__)


class TeacherService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TeacherRepository(session)
        self.entitlement_service = EntitlementService(session)

    # ── Create Teacher ────────────────────────────────────────────────────────
    async def create_teacher(
        self,
        tenant_id: uuid.UUID,
        payload: TeacherCreateRequest,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> TeacherResponse:
        # 1. Dynamic Entitlement Check: Verify tenant has teacher/faculty quota
        await self.entitlement_service.check_quota(tenant_id, "teachers", increment=1)

        # 2. Employee ID Generation / Uniqueness
        employee_id = payload.employee_id
        if not employee_id or not employee_id.strip():
            employee_id = await self.repo.generate_employee_id(tenant_id)
        else:
            employee_id = employee_id.strip()
            existing = await self.repo.get_teacher_by_employee_id(tenant_id, employee_id)
            if existing:
                raise AppException(409, "DUPLICATE_EMPLOYEE_ID", f"Employee ID '{employee_id}' already exists in this institution.")

        # 3. Create or Link User
        if payload.initial_password and not payload.email:
            raise AppException(422, "STAFF_EMAIL_REQUIRED", "Enter an email address to set up staff sign-in.")
        if payload.email:
            teacher_email = payload.email
        else:
            tenant_obj = (await self.session.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
            t_slug = tenant_obj.slug.replace("-", "_") if tenant_obj else str(tenant_id)[:8]
            teacher_email = f"{employee_id.lower().replace('-', '_')}_{t_slug}@staff.internal"

        user, _ = await self.repo.get_or_create_user_and_membership(
            tenant_id=tenant_id,
            email=str(teacher_email),
            full_name=payload.full_name,
            phone=payload.phone,
            role_code="TEACHER",
            initial_password=payload.initial_password.get_secret_value() if payload.initial_password else None,
        )
        if await self.session.scalar(select(TeacherProfile.id).where(
            TeacherProfile.tenant_id == tenant_id, TeacherProfile.user_id == user.id,
            TeacherProfile.is_deleted.is_(False),
        ).limit(1)):
            raise AppException(409, "FACULTY_PROFILE_EXISTS", "A faculty profile already exists for this email.")

        # 4. Create TeacherProfile
        profile = TeacherProfile(
            tenant_id=tenant_id,
            user_id=user.id,
            employee_id=employee_id,
            designation=payload.designation,
            qualification=payload.qualification,
            specialization=payload.specialization,
            experience_years=payload.experience_years,
            department_id=payload.department_id,
            joining_date=payload.joining_date or date.today(),
            employment_type=payload.employment_type,
            status="ACTIVE",
            address_line1=payload.address_line1,
            address_line2=payload.address_line2,
            city=payload.city,
            state=payload.state,
            postal_code=payload.postal_code,
            country=payload.country or "India",
            emergency_contact_name=payload.emergency_contact_name,
            emergency_contact_phone=payload.emergency_contact_phone,
            pan_number=payload.pan_number,
            aadhar_number=payload.aadhar_number,
            bank_name=payload.bank_name,
            bank_account_number=payload.bank_account_number,
            bank_ifsc=payload.bank_ifsc,
            photo_url=payload.photo_url,
            custom_fields=payload.custom_fields,
        )
        self.session.add(profile)
        await self.session.flush()

        await self.repo.log_audit(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action="TEACHER_CREATED",
            entity_id=str(profile.id),
            changes={"employee_id": employee_id, "full_name": payload.full_name},
        )
        await self.session.commit()

        return await self.get_teacher_detail(tenant_id, profile.id)

    # ── Update Teacher ────────────────────────────────────────────────────────
    async def update_teacher(
        self,
        tenant_id: uuid.UUID,
        teacher_id: uuid.UUID,
        payload: TeacherUpdateRequest,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> TeacherResponse:
        teacher = await self.repo.get_teacher_by_id(tenant_id, teacher_id)
        if not teacher:
            raise AppException(404, "TEACHER_NOT_FOUND", "Teacher not found")

        update_dict = payload.model_dump(exclude_unset=True)

        if "full_name" in update_dict and teacher.user:
            teacher.user.full_name = update_dict.pop("full_name")
        if "phone" in update_dict and teacher.user:
            teacher.user.phone = update_dict.pop("phone")
        if "email" in update_dict and teacher.user:
            new_email = update_dict.pop("email")
            if new_email:
                teacher.user.email = str(new_email).strip().lower()

        for k, v in update_dict.items():
            if hasattr(teacher, k):
                setattr(teacher, k, v)

        await self.repo.log_audit(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action="TEACHER_UPDATED",
            entity_id=str(teacher.id),
            changes=update_dict,
        )
        await self.session.commit()
        return await self.get_teacher_detail(tenant_id, teacher.id)

    # ── Get Teacher Detail ────────────────────────────────────────────────────
    async def get_teacher_detail(
        self, tenant_id: uuid.UUID, teacher_id: uuid.UUID, access: StaffAccess | None = None
    ) -> TeacherResponse:
        t = await self.repo.get_teacher_by_id(tenant_id, teacher_id)
        if not t:
            raise AppException(404, "TEACHER_NOT_FOUND", "Teacher profile not found")
        if access and not access.can_view(t):
            raise AuthorizationException("This faculty member is outside your staff access.")
        role_codes = await self._staff_roles(tenant_id, [t.user_id])
        private = access is None or access.is_admin or access.user_id == t.user_id
        active_assignments = [assignment for assignment in t.assignments if not assignment.is_deleted]

        assignments = [
            TeacherAssignmentSchema(
                id=a.id,
                teacher_id=a.teacher_id,
                academic_session_id=a.academic_session_id,
                class_id=a.class_id,
                class_name=a.school_class.name if a.school_class else None,
                section_id=a.section_id,
                section_name=a.section.name if a.section else None,
                department_id=a.department_id,
                department_name=a.department.name if a.department else None,
                course_id=a.course_id,
                course_name=a.course.name if a.course else None,
                semester=a.semester,
                subject_id=a.subject_id,
                subject_name=a.subject.name if a.subject else None,
                subject_code=a.subject.code if a.subject else None,
                is_class_teacher=a.is_class_teacher,
            )
            for a in active_assignments
            if not a.is_deleted
        ]

        # Workload calculation
        classes_set = set()
        subjects_set = set()
        class_teacher_section = None
        for a in active_assignments:
            if a.is_deleted:
                continue
            if a.class_id:
                classes_set.add(str(a.class_id))
            if a.course_id:
                classes_set.add(str(a.course_id))
            if a.subject_id:
                subjects_set.add(str(a.subject_id))
            if a.is_class_teacher:
                sec_name = a.section.name if a.section else ""
                cls_name = a.school_class.name if a.school_class else ""
                class_teacher_section = f"{cls_name} - Sec {sec_name}"

        attendance = sorted(t.attendances, key=lambda record: record.attendance_date, reverse=True)
        leaves = sorted(t.leaves, key=lambda record: record.applied_at, reverse=True)
        tracked_days = [record for record in attendance if record.status in ("PRESENT", "ABSENT", "LATE", "HALF_DAY")]
        attended = sum(record.status in ("PRESENT", "LATE", "HALF_DAY") for record in tracked_days)
        workload = TeacherWorkloadResponse(
            total_classes_assigned=len(classes_set),
            total_subjects_assigned=len(subjects_set),
            weekly_periods_count=len(t.timetable_entries),
            is_class_teacher_of=class_teacher_section,
            approved_leave_days=sum(float(leave.days_count) for leave in leaves if leave.status == "APPROVED" and leave.start_date.year == date.today().year),
            attendance_rate_percentage=(round(attended * 100 / len(tracked_days), 1) if tracked_days else None),
        )

        return TeacherResponse(
            id=t.id,
            tenant_id=t.tenant_id,
            user_id=t.user_id,
            staff_role=role_codes.get(t.user_id),
            full_name=t.user.full_name if t.user else "Faculty",
            email=t.user.email if t.user else None,
            phone=t.user.phone if private and t.user else None,
            employee_id=t.employee_id,
            designation=t.designation,
            qualification=t.qualification,
            specialization=t.specialization,
            experience_years=t.experience_years,
            department_id=t.department_id,
            department_name=t.department.name if t.department else None,
            joining_date=t.joining_date,
            employment_type=t.employment_type,
            status=t.status,
            address_line1=t.address_line1 if private else None,
            address_line2=t.address_line2 if private else None,
            city=t.city if private else None,
            state=t.state if private else None,
            postal_code=t.postal_code if private else None,
            country=t.country,
            emergency_contact_name=t.emergency_contact_name if private else None,
            emergency_contact_phone=t.emergency_contact_phone if private else None,
            pan_number=t.pan_number if private else None,
            aadhar_number=t.aadhar_number if private else None,
            bank_name=t.bank_name if private else None,
            bank_account_number=t.bank_account_number if private else None,
            bank_ifsc=t.bank_ifsc if private else None,
            photo_url=t.photo_url,
            custom_fields=t.custom_fields if private else {},
            assignments=assignments,
            workload=workload,
            leave_history=[self._leave_response(leave, t.user.full_name if t.user else "Faculty") for leave in leaves[:50]],
            attendance_history=[TeacherAttendanceResponse.model_validate(record, from_attributes=True) for record in attendance[:50]],
            created_at=t.created_at,
            updated_at=t.updated_at,
        )

    async def _staff_roles(self, tenant_id, user_ids):
        if not user_ids:
            return {}
        rows = await self.session.execute(staff_role_query(tenant_id).where(Membership.user_id.in_(user_ids)))
        return {user_id: role for user_id, role in rows if role in ("PRINCIPAL", "HOD", "TEACHER")}

    async def require_own_staff_record(self, tenant_id, teacher_id, access: StaffAccess) -> None:
        if access.is_admin:
            return
        teacher = await self.repo.get_teacher_by_id(tenant_id, teacher_id)
        if not teacher or teacher.user_id != access.user_id:
            raise AuthorizationException("This action is limited to your own faculty record.")

    # ── List Teachers ─────────────────────────────────────────────────────────
    async def list_teachers(
        self,
        tenant_id: uuid.UUID,
        search: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        employment_type: Optional[str] = None,
        page: int = 1,
        size: int = 20,
        access: StaffAccess | None = None,
    ) -> Tuple[List[TeacherResponse], int]:
        teachers, total = await self.repo.list_teachers(
            tenant_id=tenant_id,
            search=search,
            department_id=department_id,
            status=status,
            employment_type=employment_type,
            page=page,
            size=size,
            allowed_departments=access.department_ids if access else None,
        )

        role_codes = await self._staff_roles(tenant_id, [teacher.user_id for teacher in teachers])
        items = []
        for t in teachers:
            assignments = [assignment for assignment in t.assignments if not assignment.is_deleted]
            items.append(
                TeacherResponse(
                    id=t.id,
                    tenant_id=t.tenant_id,
                    user_id=t.user_id,
                    staff_role=role_codes.get(t.user_id),
                    full_name=t.user.full_name if t.user else "Faculty",
                    email=t.user.email if t.user else None,
                    phone=t.user.phone if t.user and (access is None or access.is_admin) else None,
                    employee_id=t.employee_id,
                    designation=t.designation,
                    qualification=t.qualification,
                    specialization=t.specialization,
                    experience_years=t.experience_years,
                    department_id=t.department_id,
                    department_name=t.department.name if t.department else None,
                    joining_date=t.joining_date,
                    employment_type=t.employment_type,
                    status=t.status,
                    city=t.city,
                    state=t.state,
                    country=t.country,
                    assignments=[],
                    workload=TeacherWorkloadResponse(
                        total_classes_assigned=len(assignments),
                        total_subjects_assigned=len({a.subject_id for a in assignments if a.subject_id}),
                        weekly_periods_count=len(t.timetable_entries),
                    ),
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )
            )
        return items, total

    # ── Assign Academic Resources (Classes, Subjects, Sections) ───────────────
    async def assign_resource(
        self,
        tenant_id: uuid.UUID,
        teacher_id: uuid.UUID,
        payload: TeacherAssignmentCreateRequest,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> TeacherAssignment:
        teacher = await self.repo.get_teacher_by_id(tenant_id, teacher_id)
        if not teacher:
            raise AppException(404, "TEACHER_NOT_FOUND", "Teacher not found")

        if not (payload.class_id or payload.course_id or payload.section_id or payload.subject_id):
            raise AppException(422, "ASSIGNMENT_TARGET_REQUIRED", "Select a class, course, section, or subject.")
        if payload.class_id and payload.course_id:
            raise AppException(422, "INVALID_ASSIGNMENT_TARGET", "Select either a school class or a college course.")
        for model, resource_id in (
            (AcademicSession, payload.academic_session_id), (SchoolClass, payload.class_id),
            (Course, payload.course_id), (Department, payload.department_id), (Subject, payload.subject_id),
        ):
            if resource_id and not await self.session.scalar(
                select(model.id).where(model.id == resource_id, model.tenant_id == tenant_id, model.is_deleted.is_(False))
            ):
                raise AppException(422, "INVALID_ASSIGNMENT_TARGET", "Select academic resources from this institution.")
        if payload.section_id:
            section = await self.session.scalar(select(Section).where(
                Section.id == payload.section_id, Section.tenant_id == tenant_id, Section.is_deleted.is_(False),
            ))
            if section is None or (payload.class_id and section.class_id != payload.class_id) or (
                payload.course_id and section.course_id != payload.course_id
            ):
                raise AppException(422, "INVALID_SECTION", "The section must belong to the selected class or course.")

        assignment = TeacherAssignment(
            tenant_id=tenant_id,
            teacher_id=teacher_id,
            academic_session_id=payload.academic_session_id,
            class_id=payload.class_id,
            section_id=payload.section_id,
            department_id=payload.department_id,
            course_id=payload.course_id,
            semester=payload.semester,
            subject_id=payload.subject_id,
            is_class_teacher=payload.is_class_teacher,
        )
        self.session.add(assignment)
        await self.session.flush()

        await self.repo.log_audit(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action="TEACHER_ASSIGNMENT_CREATED",
            entity_id=str(assignment.id),
            changes=payload.model_dump(mode="json"),
        )
        return assignment

    async def remove_assignment(
        self,
        tenant_id: uuid.UUID,
        teacher_id: uuid.UUID,
        assignment_id: uuid.UUID,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> None:
        stmt = select(TeacherAssignment).where(
            TeacherAssignment.tenant_id == tenant_id,
            TeacherAssignment.teacher_id == teacher_id,
            TeacherAssignment.id == assignment_id,
        )
        res = await self.session.execute(stmt)
        assignment = res.scalar_one_or_none()
        if not assignment:
            raise AppException(404, "ASSIGNMENT_NOT_FOUND", "Assignment record not found")

        assignment.is_deleted = True
        await self.session.commit()

    # ── Timetable Management ──────────────────────────────────────────────────
    async def create_timetable_entry(
        self,
        tenant_id: uuid.UUID,
        teacher_id: uuid.UUID,
        payload: TimetableEntryCreateRequest,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> TimetableEntry:
        teacher = await self.repo.get_teacher_by_id(tenant_id, teacher_id)
        if not teacher:
            raise AppException(404, "TEACHER_NOT_FOUND", "Teacher not found")

        entry = TimetableEntry(
            tenant_id=tenant_id,
            teacher_id=teacher_id,
            academic_session_id=payload.academic_session_id,
            subject_id=payload.subject_id,
            class_id=payload.class_id,
            section_id=payload.section_id,
            course_id=payload.course_id,
            semester=payload.semester,
            day_of_week=payload.day_of_week.upper(),
            period_number=payload.period_number,
            start_time=payload.start_time,
            end_time=payload.end_time,
            room_number=payload.room_number,
        )
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def list_timetable(
        self,
        tenant_id: uuid.UUID,
        teacher_id: uuid.UUID,
        day_of_week: Optional[str] = None,
    ) -> List[TimetableEntrySchema]:
        query = (
            select(TimetableEntry)
            .options(
                selectinload(TimetableEntry.teacher).selectinload(TeacherProfile.user),
                selectinload(TimetableEntry.subject),
                selectinload(TimetableEntry.school_class),
                selectinload(TimetableEntry.section),
                selectinload(TimetableEntry.course),
            )
            .where(
                TimetableEntry.tenant_id == tenant_id,
                TimetableEntry.teacher_id == teacher_id,
                TimetableEntry.is_deleted == False,
            )
        )
        if day_of_week:
            query = query.where(TimetableEntry.day_of_week == day_of_week.upper())

        query = query.order_by(TimetableEntry.period_number.asc())
        res = await self.session.execute(query)
        entries = res.scalars().all()

        return [
            TimetableEntrySchema(
                id=e.id,
                academic_session_id=e.academic_session_id,
                teacher_id=e.teacher_id,
                teacher_name=e.teacher.user.full_name if e.teacher and e.teacher.user else None,
                subject_id=e.subject_id,
                subject_name=e.subject.name if e.subject else None,
                class_id=e.class_id,
                class_name=e.school_class.name if e.school_class else None,
                section_id=e.section_id,
                section_name=e.section.name if e.section else None,
                course_id=e.course_id,
                course_name=e.course.name if e.course else None,
                semester=e.semester,
                day_of_week=e.day_of_week,
                period_number=e.period_number,
                start_time=e.start_time,
                end_time=e.end_time,
                room_number=e.room_number,
            )
            for e in entries
        ]

    # ── Teacher Attendance ────────────────────────────────────────────────────
    async def record_attendance(
        self,
        tenant_id: uuid.UUID,
        teacher_id: uuid.UUID,
        payload: TeacherAttendanceRecordRequest,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> TeacherAttendanceResponse:
        teacher = await self.repo.get_teacher_by_id(tenant_id, teacher_id)
        if not teacher:
            raise AppException(404, "TEACHER_NOT_FOUND", "Teacher not found")

        stmt = select(TeacherAttendance).where(
            TeacherAttendance.tenant_id == tenant_id,
            TeacherAttendance.teacher_id == teacher_id,
            TeacherAttendance.attendance_date == payload.attendance_date,
        )
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()

        if record:
            record.status = payload.status
            record.check_in_time = payload.check_in_time
            record.check_out_time = payload.check_out_time
            record.remarks = payload.remarks
            record.recorded_by_user_id = actor_user_id
        else:
            record = TeacherAttendance(
                tenant_id=tenant_id,
                teacher_id=teacher_id,
                attendance_date=payload.attendance_date,
                status=payload.status,
                check_in_time=payload.check_in_time,
                check_out_time=payload.check_out_time,
                remarks=payload.remarks,
                recorded_by_user_id=actor_user_id,
            )
            self.session.add(record)

        await self.session.commit()
        await self.session.refresh(record)

        return TeacherAttendanceResponse(
            id=record.id,
            teacher_id=record.teacher_id,
            attendance_date=record.attendance_date,
            status=record.status,
            check_in_time=record.check_in_time,
            check_out_time=record.check_out_time,
            remarks=record.remarks,
            created_at=record.created_at,
        )

    # ── Leave Management ──────────────────────────────────────────────────────
    async def apply_leave(
        self,
        tenant_id: uuid.UUID,
        teacher_id: uuid.UUID,
        payload: TeacherLeaveApplyRequest,
    ) -> TeacherLeaveResponse:
        teacher = await self.repo.get_teacher_by_id(tenant_id, teacher_id)
        if not teacher:
            raise AppException(404, "TEACHER_NOT_FOUND", "Teacher not found")

        leave = TeacherLeave(
            tenant_id=tenant_id,
            teacher_id=teacher_id,
            leave_type=payload.leave_type,
            start_date=payload.start_date,
            end_date=payload.end_date,
            days_count=payload.days_count,
            reason=payload.reason,
            status="PENDING",
        )
        self.session.add(leave)
        await self.session.commit()
        await self.session.refresh(leave)

        return TeacherLeaveResponse(
            id=leave.id,
            teacher_id=leave.teacher_id,
            teacher_name=teacher.user.full_name if teacher.user else "Faculty",
            leave_type=leave.leave_type,
            start_date=leave.start_date,
            end_date=leave.end_date,
            days_count=float(leave.days_count),
            reason=leave.reason,
            status=leave.status,
            rejection_reason=leave.rejection_reason,
            applied_at=leave.applied_at,
            reviewed_at=leave.reviewed_at,
        )

    async def review_leave(
        self,
        tenant_id: uuid.UUID,
        leave_id: uuid.UUID,
        payload: TeacherLeaveReviewRequest,
        actor_user_id: Optional[uuid.UUID] = None,
        access: StaffAccess | None = None,
    ) -> TeacherLeaveResponse:
        stmt = self._leave_review_query(tenant_id, access).where(TeacherLeave.id == leave_id).with_for_update(of=TeacherLeave)
        res = await self.session.execute(stmt)
        leave = res.scalar_one_or_none()
        if not leave:
            raise AppException(404, "LEAVE_NOT_FOUND", "Leave application not found")
        if leave.status != "PENDING":
            raise AppException(409, "LEAVE_ALREADY_REVIEWED", "This application has already been reviewed.")

        leave.status = payload.status.upper()
        leave.rejection_reason = payload.rejection_reason
        leave.approved_by_user_id = actor_user_id
        leave.reviewed_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(leave)

        return self._leave_response(leave)

    def _leave_review_query(self, tenant_id: uuid.UUID, access: StaffAccess | None):
        query = (
            select(TeacherLeave)
            .join(TeacherProfile, TeacherLeave.teacher_id == TeacherProfile.id)
            .options(selectinload(TeacherLeave.teacher).selectinload(TeacherProfile.user))
            .where(
                TeacherLeave.tenant_id == tenant_id,
                TeacherProfile.tenant_id == tenant_id,
                TeacherProfile.is_deleted.is_(False),
            )
        )
        if access is None or access.is_admin:
            return query

        managed_roles = ("TEACHER",) if access.role == "HOD" else ("TEACHER", "HOD")
        scoped = query.join(
            Membership,
            and_(Membership.user_id == TeacherProfile.user_id, Membership.tenant_id == tenant_id),
        ).join(Role, Role.id == Membership.role_id).where(
            TeacherProfile.user_id != access.user_id,
            Role.code.in_(managed_roles),
            Membership.status == MembershipStatus.ACTIVE,
            Membership.is_deleted.is_(False),
        )
        if access.department_ids is not None:
            scoped = scoped.where(TeacherProfile.department_id.in_(access.department_ids))
        return scoped

    async def list_pending_leaves(self, tenant_id: uuid.UUID, access: StaffAccess) -> list[TeacherLeaveResponse]:
        leaves = await self.session.scalars(
            self._leave_review_query(tenant_id, access)
            .where(TeacherLeave.status == "PENDING")
            .order_by(TeacherLeave.applied_at, TeacherLeave.id)
            .limit(100)
        )
        return [self._leave_response(leave) for leave in leaves]

    @staticmethod
    def _leave_response(leave: TeacherLeave, teacher_name: str | None = None) -> TeacherLeaveResponse:
        if teacher_name is None:
            teacher_name = leave.teacher.user.full_name if leave.teacher and leave.teacher.user else "Faculty"
        return TeacherLeaveResponse(
            id=leave.id,
            teacher_id=leave.teacher_id,
            teacher_name=teacher_name,
            leave_type=leave.leave_type,
            start_date=leave.start_date,
            end_date=leave.end_date,
            days_count=float(leave.days_count),
            reason=leave.reason,
            status=leave.status,
            rejection_reason=leave.rejection_reason,
            applied_at=leave.applied_at,
            reviewed_at=leave.reviewed_at,
        )

    # ── Teacher Documents ─────────────────────────────────────────────────────
    async def upload_document(
        self,
        tenant_id: uuid.UUID,
        teacher_id: uuid.UUID,
        payload: TeacherDocumentCreateRequest,
    ) -> TeacherDocumentResponse:
        teacher = await self.repo.get_teacher_by_id(tenant_id, teacher_id)
        if not teacher:
            raise AppException(404, "TEACHER_NOT_FOUND", "Teacher not found")

        doc = TeacherDocument(
            tenant_id=tenant_id,
            teacher_id=teacher_id,
            document_type=payload.document_type,
            document_name=payload.document_name,
            file_url=payload.file_url,
            file_size_bytes=payload.file_size_bytes,
            mime_type=payload.mime_type,
        )
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)

        return TeacherDocumentResponse(
            id=doc.id,
            teacher_id=doc.teacher_id,
            document_type=doc.document_type,
            document_name=doc.document_name,
            file_url=doc.file_url,
            file_size_bytes=doc.file_size_bytes,
            mime_type=doc.mime_type,
            created_at=doc.created_at,
        )

    # ── Deactivate / Activate Teacher ─────────────────────────────────────────
    async def set_teacher_status(
        self,
        tenant_id: uuid.UUID,
        teacher_id: uuid.UUID,
        status: str,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        teacher = await self.repo.get_teacher_by_id(tenant_id, teacher_id)
        if not teacher:
            raise AppException(404, "TEACHER_NOT_FOUND", "Teacher not found")

        status = status.upper()
        if status not in ("ACTIVE", "INACTIVE"):
            raise AppException(422, "INVALID_STAFF_STATUS", "Choose Active or Inactive.")
        teacher.status = status
        membership = await self.session.scalar(
            select(Membership)
            .join(Role, Role.id == Membership.role_id)
            .where(
                Membership.tenant_id == tenant_id, Membership.user_id == teacher.user_id,
                Membership.is_deleted.is_(False), Role.code.in_(("PRINCIPAL", "HOD", "TEACHER")),
            )
            .with_for_update(of=Membership)
        )
        if membership and membership.status != MembershipStatus.INVITED:
            membership.status = MembershipStatus.ACTIVE if status == "ACTIVE" else MembershipStatus.SUSPENDED
        await self.repo.log_audit(tenant_id, actor_user_id, "STAFF_STATUS_UPDATED", str(teacher.id), {"status": status})

        await self.session.commit()
        return {"success": True, "status": teacher.status, "message": f"Teacher status set to {teacher.status}"}

    # ── Teacher Dedicated Dashboard Summary ───────────────────────────────────
    async def get_teacher_dashboard(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> TeacherDashboardSummary:
        teacher = await self.repo.get_teacher_by_user_id(tenant_id, user_id)
        if not teacher:
            raise AppException(404, "TEACHER_PROFILE_NOT_FOUND", "No faculty profile associated with your account in this institution.")

        teacher_detail = await self.get_teacher_detail(tenant_id, teacher.id)

        # 1. Assigned classes & subjects
        assigned_classes = []
        assigned_subjects = []
        for a in teacher_detail.assignments:
            name = a.class_name or a.course_name or "Class"
            if a.section_name:
                name += f" - Sec {a.section_name}"
            elif a.semester:
                name += f" - Sem {a.semester}"

            if name not in [c.get("title") for c in assigned_classes]:
                assigned_classes.append({
                    "id": str(a.class_id or a.course_id or a.id),
                    "title": name,
                    "is_class_teacher": a.is_class_teacher,
                })

            if a.subject_name and a.subject_name not in [s.get("title") for s in assigned_subjects]:
                assigned_subjects.append({
                    "id": str(a.subject_id or a.id),
                    "title": a.subject_name,
                    "code": a.subject_code or "",
                })

        # 2. Today's timetable
        day_names = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
        today_name = day_names[date.today().weekday()]
        today_timetable = await self.list_timetable(tenant_id, teacher.id, day_of_week=today_name)

        today = date.today()
        completed_periods = set((await self.session.execute(
            select(StudentAttendanceSession.period_number, StudentAttendanceSession.class_id,
                   StudentAttendanceSession.section_id, StudentAttendanceSession.course_id)
            .where(
                StudentAttendanceSession.tenant_id == tenant_id,
                StudentAttendanceSession.conducted_by_teacher_id == teacher.id,
                StudentAttendanceSession.session_date == today,
                StudentAttendanceSession.status.in_(("SUBMITTED", "APPROVED", "LOCKED")),
                StudentAttendanceSession.is_deleted.is_(False),
            )
        )).all())
        attendance_tasks = [
            {
                "class_name": " · ".join(filter(None, (slot.class_name or slot.course_name, slot.section_name))) or "Scheduled class",
                "status": "PENDING",
                "due_time": slot.start_time,
            }
            for slot in today_timetable
            if (slot.period_number, slot.class_id, slot.section_id, slot.course_id) not in completed_periods
        ]

        exam_rows = await self.session.execute(
            select(Examination.title, Subject.name, Examination.start_datetime)
            .outerjoin(Subject, and_(Subject.id == Examination.subject_id, Subject.tenant_id == tenant_id))
            .where(
                Examination.tenant_id == tenant_id,
                Examination.created_by == user_id,
                Examination.is_deleted.is_(False),
                Examination.status == "SCHEDULED",
                Examination.start_datetime >= datetime.now(timezone.utc),
            )
            .order_by(Examination.start_datetime)
            .limit(10)
        )
        upcoming_examinations = [
            {"title": title, "subject": subject_name or "General", "date": starts_at.date().isoformat()}
            for title, subject_name, starts_at in exam_rows
        ]

        submitted = func.count(AssignmentSubmission.id)
        evaluated = submitted.filter(AssignmentSubmission.status == "EVALUATED")
        pending = submitted.filter(AssignmentSubmission.status == "SUBMITTED")
        assignment_rows = await self.session.execute(
            select(Assignment.title, SchoolClass.name, Course.name, submitted, evaluated)
            .join(AssignmentSubmission, and_(
                AssignmentSubmission.assignment_id == Assignment.id,
                AssignmentSubmission.tenant_id == tenant_id,
                AssignmentSubmission.is_deleted.is_(False),
            ))
            .outerjoin(SchoolClass, and_(SchoolClass.id == Assignment.class_id, SchoolClass.tenant_id == tenant_id))
            .outerjoin(Course, and_(Course.id == Assignment.course_id, Course.tenant_id == tenant_id))
            .where(
                Assignment.tenant_id == tenant_id,
                Assignment.created_by == user_id,
                Assignment.is_deleted.is_(False),
                Assignment.status.in_(("PUBLISHED", "CLOSED")),
            )
            .group_by(Assignment.id, SchoolClass.name, Course.name)
            .having(pending > 0)
            .order_by(Assignment.due_datetime, Assignment.id)
            .limit(10)
        )
        assignments_to_evaluate = [
            {"title": title, "class_name": class_name or course_name or "General", "submissions_count": count, "evaluated_count": graded}
            for title, class_name, course_name, count, graded in assignment_rows
        ]

        notifications = [
            {"title": item.title, "message": item.message, "created_at": item.created_at.isoformat()}
            for item in await NotificationRepository(self.session).list_user_notifications(tenant_id, user_id, limit=10)
        ]

        return TeacherDashboardSummary(
            teacher=teacher_detail,
            assigned_classes=assigned_classes,
            assigned_subjects=assigned_subjects,
            today_timetable=today_timetable,
            attendance_tasks=attendance_tasks,
            upcoming_examinations=upcoming_examinations,
            assignments_to_evaluate=assignments_to_evaluate,
            notifications=notifications,
        )
