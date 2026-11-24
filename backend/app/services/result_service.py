from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException, AuthorizationException, BadRequestException, NotFoundException
from app.core.logging import get_logger
from app.models.academic import StudentParent, StudentProfile, Subject
from app.models.examination import Examination
from app.models.result import (
    GradingScale,
    ReEvaluationRequest,
    ResultRevisionHistory,
    StudentSubjectResult,
    StudentTermResult,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.result import ResultRepository
from app.repositories.attendance import AttendanceRepository
from app.services.staff_access_service import require_teaching_assignment
from app.schemas.result import (
    BulkSubjectMarksEntryRequest,
    ClassPerformanceAnalytics,
    GradingScaleBase,
    GradingScaleCreate,
    GradingScaleResponse,
    ReEvaluationActionRequest,
    ReEvaluationRequestCreate,
    ReEvaluationResponse,
    ResultApprovalWorkflowRequest,
    ResultRevisionHistoryResponse,
    ResultRevisionRequest,
    StudentSubjectResultResponse,
    StudentTermResultResponse,
)
from app.utils.report_card_pdf import generate_report_card_pdf

logger = get_logger("result_service")


class ResultService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ResultRepository(session)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Grading Scale Management
    # ─────────────────────────────────────────────────────────────────────────

    async def get_or_create_grading_scale(self, tenant_id: uuid.UUID) -> GradingScaleResponse:
        scale = await self.repo.get_or_create_default_grading_scale(tenant_id)
        await self.session.commit()
        return GradingScaleResponse.model_validate(scale)

    async def create_grading_scale(
        self, tenant_id: uuid.UUID, data: GradingScaleCreate
    ) -> GradingScaleResponse:
        grades_json = [g.model_dump() for g in data.grades]
        scale = GradingScale(
            tenant_id=tenant_id,
            name=data.name,
            scale_type=data.scale_type,
            grades=grades_json,
            is_default=data.is_default,
        )
        self.session.add(scale)
        await self.session.commit()
        return GradingScaleResponse.model_validate(scale)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Subject Marks Entry & Calculation
    # ─────────────────────────────────────────────────────────────────────────

    async def marks_roster(self, tenant_id: uuid.UUID, exam_id: uuid.UUID, subject_id: uuid.UUID, teacher_user_id: Optional[uuid.UUID]):
        exam = await self.session.scalar(select(Examination).where(
            Examination.id == exam_id, Examination.tenant_id == tenant_id, Examination.is_deleted.is_(False),
        ))
        if not exam:
            raise NotFoundException("Examination not found.")
        subject = await self.session.scalar(select(Subject.id).where(
            Subject.id == subject_id, Subject.tenant_id == tenant_id, Subject.is_deleted.is_(False),
        ))
        if not subject or (exam.subject_id and exam.subject_id != subject_id):
            raise BadRequestException("Select the subject assigned to this examination.")
        cohort = {
            "class_id": exam.class_id, "section_id": exam.section_id,
            "course_id": exam.course_id, "semester_id": exam.semester_id,
        }
        await require_teaching_assignment(
            self.session, tenant_id, teacher_user_id, exam.academic_session_id, subject_id=subject_id, **cohort,
        )
        _, roster = await AttendanceRepository(self.session).get_roster_for_marking(
            tenant_id, exam.academic_session_id, date.today(), **cohort,
        )
        return exam, roster

    async def load_marks_roster(self, tenant_id: uuid.UUID, exam_id: uuid.UUID, subject_id: uuid.UUID, teacher_user_id: Optional[uuid.UUID]):
        _, roster = await self.marks_roster(tenant_id, exam_id, subject_id, teacher_user_id)
        marks = await self.session.scalars(select(StudentSubjectResult).where(
            StudentSubjectResult.tenant_id == tenant_id, StudentSubjectResult.exam_id == exam_id,
            StudentSubjectResult.subject_id == subject_id, StudentSubjectResult.is_deleted.is_(False),
        ))
        saved = {mark.student_id: mark for mark in marks}
        rows = []
        for student in roster:
            row = {key: student[key] for key in ("student_id", "admission_number", "roll_number")}
            row["student_name"] = student["full_name"]
            if mark := saved.get(student["student_id"]):
                for field in ("theory", "practical", "internal", "assignment"):
                    row[f"{field}_marks"] = float(getattr(mark, f"{field}_marks"))
                    row[f"{field}_max_marks"] = float(getattr(mark, f"{field}_max_marks"))
                row.update(credits=float(mark.credits), remarks=mark.remarks)
            rows.append(row)
        return rows

    async def enter_subject_marks_bulk(
        self, tenant_id: uuid.UUID, data: BulkSubjectMarksEntryRequest, current_user: User,
        teacher_user_id: Optional[uuid.UUID] = None,
    ) -> List[StudentSubjectResultResponse]:
        exam, roster = await self.marks_roster(tenant_id, data.exam_id, data.subject_id, teacher_user_id)
        enrolled = {student["student_id"] for student in roster}
        submitted = {entry.student_id for entry in data.entries}
        if not submitted or len(submitted) != len(data.entries) or not submitted.issubset(enrolled):
            raise BadRequestException("Marks must list each selected student once and belong to this examination's roster.")
        entries_dict = [e.model_dump() for e in data.entries]
        try:
            results = await self.repo.save_subject_marks_bulk(
                tenant_id=tenant_id,
                exam_id=data.exam_id,
                academic_session_id=data.academic_session_id,
                subject_id=data.subject_id,
                class_id=exam.class_id,
                section_id=exam.section_id,
                entries=entries_dict,
                user_id=current_user.id,
            )
            await self.session.commit()
        except ValueError as e:
            raise BadRequestException(str(e))

        # Reload results with relationships
        output: List[StudentSubjectResultResponse] = []
        for r in results:
            stmt = (
                select(StudentSubjectResult)
                .where(StudentSubjectResult.tenant_id == tenant_id, StudentSubjectResult.id == r.id)
                .options(
                    selectinload(StudentSubjectResult.subject),
                    selectinload(StudentSubjectResult.student).selectinload(StudentProfile.user),
                )
            )
            loaded = (await self.session.execute(stmt)).scalars().first()
            if loaded:
                output.append(self._build_subject_result_response(loaded))
        return output

    def _build_subject_result_response(self, record: StudentSubjectResult) -> StudentSubjectResultResponse:
        stu_user = record.student.user if record.student else None
        return StudentSubjectResultResponse(
            id=record.id,
            tenant_id=record.tenant_id,
            student_id=record.student_id,
            student_name=stu_user.full_name if stu_user else "Unknown Student",
            admission_number=record.student.admission_number if record.student else "N/A",
            roll_number=record.student.roll_number if record.student else None,
            exam_id=record.exam_id,
            subject_id=record.subject_id,
            subject_name=record.subject.name if record.subject else "Subject",
            subject_code=record.subject.code if record.subject else "",
            theory_marks=record.theory_marks,
            theory_max_marks=record.theory_max_marks,
            practical_marks=record.practical_marks,
            practical_max_marks=record.practical_max_marks,
            internal_marks=record.internal_marks,
            internal_max_marks=record.internal_max_marks,
            assignment_marks=record.assignment_marks,
            assignment_max_marks=record.assignment_max_marks,
            total_marks=record.total_marks,
            max_marks=record.max_marks,
            percentage=record.percentage,
            grade=record.grade,
            grade_point=record.grade_point,
            credits=record.credits,
            credit_points=record.credit_points,
            is_passed=record.is_passed,
            status=record.status,
            remarks=record.remarks,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Result Approval Workflow
    # ─────────────────────────────────────────────────────────────────────────

    async def process_approval_workflow(
        self, tenant_id: uuid.UUID, data: ResultApprovalWorkflowRequest, current_user: User
    ) -> Dict[str, Any]:
        try:
            res = await self.repo.transition_approval_workflow(
                tenant_id=tenant_id,
                exam_id=data.exam_id,
                action=data.action,
                user_id=current_user.id,
                comments=data.comments,
            )
            await self.session.commit()
            return res
        except ValueError as e:
            raise BadRequestException(str(e))

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Result Correction & Revision History
    # ─────────────────────────────────────────────────────────────────────────

    async def revise_subject_marks(
        self, tenant_id: uuid.UUID, data: ResultRevisionRequest, current_user: User
    ) -> StudentSubjectResultResponse:
        try:
            record = await self.repo.revise_subject_result_marks(
                tenant_id=tenant_id,
                subject_result_id=data.subject_result_id,
                revision_reason=data.revision_reason,
                modified_by=current_user.id,
                new_theory=data.theory_marks,
                new_practical=data.practical_marks,
                new_internal=data.internal_marks,
                new_assignment=data.assignment_marks,
                approved_by=current_user.id,
            )
            await self.session.commit()
            # Reload
            stmt = (
                select(StudentSubjectResult)
                .where(StudentSubjectResult.tenant_id == tenant_id, StudentSubjectResult.id == record.id)
                .options(
                    selectinload(StudentSubjectResult.subject),
                    selectinload(StudentSubjectResult.student).selectinload(StudentProfile.user),
                )
            )
            loaded = (await self.session.execute(stmt)).scalars().first()
            return self._build_subject_result_response(loaded)  # type: ignore
        except ValueError as e:
            raise BadRequestException(str(e))

    async def get_revision_history(
        self, tenant_id: uuid.UUID, subject_result_id: uuid.UUID
    ) -> List[ResultRevisionHistoryResponse]:
        stmt = (
            select(ResultRevisionHistory)
            .where(
                ResultRevisionHistory.tenant_id == tenant_id,
                ResultRevisionHistory.subject_result_id == subject_result_id,
            )
            .order_by(ResultRevisionHistory.modified_at.desc())
            .options(
                selectinload(ResultRevisionHistory.modifier),
                selectinload(ResultRevisionHistory.approver),
            )
        )
        logs = list((await self.session.execute(stmt)).scalars().all())
        output = []
        for l in logs:
            output.append(
                ResultRevisionHistoryResponse(
                    id=l.id,
                    subject_result_id=l.subject_result_id,
                    previous_marks=l.previous_marks,
                    new_marks=l.new_marks,
                    revision_reason=l.revision_reason,
                    modified_by=l.modified_by,
                    modified_by_name=l.modifier.full_name if l.modifier else "Staff",
                    approved_by=l.approved_by,
                    approved_by_name=l.approver.full_name if l.approver else None,
                    modified_at=l.modified_at,
                )
            )
        return output

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Re-Evaluation Appeals
    # ─────────────────────────────────────────────────────────────────────────

    async def submit_reevaluation_request(
        self, tenant_id: uuid.UUID, data: ReEvaluationRequestCreate, current_user: User, role: str
    ) -> ReEvaluationResponse:
        stmt = select(StudentSubjectResult).where(
            StudentSubjectResult.tenant_id == tenant_id,
            StudentSubjectResult.id == data.subject_result_id,
            StudentSubjectResult.is_deleted.is_(False),
        )
        subject_result = await self.session.scalar(stmt)
        if not subject_result:
            raise NotFoundException("Subject result not found.")
        await self._require_result_reader(tenant_id, subject_result.student_id, current_user, role)
        if subject_result.status != "PUBLISHED":
            raise BadRequestException("Re-evaluation opens after results are published.")

        req = await self.repo.create_reevaluation_request(
            tenant_id=tenant_id,
            subject_result_id=data.subject_result_id,
            student_id=subject_result.student_id,
            reason=data.reason,
            user_id=current_user.id,
        )
        await self.session.commit()

        # Reload
        stmt_reload = (
            select(ReEvaluationRequest)
            .where(ReEvaluationRequest.id == req.id)
            .options(
                selectinload(ReEvaluationRequest.subject_result).selectinload(StudentSubjectResult.subject),
                selectinload(ReEvaluationRequest.student).selectinload(StudentProfile.user),
            )
        )
        loaded = (await self.session.execute(stmt_reload)).scalars().first()
        stu_user = loaded.student.user if loaded and loaded.student else None
        return ReEvaluationResponse(
            id=loaded.id,  # type: ignore
            subject_result_id=loaded.subject_result_id,  # type: ignore
            student_id=loaded.student_id,  # type: ignore
            student_name=stu_user.full_name if stu_user else "Student",
            subject_name=loaded.subject_result.subject.name if loaded and loaded.subject_result.subject else "Subject",  # type: ignore
            reason=loaded.reason,  # type: ignore
            status=loaded.status,  # type: ignore
            created_at=loaded.created_at,  # type: ignore
        )

    async def list_reevaluation_requests(
        self, tenant_id: uuid.UUID, status: Optional[str] = None
    ) -> List[ReEvaluationResponse]:
        reqs = await self.repo.list_reevaluation_requests(tenant_id, status)
        output = []
        for r in reqs:
            stu_user = r.student.user if r.student else None
            output.append(
                ReEvaluationResponse(
                    id=r.id,
                    subject_result_id=r.subject_result_id,
                    student_id=r.student_id,
                    student_name=stu_user.full_name if stu_user else "Student",
                    subject_name=r.subject_result.subject.name if r.subject_result and r.subject_result.subject else "Subject",
                    reason=r.reason,
                    status=r.status,
                    reviewer_name=r.reviewer.full_name if r.reviewer else None,
                    reviewer_remarks=r.reviewer_remarks,
                    reviewed_at=r.reviewed_at,
                    created_at=r.created_at,
                )
            )
        return output

    async def resolve_reevaluation_request(
        self, tenant_id: uuid.UUID, request_id: uuid.UUID, data: ReEvaluationActionRequest, current_user: User
    ) -> ReEvaluationResponse:
        try:
            resolved = await self.repo.resolve_reevaluation_request(
                tenant_id=tenant_id,
                request_id=request_id,
                status=data.status,
                reviewer_remarks=data.reviewer_remarks,
                reviewer_id=current_user.id,
                updated_theory=data.updated_theory_marks,
                updated_practical=data.updated_practical_marks,
                updated_internal=data.updated_internal_marks,
            )
            await self.session.commit()
            stu_user = resolved.student.user if resolved.student else None
            return ReEvaluationResponse(
                id=resolved.id,
                subject_result_id=resolved.subject_result_id,
                student_id=resolved.student_id,
                student_name=stu_user.full_name if stu_user else "Student",
                subject_name=resolved.subject_result.subject.name if resolved.subject_result and resolved.subject_result.subject else "Subject",
                reason=resolved.reason,
                status=resolved.status,
                reviewer_name=current_user.full_name,
                reviewer_remarks=resolved.reviewer_remarks,
                reviewed_at=resolved.reviewed_at,
                created_at=resolved.created_at,
            )
        except ValueError as e:
            raise BadRequestException(str(e))

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Performance Analytics
    # ─────────────────────────────────────────────────────────────────────────

    async def get_class_performance_analytics(
        self, tenant_id: uuid.UUID, exam_id: uuid.UUID
    ) -> ClassPerformanceAnalytics:
        try:
            data = await self.repo.get_class_performance_analytics(tenant_id, exam_id)
            return ClassPerformanceAnalytics.model_validate(data)
        except ValueError as e:
            raise NotFoundException(str(e))

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Student Term Results & Downloadable PDF Report Card
    # ─────────────────────────────────────────────────────────────────────────

    async def _require_result_reader(self, tenant_id: uuid.UUID, student_id: uuid.UUID, user: User, role: str) -> None:
        if user.is_superadmin or role in ("INSTITUTION_ADMIN", "TEACHER"):
            return
        if role == "STUDENT":
            access = await self.session.scalar(select(StudentProfile.id).where(
                StudentProfile.tenant_id == tenant_id, StudentProfile.id == student_id,
                StudentProfile.user_id == user.id, StudentProfile.is_deleted.is_(False),
            ))
        elif role == "PARENT":
            access = await self.session.scalar(select(StudentParent.id).where(
                StudentParent.tenant_id == tenant_id, StudentParent.student_id == student_id,
                StudentParent.parent_user_id == user.id, StudentParent.status == "VERIFIED",
                StudentParent.can_view_grades.is_(True), StudentParent.is_deleted.is_(False),
            ))
        else:
            access = None
        if not access:
            raise AuthorizationException("You do not have access to this student's results.")

    async def get_student_report_card(
        self, tenant_id: uuid.UUID, exam_id: uuid.UUID, student_id: uuid.UUID, current_user: User, role: str
    ) -> StudentTermResultResponse:
        await self._require_result_reader(tenant_id, student_id, current_user, role)
        term_res = await self.repo.get_student_term_result(tenant_id, exam_id, student_id)
        if not term_res:
            raise NotFoundException("Term result card not found for this examination.")

        if not current_user.is_superadmin and role in ("STUDENT", "PARENT") and term_res.approval_status != "PUBLISHED":
            raise AuthorizationException("Results have not been officially published yet.")

        # Fetch subject breakdown
        subject_results = await self.repo.get_student_subject_results(tenant_id, exam_id, student_id)
        subjects_resp = [self._build_subject_result_response(s) for s in subject_results]

        stu_user = term_res.student.user if term_res.student else None
        return StudentTermResultResponse(
            id=term_res.id,
            tenant_id=term_res.tenant_id,
            student_id=term_res.student_id,
            student_name=stu_user.full_name if stu_user else "Student",
            admission_number=term_res.student.admission_number if term_res.student else "N/A",
            roll_number=term_res.student.roll_number if term_res.student else None,
            exam_id=term_res.exam_id,
            exam_title=term_res.exam.title if term_res.exam else "Examination",
            academic_session_name=term_res.academic_session.name if term_res.academic_session else None,
            total_obtained=term_res.total_obtained,
            total_max=term_res.total_max,
            overall_percentage=term_res.overall_percentage,
            overall_grade=term_res.overall_grade,
            cgpa=term_res.cgpa,
            sgpa=term_res.sgpa,
            total_credits=term_res.total_credits,
            earned_credits=term_res.earned_credits,
            rank=term_res.rank,
            is_passed=term_res.is_passed,
            attendance_percentage=term_res.attendance_percentage,
            total_attendance_days=term_res.total_attendance_days,
            present_days=term_res.present_days,
            approval_status=term_res.approval_status,
            approved_at=term_res.approved_at,
            published_at=term_res.published_at,
            subject_results=subjects_resp,
        )

    async def list_exam_results(
        self,
        tenant_id: uuid.UUID,
        exam_id: uuid.UUID,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        approval_status: Optional[str] = None,
    ) -> List[StudentTermResultResponse]:
        results = await self.repo.list_exam_term_results(tenant_id, exam_id, class_id, section_id, approval_status)
        output = []
        for term_res in results:
            stu_user = term_res.student.user if term_res.student else None
            output.append(
                StudentTermResultResponse(
                    id=term_res.id,
                    tenant_id=term_res.tenant_id,
                    student_id=term_res.student_id,
                    student_name=stu_user.full_name if stu_user else "Student",
                    admission_number=term_res.student.admission_number if term_res.student else "N/A",
                    roll_number=term_res.student.roll_number if term_res.student else None,
                    exam_id=term_res.exam_id,
                    exam_title=term_res.exam.title if term_res.exam else "Examination",
                    academic_session_name=term_res.academic_session.name if term_res.academic_session else None,
                    total_obtained=term_res.total_obtained,
                    total_max=term_res.total_max,
                    overall_percentage=term_res.overall_percentage,
                    overall_grade=term_res.overall_grade,
                    cgpa=term_res.cgpa,
                    sgpa=term_res.sgpa,
                    total_credits=term_res.total_credits,
                    earned_credits=term_res.earned_credits,
                    rank=term_res.rank,
                    is_passed=term_res.is_passed,
                    attendance_percentage=term_res.attendance_percentage,
                    total_attendance_days=term_res.total_attendance_days,
                    present_days=term_res.present_days,
                    approval_status=term_res.approval_status,
                    approved_at=term_res.approved_at,
                    published_at=term_res.published_at,
                )
            )
        return output

    async def generate_pdf_report_card(
        self, tenant_id: uuid.UUID, exam_id: uuid.UUID, student_id: uuid.UUID, current_user: User, role: str
    ) -> bytes:
        report_data = await self.get_student_report_card(tenant_id, exam_id, student_id, current_user, role)

        # Get tenant info
        tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
        tenant = (await self.session.execute(tenant_stmt)).scalars().first()
        inst_data = {
            "name": tenant.name if tenant else "EduSaaS Institution",
            "address": tenant.address or "Affiliated Education Campus",
        }

        student_data = {
            "name": report_data.student_name,
            "admission_number": report_data.admission_number,
            "roll_number": report_data.roll_number,
            "class_name": report_data.class_name or "",
            "section_name": report_data.section_name or "",
        }

        exam_data = {
            "title": report_data.exam_title,
            "academic_session": report_data.academic_session_name or "2026-2027",
        }

        subject_list = []
        for s in (report_data.subject_results or []):
            subject_list.append({
                "subject_name": s.subject_name,
                "subject_code": s.subject_code,
                "theory_marks": float(s.theory_marks),
                "theory_max": float(s.theory_max_marks),
                "practical_marks": float(s.practical_marks),
                "practical_max": float(s.practical_max_marks),
                "internal_marks": float(s.internal_marks),
                "internal_max": float(s.internal_max_marks),
                "total_marks": float(s.total_marks),
                "max_marks": float(s.max_marks),
                "percentage": float(s.percentage or 0.0),
                "grade": s.grade,
                "credits": float(s.credits),
            })

        term_summary = {
            "total_obtained": float(report_data.total_obtained),
            "total_max": float(report_data.total_max),
            "overall_percentage": float(report_data.overall_percentage),
            "overall_grade": report_data.overall_grade,
            "cgpa": float(report_data.cgpa) if report_data.cgpa is not None else None,
            "sgpa": float(report_data.sgpa) if report_data.sgpa is not None else None,
            "rank": report_data.rank,
            "is_passed": report_data.is_passed,
            "attendance_percentage": float(report_data.attendance_percentage) if report_data.attendance_percentage is not None else None,
            "total_attendance_days": report_data.total_attendance_days,
            "present_days": report_data.present_days,
            "published_at": report_data.published_at.strftime("%d-%b-%Y") if report_data.published_at else "Not Published",
        }

        return generate_report_card_pdf(
            institution_data=inst_data,
            student_data=student_data,
            exam_data=exam_data,
            subject_results=subject_list,
            term_summary=term_summary,
        )
