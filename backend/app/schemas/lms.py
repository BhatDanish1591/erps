from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# 1. Study Material Schemas
# ─────────────────────────────────────────────────────────────────────────────

class StudyMaterialBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    chapter: Optional[str] = None
    material_type: str = Field(
        default="PDF",
        description="PDF, WORD, POWERPOINT, IMAGE, VIDEO_LINK, RECORDED_LECTURE, REFERENCE_MATERIAL, PREVIOUS_PAPER, OTHER",
    )
    category: str = Field(
        default="GENERAL",
        description="LECTURE_NOTE, SYLLABUS, PAST_PAPER, READING, REFERENCE, LAB_MANUAL, GENERAL",
    )
    external_url: Optional[str] = None
    tags: Optional[List[str]] = None
    is_published: bool = True


class StudyMaterialCreate(StudyMaterialBase):
    academic_session_id: uuid.UUID
    subject_id: Optional[uuid.UUID] = None
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None


class StudyMaterialUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    chapter: Optional[str] = None
    category: Optional[str] = None
    external_url: Optional[str] = None
    tags: Optional[List[str]] = None
    is_published: Optional[bool] = None


class StudyMaterialVersionResponse(BaseModel):
    id: uuid.UUID
    material_id: uuid.UUID
    version_number: int
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    change_summary: Optional[str] = None
    uploader_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudyMaterialResponse(StudyMaterialBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    academic_session_id: uuid.UUID
    academic_session_name: Optional[str] = None
    subject_id: Optional[uuid.UUID] = None
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    class_id: Optional[uuid.UUID] = None
    class_name: Optional[str] = None
    section_id: Optional[uuid.UUID] = None
    section_name: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None

    file_key: Optional[str] = None
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    download_url: Optional[str] = None
    preview_url: Optional[str] = None

    version: int
    download_count: int
    view_count: int
    uploaded_by: uuid.UUID
    uploader_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    versions: Optional[List[StudyMaterialVersionResponse]] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Assignment Schemas
# ─────────────────────────────────────────────────────────────────────────────

class AssignmentBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str
    due_datetime: datetime
    allow_late_submission: bool = True
    late_penalty_percent: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    total_marks: Decimal = Field(default=Decimal("100.00"), gt=Decimal("0.00"))
    passing_marks: Decimal = Field(default=Decimal("40.00"), ge=Decimal("0.00"))
    status: str = Field(default="PUBLISHED", description="DRAFT, PUBLISHED, CLOSED, ARCHIVED")


class AssignmentCreate(AssignmentBase):
    academic_session_id: uuid.UUID
    subject_id: Optional[uuid.UUID] = None
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None


class AssignmentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    due_datetime: Optional[datetime] = None
    allow_late_submission: Optional[bool] = None
    late_penalty_percent: Optional[Decimal] = None
    total_marks: Optional[Decimal] = None
    passing_marks: Optional[Decimal] = None
    status: Optional[str] = None


class AssignmentResponse(AssignmentBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    academic_session_id: uuid.UUID
    academic_session_name: Optional[str] = None
    subject_id: Optional[uuid.UUID] = None
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    class_id: Optional[uuid.UUID] = None
    class_name: Optional[str] = None
    section_id: Optional[uuid.UUID] = None
    section_name: Optional[str] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None

    instructions_file_key: Optional[str] = None
    instructions_file_name: Optional[str] = None
    instructions_file_size: Optional[int] = None
    instructions_download_url: Optional[str] = None

    created_by: uuid.UUID
    creator_name: Optional[str] = None
    submissions_count: int = 0
    evaluated_count: int = 0
    pending_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Assignment Submission & Evaluation Schemas
# ─────────────────────────────────────────────────────────────────────────────

class AssignmentSubmissionCreate(BaseModel):
    submission_text: Optional[str] = None


class AssignmentEvaluationRequest(BaseModel):
    marks_obtained: Decimal = Field(..., ge=Decimal("0.00"))
    grade: Optional[str] = None
    teacher_feedback: Optional[str] = None
    status: str = Field(default="EVALUATED", description="EVALUATED, RESUBMISSION_REQUESTED")


class AssignmentSubmissionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    assignment_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    admission_number: str
    roll_number: Optional[str] = None

    submission_text: Optional[str] = None
    attachment_file_key: Optional[str] = None
    attachment_file_name: Optional[str] = None
    attachment_file_size: Optional[int] = None
    attachment_download_url: Optional[str] = None

    submitted_at: datetime
    is_late: bool
    marks_obtained: Optional[Decimal] = None
    grade: Optional[str] = None
    teacher_feedback: Optional[str] = None
    evaluated_by: Optional[uuid.UUID] = None
    evaluator_name: Optional[str] = None
    evaluated_at: Optional[datetime] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. LMS Reports & Statistics
# ─────────────────────────────────────────────────────────────────────────────

class AssignmentReportResponse(BaseModel):
    assignment_id: uuid.UUID
    assignment_title: str
    total_assigned: int
    total_submitted: int
    total_evaluated: int
    total_pending: int
    submission_rate_percent: float
    average_score: float
    highest_score: float
    lowest_score: float
    pass_percentage: float
