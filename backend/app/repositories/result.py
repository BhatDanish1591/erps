from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import (
    AcademicSession,
    CollegeSemester,
    Course,
    SchoolClass,
    Section,
    StudentProfile,
    Subject,
)
from app.models.attendance import StudentAttendanceEntry, StudentAttendanceSession
from app.models.examination import Examination
from app.models.result import (
    GradingScale,
    ReEvaluationRequest,
    ReportCardTemplate,
    ResultRevisionHistory,
    StudentSubjectResult,
    StudentTermResult,
)
from app.models.tenant import Tenant
from app.models.user import User


class ResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _lock_exam(self, tenant_id: uuid.UUID, exam_id: uuid.UUID) -> Examination:
        exam = await self.session.scalar(
            select(Examination).where(Examination.tenant_id == tenant_id, Examination.id == exam_id,
                                      Examination.is_deleted.is_(False)).with_for_update()
        )
        if not exam:
            raise ValueError("Examination not found in this institution.")
        return exam

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Grading Scales
    # ─────────────────────────────────────────────────────────────────────────

    async def get_or_create_default_grading_scale(self, tenant_id: uuid.UUID) -> GradingScale:
        stmt = (
            select(GradingScale)
            .where(GradingScale.tenant_id == tenant_id, GradingScale.is_default == True)
        )
        res = (await self.session.execute(stmt)).scalars().first()
        if res:
            return res

        # Create default 10-point / CBSE grade scale
        default_grades = [
            {"grade": "A1", "min_percentage": 91.0, "max_percentage": 100.0, "grade_point": 10.0, "description": "Outstanding"},
            {"grade": "A2", "min_percentage": 81.0, "max_percentage": 90.99, "grade_point": 9.0, "description": "Excellent"},
            {"grade": "B1", "min_percentage": 71.0, "max_percentage": 80.99, "grade_point": 8.0, "description": "Very Good"},
            {"grade": "B2", "min_percentage": 61.0, "max_percentage": 70.99, "grade_point": 7.0, "description": "Good"},
            {"grade": "C1", "min_percentage": 51.0, "max_percentage": 60.99, "grade_point": 6.0, "description": "Above Average"},
            {"grade": "C2", "min_percentage": 41.0, "max_percentage": 50.99, "grade_point": 5.0, "description": "Average"},
            {"grade": "D", "min_percentage": 33.0, "max_percentage": 40.99, "grade_point": 4.0, "description": "Pass"},
            {"grade": "E", "min_percentage": 0.0, "max_percentage": 32.99, "grade_point": 0.0, "description": "Needs Improvement"},
        ]
        scale = GradingScale(
            tenant_id=tenant_id,
            name="Default Standard Grading Scale",
            scale_type="CBSE_9_POINT",
            grades=default_grades,
            is_default=True,
        )
        self.session.add(scale)
        await self.session.flush()
        return scale

    def determine_grade_and_point(
        self, percentage: float, scale: GradingScale
    ) -> Tuple[str, Decimal]:
        grades_list = scale.grades if isinstance(scale.grades, list) else []
        for g in grades_list:
            min_p = float(g.get("min_percentage", 0))
            max_p = float(g.get("max_percentage", 100))
            if min_p <= percentage <= max_p:
                return str(g.get("grade", "P")), Decimal(str(g.get("grade_point", 0.0)))
        # Fallback
        if percentage >= 40.0:
            return "Pass", Decimal("5.00")
        return "F", Decimal("0.00")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Subject Marks Entry & Calculation
    # ─────────────────────────────────────────────────────────────────────────

    async def save_subject_marks_bulk(
        self,
        tenant_id: uuid.UUID,
        exam_id: uuid.UUID,
        academic_session_id: uuid.UUID,
        subject_id: uuid.UUID,
        class_id: Optional[uuid.UUID],
        section_id: Optional[uuid.UUID],
        entries: List[Dict[str, Any]],
        user_id: Optional[uuid.UUID],
    ) -> List[StudentSubjectResult]:
        exam = await self._lock_exam(tenant_id, exam_id)
        if exam.academic_session_id != academic_session_id:
            raise ValueError("Marks must use the examination's academic session.")
        if exam.is_results_published:
            raise ValueError("Cannot directly edit published results. Use an audited marks revision.")
        if await self.session.scalar(select(StudentTermResult.id).where(
            StudentTermResult.tenant_id == tenant_id, StudentTermResult.exam_id == exam_id,
            StudentTermResult.approval_status != "DRAFT", StudentTermResult.is_deleted.is_(False),
        ).limit(1)):
            raise ValueError("Marks are locked after submission. Return the draft for editing or use an audited revision.")
        scale = await self.get_or_create_default_grading_scale(tenant_id)
        saved_results: List[StudentSubjectResult] = []

        for item in entries:
            student_id = item["student_id"]
            theory = Decimal(str(item.get("theory_marks", 0.0)))
            theory_max = Decimal(str(item.get("theory_max_marks", 70.0)))
            practical = Decimal(str(item.get("practical_marks", 0.0)))
            practical_max = Decimal(str(item.get("practical_max_marks", 20.0)))
            internal = Decimal(str(item.get("internal_marks", 0.0)))
            internal_max = Decimal(str(item.get("internal_max_marks", 10.0)))
            assignment = Decimal(str(item.get("assignment_marks", 0.0)))
            assignment_max = Decimal(str(item.get("assignment_max_marks", 0.0)))
            credits_val = Decimal(str(item.get("credits", 3.0)))

            if any(mark > maximum for mark, maximum in (
                (theory, theory_max), (practical, practical_max), (internal, internal_max), (assignment, assignment_max),
            )):
                raise ValueError("Component marks must not exceed the corresponding maximum.")
            total_obtained = theory + practical + internal + assignment
            total_max = theory_max + practical_max + internal_max + assignment_max
            if total_max <= Decimal("0.00"):
                raise ValueError("Maximum marks must be greater than zero.")

            pct = round((total_obtained / total_max) * Decimal("100.00"), 2)
            grade_str, gp = self.determine_grade_and_point(float(pct), scale)
            credit_points = gp * credits_val
            is_passed = total_obtained * exam.total_marks >= exam.passing_marks * total_max

            # Check if record already exists
            stmt = select(StudentSubjectResult).where(
                StudentSubjectResult.tenant_id == tenant_id,
                StudentSubjectResult.student_id == student_id,
                StudentSubjectResult.exam_id == exam_id,
                StudentSubjectResult.subject_id == subject_id,
            )
            existing = (await self.session.execute(stmt)).scalars().first()

            if existing:
                # If published, check that revision history is used instead of overwrite!
                if existing.status == "PUBLISHED":
                    raise ValueError(
                        f"Cannot directly edit published result for student {student_id}. Use the Revision History API."
                    )
                existing.theory_marks = theory
                existing.theory_max_marks = theory_max
                existing.practical_marks = practical
                existing.practical_max_marks = practical_max
                existing.internal_marks = internal
                existing.internal_max_marks = internal_max
                existing.assignment_marks = assignment
                existing.assignment_max_marks = assignment_max
                existing.total_marks = total_obtained
                existing.max_marks = total_max
                existing.percentage = pct
                existing.grade = grade_str
                existing.grade_point = gp
                existing.credits = credits_val
                existing.credit_points = credit_points
                existing.is_passed = is_passed
                existing.remarks = item.get("remarks")
                existing.entered_by = user_id
                saved_results.append(existing)
            else:
                new_res = StudentSubjectResult(
                    tenant_id=tenant_id,
                    student_id=student_id,
                    exam_id=exam_id,
                    academic_session_id=academic_session_id,
                    subject_id=subject_id,
                    class_id=class_id,
                    section_id=section_id,
                    course_id=exam.course_id,
                    semester_id=exam.semester_id,
                    theory_marks=theory,
                    theory_max_marks=theory_max,
                    practical_marks=practical,
                    practical_max_marks=practical_max,
                    internal_marks=internal,
                    internal_max_marks=internal_max,
                    assignment_marks=assignment,
                    assignment_max_marks=assignment_max,
                    total_marks=total_obtained,
                    max_marks=total_max,
                    percentage=pct,
                    grade=grade_str,
                    grade_point=gp,
                    credits=credits_val,
                    credit_points=credit_points,
                    is_passed=is_passed,
                    status="DRAFT",
                    remarks=item.get("remarks"),
                    entered_by=user_id,
                )
                self.session.add(new_res)
                saved_results.append(new_res)

        await self.session.flush()

        # Recalculate term summaries for each student
        distinct_student_ids = list(set([r.student_id for r in saved_results]))
        for sid in distinct_student_ids:
            await self.recalculate_term_result(tenant_id, exam_id, sid)

        return saved_results

    async def recalculate_term_result(
        self, tenant_id: uuid.UUID, exam_id: uuid.UUID, student_id: uuid.UUID
    ) -> StudentTermResult:
        scale = await self.get_or_create_default_grading_scale(tenant_id)

        # Get all subject results for this exam & student
        stmt = (
            select(StudentSubjectResult)
            .where(
                StudentSubjectResult.tenant_id == tenant_id,
                StudentSubjectResult.exam_id == exam_id,
                StudentSubjectResult.student_id == student_id,
            )
            .options(
                selectinload(StudentSubjectResult.subject),
                selectinload(StudentSubjectResult.exam),
            )
        )
        subjects = list((await self.session.execute(stmt)).scalars().all())

        total_obtained = sum([s.total_marks for s in subjects], Decimal("0.00"))
        total_max = sum([s.max_marks for s in subjects], Decimal("0.00"))
        total_credits = sum([s.credits for s in subjects], Decimal("0.00"))
        total_credit_points = sum([s.credit_points for s in subjects], Decimal("0.00"))

        overall_pct = (
            round((total_obtained / total_max) * Decimal("100.00"), 2)
            if total_max > Decimal("0.00")
            else Decimal("0.00")
        )
        overall_grade, _ = self.determine_grade_and_point(float(overall_pct), scale)

        cgpa = (
            round(total_credit_points / total_credits, 2)
            if total_credits > Decimal("0.00")
            else None
        )
        is_passed = all([s.is_passed for s in subjects]) if subjects else False

        first_sub = subjects[0] if subjects else None
        academic_session_id = first_sub.academic_session_id if first_sub else exam_id
        # Attendance calculation for the examination's academic session.
        att_stmt = select(
            func.count(StudentAttendanceEntry.id).label("total_days"),
            func.count(StudentAttendanceEntry.id).filter(StudentAttendanceEntry.status == "PRESENT").label("present_days"),
        ).join(StudentAttendanceSession, StudentAttendanceSession.id == StudentAttendanceEntry.session_id).where(
            StudentAttendanceEntry.tenant_id == tenant_id,
            StudentAttendanceEntry.student_id == student_id,
            StudentAttendanceSession.tenant_id == tenant_id,
            StudentAttendanceSession.academic_session_id == academic_session_id,
            StudentAttendanceSession.status == "SUBMITTED",
        )
        att_res = (await self.session.execute(att_stmt)).first()
        total_days = att_res.total_days if att_res else 0
        present_days = att_res.present_days if att_res else 0
        att_pct = (
            round((Decimal(present_days) / Decimal(total_days)) * Decimal("100.00"), 2)
            if total_days > 0
            else None
        )

        # Get context IDs from the first subject record
        class_id = first_sub.class_id if first_sub else None
        section_id = first_sub.section_id if first_sub else None
        course_id = first_sub.course_id if first_sub else None
        semester_id = first_sub.semester_id if first_sub else None

        # Upsert StudentTermResult
        term_stmt = select(StudentTermResult).where(
            StudentTermResult.tenant_id == tenant_id,
            StudentTermResult.exam_id == exam_id,
            StudentTermResult.student_id == student_id,
        )
        term_res = (await self.session.execute(term_stmt)).scalars().first()

        if term_res:
            term_res.total_obtained = total_obtained
            term_res.total_max = total_max
            term_res.overall_percentage = overall_pct
            term_res.overall_grade = overall_grade
            term_res.cgpa = cgpa
            term_res.sgpa = cgpa
            term_res.total_credits = total_credits
            term_res.earned_credits = total_credits if is_passed else Decimal("0.0")
            term_res.is_passed = is_passed
            term_res.attendance_percentage = att_pct
            term_res.total_attendance_days = total_days
            term_res.present_days = present_days
        else:
            term_res = StudentTermResult(
                tenant_id=tenant_id,
                student_id=student_id,
                exam_id=exam_id,
                academic_session_id=academic_session_id,
                class_id=class_id,
                section_id=section_id,
                course_id=course_id,
                semester_id=semester_id,
                total_obtained=total_obtained,
                total_max=total_max,
                overall_percentage=overall_pct,
                overall_grade=overall_grade,
                cgpa=cgpa,
                sgpa=cgpa,
                total_credits=total_credits,
                earned_credits=total_credits if is_passed else Decimal("0.0"),
                is_passed=is_passed,
                attendance_percentage=att_pct,
                total_attendance_days=total_days,
                present_days=present_days,
                approval_status="DRAFT",
            )
            self.session.add(term_res)

        await self.session.flush()
        return term_res

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Result Approval Workflow
    # ─────────────────────────────────────────────────────────────────────────

    async def transition_approval_workflow(
        self,
        tenant_id: uuid.UUID,
        exam_id: uuid.UUID,
        action: str,
        user_id: uuid.UUID,
        comments: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transitions:
        - SUBMIT_FOR_REVIEW: DRAFT -> SUBMITTED
        - APPROVE: SUBMITTED / IN_REVIEW -> APPROVED
        - PUBLISH: APPROVED -> PUBLISHED
        - REJECT_TO_DRAFT: IN_REVIEW / SUBMITTED -> DRAFT
        """
        exam = await self._lock_exam(tenant_id, exam_id)
        if exam.is_results_published:
            raise ValueError("Published results are locked. Use an audited marks revision.")
        transitions = {
            "SUBMIT_FOR_REVIEW": ({"DRAFT"}, "SUBMITTED"),
            "APPROVE": ({"SUBMITTED", "IN_REVIEW"}, "APPROVED"),
            "PUBLISH": ({"APPROVED"}, "PUBLISHED"),
            "REJECT_TO_DRAFT": ({"SUBMITTED", "IN_REVIEW", "APPROVED"}, "DRAFT"),
        }
        if action not in transitions:
            raise ValueError(f"Invalid workflow action: {action}")
        valid_states, target_status = transitions[action]
        statuses = set(await self.session.scalars(select(StudentTermResult.approval_status).where(
            StudentTermResult.tenant_id == tenant_id, StudentTermResult.exam_id == exam_id,
            StudentTermResult.is_deleted.is_(False),
        )))
        if not statuses or not statuses.issubset(valid_states):
            raise ValueError("This action does not match the current results approval stage.")
        now = datetime.now(timezone.utc)

        # Update all subject results
        sub_update = (
            update(StudentSubjectResult)
            .where(StudentSubjectResult.tenant_id == tenant_id, StudentSubjectResult.exam_id == exam_id)
            .values(status=target_status, approved_by=user_id if target_status in ("APPROVED", "PUBLISHED") else None)
        )
        await self.session.execute(sub_update)

        # Update all term results
        term_values: Dict[str, Any] = {"approval_status": target_status}
        if target_status == "APPROVED":
            term_values["approved_by"] = user_id
            term_values["approved_at"] = now
        elif target_status == "PUBLISHED":
            term_values["published_at"] = now
        elif target_status == "DRAFT":
            term_values.update(approved_by=None, approved_at=None)

        term_update = (
            update(StudentTermResult)
            .where(StudentTermResult.tenant_id == tenant_id, StudentTermResult.exam_id == exam_id)
            .values(**term_values)
        )
        await self.session.execute(term_update)

        # Also publish examination results release flag if PUBLISH
        if target_status == "PUBLISHED":
            exam_update = (
                update(Examination)
                .where(Examination.tenant_id == tenant_id, Examination.id == exam_id)
                .values(is_results_published=True, results_published_at=now)
            )
            await self.session.execute(exam_update)

        # Compute ranks for the class
        await self._calculate_class_ranks(tenant_id, exam_id)
        await self.session.flush()

        return {"exam_id": str(exam_id), "status": target_status, "action": action, "timestamp": now.isoformat()}

    async def _calculate_class_ranks(self, tenant_id: uuid.UUID, exam_id: uuid.UUID) -> None:
        stmt = (
            select(StudentTermResult)
            .where(StudentTermResult.tenant_id == tenant_id, StudentTermResult.exam_id == exam_id)
            .order_by(StudentTermResult.total_obtained.desc())
        )
        terms = list((await self.session.execute(stmt)).scalars().all())
        for idx, term in enumerate(terms):
            term.rank = idx + 1
        await self.session.flush()

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Result Correction & Revision History
    # ─────────────────────────────────────────────────────────────────────────

    async def revise_subject_result_marks(
        self,
        tenant_id: uuid.UUID,
        subject_result_id: uuid.UUID,
        revision_reason: str,
        modified_by: uuid.UUID,
        new_theory: Optional[Decimal] = None,
        new_practical: Optional[Decimal] = None,
        new_internal: Optional[Decimal] = None,
        new_assignment: Optional[Decimal] = None,
        approved_by: Optional[uuid.UUID] = None,
    ) -> StudentSubjectResult:
        stmt = (
            select(StudentSubjectResult)
            .where(
                StudentSubjectResult.tenant_id == tenant_id,
                StudentSubjectResult.id == subject_result_id,
            )
            .options(selectinload(StudentSubjectResult.revisions))
        )
        record = (await self.session.execute(stmt)).scalars().first()
        if not record:
            raise ValueError("Student subject result record not found.")

        # Capture old marks snapshot
        prev_marks = {
            "theory_marks": str(record.theory_marks),
            "practical_marks": str(record.practical_marks),
            "internal_marks": str(record.internal_marks),
            "assignment_marks": str(record.assignment_marks),
            "total_marks": str(record.total_marks),
            "percentage": str(record.percentage),
            "grade": record.grade,
        }

        # Apply modifications
        if new_theory is not None:
            record.theory_marks = new_theory
        if new_practical is not None:
            record.practical_marks = new_practical
        if new_internal is not None:
            record.internal_marks = new_internal
        if new_assignment is not None:
            record.assignment_marks = new_assignment

        if any(not 0 <= mark <= maximum for mark, maximum in (
            (record.theory_marks, record.theory_max_marks), (record.practical_marks, record.practical_max_marks),
            (record.internal_marks, record.internal_max_marks), (record.assignment_marks, record.assignment_max_marks),
        )):
            raise ValueError("Revised component marks must be between zero and the corresponding maximum.")
        total_obtained = record.theory_marks + record.practical_marks + record.internal_marks + record.assignment_marks
        total_max = record.theory_max_marks + record.practical_max_marks + record.internal_max_marks + record.assignment_max_marks
        if total_max <= Decimal("0.00"):
            total_max = Decimal("100.00")

        pct = round((total_obtained / total_max) * Decimal("100.00"), 2)
        scale = await self.get_or_create_default_grading_scale(tenant_id)
        grade_str, gp = self.determine_grade_and_point(float(pct), scale)

        record.total_marks = total_obtained
        record.percentage = pct
        record.grade = grade_str
        record.grade_point = gp
        record.credit_points = gp * record.credits
        record.is_passed = total_obtained * record.exam.total_marks >= record.exam.passing_marks * total_max

        new_marks = {
            "theory_marks": str(record.theory_marks),
            "practical_marks": str(record.practical_marks),
            "internal_marks": str(record.internal_marks),
            "assignment_marks": str(record.assignment_marks),
            "total_marks": str(record.total_marks),
            "percentage": str(record.percentage),
            "grade": record.grade,
        }

        # Record immutable revision log
        history_entry = ResultRevisionHistory(
            tenant_id=tenant_id,
            subject_result_id=record.id,
            previous_marks=prev_marks,
            new_marks=new_marks,
            revision_reason=revision_reason,
            modified_by=modified_by,
            approved_by=approved_by or modified_by,
            modified_at=datetime.now(timezone.utc),
        )
        self.session.add(history_entry)
        await self.session.flush()

        # Recalculate student overall term result
        await self.recalculate_term_result(tenant_id, record.exam_id, record.student_id)
        return record

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Re-Evaluation Requests
    # ─────────────────────────────────────────────────────────────────────────

    async def create_reevaluation_request(
        self,
        tenant_id: uuid.UUID,
        subject_result_id: uuid.UUID,
        student_id: uuid.UUID,
        reason: str,
        user_id: uuid.UUID,
    ) -> ReEvaluationRequest:
        req = ReEvaluationRequest(
            tenant_id=tenant_id,
            subject_result_id=subject_result_id,
            student_id=student_id,
            requested_by=user_id,
            reason=reason,
            status="PENDING",
        )
        self.session.add(req)
        await self.session.flush()
        return req

    async def list_reevaluation_requests(
        self, tenant_id: uuid.UUID, status: Optional[str] = None
    ) -> List[ReEvaluationRequest]:
        stmt = select(ReEvaluationRequest).where(ReEvaluationRequest.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(ReEvaluationRequest.status == status)
        stmt = (
            stmt.order_by(ReEvaluationRequest.created_at.desc())
            .options(
                selectinload(ReEvaluationRequest.subject_result).selectinload(StudentSubjectResult.subject),
                selectinload(ReEvaluationRequest.student).selectinload(StudentProfile.user),
                selectinload(ReEvaluationRequest.requester),
                selectinload(ReEvaluationRequest.reviewer),
            )
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def resolve_reevaluation_request(
        self,
        tenant_id: uuid.UUID,
        request_id: uuid.UUID,
        status: str,
        reviewer_remarks: str,
        reviewer_id: uuid.UUID,
        updated_theory: Optional[Decimal] = None,
        updated_practical: Optional[Decimal] = None,
        updated_internal: Optional[Decimal] = None,
    ) -> ReEvaluationRequest:
        stmt = (
            select(ReEvaluationRequest)
            .where(ReEvaluationRequest.tenant_id == tenant_id, ReEvaluationRequest.id == request_id)
            .options(
                selectinload(ReEvaluationRequest.subject_result).selectinload(StudentSubjectResult.subject),
                selectinload(ReEvaluationRequest.student).selectinload(StudentProfile.user),
            )
        )
        req = (await self.session.execute(stmt)).scalars().first()
        if not req:
            raise ValueError("Re-evaluation request not found.")

        req.status = status
        req.reviewer_remarks = reviewer_remarks
        req.reviewer_id = reviewer_id
        req.reviewed_at = datetime.now(timezone.utc)

        if status == "APPROVED_UPDATED":
            # Apply revised marks
            await self.revise_subject_result_marks(
                tenant_id=tenant_id,
                subject_result_id=req.subject_result_id,
                revision_reason=f"Re-evaluation appeal approved: {reviewer_remarks}",
                modified_by=reviewer_id,
                new_theory=updated_theory,
                new_practical=updated_practical,
                new_internal=updated_internal,
                approved_by=reviewer_id,
            )

        await self.session.flush()
        return req

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Analytics & Performance Reports
    # ─────────────────────────────────────────────────────────────────────────

    async def get_class_performance_analytics(
        self, tenant_id: uuid.UUID, exam_id: uuid.UUID
    ) -> Dict[str, Any]:
        exam_stmt = select(Examination).where(Examination.tenant_id == tenant_id, Examination.id == exam_id)
        exam = (await self.session.execute(exam_stmt)).scalars().first()
        if not exam:
            raise ValueError("Examination not found.")

        term_stmt = (
            select(StudentTermResult)
            .where(StudentTermResult.tenant_id == tenant_id, StudentTermResult.exam_id == exam_id)
        )
        term_results = list((await self.session.execute(term_stmt)).scalars().all())

        total_students = len(term_results)
        passed_students = sum(1 for t in term_results if t.is_passed)
        failed_students = total_students - passed_students
        pass_pct = round((passed_students / total_students) * 100, 2) if total_students else 0.0

        pct_list = [float(t.overall_percentage) for t in term_results]
        avg_pct = round(sum(pct_list) / len(pct_list), 2) if pct_list else 0.0
        max_pct = max(pct_list) if pct_list else 0.0
        min_pct = min(pct_list) if pct_list else 0.0

        # Grade distribution
        grades_dist = {"A1": 0, "A2": 0, "B1": 0, "B2": 0, "C1": 0, "C2": 0, "D": 0, "E/F": 0}
        for t in term_results:
            g = t.overall_grade
            if g in grades_dist:
                grades_dist[g] += 1
            else:
                grades_dist["E/F"] += 1

        # Per-subject analytics
        sub_stmt = (
            select(StudentSubjectResult)
            .where(StudentSubjectResult.tenant_id == tenant_id, StudentSubjectResult.exam_id == exam_id)
            .options(selectinload(StudentSubjectResult.subject))
        )
        sub_results = list((await self.session.execute(sub_stmt)).scalars().all())

        subj_map: Dict[uuid.UUID, List[StudentSubjectResult]] = {}
        for s in sub_results:
            subj_map.setdefault(s.subject_id, []).append(s)

        subject_stats: List[Dict[str, Any]] = []
        for s_id, s_list in subj_map.items():
            first = s_list[0]
            s_name = first.subject.name if first.subject else "Subject"
            s_code = first.subject.code if first.subject else ""
            marks = [float(item.total_marks) for item in s_list]
            passed = sum(1 for item in s_list if item.is_passed)
            s_avg = round(sum(marks) / len(marks), 2) if marks else 0.0
            subject_stats.append({
                "subject_id": s_id,
                "subject_name": s_name,
                "subject_code": s_code,
                "average_marks": s_avg,
                "highest_marks": max(marks) if marks else 0.0,
                "lowest_marks": min(marks) if marks else 0.0,
                "pass_percentage": round((passed / len(s_list)) * 100, 2) if s_list else 0.0,
                "total_appeared": len(s_list),
            })

        return {
            "exam_id": str(exam.id),
            "exam_title": exam.title,
            "total_students": total_students,
            "passed_students": passed_students,
            "failed_students": failed_students,
            "pass_percentage": pass_pct,
            "class_average_percentage": avg_pct,
            "highest_percentage": max_pct,
            "lowest_percentage": min_pct,
            "subject_analytics": subject_stats,
            "grade_distribution": grades_dist,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Student Term & Report Card Queries
    # ─────────────────────────────────────────────────────────────────────────

    async def get_student_term_result(
        self, tenant_id: uuid.UUID, exam_id: uuid.UUID, student_id: uuid.UUID
    ) -> Optional[StudentTermResult]:
        stmt = (
            select(StudentTermResult)
            .where(
                StudentTermResult.tenant_id == tenant_id,
                StudentTermResult.exam_id == exam_id,
                StudentTermResult.student_id == student_id,
            )
            .options(
                selectinload(StudentTermResult.student).selectinload(StudentProfile.user),
                selectinload(StudentTermResult.exam),
                selectinload(StudentTermResult.academic_session),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_student_subject_results(
        self, tenant_id: uuid.UUID, exam_id: uuid.UUID, student_id: uuid.UUID
    ) -> List[StudentSubjectResult]:
        stmt = (
            select(StudentSubjectResult)
            .where(
                StudentSubjectResult.tenant_id == tenant_id,
                StudentSubjectResult.exam_id == exam_id,
                StudentSubjectResult.student_id == student_id,
            )
            .options(
                selectinload(StudentSubjectResult.subject),
                selectinload(StudentSubjectResult.student).selectinload(StudentProfile.user),
            )
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_exam_term_results(
        self,
        tenant_id: uuid.UUID,
        exam_id: uuid.UUID,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        approval_status: Optional[str] = None,
    ) -> List[StudentTermResult]:
        stmt = (
            select(StudentTermResult)
            .where(StudentTermResult.tenant_id == tenant_id, StudentTermResult.exam_id == exam_id)
        )
        if class_id:
            stmt = stmt.where(StudentTermResult.class_id == class_id)
        if section_id:
            stmt = stmt.where(StudentTermResult.section_id == section_id)
        if approval_status:
            stmt = stmt.where(StudentTermResult.approval_status == approval_status)

        stmt = (
            stmt.order_by(StudentTermResult.total_obtained.desc())
            .options(
                selectinload(StudentTermResult.student).selectinload(StudentProfile.user),
                selectinload(StudentTermResult.exam),
                selectinload(StudentTermResult.academic_session),
            )
        )
        return list((await self.session.execute(stmt)).scalars().all())
