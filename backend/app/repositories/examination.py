from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import (
    CollegeSemester,
    Course,
    SchoolClass,
    Section,
    StudentAcademicEnrollment,
    StudentProfile,
    Subject,
)
from app.models.examination import (
    ExamAuditLog,
    Examination,
    ExaminationQuestion,
    QuestionBank,
    StudentExamAnswer,
    StudentExamAttempt,
)
from app.schemas.examination import (
    ExaminationCreate,
    ExaminationQuestionAdd,
    ExaminationUpdate,
    QuestionBankCreate,
    QuestionBankUpdate,
)


class ExaminationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Question Bank
    # ─────────────────────────────────────────────────────────────────────────

    async def create_question(
        self, tenant_id: uuid.UUID, data: QuestionBankCreate, user_id: Optional[uuid.UUID] = None
    ) -> QuestionBank:
        question = QuestionBank(
            tenant_id=tenant_id,
            subject_id=data.subject_id,
            category=data.category,
            difficulty=data.difficulty,
            question_type=data.question_type,
            question_text=data.question_text,
            options=data.options,
            correct_answer=data.correct_answer,
            explanation=data.explanation,
            rubric=data.rubric,
            default_marks=data.default_marks,
            default_negative_marks=data.default_negative_marks,
            is_active=data.is_active,
            created_by=user_id,
        )
        self.session.add(question)
        await self.session.flush()
        return question

    async def get_question(self, tenant_id: uuid.UUID, question_id: uuid.UUID) -> Optional[QuestionBank]:
        stmt = (
            select(QuestionBank)
            .where(QuestionBank.tenant_id == tenant_id, QuestionBank.id == question_id)
            .options(selectinload(QuestionBank.subject))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_question(
        self, tenant_id: uuid.UUID, question_id: uuid.UUID, data: QuestionBankUpdate
    ) -> Optional[QuestionBank]:
        question = await self.get_question(tenant_id, question_id)
        if not question:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(question, key, value)
        await self.session.flush()
        return question

    async def delete_question(self, tenant_id: uuid.UUID, question_id: uuid.UUID) -> bool:
        question = await self.get_question(tenant_id, question_id)
        if not question:
            return False
        await self.session.delete(question)
        await self.session.flush()
        return True

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
    ) -> Tuple[List[QuestionBank], int]:
        stmt = select(QuestionBank).where(QuestionBank.tenant_id == tenant_id)
        if subject_id:
            stmt = stmt.where(QuestionBank.subject_id == subject_id)
        if category:
            stmt = stmt.where(QuestionBank.category.ilike(f"%{category}%"))
        if difficulty:
            stmt = stmt.where(QuestionBank.difficulty == difficulty)
        if question_type:
            stmt = stmt.where(QuestionBank.question_type == question_type)
        if search:
            stmt = stmt.where(QuestionBank.question_text.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(QuestionBank.created_at.desc()).offset(skip).limit(limit)
        stmt = stmt.options(selectinload(QuestionBank.subject))
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Examination Operations
    # ─────────────────────────────────────────────────────────────────────────

    async def create_examination(
        self, tenant_id: uuid.UUID, data: ExaminationCreate, user_id: Optional[uuid.UUID] = None
    ) -> Examination:
        exam = Examination(
            tenant_id=tenant_id,
            academic_session_id=data.academic_session_id,
            title=data.title,
            code=data.code,
            exam_type=data.exam_type,
            mode=data.mode,
            subject_id=data.subject_id,
            class_id=data.class_id,
            section_id=data.section_id,
            course_id=data.course_id,
            semester_id=data.semester_id,
            batch_id=data.batch_id,
            total_marks=data.total_marks,
            passing_marks=data.passing_marks,
            duration_minutes=data.duration_minutes,
            start_datetime=data.start_datetime,
            end_datetime=data.end_datetime,
            shuffle_questions=data.shuffle_questions,
            shuffle_options=data.shuffle_options,
            allow_late_submission=data.allow_late_submission,
            late_submission_grace_minutes=data.late_submission_grace_minutes,
            max_attempts=data.max_attempts,
            instructions=data.instructions,
            status=data.status,
            is_published=data.is_published,
            created_by=user_id,
        )
        self.session.add(exam)
        await self.session.flush()

        # If question_ids provided from question bank, attach them
        if data.question_ids:
            for idx, q_id in enumerate(data.question_ids):
                bank_q = await self.get_question(tenant_id, q_id)
                if bank_q:
                    exam_q = ExaminationQuestion(
                        tenant_id=tenant_id,
                        exam_id=exam.id,
                        question_id=bank_q.id,
                        order_index=idx,
                        marks=bank_q.default_marks,
                        negative_marks=bank_q.default_negative_marks,
                    )
                    self.session.add(exam_q)
            await self.session.flush()

        return exam

    async def get_examination(self, tenant_id: uuid.UUID, exam_id: uuid.UUID) -> Optional[Examination]:
        stmt = (
            select(Examination)
            .where(Examination.tenant_id == tenant_id, Examination.id == exam_id)
            .options(
                selectinload(Examination.questions).selectinload(ExaminationQuestion.bank_question),
                selectinload(Examination.subject),
                selectinload(Examination.school_class),
                selectinload(Examination.section),
                selectinload(Examination.course),
                selectinload(Examination.semester),
                selectinload(Examination.batch),
                selectinload(Examination.attempts),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_examination(
        self, tenant_id: uuid.UUID, exam_id: uuid.UUID, data: ExaminationUpdate
    ) -> Optional[Examination]:
        exam = await self.get_examination(tenant_id, exam_id)
        if not exam:
            return None
        update_data = data.model_dump(exclude_unset=True)
        if update_data.get("is_results_published") and not exam.is_results_published:
            exam.results_published_at = datetime.now(timezone.utc)
        for key, value in update_data.items():
            setattr(exam, key, value)
        await self.session.flush()
        return exam

    async def delete_examination(self, tenant_id: uuid.UUID, exam_id: uuid.UUID) -> bool:
        exam = await self.get_examination(tenant_id, exam_id)
        if not exam:
            return False
        await self.session.delete(exam)
        await self.session.flush()
        return True

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
    ) -> Tuple[List[Examination], int]:
        stmt = select(Examination).where(Examination.tenant_id == tenant_id)
        if academic_session_id:
            stmt = stmt.where(Examination.academic_session_id == academic_session_id)
        if subject_id:
            stmt = stmt.where(Examination.subject_id == subject_id)
        if class_id:
            stmt = stmt.where(Examination.class_id == class_id)
        if section_id:
            stmt = stmt.where(Examination.section_id == section_id)
        if course_id:
            stmt = stmt.where(Examination.course_id == course_id)
        if semester_id:
            stmt = stmt.where(Examination.semester_id == semester_id)
        if status:
            stmt = stmt.where(Examination.status == status)
        if exam_type:
            stmt = stmt.where(Examination.exam_type == exam_type)
        if search:
            stmt = stmt.where(Examination.title.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(Examination.created_at.desc()).offset(skip).limit(limit)
        stmt = stmt.options(
            selectinload(Examination.questions).selectinload(ExaminationQuestion.bank_question),
            selectinload(Examination.subject),
            selectinload(Examination.school_class),
            selectinload(Examination.section),
            selectinload(Examination.course),
            selectinload(Examination.semester),
            selectinload(Examination.attempts),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def add_question_to_exam(
        self, tenant_id: uuid.UUID, exam_id: uuid.UUID, data: ExaminationQuestionAdd
    ) -> ExaminationQuestion:
        # Determine order_index if 0
        if data.order_index == 0:
            count_stmt = select(func.count(ExaminationQuestion.id)).where(
                ExaminationQuestion.tenant_id == tenant_id, ExaminationQuestion.exam_id == exam_id
            )
            data.order_index = (await self.session.execute(count_stmt)).scalar() or 0

        exam_q = ExaminationQuestion(
            tenant_id=tenant_id,
            exam_id=exam_id,
            question_id=data.question_id,
            custom_question_text=data.custom_question_text,
            custom_options=data.custom_options,
            custom_correct_answer=data.custom_correct_answer,
            custom_explanation=data.custom_explanation,
            question_type=data.question_type,
            order_index=data.order_index,
            marks=data.marks,
            negative_marks=data.negative_marks,
            is_mandatory=data.is_mandatory,
        )
        self.session.add(exam_q)
        await self.session.flush()
        return exam_q

    async def remove_question_from_exam(
        self, tenant_id: uuid.UUID, exam_id: uuid.UUID, question_id: uuid.UUID
    ) -> bool:
        stmt = select(ExaminationQuestion).where(
            ExaminationQuestion.tenant_id == tenant_id,
            ExaminationQuestion.exam_id == exam_id,
            ExaminationQuestion.id == question_id,
        )
        result = await self.session.execute(stmt)
        eq = result.scalars().first()
        if not eq:
            return False
        await self.session.delete(eq)
        await self.session.flush()
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Student Exam Taking, Timer, Autosave & Submission
    # ─────────────────────────────────────────────────────────────────────────

    async def get_active_attempt(
        self, tenant_id: uuid.UUID, exam_id: uuid.UUID, student_id: uuid.UUID
    ) -> Optional[StudentExamAttempt]:
        stmt = (
            select(StudentExamAttempt)
            .where(
                StudentExamAttempt.tenant_id == tenant_id,
                StudentExamAttempt.exam_id == exam_id,
                StudentExamAttempt.student_id == student_id,
                StudentExamAttempt.status == "IN_PROGRESS",
            )
            .order_by(StudentExamAttempt.attempt_number.desc())
            .options(
                selectinload(StudentExamAttempt.exam).selectinload(Examination.questions).selectinload(ExaminationQuestion.bank_question),
                selectinload(StudentExamAttempt.student).selectinload(StudentProfile.user),
                selectinload(StudentExamAttempt.answers).selectinload(StudentExamAnswer.exam_question).selectinload(ExaminationQuestion.bank_question),
                selectinload(StudentExamAttempt.audit_logs),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_attempt_by_id(
        self, tenant_id: uuid.UUID, attempt_id: uuid.UUID
    ) -> Optional[StudentExamAttempt]:
        stmt = (
            select(StudentExamAttempt)
            .where(StudentExamAttempt.tenant_id == tenant_id, StudentExamAttempt.id == attempt_id)
            .options(
                selectinload(StudentExamAttempt.exam).selectinload(Examination.questions).selectinload(ExaminationQuestion.bank_question),
                selectinload(StudentExamAttempt.student).selectinload(StudentProfile.user),
                selectinload(StudentExamAttempt.answers).selectinload(StudentExamAnswer.exam_question).selectinload(ExaminationQuestion.bank_question),
                selectinload(StudentExamAttempt.audit_logs),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def start_or_resume_attempt(
        self,
        tenant_id: uuid.UUID,
        exam: Examination,
        student_id: uuid.UUID,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> StudentExamAttempt:
        # Check if active in-progress attempt exists
        active = await self.get_active_attempt(tenant_id, exam.id, student_id)
        now = datetime.now(timezone.utc)
        if active:
            # Check if expired
            if now > active.expires_at + timedelta(minutes=exam.late_submission_grace_minutes):
                active.status = "EXPIRED"
                await self.session.flush()
                # If attempts exhausted, return expired
            else:
                return active

        # Count total previous attempts
        count_stmt = select(func.count(StudentExamAttempt.id)).where(
            StudentExamAttempt.tenant_id == tenant_id,
            StudentExamAttempt.exam_id == exam.id,
            StudentExamAttempt.student_id == student_id,
        )
        attempts_count = (await self.session.execute(count_stmt)).scalar() or 0
        if attempts_count >= exam.max_attempts:
            raise ValueError(f"Maximum number of attempts ({exam.max_attempts}) reached for this examination.")

        attempt_number = attempts_count + 1
        duration_delta = timedelta(minutes=exam.duration_minutes)
        expires_at = now + duration_delta

        # Order / shuffle questions
        q_ids = [str(q.id) for q in exam.questions]
        if exam.shuffle_questions:
            random.shuffle(q_ids)

        new_attempt = StudentExamAttempt(
            tenant_id=tenant_id,
            exam_id=exam.id,
            student_id=student_id,
            attempt_number=attempt_number,
            status="IN_PROGRESS",
            started_at=now,
            expires_at=expires_at,
            ip_address=client_ip,
            user_agent=user_agent,
            question_order=q_ids,
        )
        self.session.add(new_attempt)
        await self.session.flush()

        # Pre-create empty student exam answers for each question
        for q in exam.questions:
            ans = StudentExamAnswer(
                tenant_id=tenant_id,
                attempt_id=new_attempt.id,
                exam_question_id=q.id,
                student_answer=None,
                is_evaluated=False,
            )
            self.session.add(ans)

        # Log audit entry
        audit = ExamAuditLog(
            tenant_id=tenant_id,
            attempt_id=new_attempt.id,
            event_type="STARTED",
            event_payload={"client_ip": client_ip, "started_at": now.isoformat()},
        )
        self.session.add(audit)
        await self.session.flush()

        return await self.get_attempt_by_id(tenant_id, new_attempt.id)  # type: ignore

    async def autosave_answers(
        self,
        tenant_id: uuid.UUID,
        attempt: StudentExamAttempt,
        answers: List[Dict[str, Any]],
    ) -> int:
        now = datetime.now(timezone.utc)
        # Check server timer
        grace = attempt.exam.late_submission_grace_minutes if attempt.exam else 5
        if now > attempt.expires_at + timedelta(minutes=grace):
            attempt.status = "EXPIRED"
            await self.session.flush()
            raise ValueError("Examination time has expired. Attempt marked as EXPIRED.")

        saved_count = 0
        existing_answers_map = {str(a.exam_question_id): a for a in attempt.answers}

        for item in answers:
            q_id_str = str(item["question_id"])
            answer_val = item.get("student_answer")
            if q_id_str in existing_answers_map:
                ans_record = existing_answers_map[q_id_str]
                ans_record.student_answer = answer_val
                ans_record.last_autosaved_at = now
                saved_count += 1
            else:
                # Insert if not present
                new_ans = StudentExamAnswer(
                    tenant_id=tenant_id,
                    attempt_id=attempt.id,
                    exam_question_id=uuid.UUID(q_id_str),
                    student_answer=answer_val,
                    last_autosaved_at=now,
                )
                self.session.add(new_ans)
                saved_count += 1

        # Audit log for autosave
        audit = ExamAuditLog(
            tenant_id=tenant_id,
            attempt_id=attempt.id,
            event_type="AUTOSAVE",
            event_payload={"count": saved_count, "saved_at": now.isoformat()},
        )
        self.session.add(audit)
        await self.session.flush()
        return saved_count

    async def submit_attempt(
        self,
        tenant_id: uuid.UUID,
        attempt: StudentExamAttempt,
        final_answers: Optional[List[Dict[str, Any]]] = None,
        submission_hash: Optional[str] = None,
    ) -> StudentExamAttempt:
        # Idempotency check: if already submitted or evaluated, return directly
        if attempt.status in ("SUBMITTED", "EVALUATED"):
            return attempt

        now = datetime.now(timezone.utc)
        grace = attempt.exam.late_submission_grace_minutes if attempt.exam else 5
        is_late = now > attempt.expires_at + timedelta(minutes=grace)

        # Save any final answers provided with submission
        if final_answers:
            await self.autosave_answers(tenant_id, attempt, final_answers)

        attempt.submitted_at = now
        attempt.submission_hash = submission_hash
        attempt.status = "SUBMITTED"

        # ── Run Automatic Grading for Objective Questions ─────────────────────
        exam_questions_map = {q.id: q for q in attempt.exam.questions}
        has_subjective = False
        running_score = Decimal("0.00")

        for ans in attempt.answers:
            q = exam_questions_map.get(ans.exam_question_id)
            if not q:
                continue

            q_type = q.effective_question_type
            correct_ans = q.effective_correct_answer
            student_ans = ans.student_answer

            if q_type in ("MCQ", "TRUE_FALSE", "MULTIPLE_SELECT", "FILL_IN_THE_BLANKS", "NUMERICAL"):
                is_correct = self._check_objective_answer(q_type, student_ans, correct_ans)
                ans.is_correct = is_correct
                ans.is_evaluated = True
                if is_correct:
                    ans.marks_awarded = q.marks
                    running_score += q.marks
                else:
                    if student_ans is not None:
                        # Negative mark penalty if attempted and incorrect
                        ans.marks_awarded = -abs(q.negative_marks)
                        running_score -= abs(q.negative_marks)
                    else:
                        # Unattempted: 0 marks
                        ans.marks_awarded = Decimal("0.00")
            else:
                # Subjective questions: SHORT_ANSWER, LONG_ANSWER, MATCHING, FILE_UPLOAD
                has_subjective = True
                ans.is_evaluated = False
                ans.marks_awarded = None

        # If exam has only objective questions, evaluate immediately!
        if not has_subjective:
            attempt.status = "EVALUATED"
            attempt.total_score = max(Decimal("0.00"), running_score)
            if attempt.exam.total_marks > Decimal("0.00"):
                attempt.percentage = Decimal(round((attempt.total_score / attempt.exam.total_marks) * 100, 2))
            else:
                attempt.percentage = Decimal("0.00")
            attempt.is_passed = attempt.total_score >= attempt.exam.passing_marks

        # Audit log
        audit = ExamAuditLog(
            tenant_id=tenant_id,
            attempt_id=attempt.id,
            event_type="SUBMITTED" if not is_late else "EXPIRED_AUTO_SUBMIT",
            event_payload={
                "submitted_at": now.isoformat(),
                "instant_score": str(running_score) if not has_subjective else None,
                "is_fully_evaluated": not has_subjective,
            },
        )
        self.session.add(audit)
        await self.session.flush()
        return attempt

    def _check_objective_answer(self, q_type: str, student_ans: Any, correct_ans: Any) -> bool:
        if student_ans is None or correct_ans is None:
            return False

        if q_type in ("MCQ", "TRUE_FALSE"):
            # Compare primitive strings or booleans
            return str(student_ans).strip().lower() == str(correct_ans).strip().lower()

        elif q_type == "MULTIPLE_SELECT":
            # Compare sets/lists of option identifiers
            if not isinstance(student_ans, list) or not isinstance(correct_ans, list):
                return False
            return set(str(x).strip().lower() for x in student_ans) == set(str(x).strip().lower() for x in correct_ans)

        elif q_type == "NUMERICAL":
            try:
                stu_val = float(student_ans)
                if isinstance(correct_ans, dict):
                    expected = float(correct_ans.get("value", 0))
                    tolerance = float(correct_ans.get("tolerance", 0.001))
                    return abs(stu_val - expected) <= tolerance
                corr_val = float(correct_ans)
                return abs(stu_val - corr_val) <= 0.001
            except (ValueError, TypeError):
                return False

        elif q_type == "FILL_IN_THE_BLANKS":
            # String matching, with potential alternatives
            s_clean = str(student_ans).strip().lower()
            if isinstance(correct_ans, dict) and "alternatives" in correct_ans:
                alts = [str(a).strip().lower() for a in correct_ans["alternatives"]]
                return s_clean in alts
            if isinstance(correct_ans, list):
                return s_clean in [str(a).strip().lower() for a in correct_ans]
            return s_clean == str(correct_ans).strip().lower()

        return False

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Teacher Evaluation & Scoring
    # ─────────────────────────────────────────────────────────────────────────

    async def evaluate_attempt(
        self,
        tenant_id: uuid.UUID,
        attempt_id: uuid.UUID,
        evaluations: List[Dict[str, Any]],
        teacher_id: Optional[uuid.UUID] = None,
    ) -> StudentExamAttempt:
        attempt = await self.get_attempt_by_id(tenant_id, attempt_id)
        if not attempt:
            raise ValueError("Student examination attempt not found.")

        now = datetime.now(timezone.utc)
        ans_map = {a.id: a for a in attempt.answers}

        for ev in evaluations:
            a_id = ev["answer_id"]
            if a_id in ans_map:
                record = ans_map[a_id]
                marks = Decimal(str(ev["marks_awarded"]))
                record.marks_awarded = marks
                record.teacher_feedback = ev.get("teacher_feedback")
                record.is_evaluated = True
                record.evaluated_by = teacher_id
                record.evaluated_at = now
                if record.exam_question:
                    record.is_correct = marks >= record.exam_question.marks

        # Calculate final total score
        total = Decimal("0.00")
        all_evaluated = True
        for a in attempt.answers:
            if a.marks_awarded is not None:
                total += a.marks_awarded
            else:
                all_evaluated = False

        attempt.total_score = max(Decimal("0.00"), total)
        if attempt.exam.total_marks > Decimal("0.00"):
            attempt.percentage = Decimal(round((attempt.total_score / attempt.exam.total_marks) * 100, 2))
        else:
            attempt.percentage = Decimal("0.00")

        attempt.is_passed = attempt.total_score >= attempt.exam.passing_marks
        if all_evaluated:
            attempt.status = "EVALUATED"

        audit = ExamAuditLog(
            tenant_id=tenant_id,
            attempt_id=attempt.id,
            event_type="EVALUATED",
            event_payload={"evaluated_by": str(teacher_id) if teacher_id else None, "total_score": str(total)},
        )
        self.session.add(audit)
        await self.session.flush()
        return attempt

    async def list_exam_attempts(
        self,
        tenant_id: uuid.UUID,
        exam_id: uuid.UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[StudentExamAttempt], int]:
        stmt = (
            select(StudentExamAttempt)
            .where(StudentExamAttempt.tenant_id == tenant_id, StudentExamAttempt.exam_id == exam_id)
        )
        if status:
            stmt = stmt.where(StudentExamAttempt.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            stmt.order_by(StudentExamAttempt.total_score.desc().nullslast(), StudentExamAttempt.created_at.asc())
            .offset(skip)
            .limit(limit)
            .options(
                selectinload(StudentExamAttempt.student).selectinload(StudentProfile.user),
                selectinload(StudentExamAttempt.exam),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Examination Analytics & Reports
    # ─────────────────────────────────────────────────────────────────────────

    async def get_exam_analytics(self, tenant_id: uuid.UUID, exam_id: uuid.UUID) -> Dict[str, Any]:
        exam = await self.get_examination(tenant_id, exam_id)
        if not exam:
            raise ValueError("Examination not found.")

        # Get all attempts
        stmt = (
            select(StudentExamAttempt)
            .where(StudentExamAttempt.tenant_id == tenant_id, StudentExamAttempt.exam_id == exam_id)
            .options(
                selectinload(StudentExamAttempt.answers),
            )
        )
        attempts = list((await self.session.execute(stmt)).scalars().all())

        total_attempts = len(attempts)
        submitted_count = sum(1 for a in attempts if a.status in ("SUBMITTED", "EVALUATED"))
        evaluated_attempts = [a for a in attempts if a.status == "EVALUATED" and a.total_score is not None]
        evaluated_count = len(evaluated_attempts)

        scores = [float(a.total_score) for a in evaluated_attempts]  # type: ignore
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        max_score = max(scores) if scores else 0.0
        min_score = min(scores) if scores else 0.0
        passed_count = sum(1 for a in evaluated_attempts if a.is_passed)
        pass_pct = round((passed_count / evaluated_count) * 100, 2) if evaluated_count else 0.0

        # Grade distribution
        grades = {"A+": 0, "A": 0, "B": 0, "C": 0, "F": 0}
        for a in evaluated_attempts:
            pct = float(a.percentage or 0.0)
            if pct >= 90:
                grades["A+"] += 1
            elif pct >= 80:
                grades["A"] += 1
            elif pct >= 60:
                grades["B"] += 1
            elif pct >= 40:
                grades["C"] += 1
            else:
                grades["F"] += 1

        # Question analytics
        q_stats: List[Dict[str, Any]] = []
        for q in exam.questions:
            q_answers = [
                ans for att in attempts for ans in att.answers if ans.exam_question_id == q.id
            ]
            total_answered = len([ans for ans in q_answers if ans.student_answer is not None])
            correct_count = sum(1 for ans in q_answers if ans.is_correct is True)
            success_rate = round((correct_count / total_answered) * 100, 1) if total_answered else 0.0
            q_stats.append({
                "question_id": str(q.id),
                "order_index": q.order_index,
                "question_text": q.effective_question_text[:60] + "...",
                "question_type": q.effective_question_type,
                "max_marks": float(q.marks),
                "total_attempts": total_answered,
                "correct_count": correct_count,
                "success_rate": success_rate,
            })

        return {
            "exam_id": str(exam.id),
            "title": exam.title,
            "total_enrolled": total_attempts,  # base count
            "total_attempts": total_attempts,
            "submitted_count": submitted_count,
            "evaluated_count": evaluated_count,
            "average_score": avg_score,
            "highest_score": max_score,
            "lowest_score": min_score,
            "pass_percentage": pass_pct,
            "grade_distribution": grades,
            "question_analytics": q_stats,
        }
