from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TenantBaseModel
from app.models.enums import SessionStatus

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class AcademicSession(TenantBaseModel):
    """
    Academic year / cycle / semester session scoped to a specific institution tenant.
    e.g. '2026-2027 Academic Year' or 'Fall 2026 Semester'.
    """
    __tablename__ = "academic_sessions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status_enum", create_type=False),
        nullable=False,
        default=SessionStatus.ACTIVE,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="academic_sessions")

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_academic_sessions_tenant_code"),
        Index("ix_academic_sessions_tenant_current", "tenant_id", "is_current"),
        Index("ix_academic_sessions_tenant_dates", "tenant_id", "start_date", "end_date"),
    )


class AcademicFaculty(TenantBaseModel):
    """
    College faculty division / school (e.g. Faculty of Engineering, Faculty of Medicine).
    """
    __tablename__ = "academic_faculties"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    dean_teacher_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    dean_teacher: Mapped[Optional["TeacherProfile"]] = relationship("TeacherProfile", foreign_keys=[dean_teacher_id])
    departments: Mapped[List["Department"]] = relationship("Department", back_populates="faculty")

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_academic_faculties_tenant_code"),
    )


class AcademicDegree(TenantBaseModel):
    """
    College degree definition (e.g. B.Tech, M.Tech, BCA, MCA, MBA, MBBS).
    """
    __tablename__ = "academic_degrees"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(50), default="UNDERGRADUATE", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    courses: Mapped[List["Course"]] = relationship("Course", back_populates="degree")

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_academic_degrees_tenant_code"),
    )


class SchoolClass(TenantBaseModel):
    """
    School grade / class (e.g. Grade 1, Class 10, Pre-KG).
    Supports arbitrary custom names and sequence order.
    """
    __tablename__ = "school_classes"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    class_teacher_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(String(50), default="GENERAL", nullable=False)

    class_teacher: Mapped[Optional["TeacherProfile"]] = relationship("TeacherProfile", foreign_keys=[class_teacher_id])
    sections: Mapped[List["Section"]] = relationship(
        "Section", back_populates="school_class", cascade="all, delete-orphan", foreign_keys="[Section.class_id]"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_school_classes_tenant_code"),
    )


class Department(TenantBaseModel):
    """
    College academic department (e.g. Computer Science, Mechanical Engineering).
    """
    __tablename__ = "departments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    faculty_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_faculties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    hod_teacher_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    faculty: Mapped[Optional["AcademicFaculty"]] = relationship("AcademicFaculty", back_populates="departments")
    hod_teacher: Mapped[Optional["TeacherProfile"]] = relationship("TeacherProfile", foreign_keys=[hod_teacher_id])
    courses: Mapped[List["Course"]] = relationship(
        "Course", back_populates="department", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_departments_tenant_code"),
    )


class Course(TenantBaseModel):
    """
    College degree program / course (e.g. B.Tech Computer Science, BBA, MBA).
    """
    __tablename__ = "courses"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    degree_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_degrees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    duration_years: Mapped[float] = mapped_column(Numeric(3, 1), default=4.0, nullable=False)
    duration_semesters: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    coordinator_teacher_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="courses")
    degree: Mapped[Optional["AcademicDegree"]] = relationship("AcademicDegree", back_populates="courses")
    coordinator_teacher: Mapped[Optional["TeacherProfile"]] = relationship("TeacherProfile", foreign_keys=[coordinator_teacher_id])
    semesters: Mapped[List["CollegeSemester"]] = relationship("CollegeSemester", back_populates="course", cascade="all, delete-orphan")
    batches: Mapped[List["CollegeBatch"]] = relationship("CollegeBatch", back_populates="course", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_courses_tenant_code"),
    )


class CollegeSemester(TenantBaseModel):
    """
    Configurable semester within a college program (number of semesters varies dynamically per course).
    """
    __tablename__ = "college_semesters"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    semester_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    academic_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    credits_required: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)

    course: Mapped["Course"] = relationship("Course", back_populates="semesters")
    academic_session: Mapped[Optional["AcademicSession"]] = relationship("AcademicSession")

    __table_args__ = (
        UniqueConstraint("tenant_id", "course_id", "semester_number", name="uq_college_semesters_tenant_course_sem"),
    )


