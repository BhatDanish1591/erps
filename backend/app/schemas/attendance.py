from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Attendance Status & Session Enums (String constants for validation)
# ---------------------------------------------------------------------------

class AttendanceStatusEnum:
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    LEAVE = "LEAVE"
    HALF_DAY = "HALF_DAY"
    EXCUSED = "EXCUSED"


class AttendanceSessionTypeEnum:
    DAILY = "DAILY"
    PERIOD_WISE = "PERIOD_WISE"
    SUBJECT_WISE = "SUBJECT_WISE"


# ---------------------------------------------------------------------------
# Student Attendance Schemas
# ---------------------------------------------------------------------------

class StudentAttendanceEntryItem(BaseModel):
    student_id: uuid.UUID
    status: str = Field(..., description="PRESENT, ABSENT, LATE, LEAVE, HALF_DAY, EXCUSED")
    remarks: Optional[str] = None
    marked_via: Optional[str] = "WEB"  # WEB, MOBILE, QR, RFID, BIOMETRIC, GPS


class StudentAttendanceSessionCreate(BaseModel):
    academic_session_id: uuid.UUID
    session_date: date
    session_type: str = Field(default="DAILY", description="DAILY, PERIOD_WISE, SUBJECT_WISE")
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    subject_id: Optional[uuid.UUID] = None
    period_number: Optional[int] = None
    remarks: Optional[str] = None
    entries: List[StudentAttendanceEntryItem] = Field(default_factory=list)
    notify_absent_parents: bool = False


class StudentAttendanceCorrectionRequest(BaseModel):
    entry_id: uuid.UUID
    new_status: str = Field(..., description="PRESENT, ABSENT, LATE, LEAVE, HALF_DAY, EXCUSED")
    reason: str = Field(..., min_length=3, max_length=500)


class AttendanceCorrectionLogResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    entry_id: uuid.UUID
    previous_status: str
    new_status: str
    reason: str
    corrected_by_user_id: uuid.UUID
    corrected_at: datetime

    class Config:
        from_attributes = True


class StudentAttendanceEntryResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    admission_number: Optional[str] = None
    roll_number: Optional[str] = None
    status: str
    remarks: Optional[str] = None
    marked_via: str
    marked_at: datetime
    is_corrected: bool = False
    corrected_at: Optional[datetime] = None
    correction_reason: Optional[str] = None

    class Config:
        from_attributes = True


class StudentAttendanceSessionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    academic_session_id: uuid.UUID
    session_date: date
    session_type: str
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    subject_id: Optional[uuid.UUID] = None
    period_number: Optional[int] = None
    conducted_by_teacher_id: Optional[uuid.UUID] = None
    teacher_name: Optional[str] = None
    class_name: Optional[str] = None
    section_name: Optional[str] = None
    subject_name: Optional[str] = None
    status: str
    total_students: int
    present_count: int
    absent_count: int
    late_count: int
    leave_count: int
    attendance_rate: float
    remarks: Optional[str] = None
    submitted_at: Optional[datetime] = None
    entries: Optional[List[StudentAttendanceEntryResponse]] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Attendance Roster & Marking Request/Response
# ---------------------------------------------------------------------------

class AttendanceRosterStudentItem(BaseModel):
    student_id: uuid.UUID
    full_name: str
    admission_number: str
    roll_number: Optional[str] = None
    current_status: Optional[str] = None  # Existing status if session already recorded
    remarks: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_email: Optional[str] = None


class AttendanceRosterResponse(BaseModel):
    academic_session_id: uuid.UUID
    session_date: date
    session_type: str
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    subject_id: Optional[uuid.UUID] = None
    period_number: Optional[int] = None
    existing_session_id: Optional[uuid.UUID] = None
    is_submitted: bool = False
    students: List[AttendanceRosterStudentItem]


# ---------------------------------------------------------------------------
# Analytics & Reports
# ---------------------------------------------------------------------------

class StudentAttendanceSummaryResponse(BaseModel):
    student_id: uuid.UUID
    full_name: str
    admission_number: str
    total_conducted: int
    total_attended: int  # Present + Late
    present_count: int
    absent_count: int
    late_count: int
    leave_count: int
    attendance_percentage: float
    is_low_attendance: bool  # < 75%


class LowAttendanceAlertItem(BaseModel):
    student_id: uuid.UUID
    full_name: str
    admission_number: str
    class_name: Optional[str] = None
    section_name: Optional[str] = None
    total_sessions: int
    attended_sessions: int
    attendance_percentage: float
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None


