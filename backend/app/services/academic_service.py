from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from sqlalchemy.exc import IntegrityError
from app.models.academic import (
    AcademicDegree,
    AcademicFaculty,
    AcademicHierarchy,
    AcademicSession,
    AcademicSubjectMapping,
    CollegeBatch,
    CollegeSemester,
    Course,
    Department,
    SchoolClass,
    Section,
    StudentAcademicEnrollment,
    StudentProfile,
    StudentPromotion,
    Subject,
    TeacherSubjectMapping,
)
from app.repositories.academic import AcademicRepository
from app.schemas.academic import (
    AcademicDegreeCreateRequest,
    AcademicDegreeResponse,
    AcademicDegreeUpdateRequest,
    AcademicFacultyCreateRequest,
    AcademicFacultyResponse,
    AcademicFacultyUpdateRequest,
    AcademicHierarchyResponse,
    AcademicHierarchyUpdateRequest,
    AcademicSessionCreateRequest,
    AcademicSessionResponse,
    AcademicSessionUpdateRequest,
    AcademicSubjectMappingCreateRequest,
    AcademicSubjectMappingResponse,
    CohortPromotionRequest,
    CollegeBatchCreateRequest,
    CollegeBatchResponse,
    CollegeBatchUpdateRequest,
    CollegeEnrollmentDetailResponse,
    CollegeSemesterCreateRequest,
    CollegeSemesterResponse,
    CollegeSemesterUpdateRequest,
    CourseCreateRequest,
    CourseResponse,
    CourseUpdateRequest,
    DepartmentCreateRequest,
    DepartmentResponse,
    DepartmentUpdateRequest,
    SchoolClassCreateRequest,
    SchoolClassResponse,
    SchoolClassUpdateRequest,
    SchoolEnrollmentDetailResponse,
    SectionCreateRequest,
    SectionResponse,
    SectionUpdateRequest,
    StudentAcademicHistoryResponse,
    StudentEnrollmentCreateRequest,
    StudentEnrollmentResponse,
    StudentPromotionResponse,
    SubjectCreateRequest,
    SubjectResponse,
    SubjectUpdateRequest,
    TeacherSubjectMappingCreateRequest,
    TeacherSubjectMappingResponse,
)