class CollegeBatch(TenantBaseModel):
    """
    Cohort batch for a college program (e.g. 2024-2028).
    """
    __tablename__ = "college_batches"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    end_year: Mapped[int] = mapped_column(Integer, nullable=False)
    current_semester_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    course: Mapped["Course"] = relationship("Course", back_populates="batches")

    __table_args__ = (
        UniqueConstraint("tenant_id", "course_id", "name", name="uq_college_batches_tenant_course_name"),
    )


class Section(TenantBaseModel):
    """
    Specific division / batch within a class or college course semester.
    """
    __tablename__ = "sections"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    class_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("school_classes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    room_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    class_teacher_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True,
    )
    semester_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_semesters.id", ondelete="CASCADE"),
        nullable=True,
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_batches.id", ondelete="CASCADE"),
        nullable=True,
    )

    school_class: Mapped[Optional["SchoolClass"]] = relationship("SchoolClass", back_populates="sections", foreign_keys=[class_id])
    class_teacher: Mapped[Optional["TeacherProfile"]] = relationship("TeacherProfile", foreign_keys=[class_teacher_id])
    course: Mapped[Optional["Course"]] = relationship("Course")
    semester: Mapped[Optional["CollegeSemester"]] = relationship("CollegeSemester")
    batch: Mapped[Optional["CollegeBatch"]] = relationship("CollegeBatch")

    __table_args__ = (
        UniqueConstraint("tenant_id", "class_id", "name", name="uq_sections_tenant_class_name"),
    )


class Subject(TenantBaseModel):
    """
    Subject / course module taught at school or college level.
    """
    __tablename__ = "subjects"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(30), default="THEORY", nullable=False)
    credits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    hours_per_week: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    is_elective: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    department: Mapped[Optional["Department"]] = relationship("Department")

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_subjects_tenant_code"),
    )


class StudentProfile(TenantBaseModel):
    """
    Detailed student demographic and enrollment record.
    """
    __tablename__ = "student_profiles"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    admission_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    roll_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    admission_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    academic_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    class_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("school_classes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    semester: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    batch_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    blood_group: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)

    # Parents & Guardians
    parent_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    parent_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    parent_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    father_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    father_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    father_occupation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mother_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    mother_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mother_occupation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    guardian_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    guardian_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    guardian_relation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    emergency_contact_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    emergency_contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Previous Academic History
    previous_school_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    previous_grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    transfer_certificate_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    photo_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    rfid_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False, index=True)
    custom_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Relationships
    user: Mapped["User"] = relationship("User")
    tenant: Mapped["Tenant"] = relationship("Tenant")

    @property
    def full_name(self) -> str:
        return self.user.full_name if self.user else ""
    academic_session: Mapped[Optional["AcademicSession"]] = relationship("AcademicSession")
    school_class: Mapped[Optional["SchoolClass"]] = relationship("SchoolClass")
    section: Mapped[Optional["Section"]] = relationship("Section")
    department: Mapped[Optional["Department"]] = relationship("Department")
    course: Mapped[Optional["Course"]] = relationship("Course")
    documents: Mapped[List["StudentDocument"]] = relationship(
        "StudentDocument", back_populates="student", cascade="all, delete-orphan"
    )
    enrollments: Mapped[List["StudentEnrollmentHistory"]] = relationship(
        "StudentEnrollmentHistory", back_populates="student", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "admission_number", name="uq_student_profiles_tenant_admission"),
        Index("ix_student_profiles_tenant_status", "tenant_id", "status"),
        Index("ix_student_profiles_tenant_class_section", "tenant_id", "class_id", "section_id"),
        Index("ix_student_profiles_tenant_course_sem", "tenant_id", "course_id", "semester"),
    )


class StudentDocument(TenantBaseModel):
    """
    Uploaded student verification and identification documents.
    """
    __tablename__ = "student_documents"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    student: Mapped["StudentProfile"] = relationship("StudentProfile", back_populates="documents")

    __table_args__ = (
        Index("ix_student_documents_tenant_student", "tenant_id", "student_id"),
    )


class StudentEnrollmentHistory(TenantBaseModel):
    """
    Historical log of student grade promotions, academic sessions, and transfers.
    """
    __tablename__ = "student_enrollment_history"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    class_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("school_classes.id", ondelete="SET NULL"),
        nullable=True,
    )
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
    )
    semester: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    roll_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    enrollment_status: Mapped[str] = mapped_column(String(30), default="ENROLLED", nullable=False)
    promoted_to_enrollment_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    student: Mapped["StudentProfile"] = relationship("StudentProfile", back_populates="enrollments")
    academic_session: Mapped["AcademicSession"] = relationship("AcademicSession")

    __table_args__ = (
        Index("ix_student_enrollments_tenant_student", "tenant_id", "student_id"),
        Index("ix_student_enrollments_tenant_session", "tenant_id", "academic_session_id"),
    )


