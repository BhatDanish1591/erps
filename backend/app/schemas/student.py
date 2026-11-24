from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class StudentBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    admission_number: Optional[str] = Field(None, max_length=100)
    roll_number: Optional[str] = Field(None, max_length=50)
    admission_date: Optional[date] = None
    academic_session_id: Optional[uuid.UUID] = None
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester: Optional[int] = Field(None, ge=1, le=16)
    batch_year: Optional[int] = Field(None, ge=1990, le=2100)
    gender: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    blood_group: Optional[str] = Field(None, max_length=10)

    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field("India", max_length=100)

    # Parent & Guardian
    parent_name: Optional[str] = Field(None, max_length=150)
    parent_phone: Optional[str] = Field(None, max_length=50)
    parent_email: Optional[str] = Field(None, max_length=255)
    father_name: Optional[str] = Field(None, max_length=150)
    father_phone: Optional[str] = Field(None, max_length=50)
    father_occupation: Optional[str] = Field(None, max_length=100)
    mother_name: Optional[str] = Field(None, max_length=150)
    mother_phone: Optional[str] = Field(None, max_length=50)
    mother_occupation: Optional[str] = Field(None, max_length=100)
    guardian_name: Optional[str] = Field(None, max_length=150)
    guardian_phone: Optional[str] = Field(None, max_length=50)
    guardian_relation: Optional[str] = Field(None, max_length=50)
    emergency_contact_name: Optional[str] = Field(None, max_length=150)
    emergency_contact_phone: Optional[str] = Field(None, max_length=50)

    # Previous Academic History
    previous_school_name: Optional[str] = Field(None, max_length=255)
    previous_grade: Optional[str] = Field(None, max_length=50)
    transfer_certificate_number: Optional[str] = Field(None, max_length=100)

    photo_url: Optional[str] = Field(None, max_length=1024)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class StudentCreateRequest(StudentBase):
    pass


class StudentUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    roll_number: Optional[str] = None
    academic_session_id: Optional[uuid.UUID] = None
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester: Optional[int] = None
    batch_year: Optional[int] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    blood_group: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_email: Optional[str] = None
    father_name: Optional[str] = None
    father_phone: Optional[str] = None
    father_occupation: Optional[str] = None
    mother_name: Optional[str] = None
    mother_phone: Optional[str] = None
    mother_occupation: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_relation: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    previous_school_name: Optional[str] = None
    previous_grade: Optional[str] = None
    transfer_certificate_number: Optional[str] = None
    photo_url: Optional[str] = None
    status: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class StudentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    admission_number: str
    roll_number: Optional[str] = None
    admission_date: Optional[date] = None
    status: str
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    blood_group: Optional[str] = None

    # Academic Structure Details
    academic_session_id: Optional[uuid.UUID] = None
    academic_session_name: Optional[str] = None
    class_id: Optional[uuid.UUID] = None
    class_name: Optional[str] = None
    section_id: Optional[uuid.UUID] = None
    section_name: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    course_id: Optional[uuid.UUID] = None
    course_name: Optional[str] = None
    semester: Optional[int] = None
    batch_year: Optional[int] = None

    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "India"

    # Parents & Guardians
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_email: Optional[str] = None
    father_name: Optional[str] = None
    father_phone: Optional[str] = None
    father_occupation: Optional[str] = None
    mother_name: Optional[str] = None
    mother_phone: Optional[str] = None
    mother_occupation: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_relation: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    # Previous History
    previous_school_name: Optional[str] = None
    previous_grade: Optional[str] = None
    transfer_certificate_number: Optional[str] = None

    photo_url: Optional[str] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class StudentDocumentCreateRequest(BaseModel):
    document_type: str = Field(..., max_length=50)
    document_name: str = Field(..., max_length=255)
    file_url: str = Field(..., max_length=1024)
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None


class StudentDocumentResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    document_type: str
    document_name: str
    file_url: str
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    created_at: datetime


class StudentPromotionRequest(BaseModel):
    target_academic_session_id: uuid.UUID
    target_class_id: Optional[uuid.UUID] = None
    target_section_id: Optional[uuid.UUID] = None
    target_course_id: Optional[uuid.UUID] = None
    target_semester: Optional[int] = None
    student_ids: List[uuid.UUID] = Field(..., min_length=1)
    action: str = Field("PROMOTE", description="'PROMOTE', 'GRADUATE', 'TRANSFER', 'REPEAT'")
    remarks: Optional[str] = None


class StudentIDCardResponse(BaseModel):
    student_id: uuid.UUID
    full_name: str
    admission_number: str
    roll_number: Optional[str] = None
    photo_url: Optional[str] = None
    institution_name: str
    institution_logo_url: Optional[str] = None
    institution_address: Optional[str] = None
    class_or_course: str
    section_or_semester: str
    academic_session: Optional[str] = None
    blood_group: Optional[str] = None
    emergency_contact: Optional[str] = None
    barcode_data: str
    valid_until: Optional[str] = None


class BulkImportSummaryResponse(BaseModel):
    total_processed: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
