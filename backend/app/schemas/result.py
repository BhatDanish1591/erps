from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# 1. Grading Scale Schemas
# ─────────────────────────────────────────────────────────────────────────────

class GradeRule(BaseModel):
    grade: str
    min_percentage: float
    max_percentage: float
    grade_point: float
    description: Optional[str] = None


class GradingScaleBase(BaseModel):
    name: str = Field(..., max_length=100)
    scale_type: str = Field(
        default="CBSE_9_POINT",
        description="CBSE_9_POINT, CGPA_10_POINT, GPA_4_POINT, PERCENTAGE_PASS_FAIL, CUSTOM",
    )
    grades: List[GradeRule]
    is_default: bool = False


class GradingScaleCreate(GradingScaleBase):
    pass


class GradingScaleUpdate(BaseModel):
    name: Optional[str] = None
    scale_type: Optional[str] = None
    grades: Optional[List[GradeRule]] = None
    is_default: Optional[bool] = None


class GradingScaleResponse(GradingScaleBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Subject Marks Entry Schemas
# ─────────────────────────────────────────────────────────────────────────────

class SubjectMarksEntryItem(BaseModel):
    student_id: uuid.UUID
    theory_marks: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    theory_max_marks: Decimal = Field(default=Decimal("70.00"), ge=Decimal("0.00"))
    practical_marks: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    practical_max_marks: Decimal = Field(default=Decimal("20.00"), ge=Decimal("0.00"))
    internal_marks: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    internal_max_marks: Decimal = Field(default=Decimal("10.00"), ge=Decimal("0.00"))
    assignment_marks: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    assignment_max_marks: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    credits: Decimal = Field(default=Decimal("3.0"), ge=Decimal("0.0"))
    remarks: Optional[str] = None


class BulkSubjectMarksEntryRequest(BaseModel):
    exam_id: uuid.UUID
    academic_session_id: uuid.UUID
    subject_id: uuid.UUID
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    entries: List[SubjectMarksEntryItem]


class StudentSubjectResultResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    admission_number: Optional[str] = None
    roll_number: Optional[str] = None
    exam_id: uuid.UUID
    subject_id: uuid.UUID
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    theory_marks: Decimal
    theory_max_marks: Decimal
    practical_marks: Decimal
    practical_max_marks: Decimal
    internal_marks: Decimal
    internal_max_marks: Decimal
    assignment_marks: Decimal
    assignment_max_marks: Decimal
    total_marks: Decimal
    max_marks: Decimal
    percentage: Optional[Decimal] = None
    grade: Optional[str] = None
    grade_point: Decimal
    credits: Decimal
    credit_points: Decimal
    is_passed: bool
    status: str
    remarks: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Overall Term / Exam Result & Report Card Schemas
# ─────────────────────────────────────────────────────────────────────────────

class StudentTermResultResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    admission_number: str
    roll_number: Optional[str] = None
    exam_id: uuid.UUID
    exam_title: str
    academic_session_name: Optional[str] = None
    class_name: Optional[str] = None
    section_name: Optional[str] = None
    course_name: Optional[str] = None
    semester_name: Optional[str] = None
    total_obtained: Decimal
    total_max: Decimal
    overall_percentage: Decimal
    overall_grade: str
    cgpa: Optional[Decimal] = None
    sgpa: Optional[Decimal] = None
    total_credits: Decimal
    earned_credits: Decimal
    rank: Optional[int] = None
    is_passed: bool
    attendance_percentage: Optional[Decimal] = None
    total_attendance_days: Optional[int] = None
    present_days: Optional[int] = None
    approval_status: str
    approved_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    subject_results: Optional[List[StudentSubjectResultResponse]] = None

    model_config = ConfigDict(from_attributes=True)


class ResultApprovalWorkflowRequest(BaseModel):
    exam_id: uuid.UUID
    action: str = Field(
        ...,
        description="SUBMIT_FOR_REVIEW, APPROVE, PUBLISH, REJECT_TO_DRAFT",
    )
    comments: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# 4. Result Revision & History Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ResultRevisionRequest(BaseModel):
    subject_result_id: uuid.UUID
    theory_marks: Optional[Decimal] = None
    practical_marks: Optional[Decimal] = None
    internal_marks: Optional[Decimal] = None
    assignment_marks: Optional[Decimal] = None
    revision_reason: str = Field(..., min_length=5, description="Mandatory reason for marks modification")


class ResultRevisionHistoryResponse(BaseModel):
    id: uuid.UUID
    subject_result_id: uuid.UUID
    previous_marks: Dict[str, Any]
    new_marks: Dict[str, Any]
    revision_reason: str
    modified_by: uuid.UUID
    modified_by_name: Optional[str] = None
    approved_by: Optional[uuid.UUID] = None
    approved_by_name: Optional[str] = None
    modified_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Re-Evaluation Appeal Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ReEvaluationRequestCreate(BaseModel):
    subject_result_id: uuid.UUID
    reason: str = Field(..., min_length=5, description="Reason for requesting re-evaluation")


class ReEvaluationActionRequest(BaseModel):
    status: str = Field(..., description="UNDER_REVIEW, APPROVED_UPDATED, REJECTED")
    reviewer_remarks: str = Field(..., min_length=3)
    updated_theory_marks: Optional[Decimal] = None
    updated_practical_marks: Optional[Decimal] = None
    updated_internal_marks: Optional[Decimal] = None


class ReEvaluationResponse(BaseModel):
    id: uuid.UUID
    subject_result_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    subject_name: str
    reason: str
    status: str
    reviewer_name: Optional[str] = None
    reviewer_remarks: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Analytics & Performance Schemas
# ─────────────────────────────────────────────────────────────────────────────

class SubjectPerformanceStats(BaseModel):
    subject_id: uuid.UUID
    subject_name: str
    subject_code: str
    average_marks: float
    highest_marks: float
    lowest_marks: float
    pass_percentage: float
    total_appeared: int


class ClassPerformanceAnalytics(BaseModel):
    exam_id: uuid.UUID
    exam_title: str
    total_students: int
    passed_students: int
    failed_students: int
    pass_percentage: float
    class_average_percentage: float
    highest_percentage: float
    lowest_percentage: float
    subject_analytics: List[SubjectPerformanceStats]
    grade_distribution: Dict[str, int]


class ReportCardTemplateCreate(BaseModel):
    name: str = Field(..., max_length=100)
    header_title: str = "ACADEMIC REPORT CARD"
    show_attendance: bool = True
    show_signatures: bool = True
    show_ranks: bool = True
    custom_footer: Optional[str] = None
    is_default: bool = True


class ReportCardTemplateResponse(ReportCardTemplateCreate):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
