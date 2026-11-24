from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.schemas.common import AppBaseModel


# ── 1. Academic Sessions ──────────────────────────────────────────────────────

class AcademicSessionCreateRequest(AppBaseModel):
    name: str = Field(..., max_length=100, example="2026-2027 Academic Year")
    code: str = Field(..., max_length=50, example="AY-2026-27")
    start_date: date = Field(..., example="2026-06-01")
    end_date: date = Field(..., example="2027-05-31")
    is_current: bool = Field(False)
    description: Optional[str] = Field(None, max_length=255)


class AcademicSessionUpdateRequest(AppBaseModel):
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=50)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    status: Optional[str] = None
    description: Optional[str] = None


class AcademicSessionResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    code: str
    start_date: date
    end_date: date
    is_current: bool
    status: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ── 2. Academic Faculties ─────────────────────────────────────────────────────

class AcademicFacultyCreateRequest(AppBaseModel):
    name: str = Field(..., max_length=150, example="Faculty of Engineering & Technology")
    code: str = Field(..., max_length=50, example="FOET")
    dean_teacher_id: Optional[uuid.UUID] = None
    description: Optional[str] = None


class AcademicFacultyUpdateRequest(AppBaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    dean_teacher_id: Optional[uuid.UUID] = None
    description: Optional[str] = None


class AcademicFacultyResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    code: str
    dean_teacher_id: Optional[uuid.UUID] = None
    dean_name: Optional[str] = None
    description: Optional[str] = None
    department_count: int = 0
    created_at: datetime


# ── 3. Academic Degrees ───────────────────────────────────────────────────────

class AcademicDegreeCreateRequest(AppBaseModel):
    name: str = Field(..., max_length=150, example="Bachelor of Technology")
    code: str = Field(..., max_length=50, example="B.TECH")
    level: str = Field("UNDERGRADUATE", example="UNDERGRADUATE")  # UNDERGRADUATE, POSTGRADUATE, DIPLOMA, DOCTORATE
    description: Optional[str] = None


class AcademicDegreeUpdateRequest(AppBaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    level: Optional[str] = None
    description: Optional[str] = None


class AcademicDegreeResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    code: str
    level: str
    description: Optional[str] = None
    created_at: datetime


# ── 4. Departments ────────────────────────────────────────────────────────────

class DepartmentCreateRequest(AppBaseModel):
    name: str = Field(..., max_length=150, example="Computer Science & Engineering")
    code: str = Field(..., max_length=50, example="CSE")
    faculty_id: Optional[uuid.UUID] = None
    hod_teacher_id: Optional[uuid.UUID] = None


class DepartmentUpdateRequest(AppBaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    faculty_id: Optional[uuid.UUID] = None
    hod_teacher_id: Optional[uuid.UUID] = None


class DepartmentResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    code: str
    faculty_id: Optional[uuid.UUID] = None
    faculty_name: Optional[str] = None
    hod_teacher_id: Optional[uuid.UUID] = None
    hod_name: Optional[str] = None
    courses_count: int = 0
    created_at: datetime


# ── 5. School Classes ─────────────────────────────────────────────────────────

class SchoolClassCreateRequest(AppBaseModel):
    name: str = Field(..., max_length=100, example="Grade 10")
    code: str = Field(..., max_length=50, example="G10")
    order_index: int = Field(0)
    category: str = Field("GENERAL", example="SECONDARY")
    class_teacher_id: Optional[uuid.UUID] = None


class SchoolClassUpdateRequest(AppBaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    order_index: Optional[int] = None
    category: Optional[str] = None
    class_teacher_id: Optional[uuid.UUID] = None


class SchoolClassResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    code: str
    order_index: int
    category: str
    class_teacher_id: Optional[uuid.UUID] = None
    class_teacher_name: Optional[str] = None
    sections_count: int = 0
    created_at: datetime


# ── 6. Sections ───────────────────────────────────────────────────────────────

class SectionCreateRequest(AppBaseModel):
    name: str = Field(..., max_length=50, example="Section A")
    capacity: int = Field(40, ge=1, le=500)
    class_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    room_number: Optional[str] = None
    class_teacher_id: Optional[uuid.UUID] = None


class SectionUpdateRequest(AppBaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = None
    class_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    room_number: Optional[str] = None
    class_teacher_id: Optional[uuid.UUID] = None


class SectionResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    capacity: int
    class_id: Optional[uuid.UUID] = None
    class_name: Optional[str] = None
    course_id: Optional[uuid.UUID] = None
    course_name: Optional[str] = None
    semester_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    room_number: Optional[str] = None
    class_teacher_id: Optional[uuid.UUID] = None
    class_teacher_name: Optional[str] = None
    created_at: datetime


# ── 7. Courses ────────────────────────────────────────────────────────────────

class CourseCreateRequest(AppBaseModel):
    name: str = Field(..., max_length=150, example="B.Tech Computer Science")
    code: str = Field(..., max_length=50, example="BT-CSE")
    department_id: Optional[uuid.UUID] = None
    degree_id: Optional[uuid.UUID] = None
    duration_years: float = Field(4.0, ge=0.5, le=10.0)
    duration_semesters: int = Field(8, ge=1, le=20)
    coordinator_teacher_id: Optional[uuid.UUID] = None


class CourseUpdateRequest(AppBaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    degree_id: Optional[uuid.UUID] = None
    duration_years: Optional[float] = None
    duration_semesters: Optional[int] = None
    coordinator_teacher_id: Optional[uuid.UUID] = None


class CourseResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    code: str
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    degree_id: Optional[uuid.UUID] = None
    degree_name: Optional[str] = None
    duration_years: float
    duration_semesters: int
    coordinator_teacher_id: Optional[uuid.UUID] = None
    coordinator_name: Optional[str] = None
    created_at: datetime


# ── 8. College Semesters ──────────────────────────────────────────────────────

class CollegeSemesterCreateRequest(AppBaseModel):
    course_id: uuid.UUID
    semester_number: int = Field(..., ge=1, le=20)
    name: str = Field(..., max_length=100, example="Semester 1")
    academic_session_id: Optional[uuid.UUID] = None
    credits_required: int = Field(20, ge=1, le=100)
    status: str = Field("ACTIVE")


class CollegeSemesterUpdateRequest(AppBaseModel):
    name: Optional[str] = None
    academic_session_id: Optional[uuid.UUID] = None
    credits_required: Optional[int] = None
    status: Optional[str] = None


class CollegeSemesterResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    course_id: uuid.UUID
    course_name: Optional[str] = None
    semester_number: int
    name: str
    academic_session_id: Optional[uuid.UUID] = None
    credits_required: int
    status: str
    created_at: datetime


# ── 9. College Batches ────────────────────────────────────────────────────────

class CollegeBatchCreateRequest(AppBaseModel):
    course_id: uuid.UUID
    name: str = Field(..., max_length=100, example="Batch 2024-2028")
    start_year: int = Field(..., ge=1990, le=2100)
    end_year: int = Field(..., ge=1990, le=2100)
    current_semester_number: int = Field(1, ge=1, le=20)
    is_active: bool = Field(True)


class CollegeBatchUpdateRequest(AppBaseModel):
    name: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    current_semester_number: Optional[int] = None
    is_active: Optional[bool] = None


class CollegeBatchResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    course_id: uuid.UUID
    course_name: Optional[str] = None
    name: str
    start_year: int
    end_year: int
    current_semester_number: int
    is_active: bool
    created_at: datetime


# ── 10. Subjects ──────────────────────────────────────────────────────────────

class SubjectCreateRequest(AppBaseModel):
    name: str = Field(..., max_length=150, example="Data Structures & Algorithms")
    code: str = Field(..., max_length=50, example="CS201")
    subject_type: str = Field("THEORY")  # THEORY, LAB, PRACTICAL, ELECTIVE, VOCATIONAL
    credits: Optional[int] = Field(3, ge=0, le=20)
    department_id: Optional[uuid.UUID] = None
    hours_per_week: int = Field(4, ge=1, le=40)
    is_elective: bool = Field(False)
    description: Optional[str] = None


class SubjectUpdateRequest(AppBaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    subject_type: Optional[str] = None
    credits: Optional[int] = None
    department_id: Optional[uuid.UUID] = None
    hours_per_week: Optional[int] = None
    is_elective: Optional[bool] = None
    description: Optional[str] = None


class SubjectResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    code: str
    subject_type: str
    credits: Optional[int] = None
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    hours_per_week: int = 4
    is_elective: bool = False
    description: Optional[str] = None
    created_at: datetime


# ── 11. Academic Subject Mappings ─────────────────────────────────────────────

class AcademicSubjectMappingCreateRequest(AppBaseModel):
    academic_session_id: uuid.UUID
    subject_id: uuid.UUID
    class_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    semester_number: Optional[int] = None
    is_elective: bool = False
    credits: int = 3
    weekly_hours: int = 4


class AcademicSubjectMappingResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    academic_session_id: uuid.UUID
    subject_id: uuid.UUID
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    class_id: Optional[uuid.UUID] = None
    class_name: Optional[str] = None
    course_id: Optional[uuid.UUID] = None
    course_name: Optional[str] = None
    semester_id: Optional[uuid.UUID] = None
    semester_number: Optional[int] = None
    is_elective: bool
    credits: int
    weekly_hours: int
    created_at: datetime


# ── 12. Teacher Subject Mappings ──────────────────────────────────────────────

class TeacherSubjectMappingCreateRequest(AppBaseModel):
    teacher_id: uuid.UUID
    subject_id: uuid.UUID
    academic_session_id: Optional[uuid.UUID] = None
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    is_primary: bool = True


class TeacherSubjectMappingResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    teacher_id: uuid.UUID
    teacher_name: Optional[str] = None
    teacher_emp_id: Optional[str] = None
    subject_id: uuid.UUID
    subject_name: Optional[str] = None
    academic_session_id: Optional[uuid.UUID] = None
    class_id: Optional[uuid.UUID] = None
    class_name: Optional[str] = None
    section_id: Optional[uuid.UUID] = None
    section_name: Optional[str] = None
    course_id: Optional[uuid.UUID] = None
    course_name: Optional[str] = None
    semester_id: Optional[uuid.UUID] = None
    is_primary: bool
    created_at: datetime


# ── 13. Common Enrollment Model ───────────────────────────────────────────────

class SchoolEnrollmentDetailInput(AppBaseModel):
    class_id: uuid.UUID
    section_id: uuid.UUID
    stream: Optional[str] = None


class CollegeEnrollmentDetailInput(AppBaseModel):
    faculty_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    course_id: uuid.UUID
    degree_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    year_number: int = 1
    semester_number: int = 1
    specialization: Optional[str] = None


class StudentEnrollmentCreateRequest(AppBaseModel):
    student_id: uuid.UUID
    academic_session_id: uuid.UUID
    enrollment_type: str = Field(..., example="SCHOOL")  # SCHOOL | COLLEGE
    enrollment_number: Optional[str] = None
    enrollment_date: Optional[date] = None
    roll_number: Optional[str] = None
    status: str = Field("ACTIVE")
    school_detail: Optional[SchoolEnrollmentDetailInput] = None
    college_detail: Optional[CollegeEnrollmentDetailInput] = None


class SchoolEnrollmentDetailResponse(AppBaseModel):
    id: uuid.UUID
    class_id: uuid.UUID
    class_name: Optional[str] = None
    section_id: uuid.UUID
    section_name: Optional[str] = None
    stream: Optional[str] = None


class CollegeEnrollmentDetailResponse(AppBaseModel):
    id: uuid.UUID
    faculty_id: Optional[uuid.UUID] = None
    faculty_name: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    course_id: uuid.UUID
    course_name: Optional[str] = None
    degree_id: Optional[uuid.UUID] = None
    degree_name: Optional[str] = None
    batch_id: Optional[uuid.UUID] = None
    batch_name: Optional[str] = None
    semester_id: Optional[uuid.UUID] = None
    semester_number: int
    year_number: int
    specialization: Optional[str] = None


class StudentEnrollmentResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    admission_number: Optional[str] = None
    academic_session_id: uuid.UUID
    session_name: Optional[str] = None
    enrollment_type: str
    enrollment_number: str
    enrollment_date: date
    status: str
    roll_number: Optional[str] = None
    school_detail: Optional[SchoolEnrollmentDetailResponse] = None
    college_detail: Optional[CollegeEnrollmentDetailResponse] = None
    created_at: datetime


# ── 14. Student Promotion ─────────────────────────────────────────────────────

class CohortPromotionRequest(AppBaseModel):
    from_session_id: uuid.UUID
    to_session_id: uuid.UUID
    enrollment_type: str = Field(..., example="SCHOOL")  # SCHOOL | COLLEGE
    student_ids: List[uuid.UUID]
    # Target structure for School:
    target_class_id: Optional[uuid.UUID] = None
    target_section_id: Optional[uuid.UUID] = None
    # Target structure for College:
    target_course_id: Optional[uuid.UUID] = None
    target_semester_id: Optional[uuid.UUID] = None
    target_semester_number: Optional[int] = None
    target_year_number: Optional[int] = None
    action: str = Field("PROMOTED", example="PROMOTED")  # PROMOTED | DETAINED | GRADUATED
    remarks: Optional[str] = None


class StudentPromotionResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    from_session_id: uuid.UUID
    to_session_id: uuid.UUID
    action: str
    promotion_date: date
    remarks: Optional[str] = None
    created_at: datetime


# ── 15. Academic Hierarchy Configuration ──────────────────────────────────────

class AcademicHierarchyUpdateRequest(AppBaseModel):
    institution_type: Optional[str] = None  # SCHOOL, COLLEGE, HYBRID
    academic_system: Optional[str] = None   # ANNUAL, SEMESTER, TRIMESTER
    has_departments: Optional[bool] = None
    has_faculties: Optional[bool] = None
    has_batches: Optional[bool] = None
    has_sections: Optional[bool] = None
    grading_system: Optional[str] = None
    pass_percentage: Optional[float] = None
    allow_cross_department_electives: Optional[bool] = None
    max_electives_per_student: Optional[int] = None
    settings: Optional[Dict[str, Any]] = None


class AcademicHierarchyResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    institution_type: str
    academic_system: str
    has_departments: bool
    has_faculties: bool
    has_batches: bool
    has_sections: bool
    grading_system: str
    pass_percentage: float
    allow_cross_department_electives: bool
    max_electives_per_student: int
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ── 16. Academic History ──────────────────────────────────────────────────────

class StudentAcademicHistoryResponse(AppBaseModel):
    student_id: uuid.UUID
    admission_number: str
    student_name: str
    enrollments: List[StudentEnrollmentResponse]
    promotions: List[StudentPromotionResponse]
