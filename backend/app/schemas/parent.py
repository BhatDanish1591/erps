import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, ConfigDict


# ── Linking & Invitation Requests ──────────────────────────────────────────

class ParentLinkChildRequest(BaseModel):
    admission_number: str = Field(..., max_length=100)
    verification_code: Optional[str] = Field(None, max_length=50)
    relation_type: str = Field("GUARDIAN", max_length=50)  # FATHER | MOTHER | GUARDIAN | OTHER
    emergency_contact: bool = Field(False)
    notes: Optional[str] = Field(None, max_length=500)


class AdminInviteParentRequest(BaseModel):
    parent_email: EmailStr
    parent_name: str = Field(..., max_length=150)
    parent_phone: Optional[str] = Field(None, max_length=50)
    student_id: uuid.UUID
    relation_type: str = Field("GUARDIAN", max_length=50)
    is_primary: bool = Field(True)
    can_view_grades: bool = Field(True)
    can_pay_fees: bool = Field(True)
    emergency_contact: bool = Field(False)


class AdminApproveLinkRequest(BaseModel):
    action: str = Field(..., pattern="^(APPROVE|REJECT)$")
    approval_notes: Optional[str] = Field(None, max_length=500)
    can_view_grades: bool = Field(True)
    can_pay_fees: bool = Field(True)


class AdminGenerateVerificationCodeRequest(BaseModel):
    student_id: uuid.UUID
    valid_days: int = Field(7, ge=1, le=30)


class VerificationCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    student_id: uuid.UUID
    student_name: str
    admission_number: str
    expires_at: datetime
    is_used: bool


class ParentLinkRequestItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    admission_number: str
    parent_user_id: uuid.UUID
    parent_name: str
    parent_email: str
    parent_phone: Optional[str] = None
    relation_type: str
    status: str
    verification_method: Optional[str] = None
    verification_notes: Optional[str] = None
    emergency_contact: bool
    created_at: datetime


# ── Linked Child Summary & Profiles ────────────────────────────────────────

class LinkedChildSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: uuid.UUID
    student_name: str
    admission_number: str
    roll_number: Optional[str] = None
    institution_id: uuid.UUID
    institution_name: str
    institution_slug: str
    class_id: Optional[uuid.UUID] = None
    class_name: Optional[str] = None
    section_id: Optional[uuid.UUID] = None
    section_name: Optional[str] = None
    course_name: Optional[str] = None
    semester_name: Optional[str] = None
    relation_type: str
    is_primary: bool
    verification_status: str
    can_view_grades: bool
    can_pay_fees: bool
    attendance_percentage: float = 0.0
    total_due_fees: float = 0.0
    avatar_url: Optional[str] = None


class ChildDetailedProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: uuid.UUID
    admission_number: str
    roll_number: Optional[str] = None
    admission_date: Optional[date] = None
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    institution_name: str
    academic_session_name: Optional[str] = None
    class_name: Optional[str] = None
    section_name: Optional[str] = None
    course_name: Optional[str] = None
    semester_name: Optional[str] = None
    class_teacher_name: Optional[str] = None
    relation_type: str
    is_primary: bool
    emergency_contact: bool
    status: str


# ── Academic Module Views for Child ────────────────────────────────────────

class ChildAttendanceDayEntry(BaseModel):
    date: date
    status: str  # PRESENT | ABSENT | LATE | LEAVE
    period_number: Optional[int] = None
    subject_name: Optional[str] = None
    remarks: Optional[str] = None


class ChildAttendanceResponse(BaseModel):
    overall_percentage: float
    total_days: int
    present_days: int
    absent_days: int
    late_days: int
    recent_entries: List[ChildAttendanceDayEntry] = []
    low_attendance_alert: bool = False


class ChildTimetableEntryItem(BaseModel):
    period_number: int
    start_time: str
    end_time: str
    subject_name: str
    teacher_name: Optional[str] = None
    room_number: Optional[str] = None
    is_practical: bool = False


class ChildDayTimetable(BaseModel):
    day_of_week: str
    entries: List[ChildTimetableEntryItem] = []


class ChildTimetableResponse(BaseModel):
    class_name: Optional[str] = None
    section_name: Optional[str] = None
    schedule: List[ChildDayTimetable] = []


class ChildExamItem(BaseModel):
    exam_id: uuid.UUID
    title: str
    exam_type: str
    subject_name: str
    exam_date: date
    start_time: str
    duration_minutes: int
    total_marks: float
    passing_marks: float
    is_online: bool


class ChildExaminationsResponse(BaseModel):
    upcoming_exams: List[ChildExamItem] = []
    past_exams: List[ChildExamItem] = []


class ChildSubjectResultItem(BaseModel):
    subject_name: str
    subject_code: str
    theory_marks: Optional[float] = None
    practical_marks: Optional[float] = None
    assignment_marks: Optional[float] = None
    total_marks: float
    max_marks: float
    grade: Optional[str] = None
    is_pass: bool


class ChildTermResultResponse(BaseModel):
    result_id: uuid.UUID
    examination_title: str
    academic_session_name: str
    total_marks_obtained: float
    max_marks_possible: float
    percentage: float
    cgpa: Optional[float] = None
    final_grade: Optional[str] = None
    result_status: str  # PASS | FAIL
    is_published: bool
    subjects: List[ChildSubjectResultItem] = []


class ChildAssignmentItem(BaseModel):
    id: uuid.UUID
    title: str
    subject_name: str
    teacher_name: str
    due_date: datetime
    max_score: float
    is_submitted: bool
    submitted_at: Optional[datetime] = None
    is_late: bool = False
    grade: Optional[str] = None
    score: Optional[float] = None
    teacher_feedback: Optional[str] = None


class ChildStudyMaterialItem(BaseModel):
    id: uuid.UUID
    title: str
    subject_name: str
    material_type: str
    description: Optional[str] = None
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    download_url: Optional[str] = None
    external_url: Optional[str] = None
    created_at: datetime


class ChildTeacherContact(BaseModel):
    teacher_user_id: uuid.UUID
    teacher_name: str
    subject_name: str
    department_name: Optional[str] = None
    email: Optional[str] = None


# ── Parent-Teacher Communication ───────────────────────────────────────────

class SendParentTeacherMessageRequest(BaseModel):
    student_id: uuid.UUID
    teacher_user_id: uuid.UUID
    subject: str = Field(..., max_length=255)
    message: str = Field(..., max_length=5000)
    parent_message_id: Optional[uuid.UUID] = None


SendMessageRequest = SendParentTeacherMessageRequest


class ParentTeacherMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    parent_user_id: uuid.UUID
    parent_name: str
    teacher_user_id: uuid.UUID
    teacher_name: str
    subject: str
    message: str
    sender_role: str
    is_read: bool
    created_at: datetime
    replies: List["ParentTeacherMessageResponse"] = []
