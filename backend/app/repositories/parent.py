import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import (
    AcademicSession,
    SchoolClass,
    Section,
    Course,
    CollegeSemester,
    StudentAcademicEnrollment,
    StudentParent,
    StudentProfile,
    Subject,
    TeacherProfile,
    TeacherAssignment,
    TimetableEntry,
)
from app.models.attendance import StudentAttendanceEntry, StudentAttendanceSession
from app.models.user import User
from app.models.examination import Examination
from app.models.fee import FeeInvoice, FeePayment
from app.models.lms import Assignment, AssignmentSubmission, StudyMaterial
from app.models.parent import ParentTeacherMessage, StudentLinkVerificationCode
from app.models.result import StudentSubjectResult, StudentTermResult
from app.models.tenant import Tenant


class ParentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Verification, Linking & Governance
    # ─────────────────────────────────────────────────────────────────────────

    async def get_student_parent(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID, parent_user_id: uuid.UUID
    ) -> Optional[StudentParent]:
        stmt = (
            select(StudentParent)
            .where(
                StudentParent.tenant_id == tenant_id,
                StudentParent.student_id == student_id,
                StudentParent.parent_user_id == parent_user_id,
                StudentParent.is_deleted == False,
            )
            .options(
                selectinload(StudentParent.student).selectinload(StudentProfile.user),
                selectinload(StudentParent.parent_user),
                selectinload(StudentParent.verified_by),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_student_parent_by_id(
        self, tenant_id: uuid.UUID, link_id: uuid.UUID
    ) -> Optional[StudentParent]:
        stmt = (
            select(StudentParent)
            .where(
                StudentParent.tenant_id == tenant_id,
                StudentParent.id == link_id,
                StudentParent.is_deleted == False,
            )
            .options(
                selectinload(StudentParent.student).selectinload(StudentProfile.user),
                selectinload(StudentParent.parent_user),
                selectinload(StudentParent.verified_by),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_linked_children_for_user(
        self, parent_user_id: uuid.UUID, status: Optional[str] = "VERIFIED"
    ) -> List[StudentParent]:
        stmt = (
            select(StudentParent)
            .where(
                StudentParent.parent_user_id == parent_user_id,
                StudentParent.is_deleted == False,
            )
            .options(
                selectinload(StudentParent.student).selectinload(StudentProfile.user),
                selectinload(StudentParent.student).selectinload(StudentProfile.school_class),
                selectinload(StudentParent.student).selectinload(StudentProfile.section),
                selectinload(StudentParent.student).selectinload(StudentProfile.course),
                selectinload(StudentParent.student).selectinload(StudentProfile.academic_session),
                selectinload(StudentParent.student).selectinload(StudentProfile.tenant),
                selectinload(StudentParent.parent_user),
            )
        )
        if status:
            stmt = stmt.where(StudentParent.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_pending_link_requests(self, tenant_id: uuid.UUID) -> List[StudentParent]:
        stmt = (
            select(StudentParent)
            .where(
                StudentParent.tenant_id == tenant_id,
                StudentParent.status == "PENDING_APPROVAL",
                StudentParent.is_deleted == False,
            )
            .options(
                selectinload(StudentParent.student).selectinload(StudentProfile.user),
                selectinload(StudentParent.parent_user),
            )
            .order_by(StudentParent.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def create_link_request(
        self,
        tenant_id: uuid.UUID,
        student_id: uuid.UUID,
        parent_user_id: uuid.UUID,
        relation_type: str,
        emergency_contact: bool = False,
        verification_method: str = "ADMIN_APPROVAL",
        status: str = "PENDING_APPROVAL",
        notes: Optional[str] = None,
        is_primary: bool = True,
        can_view_grades: bool = True,
        can_pay_fees: bool = True,
        verified_by_user_id: Optional[uuid.UUID] = None,
    ) -> StudentParent:
        link = StudentParent(
            tenant_id=tenant_id,
            student_id=student_id,
            parent_user_id=parent_user_id,
            relation_type=relation_type,
            emergency_contact=emergency_contact,
            verification_method=verification_method,
            status=status,
            verification_notes=notes,
            is_primary=is_primary,
            can_view_grades=can_view_grades,
            can_pay_fees=can_pay_fees,
            verified_by_user_id=verified_by_user_id,
            verified_at=datetime.now(timezone.utc) if status == "VERIFIED" else None,
        )
        self.session.add(link)
        await self.session.flush()
        return link

    async def update_link_status(
        self,
        tenant_id: uuid.UUID,
        link_id: uuid.UUID,
        status: str,
        verified_by_user_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
        can_view_grades: bool = True,
        can_pay_fees: bool = True,
    ) -> Optional[StudentParent]:
        link = await self.get_student_parent_by_id(tenant_id, link_id)
        if not link:
            return None
        link.status = status
        link.verified_by_user_id = verified_by_user_id
        link.verified_at = datetime.now(timezone.utc) if status == "VERIFIED" else None
        if notes:
            link.verification_notes = notes
        link.can_view_grades = can_view_grades
        link.can_pay_fees = can_pay_fees
        link.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return link

    async def find_valid_verification_code(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID, code: str
    ) -> Optional[StudentLinkVerificationCode]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(StudentLinkVerificationCode)
            .where(
                StudentLinkVerificationCode.tenant_id == tenant_id,
                StudentLinkVerificationCode.student_id == student_id,
                StudentLinkVerificationCode.code == code,
                StudentLinkVerificationCode.is_used == False,
                StudentLinkVerificationCode.expires_at >= now,
                StudentLinkVerificationCode.is_deleted == False,
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def create_verification_code(
        self,
        tenant_id: uuid.UUID,
        student_id: uuid.UUID,
        code: str,
        generated_by_user_id: Optional[uuid.UUID],
        expires_at: datetime,
    ) -> StudentLinkVerificationCode:
        vc = StudentLinkVerificationCode(
            tenant_id=tenant_id,
            student_id=student_id,
            code=code,
            generated_by_user_id=generated_by_user_id,
            expires_at=expires_at,
            is_used=False,
        )
        self.session.add(vc)
        await self.session.flush()
        return vc

    async def mark_verification_code_used(
        self, code_id: uuid.UUID, parent_user_id: uuid.UUID
    ) -> None:
        stmt = select(StudentLinkVerificationCode).where(StudentLinkVerificationCode.id == code_id)
        vc = (await self.session.execute(stmt)).scalars().first()
        if vc:
            vc.is_used = True
            vc.used_by_parent_user_id = parent_user_id
            vc.used_at = datetime.now(timezone.utc)
            await self.session.flush()

    async def get_student_by_admission_number(
        self, tenant_id: uuid.UUID, admission_number: str
    ) -> Optional[StudentProfile]:
        stmt = (
            select(StudentProfile)
            .where(
                StudentProfile.tenant_id == tenant_id,
                func.lower(StudentProfile.admission_number) == func.lower(admission_number),
                StudentProfile.is_deleted == False,
            )
            .options(
                selectinload(StudentProfile.user),
                selectinload(StudentProfile.school_class),
                selectinload(StudentProfile.section),
                selectinload(StudentProfile.course),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_student_by_id(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID
    ) -> Optional[StudentProfile]:
        stmt = (
            select(StudentProfile)
            .where(
                StudentProfile.tenant_id == tenant_id,
                StudentProfile.id == student_id,
                StudentProfile.is_deleted == False,
            )
            .options(
                selectinload(StudentProfile.user),
                selectinload(StudentProfile.school_class).selectinload(SchoolClass.class_teacher).selectinload(TeacherProfile.user),
                selectinload(StudentProfile.section),
                selectinload(StudentProfile.course),
                selectinload(StudentProfile.academic_session),
                selectinload(StudentProfile.tenant),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Child Academic Queries
    # ─────────────────────────────────────────────────────────────────────────

    async def get_child_attendance(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID, limit: int = 60
    ) -> List[StudentAttendanceEntry]:
        stmt = (
            select(StudentAttendanceEntry)
            .join(StudentAttendanceEntry.session)
            .where(
                StudentAttendanceEntry.tenant_id == tenant_id,
                StudentAttendanceEntry.student_id == student_id,
            )
            .options(selectinload(StudentAttendanceEntry.session))
            .order_by(StudentAttendanceSession.session_date.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_child_attendance_counts(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID
    ) -> Dict[str, int]:
        stmt = (
            select(StudentAttendanceEntry.status, func.count(StudentAttendanceEntry.id))
            .where(
                StudentAttendanceEntry.tenant_id == tenant_id,
                StudentAttendanceEntry.student_id == student_id,
            )
            .group_by(StudentAttendanceEntry.status)
        )
        rows = (await self.session.execute(stmt)).all()
        return {r[0]: r[1] for r in rows}

    def child_cohort_filters(self, model, student: StudentProfile):
        section = or_(model.section_id == student.section_id, model.section_id.is_(None))
        if student.course_id:
            if model is TeacherAssignment:
                semester = or_(model.semester == student.semester, model.semester.is_(None))
            else:
                semester_ids = select(CollegeSemester.id).where(
                    CollegeSemester.tenant_id == student.tenant_id,
                    CollegeSemester.course_id == student.course_id,
                    CollegeSemester.semester_number == student.semester,
                    CollegeSemester.is_deleted.is_(False),
                )
                semester = or_(model.semester_id.in_(semester_ids), model.semester_id.is_(None))
            return model.course_id == student.course_id, semester, section
        if student.class_id:
            return model.class_id == student.class_id, section
        return (model.id.is_(None),)

    async def get_child_timetable_entries(
        self, tenant_id: uuid.UUID, student: StudentProfile
    ) -> List[TimetableEntry]:
        stmt = (
            select(TimetableEntry)
            .where(
                TimetableEntry.tenant_id == tenant_id,
                *self.child_cohort_filters(TimetableEntry, student),
                TimetableEntry.is_deleted == False,
            )
            .options(
                selectinload(TimetableEntry.subject),
                selectinload(TimetableEntry.teacher).selectinload(TeacherProfile.user),
            )
            .order_by(TimetableEntry.day_of_week, TimetableEntry.period_number)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_child_examinations(
        self, tenant_id: uuid.UUID, student: StudentProfile
    ) -> List[Examination]:
        stmt = (
            select(Examination)
            .where(
                Examination.tenant_id == tenant_id,
                *self.child_cohort_filters(Examination, student),
                Examination.is_deleted.is_(False),
                Examination.start_datetime.is_not(None),
                Examination.status.in_(("SCHEDULED", "ONGOING", "COMPLETED")),
            )
            .options(selectinload(Examination.subject))
            .order_by(Examination.start_datetime.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_child_published_results(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID
    ) -> List[StudentTermResult]:
        stmt = (
            select(StudentTermResult)
            .where(
                StudentTermResult.tenant_id == tenant_id,
                StudentTermResult.student_id == student_id,
                StudentTermResult.approval_status == "PUBLISHED",
                StudentTermResult.is_deleted == False,
            )
            .options(
                selectinload(StudentTermResult.exam),
                selectinload(StudentTermResult.academic_session),
            )
            .order_by(StudentTermResult.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_published_subject_results(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID, exam_ids: list[uuid.UUID]
    ) -> list[StudentSubjectResult]:
        stmt = (
            select(StudentSubjectResult)
            .where(
                StudentSubjectResult.tenant_id == tenant_id,
                StudentSubjectResult.student_id == student_id,
                StudentSubjectResult.exam_id.in_(exam_ids),
                StudentSubjectResult.status == "PUBLISHED",
                StudentSubjectResult.is_deleted.is_(False),
            )
            .options(selectinload(StudentSubjectResult.subject))
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_child_assignments(
        self, tenant_id: uuid.UUID, student: StudentProfile
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(Assignment)
            .where(
                Assignment.tenant_id == tenant_id,
                *self.child_cohort_filters(Assignment, student),
                Assignment.status.in_(("PUBLISHED", "CLOSED", "ARCHIVED")),
                Assignment.is_deleted == False,
            )
            .options(
                selectinload(Assignment.subject),
                selectinload(Assignment.creator),
            )
            .order_by(Assignment.due_datetime.desc())
        )
        assignments = list((await self.session.execute(stmt)).scalars().all())

        sub_stmt = (
            select(AssignmentSubmission)
            .where(
                AssignmentSubmission.tenant_id == tenant_id,
                AssignmentSubmission.student_id == student.id,
                AssignmentSubmission.is_deleted == False,
            )
        )
        submissions = {s.assignment_id: s for s in (await self.session.execute(sub_stmt)).scalars().all()}

        result = []
        for a in assignments:
            sub = submissions.get(a.id)
            teacher_name = a.creator.full_name if a.creator else "Faculty"
            subject_name = a.subject.name if a.subject else "General"
            result.append({
                "assignment": a,
                "submission": sub,
                "teacher_name": teacher_name,
                "subject_name": subject_name,
            })
        return result

    async def get_child_study_materials(
        self, tenant_id: uuid.UUID, student: StudentProfile
    ) -> List[StudyMaterial]:
        stmt = (
            select(StudyMaterial)
            .where(
                StudyMaterial.tenant_id == tenant_id,
                *self.child_cohort_filters(StudyMaterial, student),
                StudyMaterial.is_published == True,
                StudyMaterial.is_deleted == False,
            )
            .options(selectinload(StudyMaterial.subject))
            .order_by(StudyMaterial.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_child_invoices_and_due(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID
    ) -> Dict[str, Any]:
        stmt = (
            select(FeeInvoice)
            .where(
                FeeInvoice.tenant_id == tenant_id,
                FeeInvoice.student_id == student_id,
                FeeInvoice.status != "CANCELLED",
                FeeInvoice.is_deleted == False,
            )
            .order_by(FeeInvoice.due_date.asc())
        )
        invoices = list((await self.session.execute(stmt)).scalars().all())
        total_due = sum(float(inv.balance_amount) for inv in invoices)

        pay_stmt = (
            select(FeePayment)
            .where(
                FeePayment.tenant_id == tenant_id,
                FeePayment.student_id == student_id,
                FeePayment.status == "SUCCESS",
            )
            .order_by(FeePayment.payment_date.desc())
        )
        payments = list((await self.session.execute(pay_stmt)).scalars().all())

        return {"invoices": invoices, "total_due": total_due, "payments": payments}

    async def get_child_teachers(
        self, tenant_id: uuid.UUID, student: StudentProfile
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(TeacherAssignment)
            .where(
                TeacherAssignment.tenant_id == tenant_id,
                *self.child_cohort_filters(TeacherAssignment, student),
                TeacherAssignment.is_deleted == False,
            )
            .options(
                selectinload(TeacherAssignment.teacher).selectinload(TeacherProfile.user),
                selectinload(TeacherAssignment.subject),
            )
        )
        assignments = list((await self.session.execute(stmt)).scalars().all())
        contacts = []
        seen = set()
        for asgn in assignments:
            if asgn.teacher and asgn.teacher.user:
                key = (asgn.teacher.user.id, asgn.subject_id)
                if key not in seen:
                    seen.add(key)
                    contacts.append({
                        "teacher_user_id": asgn.teacher.user.id,
                        "teacher_name": asgn.teacher.user.full_name,
                        "subject_name": asgn.subject.name if asgn.subject else "General",
                        "department_name": None,
                        "email": asgn.teacher.user.email,
                    })
        return contacts

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Parent-Teacher Messaging
    # ─────────────────────────────────────────────────────────────────────────

    async def create_message(
        self,
        tenant_id: uuid.UUID,
        student_id: uuid.UUID,
        parent_user_id: uuid.UUID,
        teacher_user_id: uuid.UUID,
        subject: str,
        message: str,
        sender_role: str,
        parent_message_id: Optional[uuid.UUID] = None,
    ) -> ParentTeacherMessage:
        msg = ParentTeacherMessage(
            tenant_id=tenant_id,
            student_id=student_id,
            parent_user_id=parent_user_id,
            teacher_user_id=teacher_user_id,
            subject=subject,
            message=message,
            sender_role=sender_role,
            parent_message_id=parent_message_id,
            is_read=False,
        )
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def list_messages_for_parent(
        self, parent_user_id: uuid.UUID, student_id: Optional[uuid.UUID] = None
    ) -> List[ParentTeacherMessage]:
        stmt = (
            select(ParentTeacherMessage)
            .where(
                ParentTeacherMessage.parent_user_id == parent_user_id,
                ParentTeacherMessage.parent_message_id.is_(None),  # Top-level threads
                ParentTeacherMessage.is_deleted == False,
            )
            .options(
                selectinload(ParentTeacherMessage.student).selectinload(StudentProfile.user),
                selectinload(ParentTeacherMessage.parent_user),
                selectinload(ParentTeacherMessage.teacher_user),
                selectinload(ParentTeacherMessage.replies).selectinload(ParentTeacherMessage.parent_user),
                selectinload(ParentTeacherMessage.replies).selectinload(ParentTeacherMessage.teacher_user),
            )
            .order_by(ParentTeacherMessage.created_at.desc())
        )
        if student_id:
            stmt = stmt.where(ParentTeacherMessage.student_id == student_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_messages_for_teacher(
        self, teacher_user_id: uuid.UUID, student_id: Optional[uuid.UUID] = None
    ) -> List[ParentTeacherMessage]:
        stmt = (
            select(ParentTeacherMessage)
            .where(
                ParentTeacherMessage.teacher_user_id == teacher_user_id,
                ParentTeacherMessage.parent_message_id.is_(None),
                ParentTeacherMessage.is_deleted == False,
            )
            .options(
                selectinload(ParentTeacherMessage.student).selectinload(StudentProfile.user),
                selectinload(ParentTeacherMessage.parent_user),
                selectinload(ParentTeacherMessage.teacher_user),
                selectinload(ParentTeacherMessage.replies).selectinload(ParentTeacherMessage.parent_user),
                selectinload(ParentTeacherMessage.replies).selectinload(ParentTeacherMessage.teacher_user),
            )
            .order_by(ParentTeacherMessage.created_at.desc())
        )
        if student_id:
            stmt = stmt.where(ParentTeacherMessage.student_id == student_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def mark_thread_read(self, thread_id: uuid.UUID, reader_user_id: uuid.UUID) -> None:
        stmt = select(ParentTeacherMessage).where(
            or_(ParentTeacherMessage.id == thread_id, ParentTeacherMessage.parent_message_id == thread_id),
            ParentTeacherMessage.is_read == False,
        )
        msgs = (await self.session.execute(stmt)).scalars().all()
        for m in msgs:
            # Only mark read if sent by the other party
            if (m.sender_role == "TEACHER" and m.parent_user_id == reader_user_id) or \
               (m.sender_role == "PARENT" and m.teacher_user_id == reader_user_id):
                m.is_read = True
        await self.session.flush()