class StudentParent(TenantBaseModel):
    """
    Linking between students and registered parent/guardian user accounts.
    """
    __tablename__ = "student_parents"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(String(50), default="GUARDIAN", nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_view_grades: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_pay_fees: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="VERIFIED", nullable=False, index=True)  # PENDING_APPROVAL | VERIFIED | REJECTED | REVOKED
    verification_method: Mapped[Optional[str]] = mapped_column(String(50), default="ADMIN_INVITATION", nullable=True)  # ADMIN_INVITATION | ADMIN_APPROVAL | VERIFICATION_CODE
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    verification_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_token: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    emergency_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    student: Mapped["StudentProfile"] = relationship("StudentProfile")
    parent_user: Mapped["User"] = relationship("User", foreign_keys=[parent_user_id])
    verified_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[verified_by_user_id])

    __table_args__ = (
        UniqueConstraint("tenant_id", "student_id", "parent_user_id", name="uq_student_parents_tenant_student_user"),
    )


class TeacherProfile(TenantBaseModel):
    """
    Detailed faculty employment and qualification record.
    """
    __tablename__ = "teacher_profiles"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rfid_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    qualification: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    specialization: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    experience_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    joining_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    employment_type: Mapped[str] = mapped_column(String(50), default="FULL_TIME", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)

    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)

    # Emergency & Statutory
    emergency_contact_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    emergency_contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    pan_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    aadhar_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Banking
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bank_ifsc: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    photo_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    custom_fields: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    user: Mapped["User"] = relationship("User")

    @property
    def full_name(self) -> str:
        return self.user.full_name if self.user else ""
    department: Mapped[Optional["Department"]] = relationship("Department", foreign_keys=[department_id])
    assignments: Mapped[List["TeacherAssignment"]] = relationship("TeacherAssignment", back_populates="teacher", cascade="all, delete-orphan")
    timetable_entries: Mapped[List["TimetableEntry"]] = relationship("TimetableEntry", back_populates="teacher", cascade="all, delete-orphan")
    attendances: Mapped[List["TeacherAttendance"]] = relationship("TeacherAttendance", back_populates="teacher", cascade="all, delete-orphan")
    leaves: Mapped[List["TeacherLeave"]] = relationship("TeacherLeave", back_populates="teacher", cascade="all, delete-orphan")
    documents: Mapped[List["TeacherDocument"]] = relationship("TeacherDocument", back_populates="teacher", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", name="uq_teacher_profiles_tenant_emp"),
    )


class TeacherAssignment(TenantBaseModel):
    """
    Teacher mapping to academic classes, sections, courses, and subjects.
    """
    __tablename__ = "teacher_assignments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    class_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("school_classes.id", ondelete="CASCADE"),
        nullable=True,
    )
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=True,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
    )
    semester: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    is_class_teacher: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    teacher: Mapped["TeacherProfile"] = relationship("TeacherProfile", back_populates="assignments")
    academic_session: Mapped[Optional["AcademicSession"]] = relationship("AcademicSession")
    school_class: Mapped[Optional["SchoolClass"]] = relationship("SchoolClass")
    section: Mapped[Optional["Section"]] = relationship("Section")
    department: Mapped[Optional["Department"]] = relationship("Department")
    course: Mapped[Optional["Course"]] = relationship("Course")
    subject: Mapped[Optional["Subject"]] = relationship("Subject")


