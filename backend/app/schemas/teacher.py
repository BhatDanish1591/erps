from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, SecretStr


class TeacherBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    employee_id: Optional[str] = Field(None, max_length=100)
    designation: Optional[str] = Field(None, max_length=100)
    qualification: Optional[str] = Field(None, max_length=255)
    specialization: Optional[str] = Field(None, max_length=150)
    experience_years: int = Field(0, ge=0, le=70)
    department_id: Optional[uuid.UUID] = None
    joining_date: Optional[date] = None
    employment_type: str = Field("FULL_TIME", max_length=50)

    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field("India", max_length=100)

    # Emergency & Statutory
    emergency_contact_name: Optional[str] = Field(None, max_length=150)
    emergency_contact_phone: Optional[str] = Field(None, max_length=50)
    pan_number: Optional[str] = Field(None, max_length=20)
    aadhar_number: Optional[str] = Field(None, max_length=20)

    # Banking
    bank_name: Optional[str] = Field(None, max_length=100)
    bank_account_number: Optional[str] = Field(None, max_length=50)
    bank_ifsc: Optional[str] = Field(None, max_length=20)

    photo_url: Optional[str] = Field(None, max_length=1024)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class TeacherCreateRequest(TeacherBase):
    send_invitation: bool = True
    initial_password: Optional[SecretStr] = Field(None, min_length=8, max_length=72)


class TeacherUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    designation: Optional[str] = None
    qualification: Optional[str] = None
    specialization: Optional[str] = None
    experience_years: Optional[int] = None
    department_id: Optional[uuid.UUID] = None
    joining_date: Optional[date] = None
    employment_type: Optional[str] = None
    status: Optional[str] = None

    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    pan_number: Optional[str] = None
    aadhar_number: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None

    photo_url: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


StaffRole = Literal["PRINCIPAL", "HOD", "TEACHER"]


class StaffAccessUpdate(BaseModel):
    role: StaffRole
    department_id: Optional[uuid.UUID] = None


class TeacherAssignmentSchema(BaseModel):
    id: uuid.UUID
    teacher_id: uuid.UUID
    academic_session_id: Optional[uuid.UUID] = None
    class_id: Optional[uuid.UUID] = None
    class_name: Optional[str] = None
    section_id: Optional[uuid.UUID] = None
    section_name: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    course_id: Optional[uuid.UUID] = None
    course_name: Optional[str] = None
    semester: Optional[int] = None
    subject_id: Optional[uuid.UUID] = None
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    is_class_teacher: bool = False


class TeacherAssignmentCreateRequest(BaseModel):
    academic_session_id: Optional[uuid.UUID] = None
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester: Optional[int] = None
    subject_id: Optional[uuid.UUID] = None
    is_class_teacher: bool = False


class TimetableEntrySchema(BaseModel):
    id: uuid.UUID
    academic_session_id: Optional[uuid.UUID] = None
    teacher_id: uuid.UUID
    teacher_name: Optional[str] = None
    subject_id: Optional[uuid.UUID] = None
    subject_name: Optional[str] = None
    class_id: Optional[uuid.UUID] = None
    class_name: Optional[str] = None
    section_id: Optional[uuid.UUID] = None
    section_name: Optional[str] = None
    course_id: Optional[uuid.UUID] = None
    course_name: Optional[str] = None
    semester: Optional[int] = None
    day_of_week: str
    period_number: int
    start_time: str
    end_time: str
    room_number: Optional[str] = None


class TimetableEntryCreateRequest(BaseModel):
    academic_session_id: Optional[uuid.UUID] = None
    subject_id: Optional[uuid.UUID] = None
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester: Optional[int] = None
    day_of_week: str = Field(..., description="MONDAY, TUESDAY, etc.")
    period_number: int = Field(1, ge=1, le=15)
    start_time: str = Field(..., max_length=10, description="HH:MM e.g. 09:00")
    end_time: str = Field(..., max_length=10, description="HH:MM e.g. 09:45")
    room_number: Optional[str] = Field(None, max_length=50)


class TeacherAttendanceRecordRequest(BaseModel):
    attendance_date: date
    status: str = Field("PRESENT", description="PRESENT, ABSENT, HALF_DAY, LATE, ON_LEAVE")
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    remarks: Optional[str] = None


class TeacherAttendanceResponse(BaseModel):
    id: uuid.UUID
    teacher_id: uuid.UUID
    attendance_date: date
    status: str
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    remarks: Optional[str] = None
    created_at: datetime


class TeacherLeaveApplyRequest(BaseModel):
    leave_type: str = Field("CASUAL", description="CASUAL, SICK, MATERNITY, PATERNITY, EARNED, UNPAID")
    start_date: date
    end_date: date
    days_count: float = Field(1.0, ge=0.5, le=90.0)
    reason: str = Field(..., min_length=3, max_length=1000)


class TeacherLeaveReviewRequest(BaseModel):
    status: Literal["APPROVED", "REJECTED"]
    rejection_reason: Optional[str] = Field(None, max_length=255)


class TeacherLeaveResponse(BaseModel):
    id: uuid.UUID
    teacher_id: uuid.UUID
    teacher_name: str
    leave_type: str
    start_date: date
    end_date: date
    days_count: float
    reason: str
    status: str
    rejection_reason: Optional[str] = None
    applied_at: datetime
    reviewed_at: Optional[datetime] = None


class TeacherDocumentCreateRequest(BaseModel):
    document_type: str = Field(..., max_length=50)
    document_name: str = Field(..., max_length=255)
    file_url: str = Field(..., max_length=1024)
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None


class TeacherDocumentResponse(BaseModel):
    id: uuid.UUID
    teacher_id: uuid.UUID
    document_type: str
    document_name: str
    file_url: str
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    created_at: datetime


class TeacherWorkloadResponse(BaseModel):
    total_classes_assigned: int
    total_subjects_assigned: int
    weekly_periods_count: int
    is_class_teacher_of: Optional[str] = None
    leave_balance_days: Optional[float] = None
    approved_leave_days: Optional[float] = None
    attendance_rate_percentage: Optional[float] = None


class TeacherResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    staff_role: Optional[StaffRole] = None
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    employee_id: str
    designation: Optional[str] = None
    qualification: Optional[str] = None
    specialization: Optional[str] = None
    experience_years: int = 0
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    joining_date: Optional[date] = None
    employment_type: str = "FULL_TIME"
    status: str = "ACTIVE"

    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "India"

    # Emergency & Statutory
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    pan_number: Optional[str] = None
    aadhar_number: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None

    photo_url: Optional[str] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    assignments: List[TeacherAssignmentSchema] = Field(default_factory=list)
    workload: Optional[TeacherWorkloadResponse] = None
    leave_history: List[TeacherLeaveResponse] = Field(default_factory=list)
    attendance_history: List[TeacherAttendanceResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TeacherDashboardSummary(BaseModel):
    teacher: TeacherResponse
    assigned_classes: List[Dict[str, Any]]
    assigned_subjects: List[Dict[str, Any]]
    today_timetable: List[TimetableEntrySchema]
    attendance_tasks: List[Dict[str, Any]]
    upcoming_examinations: List[Dict[str, Any]]
    assignments_to_evaluate: List[Dict[str, Any]]
    notifications: List[Dict[str, Any]]
