from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# 1. Question Bank Schemas
# ─────────────────────────────────────────────────────────────────────────────

class QuestionBankBase(BaseModel):
    subject_id: Optional[uuid.UUID] = None
    category: str = Field(default="General", max_length=100)
    difficulty: str = Field(default="MEDIUM", description="EASY, MEDIUM, HARD")
    question_type: str = Field(
        ...,
        description="MCQ, MULTIPLE_SELECT, TRUE_FALSE, SHORT_ANSWER, LONG_ANSWER, FILL_IN_THE_BLANKS, MATCHING, NUMERICAL, FILE_UPLOAD",
    )
    question_text: str
    options: Optional[Any] = None
    correct_answer: Optional[Any] = None
    explanation: Optional[str] = None
    rubric: Optional[Any] = None
    default_marks: Decimal = Field(default=Decimal("1.00"), ge=Decimal("0.00"))
    default_negative_marks: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    is_active: bool = True


class QuestionBankCreate(QuestionBankBase):
    pass


class QuestionBankUpdate(BaseModel):
    subject_id: Optional[uuid.UUID] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    question_type: Optional[str] = None
    question_text: Optional[str] = None
    options: Optional[Any] = None
    correct_answer: Optional[Any] = None
    explanation: Optional[str] = None
    rubric: Optional[Any] = None
    default_marks: Optional[Decimal] = None
    default_negative_marks: Optional[Decimal] = None
    is_active: Optional[bool] = None