class MonthlyAttendanceDayRecord(BaseModel):
    date: date
    status: str
    period_number: Optional[int] = None
    subject_name: Optional[str] = None


class StudentMonthlyAttendanceReport(BaseModel):
    student_id: uuid.UUID
    full_name: str
    admission_number: str
    year: int
    month: int
    total_days: int
    conducted_days: int
    present_days: int
    absent_days: int
    late_days: int
    leave_days: int
    percentage: float
    records: List[MonthlyAttendanceDayRecord]


class AdminAttendanceOverviewResponse(BaseModel):
    today: date
    total_students_enrolled: int
    total_marked_today: int
    overall_attendance_rate_today: float
    total_present_today: int
    total_absent_today: int
    total_late_today: int
    total_leave_today: int
    low_attendance_students_count: int
    sessions_conducted_today: int


# ---------------------------------------------------------------------------
# Teacher Attendance Schemas
# ---------------------------------------------------------------------------

class TeacherCheckInRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    check_in_method: str = "WEB"  # WEB, MOBILE, QR, RFID, BIOMETRIC, GPS
    ip_address: Optional[str] = None
    notes: Optional[str] = None


class TeacherCheckOutRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None


class TeacherAttendanceResponse(BaseModel):
    id: uuid.UUID
    teacher_id: uuid.UUID
    teacher_name: Optional[str] = None
    employee_id: Optional[str] = None
    attendance_date: date
    status: str
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    working_hours: Optional[float] = None
    check_in_method: Optional[str] = "WEB"
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class TeacherLeaveApplyRequest(BaseModel):
    leave_type: str = Field(..., description="CASUAL, SICK, MATERNITY, EARNED, UNPAID")
    start_date: date
    end_date: date
    reason: str = Field(..., min_length=5, max_length=500)


class TeacherLeaveActionRequest(BaseModel):
    action: str = Field(..., description="APPROVE or REJECT")
    rejection_reason: Optional[str] = None


class TeacherLeaveResponse(BaseModel):
    id: uuid.UUID
    teacher_id: uuid.UUID
    teacher_name: Optional[str] = None
    employee_id: Optional[str] = None
    leave_type: str
    start_date: date
    end_date: date
    total_days: int
    reason: str
    status: str
    rejection_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Advanced Hardware & QR Schemas
# ---------------------------------------------------------------------------

class QRCodeGenerateRequest(BaseModel):
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    subject_id: Optional[uuid.UUID] = None
    period_number: Optional[int] = None
    validity_minutes: int = Field(default=15, ge=1, le=60)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    allowed_radius_meters: Optional[int] = 100


class QRCodeAttendanceResponse(BaseModel):
    qr_token: str
    session_id: uuid.UUID
    expires_at: datetime
    geo_fence_enabled: bool
    allowed_radius_meters: Optional[int] = None


class QRCodeScanSubmitRequest(BaseModel):
    qr_token: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class RFIDSwipeRequest(BaseModel):
    device_id: str
    rfid_tag: str
    timestamp: Optional[datetime] = None
    event_type: str = "SWIPE"  # SWIPE, CHECK_IN, CHECK_OUT


class BiometricSyncItem(BaseModel):
    device_id: str
    user_identifier: str  # admission_number or employee_id or rfid_tag
    timestamp: datetime
    event_type: str  # CHECK_IN or CHECK_OUT
    confidence_score: Optional[float] = None


class BiometricSyncBatchRequest(BaseModel):
    device_id: str
    sync_batch_id: Optional[str] = None
    records: List[BiometricSyncItem]


class DeviceSyncResultResponse(BaseModel):
    processed_count: int
    success_count: int
    failure_count: int
    failures: List[Dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# College Cohort Attendance Directory Schemas
# ---------------------------------------------------------------------------

class CollegeStudentAttendanceItem(BaseModel):
    student_id: uuid.UUID
    admission_number: str
    roll_number: Optional[str] = None
    full_name: str
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    course_id: uuid.UUID
    course_name: str
    course_code: str
    semester_id: Optional[uuid.UUID] = None
    semester_name: str
    semester_number: int
    total_classes: int
    attended_classes: int
    present_count: int
    late_count: int
    absent_count: int
    leave_count: int
    attendance_percentage: float
    status: str  # EXCELLENT, AVERAGE, CRITICAL

    class Config:
        from_attributes = True


class CollegeCohortAttendanceResponse(BaseModel):
    department_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    total_students: int
    average_attendance: float
    critical_attendance_count: int
    excellent_attendance_count: int
    students: List[CollegeStudentAttendanceItem]