class AcademicService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AcademicRepository(session)

    # ── 1. Academic Sessions ──────────────────────────────────────────────────

    async def list_sessions(
        self, tenant_id: uuid.UUID, is_current: Optional[bool] = None
    ) -> List[AcademicSessionResponse]:
        objs = await self.repo.list_sessions(tenant_id, is_current=is_current)
        return [
            AcademicSessionResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                name=o.name,
                code=o.code,
                start_date=o.start_date,
                end_date=o.end_date,
                is_current=o.is_current,
                status=o.status.value if hasattr(o.status, "value") else str(o.status),
                description=o.description,
                created_at=o.created_at,
                updated_at=o.updated_at,
            )
            for o in objs
        ]

    async def create_session(
        self, tenant_id: uuid.UUID, data: AcademicSessionCreateRequest
    ) -> AcademicSessionResponse:
        if data.end_date <= data.start_date:
            raise BadRequestException("Session end date must be after start date.")
        session_obj = await self.repo.create_session(tenant_id, data.model_dump())
        await self.session.commit()
        return AcademicSessionResponse(
            id=session_obj.id,
            tenant_id=session_obj.tenant_id,
            name=session_obj.name,
            code=session_obj.code,
            start_date=session_obj.start_date,
            end_date=session_obj.end_date,
            is_current=session_obj.is_current,
            status=session_obj.status.value if hasattr(session_obj.status, "value") else str(session_obj.status),
            description=session_obj.description,
            created_at=session_obj.created_at,
            updated_at=session_obj.updated_at,
        )

    async def update_session(
        self, tenant_id: uuid.UUID, session_id: uuid.UUID, data: AcademicSessionUpdateRequest
    ) -> AcademicSessionResponse:
        obj = await self.repo.get_session(tenant_id, session_id)
        if not obj:
            raise NotFoundException("Academic session not found.")
        payload = data.model_dump(exclude_unset=True)
        start_d = payload.get("start_date", obj.start_date)
        end_d = payload.get("end_date", obj.end_date)
        if end_d <= start_d:
            raise BadRequestException("Session end date must be after start date.")
        updated = await self.repo.update_session(tenant_id, session_id, payload)
        await self.session.commit()
        await self.session.refresh(updated)
        return AcademicSessionResponse(
            id=updated.id,  # type: ignore
            tenant_id=updated.tenant_id,
            name=updated.name,
            code=updated.code,
            start_date=updated.start_date,
            end_date=updated.end_date,
            is_current=updated.is_current,
            status=updated.status.value if hasattr(updated.status, "value") else str(updated.status),
            description=updated.description,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )

    # ── 2. Academic Faculties ─────────────────────────────────────────────────

    async def list_faculties(self, tenant_id: uuid.UUID) -> List[AcademicFacultyResponse]:
        objs = await self.repo.list_faculties(tenant_id)
        return [
            AcademicFacultyResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                name=o.name,
                code=o.code,
                dean_teacher_id=o.dean_teacher_id,
                dean_name=o.dean_teacher.user.full_name if o.dean_teacher and o.dean_teacher.user else None,
                description=o.description,
                department_count=len(o.departments) if o.departments else 0,
                created_at=o.created_at,
            )
            for o in objs
        ]

    async def create_faculty(
        self, tenant_id: uuid.UUID, data: AcademicFacultyCreateRequest
    ) -> AcademicFacultyResponse:
        obj = await self.repo.create_faculty(tenant_id, data.model_dump())
        await self.session.commit()
        return AcademicFacultyResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            name=obj.name,
            code=obj.code,
            dean_teacher_id=obj.dean_teacher_id,
            dean_name=obj.dean_teacher.user.full_name if obj.dean_teacher and obj.dean_teacher.user else None,
            description=obj.description,
            department_count=len(obj.departments) if obj.departments else 0,
            created_at=obj.created_at,
        )

    async def update_faculty(
        self, tenant_id: uuid.UUID, faculty_id: uuid.UUID, data: AcademicFacultyUpdateRequest
    ) -> AcademicFacultyResponse:
        obj = await self.repo.update_faculty(tenant_id, faculty_id, data.model_dump(exclude_unset=True))
        if not obj:
            raise NotFoundException("Academic faculty not found.")
        await self.session.commit()
        return AcademicFacultyResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            name=obj.name,
            code=obj.code,
            dean_teacher_id=obj.dean_teacher_id,
            dean_name=obj.dean_teacher.user.full_name if obj.dean_teacher and obj.dean_teacher.user else None,
            description=obj.description,
            department_count=len(obj.departments) if obj.departments else 0,
            created_at=obj.created_at,
        )

    async def delete_faculty(self, tenant_id: uuid.UUID, faculty_id: uuid.UUID) -> None:
        ok = await self.repo.delete_faculty(tenant_id, faculty_id)
        if not ok:
            raise NotFoundException("Academic faculty not found.")
        await self.session.commit()

    # ── 3. Academic Degrees ───────────────────────────────────────────────────

    async def list_degrees(self, tenant_id: uuid.UUID) -> List[AcademicDegreeResponse]:
        objs = await self.repo.list_degrees(tenant_id)
        return [
            AcademicDegreeResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                name=o.name,
                code=o.code,
                level=o.level,
                description=o.description,
                created_at=o.created_at,
            )
            for o in objs
        ]

    async def create_degree(
        self, tenant_id: uuid.UUID, data: AcademicDegreeCreateRequest
    ) -> AcademicDegreeResponse:
        obj = await self.repo.create_degree(tenant_id, data.model_dump())
        await self.session.commit()
        return AcademicDegreeResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            name=obj.name,
            code=obj.code,
            level=obj.level,
            description=obj.description,
            created_at=obj.created_at,
        )

    # ── 4. Departments ────────────────────────────────────────────────────────

    async def list_departments(
        self, tenant_id: uuid.UUID, faculty_id: Optional[uuid.UUID] = None
    ) -> List[DepartmentResponse]:
        objs = await self.repo.list_departments(tenant_id, faculty_id=faculty_id)
        return [
            DepartmentResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                name=o.name,
                code=o.code,
                faculty_id=o.faculty_id,
                faculty_name=o.faculty.name if o.faculty else None,
                hod_teacher_id=o.hod_teacher_id,
                hod_name=o.hod_teacher.user.full_name if o.hod_teacher and o.hod_teacher.user else None,
                courses_count=len(o.courses) if o.courses else 0,
                created_at=o.created_at,
            )
            for o in objs
        ]

    async def create_department(
        self, tenant_id: uuid.UUID, data: DepartmentCreateRequest
    ) -> DepartmentResponse:
        obj = await self.repo.create_department(tenant_id, data.model_dump())
        await self.session.commit()
        return DepartmentResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            name=obj.name,
            code=obj.code,
            faculty_id=obj.faculty_id,
            faculty_name=obj.faculty.name if obj.faculty else None,
            hod_teacher_id=obj.hod_teacher_id,
            hod_name=obj.hod_teacher.user.full_name if obj.hod_teacher and obj.hod_teacher.user else None,
            courses_count=len(obj.courses) if obj.courses else 0,
            created_at=obj.created_at,
        )

    async def update_department(
        self, tenant_id: uuid.UUID, department_id: uuid.UUID, data: DepartmentUpdateRequest
    ) -> DepartmentResponse:
        obj = await self.repo.update_department(tenant_id, department_id, data.model_dump(exclude_unset=True))
        if not obj:
            raise NotFoundException("Department not found.")
        await self.session.commit()
        return DepartmentResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            name=obj.name,
            code=obj.code,
            faculty_id=obj.faculty_id,
            faculty_name=obj.faculty.name if obj.faculty else None,
            hod_teacher_id=obj.hod_teacher_id,
            hod_name=obj.hod_teacher.user.full_name if obj.hod_teacher and obj.hod_teacher.user else None,
            courses_count=len(obj.courses) if obj.courses else 0,
            created_at=obj.created_at,
        )

    async def delete_department(self, tenant_id: uuid.UUID, department_id: uuid.UUID) -> None:
        ok = await self.repo.delete_department(tenant_id, department_id)
        if not ok:
            raise NotFoundException("Department not found.")
        await self.session.commit()

    # ── 5. School Classes ─────────────────────────────────────────────────────

    async def list_classes(self, tenant_id: uuid.UUID) -> List[SchoolClassResponse]:
        objs = await self.repo.list_classes(tenant_id)
        return [
            SchoolClassResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                name=o.name,
                code=o.code,
                order_index=o.order_index,
                category=o.category,
                class_teacher_id=o.class_teacher_id,
                class_teacher_name=o.class_teacher.user.full_name if o.class_teacher and o.class_teacher.user else None,
                sections_count=len(o.sections) if o.sections else 0,
                created_at=o.created_at,
            )
            for o in objs
        ]

    async def create_class(
        self, tenant_id: uuid.UUID, data: SchoolClassCreateRequest
    ) -> SchoolClassResponse:
        obj = await self.repo.create_class(tenant_id, data.model_dump())
        await self.session.commit()
        return SchoolClassResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            name=obj.name,
            code=obj.code,
            order_index=obj.order_index,
            category=obj.category,
            class_teacher_id=obj.class_teacher_id,
            class_teacher_name=obj.class_teacher.user.full_name if obj.class_teacher and obj.class_teacher.user else None,
            sections_count=len(obj.sections) if obj.sections else 0,
            created_at=obj.created_at,
        )

    async def update_class(
        self, tenant_id: uuid.UUID, class_id: uuid.UUID, data: SchoolClassUpdateRequest
    ) -> SchoolClassResponse:
        obj = await self.repo.update_class(tenant_id, class_id, data.model_dump(exclude_unset=True))
        if not obj:
            raise NotFoundException("Class not found.")
        await self.session.commit()
        return SchoolClassResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            name=obj.name,
            code=obj.code,
            order_index=obj.order_index,
            category=obj.category,
            class_teacher_id=obj.class_teacher_id,
            class_teacher_name=obj.class_teacher.user.full_name if obj.class_teacher and obj.class_teacher.user else None,
            sections_count=len(obj.sections) if obj.sections else 0,
            created_at=obj.created_at,
        )

    async def delete_class(self, tenant_id: uuid.UUID, class_id: uuid.UUID) -> None:
        ok = await self.repo.delete_class(tenant_id, class_id)
        if not ok:
            raise NotFoundException("Class not found.")
        await self.session.commit()

    # ── 6. Sections ───────────────────────────────────────────────────────────

    async def list_sections(
        self,
        tenant_id: uuid.UUID,
        class_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        semester_id: Optional[uuid.UUID] = None,
    ) -> List[SectionResponse]:
        objs = await self.repo.list_sections(tenant_id, class_id=class_id, course_id=course_id, semester_id=semester_id)
        return [
            SectionResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                name=o.name,
                capacity=o.capacity,
                class_id=o.class_id,
                class_name=o.school_class.name if o.school_class else None,
                course_id=o.course_id,
                course_name=o.course.name if o.course else None,
                semester_id=o.semester_id,
                batch_id=o.batch_id,
                room_number=o.room_number,
                class_teacher_id=o.class_teacher_id,
                class_teacher_name=o.class_teacher.user.full_name if o.class_teacher and o.class_teacher.user else None,
                created_at=o.created_at,
            )
            for o in objs
        ]

    async def create_section(
        self, tenant_id: uuid.UUID, data: SectionCreateRequest
    ) -> SectionResponse:
        obj = await self.repo.create_section(tenant_id, data.model_dump())
        await self.session.commit()
        return SectionResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            name=obj.name,
            capacity=obj.capacity,
            class_id=obj.class_id,
            class_name=obj.school_class.name if obj.school_class else None,
            course_id=obj.course_id,
            course_name=obj.course.name if obj.course else None,
            semester_id=obj.semester_id,
            batch_id=obj.batch_id,
            room_number=obj.room_number,
            class_teacher_id=obj.class_teacher_id,
            class_teacher_name=obj.class_teacher.user.full_name if obj.class_teacher and obj.class_teacher.user else None,
            created_at=obj.created_at,
        )

    async def update_section(
        self, tenant_id: uuid.UUID, section_id: uuid.UUID, data: SectionUpdateRequest
    ) -> SectionResponse:
        obj = await self.repo.update_section(tenant_id, section_id, data.model_dump(exclude_unset=True))
        if not obj:
            raise NotFoundException("Section not found.")
        await self.session.commit()
        return SectionResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            name=obj.name,
            capacity=obj.capacity,
            class_id=obj.class_id,
            class_name=obj.school_class.name if obj.school_class else None,
            course_id=obj.course_id,
            course_name=obj.course.name if obj.course else None,
            semester_id=obj.semester_id,
            batch_id=obj.batch_id,
            room_number=obj.room_number,
            class_teacher_id=obj.class_teacher_id,
            class_teacher_name=obj.class_teacher.user.full_name if obj.class_teacher and obj.class_teacher.user else None,
            created_at=obj.created_at,
        )

    async def delete_section(self, tenant_id: uuid.UUID, section_id: uuid.UUID) -> None:
        ok = await self.repo.delete_section(tenant_id, section_id)
        if not ok:
            raise NotFoundException("Section not found.")
        await self.session.commit()

    # ── 7. Courses ────────────────────────────────────────────────────────────

    async def list_courses(
        self,
        tenant_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        degree_id: Optional[uuid.UUID] = None,
    ) -> List[CourseResponse]:
        objs = await self.repo.list_courses(tenant_id, department_id=department_id, degree_id=degree_id)
        return [
            CourseResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                name=o.name,
                code=o.code,
                department_id=o.department_id,
                department_name=o.department.name if o.department else None,
                degree_id=o.degree_id,
                degree_name=o.degree.name if o.degree else None,
                duration_years=float(o.duration_years),
                duration_semesters=o.duration_semesters,
                coordinator_teacher_id=o.coordinator_teacher_id,
                coordinator_name=o.coordinator_teacher.user.full_name if o.coordinator_teacher and o.coordinator_teacher.user else None,
                created_at=o.created_at,
            )
            for o in objs
        ]

    async def create_course(
        self, tenant_id: uuid.UUID, data: CourseCreateRequest
    ) -> CourseResponse:
        obj = await self.repo.create_course(tenant_id, data.model_dump())
        # Automatically generate default semester slots for the course
        for sem_idx in range(1, obj.duration_semesters + 1):
            await self.repo.create_semester(
                tenant_id,
                {
                    "course_id": obj.id,
                    "semester_number": sem_idx,
                    "name": f"Semester {sem_idx}",
                    "credits_required": 20,
                    "status": "ACTIVE",
                },
            )
        await self.session.commit()
        return CourseResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            name=obj.name,
            code=obj.code,
            department_id=obj.department_id,
            department_name=obj.department.name if obj.department else None,
            degree_id=obj.degree_id,
            degree_name=obj.degree.name if obj.degree else None,
            duration_years=float(obj.duration_years),
            duration_semesters=obj.duration_semesters,
            coordinator_teacher_id=obj.coordinator_teacher_id,
            coordinator_name=obj.coordinator_teacher.user.full_name if obj.coordinator_teacher and obj.coordinator_teacher.user else None,
            created_at=obj.created_at,
        )

    async def update_course(
        self, tenant_id: uuid.UUID, course_id: uuid.UUID, data: CourseUpdateRequest
    ) -> CourseResponse:
        obj = await self.repo.update_course(tenant_id, course_id, data.model_dump(exclude_unset=True))
        if not obj:
            raise NotFoundException("Course not found.")
        await self.session.commit()
        return CourseResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            name=obj.name,
            code=obj.code,
            department_id=obj.department_id,
            department_name=obj.department.name if obj.department else None,
            degree_id=obj.degree_id,
            degree_name=obj.degree.name if obj.degree else None,
            duration_years=float(obj.duration_years),
            duration_semesters=obj.duration_semesters,
            coordinator_teacher_id=obj.coordinator_teacher_id,
            coordinator_name=obj.coordinator_teacher.user.full_name if obj.coordinator_teacher and obj.coordinator_teacher.user else None,
            created_at=obj.created_at,
        )

    async def delete_course(self, tenant_id: uuid.UUID, course_id: uuid.UUID) -> None:
        ok = await self.repo.delete_course(tenant_id, course_id)
        if not ok:
            raise NotFoundException("Course not found.")
        await self.session.commit()

    # ── 8. College Semesters ──────────────────────────────────────────────────

    async def list_semesters(
        self, tenant_id: uuid.UUID, course_id: Optional[uuid.UUID] = None
    ) -> List[CollegeSemesterResponse]:
        objs = await self.repo.list_semesters(tenant_id, course_id=course_id)
        return [
            CollegeSemesterResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                course_id=o.course_id,
                course_name=o.course.name if o.course else None,
                semester_number=o.semester_number,
                name=o.name,
                academic_session_id=o.academic_session_id,
                credits_required=o.credits_required,
                status=o.status,
                created_at=o.created_at,
            )
            for o in objs
        ]

    async def create_semester(
        self, tenant_id: uuid.UUID, data: CollegeSemesterCreateRequest
    ) -> CollegeSemesterResponse:
        obj = await self.repo.create_semester(tenant_id, data.model_dump())
        await self.session.commit()
        return CollegeSemesterResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            course_id=obj.course_id,
            course_name=obj.course.name if obj.course else None,
            semester_number=obj.semester_number,
            name=obj.name,
            academic_session_id=obj.academic_session_id,
            credits_required=obj.credits_required,
            status=obj.status,
            created_at=obj.created_at,
        )

    # ── 9. College Batches ────────────────────────────────────────────────────

    async def list_batches(
        self, tenant_id: uuid.UUID, course_id: Optional[uuid.UUID] = None
    ) -> List[CollegeBatchResponse]:
        objs = await self.repo.list_batches(tenant_id, course_id=course_id)
        return [
            CollegeBatchResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                course_id=o.course_id,
                course_name=o.course.name if o.course else None,
                name=o.name,
                start_year=o.start_year,
                end_year=o.end_year,
                current_semester_number=o.current_semester_number,
                is_active=o.is_active,
                created_at=o.created_at,
            )
            for o in objs
        ]

    async def create_batch(
        self, tenant_id: uuid.UUID, data: CollegeBatchCreateRequest
    ) -> CollegeBatchResponse:
        obj = await self.repo.create_batch(tenant_id, data.model_dump())
        await self.session.commit()
        return CollegeBatchResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            course_id=obj.course_id,
            course_name=obj.course.name if obj.course else None,
            name=obj.name,
            start_year=obj.start_year,
            end_year=obj.end_year,
            current_semester_number=obj.current_semester_number,
            is_active=obj.is_active,
            created_at=obj.created_at,
        )

    # ── 10. Subjects ──────────────────────────────────────────────────────────

    async def list_subjects(
        self,
        tenant_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        subject_type: Optional[str] = None,
    ) -> List[SubjectResponse]:
        objs = await self.repo.list_subjects(tenant_id, department_id=department_id, subject_type=subject_type)
        return [
            SubjectResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                name=o.name,
                code=o.code,
                subject_type=o.subject_type,
                credits=o.credits,
                department_id=o.department_id,
                department_name=o.department.name if o.department else None,
                hours_per_week=o.hours_per_week,
                is_elective=o.is_elective,
                description=o.description,
                created_at=o.created_at,
            )
            for o in objs
        ]

    async def create_subject(
        self, tenant_id: uuid.UUID, data: SubjectCreateRequest
    ) -> SubjectResponse:
        if data.department_id and not await self.repo.get_department(tenant_id, data.department_id):
            raise BadRequestException("Select a department in this institution.")
        try:
            obj = await self.repo.create_subject(tenant_id, data.model_dump())
        except IntegrityError as exc:
            if "uq_subjects_tenant_code" not in str(exc.orig):
                raise
            await self.session.rollback()
            raise ConflictException("A subject with this code already exists.") from exc
        await self.session.commit()
        return SubjectResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            name=obj.name,
            code=obj.code,
            subject_type=obj.subject_type,
            credits=obj.credits,
            department_id=obj.department_id,
            department_name=obj.department.name if obj.department else None,
            hours_per_week=obj.hours_per_week,
            is_elective=obj.is_elective,
            description=obj.description,
            created_at=obj.created_at,
        )

    async def update_subject(
        self, tenant_id: uuid.UUID, subject_id: uuid.UUID, data: SubjectUpdateRequest
    ) -> SubjectResponse:
        if data.department_id and not await self.repo.get_department(tenant_id, data.department_id):
            raise BadRequestException("Select a department in this institution.")
        try:
            obj = await self.repo.update_subject(tenant_id, subject_id, data.model_dump(exclude_unset=True))
        except IntegrityError as exc:
            if "uq_subjects_tenant_code" not in str(exc.orig):
                raise
            await self.session.rollback()
            raise ConflictException("A subject with this code already exists.") from exc
        if not obj:
            raise NotFoundException("Subject not found.")
        await self.session.commit()
        return SubjectResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            name=obj.name,
            code=obj.code,
            subject_type=obj.subject_type,
            credits=obj.credits,
            department_id=obj.department_id,
            department_name=obj.department.name if obj.department else None,
            hours_per_week=obj.hours_per_week,
            is_elective=obj.is_elective,
            description=obj.description,
            created_at=obj.created_at,
        )

    async def delete_subject(self, tenant_id: uuid.UUID, subject_id: uuid.UUID) -> None:
        ok = await self.repo.delete_subject(tenant_id, subject_id)
        if not ok:
            raise NotFoundException("Subject not found.")
        await self.session.commit()

    # ── 11. Academic Subject Mappings ─────────────────────────────────────────

    async def list_subject_mappings(
        self,
        tenant_id: uuid.UUID,
        session_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        semester_id: Optional[uuid.UUID] = None,
    ) -> List[AcademicSubjectMappingResponse]:
        objs = await self.repo.list_subject_mappings(
            tenant_id, session_id=session_id, class_id=class_id, course_id=course_id, semester_id=semester_id
        )
        return [
            AcademicSubjectMappingResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                academic_session_id=o.academic_session_id,
                subject_id=o.subject_id,
                subject_name=o.subject.name if o.subject else None,
                subject_code=o.subject.code if o.subject else None,
                class_id=o.class_id,
                class_name=o.school_class.name if o.school_class else None,
                course_id=o.course_id,
                course_name=o.course.name if o.course else None,
                semester_id=o.semester_id,
                semester_number=o.semester_number,
                is_elective=o.is_elective,
                credits=o.credits,
                weekly_hours=o.weekly_hours,
                created_at=o.created_at,
            )
            for o in objs
        ]

    async def create_subject_mapping(
        self, tenant_id: uuid.UUID, data: AcademicSubjectMappingCreateRequest
    ) -> AcademicSubjectMappingResponse:
        subject = await self.session.scalar(select(Subject).where(
            Subject.tenant_id == tenant_id, Subject.id == data.subject_id, Subject.is_deleted.is_(False),
        ).with_for_update())
        if not subject or not await self.repo.get_session(tenant_id, data.academic_session_id):
            raise BadRequestException("Select a subject and academic session in this institution.")
        if data.course_id:
            course = await self.repo.get_course(tenant_id, data.course_id)
            semester = await self.repo.get_semester(tenant_id, data.semester_id) if data.semester_id else None
            if not course or data.class_id or (data.semester_id and (not semester or semester.course_id != course.id)):
                raise BadRequestException("Select a semester belonging to the course.")
            if semester:
                data.semester_number = semester.semester_number
        elif data.class_id:
            if not await self.repo.get_class(tenant_id, data.class_id) or data.semester_id:
                raise BadRequestException("Select a class in this institution.")
        else:
            raise BadRequestException("Select a course and semester or a class.")
        existing = await self.session.scalar(select(AcademicSubjectMapping.id).where(
            AcademicSubjectMapping.tenant_id == tenant_id,
            AcademicSubjectMapping.academic_session_id == data.academic_session_id,
            AcademicSubjectMapping.subject_id == data.subject_id,
            AcademicSubjectMapping.course_id == data.course_id,
            AcademicSubjectMapping.semester_id == data.semester_id,
            AcademicSubjectMapping.class_id == data.class_id,
            AcademicSubjectMapping.is_deleted.is_(False),
        ))
        if existing:
            raise ConflictException("This subject is already assigned to the selected group and session.")
        obj = await self.repo.create_subject_mapping(tenant_id, data.model_dump())
        await self.session.commit()
        return AcademicSubjectMappingResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            academic_session_id=obj.academic_session_id,
            subject_id=obj.subject_id,
            subject_name=obj.subject.name if obj.subject else None,
            subject_code=obj.subject.code if obj.subject else None,
            class_id=obj.class_id,
            class_name=obj.school_class.name if obj.school_class else None,
            course_id=obj.course_id,
            course_name=obj.course.name if obj.course else None,
            semester_id=obj.semester_id,
            semester_number=obj.semester_number,
            is_elective=obj.is_elective,
            credits=obj.credits,
            weekly_hours=obj.weekly_hours,
            created_at=obj.created_at,
        )

    async def delete_subject_mapping(self, tenant_id: uuid.UUID, mapping_id: uuid.UUID) -> None:
        ok = await self.repo.delete_subject_mapping(tenant_id, mapping_id)
        if not ok:
            raise NotFoundException("Subject mapping not found.")
        await self.session.commit()

    # ── 12. Teacher Subject Mappings ──────────────────────────────────────────

    async def list_teacher_subject_mappings(
        self,
        tenant_id: uuid.UUID,
        teacher_id: Optional[uuid.UUID] = None,
        session_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
    ) -> List[TeacherSubjectMappingResponse]:
        objs = await self.repo.list_teacher_subject_mappings(
            tenant_id, teacher_id=teacher_id, session_id=session_id, class_id=class_id, course_id=course_id
        )
        return [
            TeacherSubjectMappingResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                teacher_id=o.teacher_id,
                teacher_name=o.teacher.user.full_name if o.teacher and o.teacher.user else None,
                teacher_emp_id=o.teacher.employee_id if o.teacher else None,
                subject_id=o.subject_id,
                subject_name=o.subject.name if o.subject else None,
                academic_session_id=o.academic_session_id,
                class_id=o.class_id,
                class_name=o.school_class.name if o.school_class else None,
                section_id=o.section_id,
                section_name=o.section.name if o.section else None,
                course_id=o.course_id,
                course_name=o.course.name if o.course else None,
                semester_id=o.semester_id,
                is_primary=o.is_primary,
                created_at=o.created_at,
            )
            for o in objs
        ]

    async def create_teacher_subject_mapping(
        self, tenant_id: uuid.UUID, data: TeacherSubjectMappingCreateRequest
    ) -> TeacherSubjectMappingResponse:
        obj = await self.repo.create_teacher_subject_mapping(tenant_id, data.model_dump())
        await self.session.commit()
        return TeacherSubjectMappingResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            teacher_id=obj.teacher_id,
            teacher_name=obj.teacher.user.full_name if obj.teacher and obj.teacher.user else None,
            teacher_emp_id=obj.teacher.employee_id if obj.teacher else None,
            subject_id=obj.subject_id,
            subject_name=obj.subject.name if obj.subject else None,
            academic_session_id=obj.academic_session_id,
            class_id=obj.class_id,
            class_name=obj.school_class.name if obj.school_class else None,
            section_id=obj.section_id,
            section_name=obj.section.name if obj.section else None,
            course_id=obj.course_id,
            course_name=obj.course.name if obj.course else None,
            semester_id=obj.semester_id,
            is_primary=obj.is_primary,
            created_at=obj.created_at,
        )

    async def delete_teacher_subject_mapping(self, tenant_id: uuid.UUID, mapping_id: uuid.UUID) -> None:
        ok = await self.repo.delete_teacher_subject_mapping(tenant_id, mapping_id)
        if not ok:
            raise NotFoundException("Teacher subject mapping not found.")
        await self.session.commit()

    # ── 13. Student Common Enrollments ────────────────────────────────────────

    async def list_enrollments(
        self,
        tenant_id: uuid.UUID,
        session_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
    ) -> List[StudentEnrollmentResponse]:
        objs = await self.repo.list_enrollments(
            tenant_id, session_id=session_id, class_id=class_id, course_id=course_id, status=status
        )
        results = []
        for o in objs:
            sch_res = None
            col_res = None
            if o.school_detail:
                sch_res = SchoolEnrollmentDetailResponse(
                    id=o.school_detail.id,
                    class_id=o.school_detail.class_id,
                    class_name=o.school_detail.school_class.name if o.school_detail.school_class else None,
                    section_id=o.school_detail.section_id,
                    section_name=o.school_detail.section.name if o.school_detail.section else None,
                    stream=o.school_detail.stream,
                )
            if o.college_detail:
                col_res = CollegeEnrollmentDetailResponse(
                    id=o.college_detail.id,
                    faculty_id=o.college_detail.faculty_id,
                    faculty_name=o.college_detail.faculty.name if o.college_detail.faculty else None,
                    department_id=o.college_detail.department_id,
                    department_name=o.college_detail.department.name if o.college_detail.department else None,
                    course_id=o.college_detail.course_id,
                    course_name=o.college_detail.course.name if o.college_detail.course else None,
                    degree_id=o.college_detail.degree_id,
                    degree_name=o.college_detail.degree.name if o.college_detail.degree else None,
                    batch_id=o.college_detail.batch_id,
                    batch_name=o.college_detail.batch.name if o.college_detail.batch else None,
                    semester_id=o.college_detail.semester_id,
                    semester_number=o.college_detail.semester_number,
                    year_number=o.college_detail.year_number,
                    specialization=o.college_detail.specialization,
                )
            results.append(
                StudentEnrollmentResponse(
                    id=o.id,
                    tenant_id=o.tenant_id,
                    student_id=o.student_id,
                    student_name=o.student.user.full_name if o.student and o.student.user else None,
                    admission_number=o.student.admission_number if o.student else None,
                    academic_session_id=o.academic_session_id,
                    session_name=o.academic_session.name if o.academic_session else None,
                    enrollment_type=o.enrollment_type,
                    enrollment_number=o.enrollment_number,
                    enrollment_date=o.enrollment_date,
                    status=o.status,
                    roll_number=o.roll_number,
                    school_detail=sch_res,
                    college_detail=col_res,
                    created_at=o.created_at,
                )
            )
        return results

    async def create_enrollment(
        self, tenant_id: uuid.UUID, data: StudentEnrollmentCreateRequest
    ) -> StudentEnrollmentResponse:
        # Validate student exists
        stmt_stu = select(StudentProfile).where(
            StudentProfile.id == data.student_id,
            StudentProfile.tenant_id == tenant_id,
        )
        stu_res = await self.session.execute(stmt_stu)
        student = stu_res.scalars().first()
        if not student:
            raise NotFoundException("Student profile not found.")

        # Generate unique enrollment number if not provided
        enr_num = data.enrollment_number
        if not enr_num:
            year = datetime.now(timezone.utc).year
            stmt_count = select(func.count(StudentAcademicEnrollment.id)).where(
                StudentAcademicEnrollment.tenant_id == tenant_id
            )
            count = (await self.session.execute(stmt_count)).scalar() or 0
            enr_num = f"ENR-{year}-{count + 1:05d}"

        enr_date = data.enrollment_date or date.today()

        base_data = {
            "student_id": data.student_id,
            "academic_session_id": data.academic_session_id,
            "enrollment_type": data.enrollment_type,
            "enrollment_number": enr_num,
            "enrollment_date": enr_date,
            "status": data.status,
            "roll_number": data.roll_number,
        }

        school_data = data.school_detail.model_dump() if data.school_detail else None
        college_data = data.college_detail.model_dump() if data.college_detail else None

        obj = await self.repo.create_enrollment(
            tenant_id,
            base_data,
            school_data=school_data,
            college_data=college_data,
        )

        # Update student profile current pointers
        student.academic_session_id = data.academic_session_id
        if school_data:
            student.class_id = school_data.get("class_id")
            student.section_id = school_data.get("section_id")
        elif college_data:
            student.course_id = college_data.get("course_id")
            student.department_id = college_data.get("department_id")
            student.semester = college_data.get("semester_number")

        await self.session.commit()

        # Format return response
        sch_res = None
        col_res = None
        if obj.school_detail:
            sch_res = SchoolEnrollmentDetailResponse(
                id=obj.school_detail.id,
                class_id=obj.school_detail.class_id,
                class_name=obj.school_detail.school_class.name if obj.school_detail.school_class else None,
                section_id=obj.school_detail.section_id,
                section_name=obj.school_detail.section.name if obj.school_detail.section else None,
                stream=obj.school_detail.stream,
            )
        if obj.college_detail:
            col_res = CollegeEnrollmentDetailResponse(
                id=obj.college_detail.id,
                faculty_id=obj.college_detail.faculty_id,
                faculty_name=obj.college_detail.faculty.name if obj.college_detail.faculty else None,
                department_id=obj.college_detail.department_id,
                department_name=obj.college_detail.department.name if obj.college_detail.department else None,
                course_id=obj.college_detail.course_id,
                course_name=obj.college_detail.course.name if obj.college_detail.course else None,
                degree_id=obj.college_detail.degree_id,
                degree_name=obj.college_detail.degree.name if obj.college_detail.degree else None,
                batch_id=obj.college_detail.batch_id,
                batch_name=obj.college_detail.batch.name if obj.college_detail.batch else None,
                semester_id=obj.college_detail.semester_id,
                semester_number=obj.college_detail.semester_number,
                year_number=obj.college_detail.year_number,
                specialization=obj.college_detail.specialization,
            )

        return StudentEnrollmentResponse(
            id=obj.id,
            tenant_id=obj.tenant_id,
            student_id=obj.student_id,
            student_name=obj.student.user.full_name if obj.student and obj.student.user else None,
            admission_number=obj.student.admission_number if obj.student else None,
            academic_session_id=obj.academic_session_id,
            session_name=obj.academic_session.name if obj.academic_session else None,
            enrollment_type=obj.enrollment_type,
            enrollment_number=obj.enrollment_number,
            enrollment_date=obj.enrollment_date,
            status=obj.status,
            roll_number=obj.roll_number,
            school_detail=sch_res,
            college_detail=col_res,
            created_at=obj.created_at,
        )

    # ── 14. Student Promotions ────────────────────────────────────────────────

    async def promote_cohort(
        self,
        tenant_id: uuid.UUID,
        data: CohortPromotionRequest,
        performed_by_user_id: Optional[uuid.UUID] = None,
    ) -> List[StudentPromotionResponse]:
        results = []
        year = datetime.now(timezone.utc).year

        for s_id in data.student_ids:
            # 1. Retrieve current active enrollment in from_session_id
            stmt = (
                select(StudentAcademicEnrollment)
                .where(
                    StudentAcademicEnrollment.tenant_id == tenant_id,
                    StudentAcademicEnrollment.student_id == s_id,
                    StudentAcademicEnrollment.academic_session_id == data.from_session_id,
                    StudentAcademicEnrollment.status == "ACTIVE",
                )
            )
            old_enr = (await self.session.execute(stmt)).scalars().first()
            if old_enr:
                old_enr.status = data.action

            # 2. If PROMOTED, create new enrollment in to_session_id
            new_enr_id = None
            if data.action == "PROMOTED":
                stmt_count = select(func.count(StudentAcademicEnrollment.id)).where(
                    StudentAcademicEnrollment.tenant_id == tenant_id
                )
                count = (await self.session.execute(stmt_count)).scalar() or 0
                enr_num = f"ENR-{year}-{count + 1:05d}"

                new_enr_data = {
                    "student_id": s_id,
                    "academic_session_id": data.to_session_id,
                    "enrollment_type": data.enrollment_type,
                    "enrollment_number": enr_num,
                    "enrollment_date": date.today(),
                    "status": "ACTIVE",
                }

                school_data = None
                college_data = None
                if data.enrollment_type == "SCHOOL" and data.target_class_id and data.target_section_id:
                    school_data = {
                        "class_id": data.target_class_id,
                        "section_id": data.target_section_id,
                    }
                elif data.enrollment_type == "COLLEGE" and data.target_course_id:
                    college_data = {
                        "course_id": data.target_course_id,
                        "semester_id": data.target_semester_id,
                        "semester_number": data.target_semester_number or 1,
                        "year_number": data.target_year_number or 1,
                    }

                created_enr = await self.repo.create_enrollment(
                    tenant_id,
                    new_enr_data,
                    school_data=school_data,
                    college_data=college_data,
                )
                new_enr_id = created_enr.id

                # Update student profile
                stmt_stu = select(StudentProfile).where(
                    StudentProfile.id == s_id, StudentProfile.tenant_id == tenant_id
                )
                student = (await self.session.execute(stmt_stu)).scalars().first()
                if student:
                    student.academic_session_id = data.to_session_id
                    if school_data:
                        student.class_id = data.target_class_id
                        student.section_id = data.target_section_id
                    elif college_data:
                        student.course_id = data.target_course_id
                        student.semester = data.target_semester_number

            # 3. Create promotion record
            promo = await self.repo.create_promotion(
                tenant_id,
                {
                    "student_id": s_id,
                    "from_session_id": data.from_session_id,
                    "to_session_id": data.to_session_id,
                    "from_enrollment_id": old_enr.id if old_enr else None,
                    "to_enrollment_id": new_enr_id,
                    "action": data.action,
                    "promotion_date": date.today(),
                    "remarks": data.remarks,
                    "performed_by_user_id": performed_by_user_id,
                },
            )
            results.append(
                StudentPromotionResponse(
                    id=promo.id,
                    tenant_id=promo.tenant_id,
                    student_id=promo.student_id,
                    student_name=promo.student.user.full_name if promo.student and promo.student.user else None,
                    from_session_id=promo.from_session_id,
                    to_session_id=promo.to_session_id,
                    action=promo.action,
                    promotion_date=promo.promotion_date,
                    remarks=promo.remarks,
                    created_at=promo.created_at,
                )
            )

        await self.session.commit()
        return results

    # ── 15. Academic Hierarchy ────────────────────────────────────────────────

    async def get_hierarchy(self, tenant_id: uuid.UUID) -> AcademicHierarchyResponse:
        hier = await self.repo.get_or_create_hierarchy(tenant_id)
        return AcademicHierarchyResponse(
            id=hier.id,
            tenant_id=hier.tenant_id,
            institution_type=hier.institution_type,
            academic_system=hier.academic_system,
            has_departments=hier.has_departments,
            has_faculties=hier.has_faculties,
            has_batches=hier.has_batches,
            has_sections=hier.has_sections,
            grading_system=hier.grading_system,
            pass_percentage=float(hier.pass_percentage),
            allow_cross_department_electives=hier.allow_cross_department_electives,
            max_electives_per_student=hier.max_electives_per_student,
            settings=hier.settings,
            created_at=hier.created_at,
            updated_at=hier.updated_at,
        )

    async def update_hierarchy(
        self, tenant_id: uuid.UUID, data: AcademicHierarchyUpdateRequest
    ) -> AcademicHierarchyResponse:
        hier = await self.repo.update_hierarchy(tenant_id, data.model_dump(exclude_unset=True))
        await self.session.commit()
        return AcademicHierarchyResponse(
            id=hier.id,
            tenant_id=hier.tenant_id,
            institution_type=hier.institution_type,
            academic_system=hier.academic_system,
            has_departments=hier.has_departments,
            has_faculties=hier.has_faculties,
            has_batches=hier.has_batches,
            has_sections=hier.has_sections,
            grading_system=hier.grading_system,
            pass_percentage=float(hier.pass_percentage),
            allow_cross_department_electives=hier.allow_cross_department_electives,
            max_electives_per_student=hier.max_electives_per_student,
            settings=hier.settings,
            created_at=hier.created_at,
            updated_at=hier.updated_at,
        )

    # ── 16. Student Academic History ──────────────────────────────────────────

    async def get_student_history(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID
    ) -> StudentAcademicHistoryResponse:
        stmt = select(StudentProfile).where(
            StudentProfile.id == student_id,
            StudentProfile.tenant_id == tenant_id,
        )
        res = await self.session.execute(stmt)
        student = res.scalars().first()
        if not student:
            raise NotFoundException("Student profile not found.")

        enrollments = await self.list_enrollments(tenant_id)
        student_enrs = [e for e in enrollments if e.student_id == student_id]

        promotions = await self.repo.get_student_promotions(tenant_id, student_id)
        promo_responses = [
            StudentPromotionResponse(
                id=p.id,
                tenant_id=p.tenant_id,
                student_id=p.student_id,
                student_name=p.student.user.full_name if p.student and p.student.user else None,
                from_session_id=p.from_session_id,
                to_session_id=p.to_session_id,
                action=p.action,
                promotion_date=p.promotion_date,
                remarks=p.remarks,
                created_at=p.created_at,
            )
            for p in promotions
        ]

        return StudentAcademicHistoryResponse(
            student_id=student.id,
            admission_number=student.admission_number,
            student_name=student.user.full_name if student.user else "Student",
            enrollments=student_enrs,
            promotions=promo_responses,
        )
