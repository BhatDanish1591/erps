from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Institution Registration ──────────────────────────────────────────────────
class InstitutionRegistrationRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    institution_type: str = Field(..., description="SCHOOL or COLLEGE")
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    postal_code: Optional[str] = None
    logo_url: Optional[str] = None
    principal_name: str = Field(..., min_length=2, max_length=150)
    principal_email: EmailStr
    principal_phone: Optional[str] = None
    plan_id: Optional[uuid.UUID] = None


class CheckSubdomainResponse(BaseModel):
    slug: str
    available: bool
    suggestion: Optional[str] = None


# ── Administrator & Staff Invitations ─────────────────────────────────────────
class AcceptInvitationRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    phone: Optional[str] = None


class InvitationVerificationResponse(BaseModel):
    valid: bool
    email: str
    institution_name: str
    institution_slug: str
    role_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class TeacherInviteItem(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    designation: Optional[str] = None
    department_name: Optional[str] = None


class BulkTeacherInviteRequest(BaseModel):
    teachers: List[TeacherInviteItem]


# ── Institution Profile & Settings ────────────────────────────────────────────
class InstitutionProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    logo_url: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None


class CustomDomainCreate(BaseModel):
    domain: str = Field(..., min_length=4, max_length=255)


# ── Onboarding Wizard Steps ───────────────────────────────────────────────────
class AcademicSessionSetupRequest(BaseModel):
    name: str
    code: str
    start_date: date
    end_date: date


class StructureItem(BaseModel):
    name: str
    code: str
    sub_items: List[str] = Field(default_factory=list, description="Sections for schools, Courses for colleges")


class OnboardingStructureSetupRequest(BaseModel):
    items: List[StructureItem]


class SubjectItem(BaseModel):
    name: str
    code: str
    subject_type: str = "THEORY"
    credits: Optional[int] = 3


class OnboardingSubjectsSetupRequest(BaseModel):
    subjects: List[SubjectItem]


class OnboardingNotificationSetupRequest(BaseModel):
    email_notifications: bool = True
    sms_notifications: bool = False
    whatsapp_notifications: bool = False


class OnboardingStatusResponse(BaseModel):
    tenant_id: uuid.UUID
    institution_name: str
    institution_type: str
    is_completed: bool
    current_step: int
    steps_status: Dict[str, bool]


# ── Bulk Import (CSV / Excel) ─────────────────────────────────────────────────
class StudentImportRow(BaseModel):
    admission_number: str
    full_name: str
    email: EmailStr
    class_or_department: str
    section_or_course: Optional[str] = None
    gender: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None


class BulkImportResponse(BaseModel):
    total_rows: int
    imported_count: int
    skipped_count: int
    errors: List[str] = Field(default_factory=list)