class TimetableEntry(TenantBaseModel):
    """
    Weekly schedule timetable slot for classes and teachers.
    """
    __tablename__ = "timetable_entries"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=True,
    )
    class_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("school_classes.id", ondelete="CASCADE"),
        nullable=True,
    )
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=True,
    )
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
    )
    semester: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    day_of_week: Mapped[str] = mapped_column(String(20), nullable=False)
    period_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    start_time: Mapped[str] = mapped_column(String(10), nullable=False)
    end_time: Mapped[str] = mapped_column(String(10), nullable=False)
    room_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    schedule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("timetable_schedules.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    period_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("timetable_periods.id", ondelete="SET NULL"),
        nullable=True,
    )
    entry_type: Mapped[str] = mapped_column(String(30), default="THEORY", nullable=False)
    is_practical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    semester_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_semesters.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    teacher: Mapped["TeacherProfile"] = relationship("TeacherProfile", back_populates="timetable_entries")
    subject: Mapped[Optional["Subject"]] = relationship("Subject")
    school_class: Mapped[Optional["SchoolClass"]] = relationship("SchoolClass")
    section: Mapped[Optional["Section"]] = relationship("Section")
    course: Mapped[Optional["Course"]] = relationship("Course")
    academic_session: Mapped[Optional["AcademicSession"]] = relationship("AcademicSession")
    schedule: Mapped[Optional["TimetableSchedule"]] = relationship("TimetableSchedule", back_populates="entries")
    substitute_assignments: Mapped[List["SubstituteTeacherAssignment"]] = relationship("SubstituteTeacherAssignment", back_populates="timetable_entry", cascade="all, delete-orphan")


class TeacherAttendance(BaseModel):
    """
    Daily attendance punch / check-in record for teachers and staff.
    """
    __tablename__ = "teacher_attendances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PRESENT", nullable=False)
    check_in_time: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    check_out_time: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recorded_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    teacher: Mapped["TeacherProfile"] = relationship("TeacherProfile", back_populates="attendances")
    recorded_by: Mapped[Optional["User"]] = relationship("User")

    __table_args__ = (
        UniqueConstraint("tenant_id", "teacher_id", "attendance_date", name="uq_teacher_attendance_tenant_date"),
    )


class TeacherLeave(BaseModel):
    """
    Faculty leave applications, balances, and admin approvals.
    """
    __tablename__ = "teacher_leaves"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    leave_type: Mapped[str] = mapped_column(String(30), default="CASUAL", nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    days_count: Mapped[float] = mapped_column(Numeric(4, 1), default=1.0, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    approved_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    teacher: Mapped["TeacherProfile"] = relationship("TeacherProfile", back_populates="leaves")
    approved_by: Mapped[Optional["User"]] = relationship("User")


class TeacherDocument(BaseModel):
    """
    Employment contracts, educational credentials, and identification proofs.
    """
    __tablename__ = "teacher_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    teacher: Mapped["TeacherProfile"] = relationship("TeacherProfile", back_populates="documents")


class AcademicSubjectMapping(TenantBaseModel):
    """
    Curriculum mapping assigning a subject to a school class or college course/semester.
    """
    __tablename__ = "academic_subject_mappings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    class_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("school_classes.id", ondelete="CASCADE"),
        nullable=True,
    )
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True,
    )
    semester_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_semesters.id", ondelete="CASCADE"),
        nullable=True,
    )
    semester_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_elective: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    weekly_hours: Mapped[int] = mapped_column(Integer, default=4, nullable=False)

    academic_session: Mapped["AcademicSession"] = relationship("AcademicSession")
    subject: Mapped["Subject"] = relationship("Subject")
    school_class: Mapped[Optional["SchoolClass"]] = relationship("SchoolClass")
    course: Mapped[Optional["Course"]] = relationship("Course")
    semester: Mapped[Optional["CollegeSemester"]] = relationship("CollegeSemester")


class TeacherSubjectMapping(TenantBaseModel):
    """
    Faculty workload mapping assigning a teacher to a specific class/section or course/semester subject.
    """
    __tablename__ = "teacher_subject_mappings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teacher_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    class_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("school_classes.id", ondelete="CASCADE"),
        nullable=True,
    )
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=True,
    )
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True,
    )
    semester_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_semesters.id", ondelete="CASCADE"),
        nullable=True,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    academic_session: Mapped[Optional["AcademicSession"]] = relationship("AcademicSession")
    teacher: Mapped["TeacherProfile"] = relationship("TeacherProfile")
    subject: Mapped["Subject"] = relationship("Subject")
    school_class: Mapped[Optional["SchoolClass"]] = relationship("SchoolClass")
    section: Mapped[Optional["Section"]] = relationship("Section")
    course: Mapped[Optional["Course"]] = relationship("Course")
    semester: Mapped[Optional["CollegeSemester"]] = relationship("CollegeSemester")


