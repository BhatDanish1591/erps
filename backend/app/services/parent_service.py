import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.logging import get_logger
from app.models.academic import SchoolClass, Section, StudentParent, StudentProfile
from app.models.auth import Membership, Role
from app.models.user import User
from app.models.tenant import Tenant
from app.repositories.parent import ParentRepository
from app.schemas.parent import (
    AdminApproveLinkRequest,
    AdminGenerateVerificationCodeRequest,
    AdminInviteParentRequest,
    ChildAssignmentItem,
    ChildAttendanceDayEntry,
    ChildAttendanceResponse,
    ChildDayTimetable,
    ChildDetailedProfileResponse,
    ChildExamItem,
    ChildExaminationsResponse,
    ChildStudyMaterialItem,
    ChildSubjectResultItem,
    ChildTeacherContact,
    ChildTermResultResponse,
    ChildTimetableEntryItem,
    ChildTimetableResponse,
    LinkedChildSummary,
    ParentLinkChildRequest,
    ParentLinkRequestItem,
    ParentTeacherMessageResponse,
    SendMessageRequest,
    VerificationCodeResponse,
)

logger = get_logger(__name__)


class ParentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ParentRepository(session)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Verification & Anti-Unverified Linking Governance
    # ─────────────────────────────────────────────────────────────────────────

    async def link_child_request(
        self, tenant_id: uuid.UUID, parent_user_id: uuid.UUID, data: ParentLinkChildRequest
    ) -> Dict[str, Any]:
        """
        Request linking a child to a parent account.
        SECURITY RULE: Never allow linking using only name or phone match.
        Must use administrator approval or verified one-time tokens.
        """
        student = await self.repo.get_student_by_admission_number(tenant_id, data.admission_number)
        if not student:
            raise NotFoundException(f"No student found with admission number '{data.admission_number}' in this institution.")

        existing = await self.repo.get_student_parent(tenant_id, student.id, parent_user_id)
        if existing:
            if existing.status == "VERIFIED":
                raise BadRequestException("This child is already verified and linked to your parent account.")
            elif existing.status == "PENDING_APPROVAL":
                raise BadRequestException("A linking request for this child is currently pending administrator verification.")
            elif existing.status == "REJECTED":
                # Reset to pending for re-submission with new info
                existing.status = "PENDING_APPROVAL"
                existing.verification_notes = data.notes
                existing.relation_type = data.relation_type
                existing.emergency_contact = data.emergency_contact
                await self.session.commit()
                return {
                    "link_id": str(existing.id),
                    "status": "PENDING_APPROVAL",
                    "message": "Your previous linking request was re-submitted for administrator verification.",
                }

        # Check if valid verification code is provided
        if data.verification_code:
            v_code = await self.repo.find_valid_verification_code(tenant_id, student.id, data.verification_code.strip())
            if not v_code:
                raise BadRequestException("The verification code entered is invalid or has expired.")

            # Immediate verified link using valid one-time security code
            link = await self.repo.create_link_request(
                tenant_id=tenant_id,
                student_id=student.id,
                parent_user_id=parent_user_id,
                relation_type=data.relation_type,
                emergency_contact=data.emergency_contact,
                verification_method="VERIFICATION_CODE",
                status="VERIFIED",
                notes="Verified via administrator-issued token.",
                verified_by_user_id=v_code.generated_by_user_id,
            )
            await self.repo.mark_verification_code_used(v_code.id, parent_user_id)
            await self.session.commit()
            return {
                "link_id": str(link.id),
                "status": "VERIFIED",
                "message": "Child successfully verified and linked to your parent portal!",
            }

        # Otherwise: Queued for Administrator Approval
        link = await self.repo.create_link_request(
            tenant_id=tenant_id,
            student_id=student.id,
            parent_user_id=parent_user_id,
            relation_type=data.relation_type,
            emergency_contact=data.emergency_contact,
            verification_method="ADMIN_APPROVAL",
            status="PENDING_APPROVAL",
            notes=data.notes,
        )
        await self.session.commit()
        return {
            "link_id": str(link.id),
            "status": "PENDING_APPROVAL",
            "message": "Linking request submitted. An institution administrator must review and approve this relationship.",
        }

    async def admin_invite_parent(
        self, tenant_id: uuid.UUID, admin_user_id: uuid.UUID, data: AdminInviteParentRequest
    ) -> Dict[str, Any]:
        """
        Administrator directly invites or registers a parent with pre-verified student linking.
        """
        student = await self.repo.get_student_by_id(tenant_id, data.student_id)
        if not student:
            raise NotFoundException("Student record not found.")

        # Find or create User for parent
        stmt = select(User).where(User.email == data.parent_email)
        parent_user = (await self.session.execute(stmt)).scalars().first()
        is_new_user = False

        if not parent_user:
            is_new_user = True
            parent_user = User(
                email=data.parent_email,
                full_name=data.parent_name,
                phone=data.parent_phone,
                password_hash="INVITED_PENDING_ACTIVATION",
                is_active=True,
                status="INVITED",
            )
            self.session.add(parent_user)
            await self.session.flush()

        # Ensure parent has PARENT role membership in this institution
        parent_role = (await self.session.execute(select(Role).where(Role.code == "PARENT"))).scalars().first()
        if parent_role:
            mem_stmt = select(Membership).where(
                Membership.tenant_id == tenant_id,
                Membership.user_id == parent_user.id,
            )
            existing_mem = (await self.session.execute(mem_stmt)).scalars().first()
            if not existing_mem:
                self.session.add(Membership(tenant_id=tenant_id, user_id=parent_user.id, role_id=parent_role.id))
                await self.session.flush()

        # Create or update verified link
        link = await self.repo.get_student_parent(tenant_id, student.id, parent_user.id)
        if link:
            link.status = "VERIFIED"
            link.relation_type = data.relation_type
            link.is_primary = data.is_primary
            link.can_view_grades = data.can_view_grades
            link.can_pay_fees = data.can_pay_fees
            link.emergency_contact = data.emergency_contact
            link.verified_by_user_id = admin_user_id
            link.verified_at = datetime.now(timezone.utc)
            link.verification_method = "ADMIN_INVITATION"
        else:
            link = await self.repo.create_link_request(
                tenant_id=tenant_id,
                student_id=student.id,
                parent_user_id=parent_user.id,
                relation_type=data.relation_type,
                emergency_contact=data.emergency_contact,
                verification_method="ADMIN_INVITATION",
                status="VERIFIED",
                notes="Created via official administrator invitation.",
                is_primary=data.is_primary,
                can_view_grades=data.can_view_grades,
                can_pay_fees=data.can_pay_fees,
                verified_by_user_id=admin_user_id,
            )

        await self.session.commit()
        return {
            "link_id": str(link.id),
            "parent_user_id": str(parent_user.id),
            "is_new_user": is_new_user,
            "status": "VERIFIED",
            "message": f"Parent successfully invited and linked to {student.user.full_name if student.user else student.admission_number}.",
        }

    async def generate_verification_code(
        self, tenant_id: uuid.UUID, admin_user_id: uuid.UUID, data: AdminGenerateVerificationCodeRequest
    ) -> VerificationCodeResponse:
        student = await self.repo.get_student_by_id(tenant_id, data.student_id)
        if not student:
            raise NotFoundException("Student not found.")

        # Generate secure token
        token = f"LNK-{secrets.token_hex(4).upper()}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.valid_days)
        code_obj = await self.repo.create_verification_code(
            tenant_id, student.id, token, admin_user_id, expires_at
        )
        await self.session.commit()

        s_name = student.user.full_name if (student.user and student.user.full_name) else "Student"
        return VerificationCodeResponse(
            id=code_obj.id,
            code=token,
            student_id=student.id,
            student_name=s_name,
            admission_number=student.admission_number,
            expires_at=expires_at,
            is_used=False,
        )

    async def list_pending_requests(self, tenant_id: uuid.UUID) -> List[ParentLinkRequestItem]:
        links = await self.repo.list_pending_link_requests(tenant_id)
        items = []
        for l in links:
            s_name = l.student.user.full_name if (l.student and l.student.user) else "Student"
            adm = l.student.admission_number if l.student else "-"
            p_name = l.parent_user.full_name if l.parent_user else "Parent"
            p_email = l.parent_user.email if l.parent_user else "-"
            p_phone = l.parent_user.phone if l.parent_user else None
            items.append(
                ParentLinkRequestItem(
                    id=l.id,
                    student_id=l.student_id,
                    student_name=s_name,
                    admission_number=adm,
                    parent_user_id=l.parent_user_id,
                    parent_name=p_name,
                    parent_email=p_email,
                    parent_phone=p_phone,
                    relation_type=l.relation_type,
                    status=l.status,
                    verification_method=l.verification_method,
                    verification_notes=l.verification_notes,
                    emergency_contact=l.emergency_contact,
                    created_at=l.created_at,
                )
            )
        return items

    async def process_link_request(
        self, tenant_id: uuid.UUID, link_id: uuid.UUID, admin_user_id: uuid.UUID, data: AdminApproveLinkRequest
    ) -> Dict[str, Any]:
        target_status = "VERIFIED" if data.action == "APPROVE" else "REJECTED"
        link = await self.repo.update_link_status(
            tenant_id=tenant_id,
            link_id=link_id,
            status=target_status,
            verified_by_user_id=admin_user_id,
            notes=data.approval_notes,
            can_view_grades=data.can_view_grades,
            can_pay_fees=data.can_pay_fees,
        )
        if not link:
            raise NotFoundException("Link request record not found.")

        # Ensure parent has membership with PARENT role
        if target_status == "VERIFIED":
            parent_role = (await self.session.execute(select(Role).where(Role.code == "PARENT"))).scalars().first()
            if parent_role:
                mem_stmt = select(Membership).where(
                    Membership.tenant_id == tenant_id,
                    Membership.user_id == link.parent_user_id,
                )
                existing_mem = (await self.session.execute(mem_stmt)).scalars().first()
                if not existing_mem:
                    self.session.add(Membership(tenant_id=tenant_id, user_id=link.parent_user_id, role_id=parent_role.id))

        await self.session.commit()
        return {
            "link_id": str(link.id),
            "status": target_status,
            "message": f"Parent-student linking request has been {target_status.lower()}.",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Multi-Child Parent Portal Queries (Restricted to Verified Links)
    # ─────────────────────────────────────────────────────────────────────────

    async def assert_verified_access(
        self, tenant_id: uuid.UUID, parent_user_id: uuid.UUID, student_id: uuid.UUID
    ) -> StudentParent:
        link = await self.repo.get_student_parent(tenant_id, student_id, parent_user_id)
        if not link or link.status != "VERIFIED":
            raise ForbiddenException("Access denied: You are not authorized to view academic data for this student.")
        return link

    async def get_parent_children(self, parent_user_id: uuid.UUID) -> List[LinkedChildSummary]:
        links = await self.repo.list_linked_children_for_user(parent_user_id, status=None)
        results = []
        for l in links:
            st = l.student
            if not st:
                continue

            inst_name = st.tenant.name if st.tenant else "Institution"
            inst_slug = st.tenant.slug if st.tenant else ""
            c_name = st.school_class.name if st.school_class else None
            sec_name = st.section.name if st.section else None
            cr_name = st.course.name if st.course else None

            # Quick attendance metric
            att_pct = 0.0
            fee_due = 0.0
            if l.status == "VERIFIED":
                counts = await self.repo.get_child_attendance_counts(st.tenant_id, st.id)
                tot = sum(counts.values())
                pres = counts.get("PRESENT", 0) + (counts.get("LATE", 0) * 0.5)
                att_pct = round((pres / tot) * 100, 1) if tot > 0 else 100.0

                fee_info = await self.repo.get_child_invoices_and_due(st.tenant_id, st.id)
                fee_due = fee_info.get("total_due", 0.0)

            results.append(
                LinkedChildSummary(
                    student_id=st.id,
                    student_name=st.user.full_name if st.user else "Child",
                    admission_number=st.admission_number,
                    roll_number=st.roll_number,
                    institution_id=st.tenant_id,
                    institution_name=inst_name,
                    institution_slug=inst_slug,
                    class_id=st.class_id,
                    class_name=c_name,
                    section_id=st.section_id,
                    section_name=sec_name,
                    course_name=cr_name,
                    semester_name=None,
                    relation_type=l.relation_type,
                    is_primary=l.is_primary,
                    verification_status=l.status,
                    can_view_grades=l.can_view_grades,
                    can_pay_fees=l.can_pay_fees,
                    attendance_percentage=att_pct,
                    total_due_fees=fee_due,
                    avatar_url=st.user.avatar_url if st.user else None,
                )
            )
        return results

    async def get_child_profile(
        self, tenant_id: uuid.UUID, parent_user_id: uuid.UUID, student_id: uuid.UUID
    ) -> ChildDetailedProfileResponse:
        link = await self.assert_verified_access(tenant_id, parent_user_id, student_id)
        st = await self.repo.get_student_by_id(tenant_id, student_id)
        if not st:
            raise NotFoundException("Student profile not found.")

        u = st.user
        return ChildDetailedProfileResponse(
            student_id=st.id,
            admission_number=st.admission_number,
            roll_number=st.roll_number,
            admission_date=st.admission_date,
            full_name=u.full_name if u else "Child",
            email=u.email if u else None,
            phone=u.phone if u else None,
            gender=st.gender,
            date_of_birth=st.date_of_birth,
            blood_group=st.blood_group,
            address=st.address_line1 or None,
            institution_name=st.tenant.name if st.tenant else "Institution",
            academic_session_name=st.academic_session.name if st.academic_session else None,
            class_name=st.school_class.name if st.school_class else None,
            section_name=st.section.name if st.section else None,
            course_name=st.course.name if st.course else None,
            semester_name=None,
            class_teacher_name=st.school_class.class_teacher.user.full_name if (st.school_class and st.school_class.class_teacher and st.school_class.class_teacher.user) else None,
            relation_type=link.relation_type,
            is_primary=link.is_primary,
            emergency_contact=link.emergency_contact,
            status=st.status,
        )

    async def get_child_attendance(
        self, tenant_id: uuid.UUID, parent_user_id: uuid.UUID, student_id: uuid.UUID
    ) -> ChildAttendanceResponse:
        await self.assert_verified_access(tenant_id, parent_user_id, student_id)
        counts = await self.repo.get_child_attendance_counts(tenant_id, student_id)
        tot = sum(counts.values())
        present = counts.get("PRESENT", 0)
        absent = counts.get("ABSENT", 0)
        late = counts.get("LATE", 0)
        pres_weighted = present + (late * 0.5)
        pct = round((pres_weighted / tot) * 100, 1) if tot > 0 else 100.0

        entries_raw = await self.repo.get_child_attendance(tenant_id, student_id, limit=30)
        recent = []
        for e in entries_raw:
            s_date = e.session.session_date if e.session else date.today()
            p_num = e.session.period_number if e.session else None
            recent.append(
                ChildAttendanceDayEntry(
                    date=s_date,
                    status=e.status,
                    period_number=p_num,
                    subject_name=None,
                    remarks=e.remarks,
                )
            )

        return ChildAttendanceResponse(
            overall_percentage=pct,
            total_days=tot,
            present_days=present,
            absent_days=absent,
            late_days=late,
            recent_entries=recent,
            low_attendance_alert=(pct < 75.0 and tot >= 5),
        )

    async def get_child_timetable(
        self, tenant_id: uuid.UUID, parent_user_id: uuid.UUID, student_id: uuid.UUID
    ) -> ChildTimetableResponse:
        await self.assert_verified_access(tenant_id, parent_user_id, student_id)
        st = await self.repo.get_student_by_id(tenant_id, student_id)
        if not st:
            raise NotFoundException("Student not found.")

        raw_entries = await self.repo.get_child_timetable_entries(tenant_id, st)
        days_map: Dict[str, List[ChildTimetableEntryItem]] = {
            "MONDAY": [], "TUESDAY": [], "WEDNESDAY": [], "THURSDAY": [], "FRIDAY": [], "SATURDAY": []
        }

        for e in raw_entries:
            d = e.day_of_week.upper()
            if d in days_map:
                t_name = e.teacher.user.full_name if (e.teacher and e.teacher.user) else None
                s_name = e.subject.name if e.subject else "General"
                room = e.room_number
                days_map[d].append(
                    ChildTimetableEntryItem(
                        period_number=e.period_number,
                        start_time=e.start_time.strftime("%H:%M") if hasattr(e.start_time, "strftime") else str(e.start_time),
                        end_time=e.end_time.strftime("%H:%M") if hasattr(e.end_time, "strftime") else str(e.end_time),
                        subject_name=s_name,
                        teacher_name=t_name,
                        room_number=room,
                        is_practical=e.is_practical,
                    )
                )

        schedule = [ChildDayTimetable(day_of_week=d, entries=entries) for d, entries in days_map.items()]
        return ChildTimetableResponse(
            class_name=st.school_class.name if st.school_class else None,
            section_name=st.section.name if st.section else None,
            schedule=schedule,
        )

    async def get_child_examinations(
        self, tenant_id: uuid.UUID, parent_user_id: uuid.UUID, student_id: uuid.UUID
    ) -> ChildExaminationsResponse:
        await self.assert_verified_access(tenant_id, parent_user_id, student_id)
        st = await self.repo.get_student_by_id(tenant_id, student_id)
        if not st:
            raise NotFoundException("Student not found.")

        exams = await self.repo.get_child_examinations(tenant_id, st)
        today = date.today()
        upcoming = []
        past = []

        for x in exams:
            item = ChildExamItem(
                exam_id=x.id,
                title=x.title,
                exam_type=x.exam_type,
                subject_name=x.subject.name if x.subject else "Subject",
                exam_date=x.start_datetime.date(),
                start_time=x.start_datetime.strftime("%H:%M"),
                duration_minutes=x.duration_minutes,
                total_marks=float(x.total_marks),
                passing_marks=float(x.passing_marks),
                is_online=x.mode in ("ONLINE", "HYBRID"),
            )
            if x.start_datetime.date() >= today:
                upcoming.append(item)
            else:
                past.append(item)

        return ChildExaminationsResponse(upcoming_exams=upcoming, past_exams=past)

    async def get_child_results(
        self, tenant_id: uuid.UUID, parent_user_id: uuid.UUID, student_id: uuid.UUID
    ) -> List[ChildTermResultResponse]:
        link = await self.assert_verified_access(tenant_id, parent_user_id, student_id)
        if not link.can_view_grades:
            raise ForbiddenException("Permission to view examination grades is restricted for this parent account.")

        results = await self.repo.get_child_published_results(tenant_id, student_id)
        by_exam: dict[uuid.UUID, list[ChildSubjectResultItem]] = {}
        if results:
            subject_rows = await self.repo.get_published_subject_results(tenant_id, student_id, [r.exam_id for r in results])
            for row in subject_rows:
                by_exam.setdefault(row.exam_id, []).append(ChildSubjectResultItem(
                    subject_name=row.subject.name,
                    subject_code=row.subject.code,
                    theory_marks=float(row.theory_marks),
                    practical_marks=float(row.practical_marks),
                    assignment_marks=float(row.assignment_marks),
                    total_marks=float(row.total_marks),
                    max_marks=float(row.max_marks),
                    grade=row.grade,
                    is_pass=row.is_passed,
                ))
        resp = []
        for r in results:
            resp.append(
                ChildTermResultResponse(
                    result_id=r.id,
                    examination_title=r.exam.title if r.exam else "Term Exam",
                    academic_session_name=r.academic_session.name if r.academic_session else "-",
                    total_marks_obtained=float(r.total_obtained),
                    max_marks_possible=float(r.total_max),
                    percentage=float(r.overall_percentage),
                    cgpa=float(r.cgpa) if r.cgpa is not None else None,
                    final_grade=r.overall_grade,
                    result_status="PASS" if r.is_passed else "FAIL",
                    is_published=r.approval_status == "PUBLISHED",
                    subjects=by_exam.get(r.exam_id, []),
                )
            )
        return resp

    async def get_child_assignments(
        self, tenant_id: uuid.UUID, parent_user_id: uuid.UUID, student_id: uuid.UUID
    ) -> List[ChildAssignmentItem]:
        await self.assert_verified_access(tenant_id, parent_user_id, student_id)
        st = await self.repo.get_student_by_id(tenant_id, student_id)
        if not st:
            raise NotFoundException("Student not found.")

        rows = await self.repo.get_child_assignments(tenant_id, st)
        items = []
        for r in rows:
            a = r["assignment"]
            sub = r["submission"]
            items.append(
                ChildAssignmentItem(
                    id=a.id,
                    title=a.title,
                    subject_name=r["subject_name"],
                    teacher_name=r["teacher_name"],
                    due_date=a.due_datetime,
                    max_score=float(a.total_marks),
                    is_submitted=sub is not None,
                    submitted_at=sub.submitted_at if sub else None,
                    is_late=sub.is_late if sub else False,
                    grade=sub.grade if sub else None,
                    score=float(sub.marks_obtained) if (sub and sub.marks_obtained is not None) else None,
                    teacher_feedback=sub.teacher_feedback if sub else None,
                )
            )
        return items

    async def get_child_study_materials(
        self, tenant_id: uuid.UUID, parent_user_id: uuid.UUID, student_id: uuid.UUID
    ) -> List[ChildStudyMaterialItem]:
        await self.assert_verified_access(tenant_id, parent_user_id, student_id)
        st = await self.repo.get_student_by_id(tenant_id, student_id)
        if not st:
            raise NotFoundException("Student not found.")

        materials = await self.repo.get_child_study_materials(tenant_id, st)
        items = []
        for m in materials:
            items.append(
                ChildStudyMaterialItem(
                    id=m.id,
                    title=m.title,
                    subject_name=m.subject.name if m.subject else "General",
                    material_type=m.material_type,
                    description=m.description,
                    file_name=m.file_name,
                    file_size_bytes=m.file_size_bytes,
                    download_url=f"/api/v1/materials/{m.id}/download" if m.file_key else None,
                    external_url=m.external_url,
                    created_at=m.created_at,
                )
            )
        return items

    async def get_child_fees(
        self, tenant_id: uuid.UUID, parent_user_id: uuid.UUID, student_id: uuid.UUID
    ) -> Dict[str, Any]:
        link = await self.assert_verified_access(tenant_id, parent_user_id, student_id)
        if not link.can_pay_fees:
            raise ForbiddenException("Fee access is restricted for this parent account.")

        fee_info = await self.repo.get_child_invoices_and_due(tenant_id, student_id)
        inv_list = []
        for inv in fee_info["invoices"]:
            inv_list.append({
                "id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "title": inv.title,
                "due_date": str(inv.due_date),
                "total_amount": float(inv.total_amount),
                "paid_amount": float(inv.paid_amount),
                "balance_amount": float(inv.balance_amount),
                "status": inv.status,
                "line_items": inv.line_items or [],
            })

        pay_list = []
        for p in fee_info["payments"]:
            pay_list.append({
                "id": str(p.id),
                "receipt_number": p.receipt_number,
                "amount": float(p.amount),
                "payment_date": str(p.payment_date),
                "payment_mode": p.payment_mode,
                "transaction_reference": p.transaction_reference,
                "status": p.status,
            })

        return {
            "total_due": fee_info["total_due"],
            "invoices": inv_list,
            "payments": pay_list,
        }

    async def get_child_teachers(
        self, tenant_id: uuid.UUID, parent_user_id: uuid.UUID, student_id: uuid.UUID
    ) -> List[ChildTeacherContact]:
        await self.assert_verified_access(tenant_id, parent_user_id, student_id)
        st = await self.repo.get_student_by_id(tenant_id, student_id)
        if not st:
            raise NotFoundException("Student not found.")

        contacts = await self.repo.get_child_teachers(tenant_id, st)
        return [ChildTeacherContact(**c) for c in contacts]

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Parent-Teacher Messaging
    # ─────────────────────────────────────────────────────────────────────────

    async def send_message(
        self,
        tenant_id: uuid.UUID,
        sender_user_id: uuid.UUID,
        sender_role: str,
        data: SendMessageRequest,
    ) -> Dict[str, Any]:
        # Guard: If sender is parent, ensure verified child link
        if sender_role == "PARENT":
            await self.assert_verified_access(tenant_id, sender_user_id, data.student_id)
            parent_id = sender_user_id
            teacher_id = data.teacher_user_id
        else:
            teacher_id = sender_user_id
            parent_id = data.teacher_user_id  # In reply context

        msg = await self.repo.create_message(
            tenant_id=tenant_id,
            student_id=data.student_id,
            parent_user_id=parent_id,
            teacher_user_id=teacher_id,
            subject=data.subject,
            message=data.message,
            sender_role=sender_role,
            parent_message_id=data.parent_message_id,
        )
        await self.session.commit()
        return {"id": str(msg.id), "status": "sent", "message": "Communication message delivered successfully."}

    async def list_messages(
        self, user_id: uuid.UUID, role: str, student_id: Optional[uuid.UUID] = None
    ) -> List[ParentTeacherMessageResponse]:
        if role == "PARENT":
            threads = await self.repo.list_messages_for_parent(user_id, student_id)
        else:
            threads = await self.repo.list_messages_for_teacher(user_id, student_id)

        items = []
        for t in threads:
            s_name = t.student.user.full_name if (t.student and t.student.user) else "Student"
            p_name = t.parent_user.full_name if t.parent_user else "Parent"
            t_name = t.teacher_user.full_name if t.teacher_user else "Teacher"

            replies = []
            for r in (t.replies or []):
                rp_pname = r.parent_user.full_name if r.parent_user else "Parent"
                rp_tname = r.teacher_user.full_name if r.teacher_user else "Teacher"
                replies.append(
                    ParentTeacherMessageResponse(
                        id=r.id,
                        student_id=r.student_id,
                        student_name=s_name,
                        parent_user_id=r.parent_user_id,
                        parent_name=rp_pname,
                        teacher_user_id=r.teacher_user_id,
                        teacher_name=rp_tname,
                        subject=r.subject,
                        message=r.message,
                        sender_role=r.sender_role,
                        is_read=r.is_read,
                        created_at=r.created_at,
                        replies=[],
                    )
                )

            items.append(
                ParentTeacherMessageResponse(
                    id=t.id,
                    student_id=t.student_id,
                    student_name=s_name,
                    parent_user_id=t.parent_user_id,
                    parent_name=p_name,
                    teacher_user_id=t.teacher_user_id,
                    teacher_name=t_name,
                    subject=t.subject,
                    message=t.message,
                    sender_role=t.sender_role,
                    is_read=t.is_read,
                    created_at=t.created_at,
                    replies=replies,
                )
            )
        return items