class QuestionBankResponse(QuestionBankBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Examination & Question Linking Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ExaminationBase(BaseModel):
    academic_session_id: uuid.UUID
    title: str = Field(..., max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    exam_type: str = Field(
        ...,
        description="DAILY_TEST, WEEKLY_TEST, MONTHLY_TEST, UNIT_TEST, MID_TERM, FINAL_EXAM, SEMESTER_EXAM, PRACTICAL, MOCK_TEST, ONLINE_MCQ, OFFLINE",
    )
    mode: str = Field(default="ONLINE", description="ONLINE, OFFLINE, HYBRID")
    subject_id: Optional[uuid.UUID] = None
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    total_marks: Decimal = Field(default=Decimal("100.00"), ge=Decimal("0.00"))
    passing_marks: Decimal = Field(default=Decimal("40.00"), ge=Decimal("0.00"))
    duration_minutes: int = Field(default=60, ge=1)
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    shuffle_questions: bool = False
    shuffle_options: bool = False
    allow_late_submission: bool = False
    late_submission_grace_minutes: int = 5
    max_attempts: int = Field(default=1, ge=1)
    instructions: Optional[str] = None
    status: str = Field(default="DRAFT", description="DRAFT, SCHEDULED, ONGOING, COMPLETED, ARCHIVED")
    is_published: bool = False


class ExaminationCreate(ExaminationBase):
    question_ids: Optional[List[uuid.UUID]] = None


class ExaminationUpdate(BaseModel):
    title: Optional[str] = None
    code: Optional[str] = None
    exam_type: Optional[str] = None
    mode: Optional[str] = None
    subject_id: Optional[uuid.UUID] = None
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    total_marks: Optional[Decimal] = None
    passing_marks: Optional[Decimal] = None
    duration_minutes: Optional[int] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    shuffle_questions: Optional[bool] = None
    shuffle_options: Optional[bool] = None
    allow_late_submission: Optional[bool] = None
    late_submission_grace_minutes: Optional[int] = None
    max_attempts: Optional[int] = None
    instructions: Optional[str] = None
    status: Optional[str] = None
    is_published: Optional[bool] = None
    is_results_published: Optional[bool] = None


class ExaminationQuestionAdd(BaseModel):
    question_id: Optional[uuid.UUID] = None
    custom_question_text: Optional[str] = None
    custom_options: Optional[Any] = None
    custom_correct_answer: Optional[Any] = None
    custom_explanation: Optional[str] = None
    question_type: Optional[str] = None
    order_index: int = 0
    marks: Decimal = Decimal("1.00")
    negative_marks: Decimal = Decimal("0.00")
    is_mandatory: bool = True


class ExaminationQuestionResponse(BaseModel):
    id: uuid.UUID
    exam_id: uuid.UUID
    question_id: Optional[uuid.UUID] = None
    question_type: str
    question_text: str
    options: Optional[Any] = None
    correct_answer: Optional[Any] = None
    explanation: Optional[str] = None
    order_index: int
    marks: Decimal
    negative_marks: Decimal
    is_mandatory: bool

    model_config = ConfigDict(from_attributes=True)


class ExaminationDetailResponse(ExaminationBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    is_results_published: bool
    results_published_at: Optional[datetime] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    subject_name: Optional[str] = None
    class_name: Optional[str] = None
    section_name: Optional[str] = None
    course_name: Optional[str] = None
    semester_name: Optional[str] = None
    questions_count: int = 0
    attempts_count: int = 0
    questions: Optional[List[ExaminationQuestionResponse]] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Student Exam Taking Schemas (Security Sanitized: No answers/explanations)
# ─────────────────────────────────────────────────────────────────────────────

class StudentExamQuestionTaking(BaseModel):
    """
    Sanitized question representation presented to students during an exam session.
    Never exposes correct_answer, explanation, or rubric!
    """
    id: uuid.UUID
    order_index: int
    question_type: str
    question_text: str
    options: Optional[Any] = None
    marks: Decimal
    negative_marks: Decimal
    is_mandatory: bool


class StudentActiveAttemptResponse(BaseModel):
    attempt_id: uuid.UUID
    exam_id: uuid.UUID
    exam_title: str
    duration_minutes: int
    started_at: datetime
    expires_at: datetime
    remaining_seconds: int
    status: str
    questions: List[StudentExamQuestionTaking]
    saved_answers: Dict[str, Any]  # question_id -> student_answer


class AutosaveAnswerItem(BaseModel):
    question_id: uuid.UUID
    student_answer: Optional[Any] = None


class AutosaveRequest(BaseModel):
    answers: List[AutosaveAnswerItem]


class AutosaveResponse(BaseModel):
    status: str
    autosaved_count: int
    remaining_seconds: int


class SubmitAttemptRequest(BaseModel):
    submission_hash: Optional[str] = None
    final_answers: Optional[List[AutosaveAnswerItem]] = None


class SubmitAttemptResponse(BaseModel):
    attempt_id: uuid.UUID
    status: str
    submitted_at: datetime
    instant_score: Optional[Decimal] = None
    is_evaluated: bool
    message: str


# ─────────────────────────────────────────────────────────────────────────────
# 4. Manual Evaluation Schemas (Teacher / Admin)
# ─────────────────────────────────────────────────────────────────────────────

class EvaluateAnswerItem(BaseModel):
    answer_id: uuid.UUID
    marks_awarded: Decimal
    teacher_feedback: Optional[str] = None


class EvaluateAttemptRequest(BaseModel):
    evaluations: List[EvaluateAnswerItem]


class StudentExamAnswerEvaluationView(BaseModel):
    id: uuid.UUID
    exam_question_id: uuid.UUID
    question_text: str
    question_type: str
    options: Optional[Any] = None
    correct_answer: Optional[Any] = None
    explanation: Optional[str] = None
    student_answer: Optional[Any] = None
    max_marks: Decimal
    negative_marks: Decimal
    is_correct: Optional[bool] = None
    marks_awarded: Optional[Decimal] = None
    teacher_feedback: Optional[str] = None
    is_evaluated: bool


class AttemptEvaluationDetailResponse(BaseModel):
    attempt_id: uuid.UUID
    exam_id: uuid.UUID
    exam_title: str
    student_id: uuid.UUID
    student_name: str
    admission_number: str
    roll_number: Optional[str] = None
    attempt_number: int
    status: str
    started_at: datetime
    submitted_at: Optional[datetime] = None
    total_score: Optional[Decimal] = None
    percentage: Optional[Decimal] = None
    is_passed: Optional[bool] = None
    answers: List[StudentExamAnswerEvaluationView]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Results & Analytics Schemas
# ─────────────────────────────────────────────────────────────────────────────

class StudentResultQuestionReview(BaseModel):
    question_id: uuid.UUID
    order_index: int
    question_text: str
    question_type: str
    options: Optional[Any] = None
    student_answer: Optional[Any] = None
    correct_answer: Optional[Any] = None
    explanation: Optional[str] = None
    marks_awarded: Optional[Decimal] = None
    max_marks: Decimal
    is_correct: Optional[bool] = None
    teacher_feedback: Optional[str] = None


class StudentExamResultResponse(BaseModel):
    attempt_id: uuid.UUID
    exam_id: uuid.UUID
    exam_title: str
    total_marks: Decimal
    passing_marks: Decimal
    total_score: Optional[Decimal] = None
    percentage: Optional[Decimal] = None
    is_passed: Optional[bool] = None
    rank: Optional[int] = None
    status: str
    is_results_published: bool
    submitted_at: Optional[datetime] = None
    review_questions: Optional[List[StudentResultQuestionReview]] = None


class ExaminationReportAnalytics(BaseModel):
    exam_id: uuid.UUID
    title: str
    total_enrolled: int
    total_attempts: int
    submitted_count: int
    evaluated_count: int
    average_score: float
    highest_score: float
    lowest_score: float
    pass_percentage: float
    grade_distribution: Dict[str, int]
    question_analytics: List[Dict[str, Any]]