class StudentAcademicEnrollment(TenantBaseModel):
    """
    Unified common student enrollment record spanning academic sessions.
    Links to school_enrollment_details or college_enrollment_details.
    """
    __tablename__ = "student_academic_enrollments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    enrollment_type: Mapped[str] = mapped_column(String(20), nullable=False)  # SCHOOL | COLLEGE
    enrollment_number: Mapped[str] = mapped_column(String(100), nullable=False)
    enrollment_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)
    roll_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    student: Mapped["StudentProfile"] = relationship("StudentProfile")
    academic_session: Mapped["AcademicSession"] = relationship("AcademicSession")
    school_detail: Mapped[Optional["SchoolEnrollmentDetail"]] = relationship("SchoolEnrollmentDetail", back_populates="enrollment", uselist=False, cascade="all, delete-orphan")
    college_detail: Mapped[Optional["CollegeEnrollmentDetail"]] = relationship("CollegeEnrollmentDetail", back_populates="enrollment", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "enrollment_number", name="uq_student_acad_enr_tenant_number"),
    )


class SchoolEnrollmentDetail(TenantBaseModel):
    """
    School-specific enrollment parameters (class, section, stream).
    """
    __tablename__ = "school_enrollment_details"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_academic_enrollments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("school_classes.id", ondelete="CASCADE"),
        nullable=False,
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
    )
    stream: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    enrollment: Mapped["StudentAcademicEnrollment"] = relationship("StudentAcademicEnrollment", back_populates="school_detail")
    school_class: Mapped["SchoolClass"] = relationship("SchoolClass")
    section: Mapped["Section"] = relationship("Section")

    __table_args__ = (
        UniqueConstraint("tenant_id", "enrollment_id", name="uq_school_enr_det_tenant_enr"),
    )


class CollegeEnrollmentDetail(TenantBaseModel):
    """
    College-specific enrollment parameters (degree, faculty, department, course, batch, semester, section).
    """
    __tablename__ = "college_enrollment_details"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_academic_enrollments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    faculty_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_faculties.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    degree_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_degrees.id", ondelete="SET NULL"),
        nullable=True,
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    semester_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_semesters.id", ondelete="SET NULL"),
        nullable=True,
    )
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="SET NULL"),
        nullable=True,
    )
    year_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    semester_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    specialization: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    enrollment: Mapped["StudentAcademicEnrollment"] = relationship("StudentAcademicEnrollment", back_populates="college_detail")
    faculty: Mapped[Optional["AcademicFaculty"]] = relationship("AcademicFaculty")
    department: Mapped[Optional["Department"]] = relationship("Department")
    course: Mapped["Course"] = relationship("Course")
    degree: Mapped[Optional["AcademicDegree"]] = relationship("AcademicDegree")
    batch: Mapped[Optional["CollegeBatch"]] = relationship("CollegeBatch")
    semester: Mapped[Optional["CollegeSemester"]] = relationship("CollegeSemester")
    section: Mapped[Optional["Section"]] = relationship("Section")

    __table_args__ = (
        UniqueConstraint("tenant_id", "enrollment_id", name="uq_college_enr_det_tenant_enr"),
    )


class StudentPromotion(BaseModel):
    """
    Cohort and individual student academic promotion records across sessions.
    """
    __tablename__ = "student_promotions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    to_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    from_enrollment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_academic_enrollments.id", ondelete="SET NULL"),
        nullable=True,
    )
    to_enrollment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_academic_enrollments.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(30), default="PROMOTED", nullable=False)
    promotion_date: Mapped[date] = mapped_column(Date, nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    performed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    student: Mapped["StudentProfile"] = relationship("StudentProfile")
    from_session: Mapped["AcademicSession"] = relationship("AcademicSession", foreign_keys=[from_session_id])
    to_session: Mapped["AcademicSession"] = relationship("AcademicSession", foreign_keys=[to_session_id])
    performed_by: Mapped[Optional["User"]] = relationship("User")


class AcademicHierarchy(BaseModel):
    """
    Tenant-level configuration for academic institution structure (School, College, Hybrid).
    """
    __tablename__ = "academic_hierarchies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    institution_type: Mapped[str] = mapped_column(String(30), default="SCHOOL", nullable=False)  # SCHOOL, COLLEGE, HYBRID
    academic_system: Mapped[str] = mapped_column(String(30), default="ANNUAL", nullable=False)    # ANNUAL, SEMESTER, TRIMESTER
    has_departments: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    has_faculties: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_batches: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    has_sections: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    grading_system: Mapped[str] = mapped_column(String(30), default="PERCENTAGE", nullable=False)
    pass_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=40.0, nullable=False)
    allow_cross_department_electives: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_electives_per_student: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

