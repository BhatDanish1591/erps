from __future__ import annotations

import copy
import random
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException, AuthorizationException, BadRequestException, NotFoundException
from app.core.logging import get_logger
from app.models.academic import StudentProfile, TeacherProfile
from app.models.examination import (
    Examination,
    ExaminationQuestion,
    QuestionBank,
    StudentExamAnswer,
    StudentExamAttempt,
)
from app.models.user import User
from app.repositories.examination import ExaminationRepository
from app.repositories.attendance import AttendanceRepository
from app.schemas.examination import (
    AttemptEvaluationDetailResponse,
    AutosaveAnswerItem,
    AutosaveResponse,
    EvaluateAttemptRequest,
    ExaminationCreate,
    ExaminationDetailResponse,
    ExaminationQuestionAdd,
    ExaminationQuestionResponse,
    ExaminationReportAnalytics,
    ExaminationUpdate,
    QuestionBankCreate,
    QuestionBankResponse,
    QuestionBankUpdate,
    StudentActiveAttemptResponse,
    StudentExamAnswerEvaluationView,
    StudentExamQuestionTaking,
    StudentExamResultResponse,
    StudentResultQuestionReview,
    SubmitAttemptResponse,
)

logger = get_logger("examination_service")


class ExaminationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ExaminationRepository(session)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Question Bank Management
    # ─────────────────────────────────────────────────────────────────────────

    async def create_question(
        self, tenant_id: uuid.UUID, data: QuestionBankCreate, current_user: User
    ) -> QuestionBankResponse:
        question = await self.repo.create_question(tenant_id, data, current_user.id)
        await self.session.commit()
        loaded = await self.repo.get_question(tenant_id, question.id)
        return QuestionBankResponse.model_validate(loaded)

    async def get_question(self, tenant_id: uuid.UUID, question_id: uuid.UUID) -> QuestionBankResponse:
        question = await self.repo.get_question(tenant_id, question_id)
        if not question:
            raise NotFoundException(f"Question {question_id} not found.")
        return QuestionBankResponse.model_validate(question)

    async def update_question(
        self, tenant_id: uuid.UUID, question_id: uuid.UUID, data: QuestionBankUpdate
    ) -> QuestionBankResponse:
        question = await self.repo.update_question(tenant_id, question_id, data)
        if not question:
            raise NotFoundException(f"Question {question_id} not found.")
        await self.session.commit()
        loaded = await self.repo.get_question(tenant_id, question_id)
        return QuestionBankResponse.model_validate(loaded)

    async def delete_question(self, tenant_id: uuid.UUID, question_id: uuid.UUID) -> None:
        success = await self.repo.delete_question(tenant_id, question_id)
        if not success:
            raise NotFoundException(f"Question {question_id} not found.")
        await self.session.commit()

    async def list_questions(
        self,
        tenant_id: uuid.UUID,
        subject_id: Optional[uuid.UUID] = None,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        question_type: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[QuestionBankResponse], int]:
        questions, total = await self.repo.list_questions(
            tenant_id=tenant_id,
            subject_id=subject_id,
            category=category,
            difficulty=difficulty,
            question_type=question_type,
            search=search,
            skip=skip,
            limit=limit,
        )
        return [QuestionBankResponse.model_validate(q) for q in questions], total

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Examination Lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    async def create_examination(
        self, tenant_id: uuid.UUID, data: ExaminationCreate, current_user: User
    ) -> ExaminationDetailResponse:
        exam = await self.repo.create_examination(tenant_id, data, current_user.id)
        await self.session.commit()
        # Reload with relationships
        loaded_exam = await self.repo.get_examination(tenant_id, exam.id)
        return self._build_exam_detail(loaded_exam)  # type: ignore

    async def get_examination(self, tenant_id: uuid.UUID, exam_id: uuid.UUID) -> ExaminationDetailResponse:
        exam = await self.repo.get_examination(tenant_id, exam_id)
        if not exam:
            raise NotFoundException(f"Examination {exam_id} not found.")
        return self._build_exam_detail(exam)

    async def update_examination(
        self, tenant_id: uuid.UUID, exam_id: uuid.UUID, data: ExaminationUpdate
    ) -> ExaminationDetailResponse:
        exam = await self.repo.update_examination(tenant_id, exam_id, data)
        if not exam:
            raise NotFoundException(f"Examination {exam_id} not found.")
        await self.session.commit()
        loaded = await self.repo.get_examination(tenant_id, exam_id)
        return self._build_exam_detail(loaded)  # type: ignore

    async def delete_examination(self, tenant_id: uuid.UUID, exam_id: uuid.UUID) -> None:
        success = await self.repo.delete_examination(tenant_id, exam_id)
        if not success:
            raise NotFoundException(f"Examination {exam_id} not found.")
        await self.session.commit()

    async def list_examinations(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        subject_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        semester_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        exam_type: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ExaminationDetailResponse], int]:
        exams, total = await self.repo.list_examinations(
            tenant_id=tenant_id,
            academic_session_id=academic_session_id,
            subject_id=subject_id,
            class_id=class_id,
            section_id=section_id,
            course_id=course_id,
            semester_id=semester_id,
            status=status,
            exam_type=exam_type,
            search=search,
            skip=skip,
            limit=limit,
        )
        return [self._build_exam_detail(e) for e in exams], total

    async def add_question(
        self, tenant_id: uuid.UUID, exam_id: uuid.UUID, data: ExaminationQuestionAdd
    ) -> ExaminationQuestionResponse:
        exam = await self.repo.get_examination(tenant_id, exam_id)
        if not exam:
            raise NotFoundException(f"Examination {exam_id} not found.")
        eq = await self.repo.add_question_to_exam(tenant_id, exam_id, data)
        await self.session.commit()
        # reload
        exam = await self.repo.get_examination(tenant_id, exam_id)
        refetched_q = next((q for q in exam.questions if q.id == eq.id), eq)  # type: ignore
        return ExaminationQuestionResponse(
            id=refetched_q.id,
            exam_id=refetched_q.exam_id,
            question_id=refetched_q.question_id,
            question_type=refetched_q.effective_question_type,
            question_text=refetched_q.effective_question_text,
            options=refetched_q.effective_options,
            correct_answer=refetched_q.effective_correct_answer,
            explanation=refetched_q.effective_explanation,
            order_index=refetched_q.order_index,
            marks=refetched_q.marks,
            negative_marks=refetched_q.negative_marks,
            is_mandatory=refetched_q.is_mandatory,
        )

    async def remove_question(
        self, tenant_id: uuid.UUID, exam_id: uuid.UUID, question_id: uuid.UUID
    ) -> None:
        success = await self.repo.remove_question_from_exam(tenant_id, exam_id, question_id)
        if not success:
            raise NotFoundException("Examination question not found.")
        await self.session.commit()

    def _build_exam_detail(self, exam: Examination) -> ExaminationDetailResponse:
        questions_resp = [
            ExaminationQuestionResponse(
                id=q.id,
                exam_id=q.exam_id,
                question_id=q.question_id,
                question_type=q.effective_question_type,
                question_text=q.effective_question_text,
                options=q.effective_options,
                correct_answer=q.effective_correct_answer,
                explanation=q.effective_explanation,
                order_index=q.order_index,
                marks=q.marks,
                negative_marks=q.negative_marks,
                is_mandatory=q.is_mandatory,
            )
            for q in (exam.questions or [])
        ]
        return ExaminationDetailResponse(
            id=exam.id,
            tenant_id=exam.tenant_id,
            academic_session_id=exam.academic_session_id,
            title=exam.title,
            code=exam.code,
            exam_type=exam.exam_type,
            mode=exam.mode,
            subject_id=exam.subject_id,
            class_id=exam.class_id,
            section_id=exam.section_id,
            course_id=exam.course_id,
            semester_id=exam.semester_id,
            batch_id=exam.batch_id,
            total_marks=exam.total_marks,
            passing_marks=exam.passing_marks,
            duration_minutes=exam.duration_minutes,
            start_datetime=exam.start_datetime,
            end_datetime=exam.end_datetime,
            shuffle_questions=exam.shuffle_questions,
            shuffle_options=exam.shuffle_options,
            allow_late_submission=exam.allow_late_submission,
            late_submission_grace_minutes=exam.late_submission_grace_minutes,
            max_attempts=exam.max_attempts,
            instructions=exam.instructions,
            status=exam.status,
            is_published=exam.is_published,
            is_results_published=exam.is_results_published,
            results_published_at=exam.results_published_at,
            created_by=exam.created_by,
            created_at=exam.created_at,
            updated_at=exam.updated_at,
            subject_name=exam.subject.name if exam.subject else None,
            class_name=exam.school_class.name if exam.school_class else None,
            section_name=exam.section.name if exam.section else None,
            course_name=exam.course.name if exam.course else None,
            semester_name=exam.semester.name if exam.semester else None,
            questions_count=len(exam.questions or []),
            attempts_count=len(exam.attempts or []),
            questions=questions_resp,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Student Online Exam Room (Timer, Autosave, Security Scrubbing)
    # ─────────────────────────────────────────────────────────────────────────

    async def start_or_resume_exam(
        self,
        tenant_id: uuid.UUID,
        exam_id: uuid.UUID,
        student_profile_id: uuid.UUID,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> StudentActiveAttemptResponse:
        await self.session.scalar(select(Examination.id).where(
            Examination.id == exam_id, Examination.tenant_id == tenant_id, Examination.is_deleted.is_(False),
        ).with_for_update())
        exam = await self.repo.get_examination(tenant_id, exam_id)
        if not exam:
            raise NotFoundException("Examination not found.")
        if not exam.is_published:
            raise BadRequestException("This examination is not published yet.")
        if exam.mode not in ("ONLINE", "HYBRID"):
            raise BadRequestException("This examination is scheduled in person.")
        _, roster = await AttendanceRepository(self.session).get_roster_for_marking(
            tenant_id, exam.academic_session_id, datetime.now(timezone.utc).date(),
            class_id=exam.class_id, section_id=exam.section_id, course_id=exam.course_id, semester_id=exam.semester_id,
        )
        if not any(row["student_id"] == student_profile_id for row in roster):
            raise AuthorizationException("You are not enrolled in this examination's cohort.")

        now = datetime.now(timezone.utc)
        if exam.start_datetime and now < exam.start_datetime:
            raise BadRequestException(f"This examination has not started yet. Starts at {exam.start_datetime}.")
        if exam.end_datetime and now > exam.end_datetime:
            raise BadRequestException(f"This examination period has ended at {exam.end_datetime}.")

        try:
            attempt = await self.repo.start_or_resume_attempt(
                tenant_id, exam, student_profile_id, client_ip, user_agent
            )
        except ValueError as e:
            raise BadRequestException(str(e))

        target_attempt_id = attempt.id
        await self.session.commit()
        attempt = await self.repo.get_attempt_by_id(tenant_id, target_attempt_id)
        if not attempt:
            raise NotFoundException("Attempt not found.")
        exam = attempt.exam

        # Compute remaining seconds
        remaining = int((attempt.expires_at - datetime.now(timezone.utc)).total_seconds())
        remaining = max(0, remaining)

        # Build sanitized question list (NO ANSWERS, NO EXPLANATIONS, NO RUBRICS)
        exam_q_map = {str(q.id): q for q in exam.questions}
        ordered_q_ids = attempt.question_order or [str(q.id) for q in exam.questions]

        sanitized_questions: List[StudentExamQuestionTaking] = []
        for q_id_str in ordered_q_ids:
            if q_id_str not in exam_q_map:
                continue
            q = exam_q_map[q_id_str]
            opts = copy.deepcopy(q.effective_options)
            if exam.shuffle_options and isinstance(opts, list):
                random.shuffle(opts)

            sanitized_questions.append(
                StudentExamQuestionTaking(
                    id=q.id,
                    order_index=q.order_index,
                    question_type=q.effective_question_type,
                    question_text=q.effective_question_text,
                    options=opts,
                    marks=q.marks,
                    negative_marks=q.negative_marks,
                    is_mandatory=q.is_mandatory,
                )
            )

        saved_answers = {
            str(a.exam_question_id): a.student_answer for a in attempt.answers if a.student_answer is not None
        }

        return StudentActiveAttemptResponse(
            attempt_id=attempt.id,
            exam_id=exam.id,
            exam_title=exam.title,
            duration_minutes=exam.duration_minutes,
            started_at=attempt.started_at,
            expires_at=attempt.expires_at,
            remaining_seconds=remaining,
            status=attempt.status,
            questions=sanitized_questions,
            saved_answers=saved_answers,
        )

    async def autosave_draft(
        self,
        tenant_id: uuid.UUID,
        attempt_id: uuid.UUID,
        answers: List[AutosaveAnswerItem],
    ) -> AutosaveResponse:
        attempt = await self.repo.get_attempt_by_id(tenant_id, attempt_id)
        if not attempt:
            raise NotFoundException("Attempt not found.")
        if attempt.status != "IN_PROGRESS":
            raise BadRequestException(f"Cannot autosave: attempt status is {attempt.status}.")

        expires_at = attempt.expires_at
        try:
            answers_payload = [a.model_dump() for a in answers]
            count = await self.repo.autosave_answers(tenant_id, attempt, answers_payload)
            await self.session.commit()
        except ValueError as e:
            await self.session.commit()
            raise BadRequestException(str(e))

        remaining = int((expires_at - datetime.now(timezone.utc)).total_seconds())
        remaining = max(0, remaining)

        return AutosaveResponse(
            status="SUCCESS",
            autosaved_count=count,
            remaining_seconds=remaining,
        )

    async def submit_exam(
        self,
        tenant_id: uuid.UUID,
        attempt_id: uuid.UUID,
        final_answers: Optional[List[AutosaveAnswerItem]] = None,
        submission_hash: Optional[str] = None,
    ) -> SubmitAttemptResponse:
        attempt = await self.repo.get_attempt_by_id(tenant_id, attempt_id)
        if not attempt:
            raise NotFoundException("Attempt not found.")

        # Idempotent check
        if attempt.status in ("SUBMITTED", "EVALUATED"):
            return SubmitAttemptResponse(
                attempt_id=attempt.id,
                status=attempt.status,
                submitted_at=attempt.submitted_at or attempt.updated_at,
                instant_score=attempt.total_score,
                is_evaluated=attempt.status == "EVALUATED",
                message="Examination already submitted.",
            )

        payload = [a.model_dump() for a in final_answers] if final_answers else None
        await self.repo.submit_attempt(tenant_id, attempt, payload, submission_hash)
        await self.session.commit()

        submitted_attempt = await self.repo.get_attempt_by_id(tenant_id, attempt_id)
        if not submitted_attempt:
            raise NotFoundException("Attempt not found after submission.")

        is_eval = submitted_attempt.status == "EVALUATED"
        msg = (
            f"Examination submitted and graded successfully! Score: {submitted_attempt.total_score}"
            if is_eval
            else "Examination submitted successfully! Pending manual teacher evaluation."
        )

        return SubmitAttemptResponse(
            attempt_id=submitted_attempt.id,
            status=submitted_attempt.status,
            submitted_at=submitted_attempt.submitted_at or datetime.now(timezone.utc),
            instant_score=submitted_attempt.total_score if is_eval else None,
            is_evaluated=is_eval,
            message=msg,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Teacher Evaluation & Scoring
    # ─────────────────────────────────────────────────────────────────────────

    async def get_attempt_for_evaluation(
        self, tenant_id: uuid.UUID, attempt_id: uuid.UUID
    ) -> AttemptEvaluationDetailResponse:
        attempt = await self.repo.get_attempt_by_id(tenant_id, attempt_id)
        if not attempt:
            raise NotFoundException("Attempt not found.")

        stu_user = attempt.student.user if attempt.student else None
        student_name = stu_user.full_name if stu_user else "Unknown Student"
        admission_num = attempt.student.admission_number if attempt.student else "N/A"

        answers_view: List[StudentExamAnswerEvaluationView] = []
        for ans in attempt.answers:
            q = ans.exam_question
            if not q:
                continue
            answers_view.append(
                StudentExamAnswerEvaluationView(
                    id=ans.id,
                    exam_question_id=ans.exam_question_id,
                    question_text=q.effective_question_text,
                    question_type=q.effective_question_type,
                    options=q.effective_options,
                    correct_answer=q.effective_correct_answer,
                    explanation=q.effective_explanation,
                    student_answer=ans.student_answer,
                    max_marks=q.marks,
                    negative_marks=q.negative_marks,
                    is_correct=ans.is_correct,
                    marks_awarded=ans.marks_awarded,
                    teacher_feedback=ans.teacher_feedback,
                    is_evaluated=ans.is_evaluated,
                )
            )

        return AttemptEvaluationDetailResponse(
            attempt_id=attempt.id,
            exam_id=attempt.exam_id,
            exam_title=attempt.exam.title if attempt.exam else "Examination",
            student_id=attempt.student_id,
            student_name=student_name,
            admission_number=admission_num,
            roll_number=attempt.student.roll_number if attempt.student else None,
            attempt_number=attempt.attempt_number,
            status=attempt.status,
            started_at=attempt.started_at,
            submitted_at=attempt.submitted_at,
            total_score=attempt.total_score,
            percentage=attempt.percentage,
            is_passed=attempt.is_passed,
            answers=answers_view,
        )

    async def evaluate_attempt(
        self,
        tenant_id: uuid.UUID,
        attempt_id: uuid.UUID,
        data: EvaluateAttemptRequest,
        current_user: User,
    ) -> AttemptEvaluationDetailResponse:
        eval_payload = [e.model_dump() for e in data.evaluations]
        await self.repo.evaluate_attempt(tenant_id, attempt_id, eval_payload, current_user.id)
        await self.session.commit()
        return await self.get_attempt_for_evaluation(tenant_id, attempt_id)

    async def list_exam_attempts(
        self,
        tenant_id: uuid.UUID,
        exam_id: uuid.UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        attempts, total = await self.repo.list_exam_attempts(tenant_id, exam_id, status, skip, limit)
        output = []
        for a in attempts:
            stu_user = a.student.user if a.student else None
            output.append({
                "attempt_id": str(a.id),
                "student_id": str(a.student_id),
                "student_name": stu_user.full_name if stu_user else "Unknown Student",
                "admission_number": a.student.admission_number if a.student else "N/A",
                "roll_number": a.student.roll_number if a.student else None,
                "attempt_number": a.attempt_number,
                "status": a.status,
                "started_at": a.started_at.isoformat() if a.started_at else None,
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
                "total_score": float(a.total_score) if a.total_score is not None else None,
                "percentage": float(a.percentage) if a.percentage is not None else None,
                "is_passed": a.is_passed,
            })
        return output, total

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Results & Analytics
    # ─────────────────────────────────────────────────────────────────────────

    async def get_student_exam_result(
        self, tenant_id: uuid.UUID, attempt_id: uuid.UUID, student_profile_id: Optional[uuid.UUID] = None
    ) -> StudentExamResultResponse:
        attempt = await self.repo.get_attempt_by_id(tenant_id, attempt_id)
        if not attempt:
            raise NotFoundException("Attempt not found.")
        if student_profile_id and attempt.student_id != student_profile_id:
            raise AuthorizationException("Access forbidden to this attempt result.")

        exam = attempt.exam
        is_published = exam.is_results_published if exam else False

        reviews = None
        if is_published:
            reviews = []
            for ans in attempt.answers:
                q = ans.exam_question
                if not q:
                    continue
                reviews.append(
                    StudentResultQuestionReview(
                        question_id=q.id,
                        order_index=q.order_index,
                        question_text=q.effective_question_text,
                        question_type=q.effective_question_type,
                        options=q.effective_options,
                        student_answer=ans.student_answer,
                        correct_answer=q.effective_correct_answer,
                        explanation=q.effective_explanation,
                        marks_awarded=ans.marks_awarded,
                        max_marks=q.marks,
                        is_correct=ans.is_correct,
                        teacher_feedback=ans.teacher_feedback,
                    )
                )

        return StudentExamResultResponse(
            attempt_id=attempt.id,
            exam_id=attempt.exam_id,
            exam_title=exam.title if exam else "Exam",
            total_marks=exam.total_marks if exam else Decimal("100.00"),
            passing_marks=exam.passing_marks if exam else Decimal("40.00"),
            total_score=attempt.total_score,
            percentage=attempt.percentage,
            is_passed=attempt.is_passed,
            rank=attempt.rank,
            status=attempt.status,
            is_results_published=is_published,
            submitted_at=attempt.submitted_at,
            review_questions=reviews,
        )

    async def get_exam_analytics(
        self, tenant_id: uuid.UUID, exam_id: uuid.UUID
    ) -> ExaminationReportAnalytics:
        data = await self.repo.get_exam_analytics(tenant_id, exam_id)
        return ExaminationReportAnalytics.model_validate(data)
