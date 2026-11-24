from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# 1. Timetable Settings & Bell Schedules
# ─────────────────────────────────────────────────────────────────────────────

class TimetableSettingBase(BaseModel):
    working_days: List[str] = Field(
        default=["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"],
        description="Active teaching days of the week",
    )
    periods_per_day: int = Field(default=8, ge=1, le=15)
    period_duration_minutes: int = Field(default=45, ge=15, le=180)
    break_duration_minutes: int = Field(default=15, ge=0, le=60)
    lunch_duration_minutes: int = Field(default=45, ge=15, le=120)
    school_start_time: str = Field(default="08:30", description="HH:MM format")


class TimetableSettingCreate(TimetableSettingBase):
    academic_session_id: uuid.UUID


class TimetableSettingResponse(TimetableSettingBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    academic_session_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Period Definitions
# ─────────────────────────────────────────────────────────────────────────────

class TimetablePeriodBase(BaseModel):
    period_number: int = Field(..., ge=1, le=20)
    name: str = Field(..., min_length=1, max_length=100)
    period_type: str = Field(
        default="ACADEMIC",
        description="ACADEMIC, PRACTICAL, ASSEMBLY, BREAK, LUNCH, EXAM",
    )
    start_time: str = Field(..., description="HH:MM format, e.g. 08:30")
    end_time: str = Field(..., description="HH:MM format, e.g. 09:15")
    is_break: bool = False


class TimetablePeriodCreate(TimetablePeriodBase):
    academic_session_id: uuid.UUID


class TimetablePeriodResponse(TimetablePeriodBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    academic_session_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Holiday Calendar
# ─────────────────────────────────────────────────────────────────────────────

class TimetableHolidayBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    holiday_date: date
    holiday_type: str = Field(
        default="NATIONAL",
        description="NATIONAL, FESTIVAL, VACATION, INSTITUTIONAL",
    )
    description: Optional[str] = None
    is_half_day: bool = False


class TimetableHolidayCreate(TimetableHolidayBase):
    academic_session_id: uuid.UUID


class TimetableHolidayResponse(TimetableHolidayBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    academic_session_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Timetable Schedule Containers
# ─────────────────────────────────────────────────────────────────────────────

class TimetableScheduleBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=150)
    institution_type: str = Field(default="SCHOOL", description="SCHOOL or COLLEGE")
    effective_from: date
    effective_to: date
    description: Optional[str] = None


class TimetableScheduleCreate(TimetableScheduleBase):
    academic_session_id: uuid.UUID
    institution_type: Optional[str] = None


class TimetableScheduleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=150)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    status: Optional[str] = None
    description: Optional[str] = None


class TimetableScheduleResponse(TimetableScheduleBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    academic_session_id: uuid.UUID
    academic_session_name: Optional[str] = None
    status: str
    published_at: Optional[datetime] = None
    published_by: Optional[uuid.UUID] = None
    publisher_name: Optional[str] = None
    entries_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Timetable Entries
# ─────────────────────────────────────────────────────────────────────────────

class TimetableEntryBase(BaseModel):
    day_of_week: str = Field(..., description="MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY")
    period_number: int = Field(default=1, ge=1, le=20)
    start_time: str = Field(..., description="HH:MM format, e.g. 09:00")
    end_time: str = Field(..., description="HH:MM format, e.g. 09:45")
    room_number: Optional[str] = Field(None, max_length=50)
    entry_type: str = Field(default="THEORY", description="THEORY, PRACTICAL, TUTORIAL, SEMINAR, EXAM")
    is_practical: bool = False
    capacity: Optional[int] = None
    notes: Optional[str] = None


class TimetableEntryCreate(TimetableEntryBase):
    academic_session_id: Optional[uuid.UUID] = None
    schedule_id: Optional[uuid.UUID] = None
    teacher_id: uuid.UUID
    subject_id: Optional[uuid.UUID] = None
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester: Optional[int] = None
    semester_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    period_id: Optional[uuid.UUID] = None


class TimetableEntryUpdate(BaseModel):
    day_of_week: Optional[str] = None
    period_number: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    room_number: Optional[str] = None
    teacher_id: Optional[uuid.UUID] = None
    subject_id: Optional[uuid.UUID] = None
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester: Optional[int] = None
    batch_id: Optional[uuid.UUID] = None
    entry_type: Optional[str] = None
    is_practical: Optional[bool] = None
    notes: Optional[str] = None


class TimetableEntryResponse(TimetableEntryBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    academic_session_id: Optional[uuid.UUID] = None
    schedule_id: Optional[uuid.UUID] = None
    period_id: Optional[uuid.UUID] = None
    teacher_id: uuid.UUID
    teacher_name: Optional[str] = None
    employee_id: Optional[str] = None
    subject_id: Optional[uuid.UUID] = None
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    class_id: Optional[uuid.UUID] = None
    class_name: Optional[str] = None
    section_id: Optional[uuid.UUID] = None
    section_name: Optional[str] = None
    course_id: Optional[uuid.UUID] = None
    course_name: Optional[str] = None
    semester: Optional[int] = None
    batch_id: Optional[uuid.UUID] = None
    batch_name: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    substitute_teacher_id: Optional[uuid.UUID] = None
    substitute_teacher_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Substitute Teacher Assignment
# ─────────────────────────────────────────────────────────────────────────────

class SubstituteAssignmentCreate(BaseModel):
    timetable_entry_id: uuid.UUID
    assignment_date: date
    substitute_teacher_id: uuid.UUID
    reason: Optional[str] = None


class SubstituteAssignmentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    timetable_entry_id: uuid.UUID
    assignment_date: date
    original_teacher_id: uuid.UUID
    original_teacher_name: Optional[str] = None
    substitute_teacher_id: uuid.UUID
    substitute_teacher_name: Optional[str] = None
    assigned_by: Optional[uuid.UUID] = None
    assigner_name: Optional[str] = None
    reason: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Conflict Detection Engine Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ConflictType(str):
    TEACHER_OVERLAP = "TEACHER_OVERLAP"
    ROOM_OVERLAP = "ROOM_OVERLAP"
    CLASS_OVERLAP = "CLASS_OVERLAP"
    SUBJECT_LIMIT = "SUBJECT_LIMIT"


class ConflictItem(BaseModel):
    conflict_type: str
    severity: str = "ERROR"  # ERROR or WARNING
    message: str
    day_of_week: str
    start_time: str
    end_time: str
    conflicting_entry_id: Optional[uuid.UUID] = None
    entity_name: str  # Teacher Name, Room Number, Class Name


class ConflictCheckResponse(BaseModel):
    has_conflicts: bool
    total_conflicts: int
    conflicts: List[ConflictItem]


# ─────────────────────────────────────────────────────────────────────────────
# 8. Calendar View Aggregate
# ─────────────────────────────────────────────────────────────────────────────

class DayScheduleResponse(BaseModel):
    day_of_week: str
    is_working_day: bool
    holiday: Optional[TimetableHolidayResponse] = None
    entries: List[TimetableEntryResponse]


class WeeklyTimetableResponse(BaseModel):
    schedule_id: Optional[uuid.UUID] = None
    schedule_name: Optional[str] = None
    entity_type: str  # CLASS, TEACHER, ROOM, STUDENT
    entity_name: str
    days: List[DayScheduleResponse]
