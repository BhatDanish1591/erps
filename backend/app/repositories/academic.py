from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.exceptions import BadRequestException, ConflictException
from app.dependencies.tenant import registered_institution_type
from app.models.enums import InstitutionType

from app.models.academic import (
    AcademicDegree,
    AcademicFaculty,
    AcademicHierarchy,
    AcademicSession,
    AcademicSubjectMapping,
    CollegeBatch,
    CollegeEnrollmentDetail,
    CollegeSemester,
    Course,
    Department,
    SchoolClass,
    SchoolEnrollmentDetail,
    Section,
    StudentAcademicEnrollment,
    StudentProfile,
    StudentPromotion,
    Subject,
    TeacherProfile,
    TeacherSubjectMapping,
)


class AcademicRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── 1. Academic Sessions ──────────────────────────────────────────────────

    async def list_sessions(
        self, tenant_id: uuid.UUID, is_current: Optional[bool] = None
    ) -> List[AcademicSession]:
        stmt = (
            select(AcademicSession)
            .where(
                AcademicSession.tenant_id == tenant_id,
                AcademicSession.is_deleted.is_(False),
            )
            .order_by(AcademicSession.start_date.desc())
        )
        if is_current is not None:
            stmt = stmt.where(AcademicSession.is_current == is_current)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_session(
        self, tenant_id: uuid.UUID, session_id: uuid.UUID
    ) -> Optional[AcademicSession]:
        stmt = select(AcademicSession).where(
            AcademicSession.id == session_id,
            AcademicSession.tenant_id == tenant_id,
            AcademicSession.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_session(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> AcademicSession:
        if data.get("is_current"):
            # Set all other sessions to not current
            await self.session.execute(
                update(AcademicSession)
                .where(AcademicSession.tenant_id == tenant_id)
                .values(is_current=False)
            )
        session_obj = AcademicSession(tenant_id=tenant_id, **data)
        self.session.add(session_obj)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            if "uq_academic_sessions_tenant_code" not in str(exc.orig):
                raise
            await self.session.rollback()
            raise ConflictException("A session with this code already exists, including deleted sessions.") from exc
        return session_obj

    async def update_session(
        self, tenant_id: uuid.UUID, session_id: uuid.UUID, data: Dict[str, Any]
    ) -> Optional[AcademicSession]:
        session_obj = await self.get_session(tenant_id, session_id)
        if not session_obj:
            return None
        if data.get("is_current"):
            await self.session.execute(
                update(AcademicSession)
                .where(AcademicSession.tenant_id == tenant_id)
                .values(is_current=False)
            )
        for k, v in data.items():
            if v is not None:
                setattr(session_obj, k, v)
        await self.session.flush()
        return session_obj

    # ── 2. Academic Faculties ─────────────────────────────────────────────────

    async def list_faculties(self, tenant_id: uuid.UUID) -> List[AcademicFaculty]:
        stmt = (
            select(AcademicFaculty)
            .options(
                selectinload(AcademicFaculty.dean_teacher).selectinload(TeacherProfile.user),
                selectinload(AcademicFaculty.departments),
            )
            .where(
                AcademicFaculty.tenant_id == tenant_id,
                AcademicFaculty.is_deleted.is_(False),
            )
            .order_by(AcademicFaculty.name.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_faculty(
        self, tenant_id: uuid.UUID, faculty_id: uuid.UUID
    ) -> Optional[AcademicFaculty]:
        stmt = (
            select(AcademicFaculty)
            .options(
                selectinload(AcademicFaculty.dean_teacher).selectinload(TeacherProfile.user),
                selectinload(AcademicFaculty.departments),
            )
            .where(
                AcademicFaculty.id == faculty_id,
                AcademicFaculty.tenant_id == tenant_id,
                AcademicFaculty.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_faculty(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> AcademicFaculty:
        faculty = AcademicFaculty(tenant_id=tenant_id, **data)
        self.session.add(faculty)
        await self.session.flush()
        return await self.get_faculty(tenant_id, faculty.id)  # type: ignore

    async def update_faculty(
        self, tenant_id: uuid.UUID, faculty_id: uuid.UUID, data: Dict[str, Any]
    ) -> Optional[AcademicFaculty]:
        faculty = await self.get_faculty(tenant_id, faculty_id)
        if not faculty:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(faculty, k, v)
        await self.session.flush()
        return await self.get_faculty(tenant_id, faculty_id)

    async def delete_faculty(self, tenant_id: uuid.UUID, faculty_id: uuid.UUID) -> bool:
        faculty = await self.get_faculty(tenant_id, faculty_id)
        if not faculty:
            return False
        faculty.is_deleted = True
        faculty.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    # ── 3. Academic Degrees ───────────────────────────────────────────────────

    async def list_degrees(self, tenant_id: uuid.UUID) -> List[AcademicDegree]:
        stmt = (
            select(AcademicDegree)
            .where(
                AcademicDegree.tenant_id == tenant_id,
                AcademicDegree.is_deleted.is_(False),
            )
            .order_by(AcademicDegree.name.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_degree(
        self, tenant_id: uuid.UUID, degree_id: uuid.UUID
    ) -> Optional[AcademicDegree]:
        stmt = select(AcademicDegree).where(
            AcademicDegree.id == degree_id,
            AcademicDegree.tenant_id == tenant_id,
            AcademicDegree.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_degree(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> AcademicDegree:
        degree = AcademicDegree(tenant_id=tenant_id, **data)
        self.session.add(degree)
        await self.session.flush()
        return degree

    async def update_degree(
        self, tenant_id: uuid.UUID, degree_id: uuid.UUID, data: Dict[str, Any]
    ) -> Optional[AcademicDegree]:
        degree = await self.get_degree(tenant_id, degree_id)
        if not degree:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(degree, k, v)
        await self.session.flush()
        return degree

    # ── 4. Departments ────────────────────────────────────────────────────────

    async def list_departments(
        self, tenant_id: uuid.UUID, faculty_id: Optional[uuid.UUID] = None
    ) -> List[Department]:
        stmt = (
            select(Department)
            .options(
                selectinload(Department.faculty),
                selectinload(Department.hod_teacher).selectinload(TeacherProfile.user),
                selectinload(Department.courses),
            )
            .where(
                Department.tenant_id == tenant_id,
                Department.is_deleted.is_(False),
            )
            .order_by(Department.name.asc())
        )
        if faculty_id:
            stmt = stmt.where(Department.faculty_id == faculty_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_department(
        self, tenant_id: uuid.UUID, department_id: uuid.UUID
    ) -> Optional[Department]:
        stmt = (
            select(Department)
            .options(
                selectinload(Department.faculty),
                selectinload(Department.hod_teacher).selectinload(TeacherProfile.user),
                selectinload(Department.courses),
            )
            .where(
                Department.id == department_id,
                Department.tenant_id == tenant_id,
                Department.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_department(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> Department:
        dept = Department(tenant_id=tenant_id, **data)
        self.session.add(dept)
        await self.session.flush()
        return await self.get_department(tenant_id, dept.id)  # type: ignore

    async def update_department(
        self, tenant_id: uuid.UUID, department_id: uuid.UUID, data: Dict[str, Any]
    ) -> Optional[Department]:
        dept = await self.get_department(tenant_id, department_id)
        if not dept:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(dept, k, v)
        await self.session.flush()
        return await self.get_department(tenant_id, department_id)

    async def delete_department(self, tenant_id: uuid.UUID, department_id: uuid.UUID) -> bool:
        dept = await self.get_department(tenant_id, department_id)
        if not dept:
            return False
        dept.is_deleted = True
        dept.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    # ── 5. School Classes ─────────────────────────────────────────────────────

    async def list_classes(self, tenant_id: uuid.UUID) -> List[SchoolClass]:
        stmt = (
            select(SchoolClass)
            .options(
                selectinload(SchoolClass.class_teacher).selectinload(TeacherProfile.user),
                selectinload(SchoolClass.sections),
            )
            .where(
                SchoolClass.tenant_id == tenant_id,
                SchoolClass.is_deleted.is_(False),
            )
            .order_by(SchoolClass.order_index.asc(), SchoolClass.name.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_class(
        self, tenant_id: uuid.UUID, class_id: uuid.UUID
    ) -> Optional[SchoolClass]:
        stmt = (
            select(SchoolClass)
            .options(
                selectinload(SchoolClass.class_teacher).selectinload(TeacherProfile.user),
                selectinload(SchoolClass.sections),
            )
            .where(
                SchoolClass.id == class_id,
                SchoolClass.tenant_id == tenant_id,
                SchoolClass.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_class(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> SchoolClass:
        cls_obj = SchoolClass(tenant_id=tenant_id, **data)
        self.session.add(cls_obj)
        await self.session.flush()
        return await self.get_class(tenant_id, cls_obj.id)  # type: ignore

    async def update_class(
        self, tenant_id: uuid.UUID, class_id: uuid.UUID, data: Dict[str, Any]
    ) -> Optional[SchoolClass]:
        cls_obj = await self.get_class(tenant_id, class_id)
        if not cls_obj:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(cls_obj, k, v)
        await self.session.flush()
        return await self.get_class(tenant_id, class_id)

    async def delete_class(self, tenant_id: uuid.UUID, class_id: uuid.UUID) -> bool:
        cls_obj = await self.get_class(tenant_id, class_id)
        if not cls_obj:
            return False
        cls_obj.is_deleted = True
        cls_obj.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    # ── 6. Sections ───────────────────────────────────────────────────────────

    async def list_sections(
        self,
        tenant_id: uuid.UUID,
        class_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        semester_id: Optional[uuid.UUID] = None,
    ) -> List[Section]:
        institution_type = await registered_institution_type(self.session, tenant_id)
        stmt = (
            select(Section)
            .options(
                selectinload(Section.school_class),
                selectinload(Section.course),
                selectinload(Section.class_teacher).selectinload(TeacherProfile.user),
            )
            .where(
                Section.tenant_id == tenant_id,
                Section.is_deleted.is_(False),
                Section.class_id.is_not(None) if institution_type == InstitutionType.SCHOOL else Section.course_id.is_not(None),
            )
            .order_by(Section.name.asc())
        )
        if class_id:
            stmt = stmt.where(Section.class_id == class_id)
        if course_id:
            stmt = stmt.where(Section.course_id == course_id)
        if semester_id:
            stmt = stmt.where(Section.semester_id == semester_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_section(
        self, tenant_id: uuid.UUID, section_id: uuid.UUID
    ) -> Optional[Section]:
        institution_type = await registered_institution_type(self.session, tenant_id)
        stmt = (
            select(Section)
            .options(
                selectinload(Section.school_class),
                selectinload(Section.course),
                selectinload(Section.class_teacher).selectinload(TeacherProfile.user),
            )
            .where(
                Section.id == section_id,
                Section.tenant_id == tenant_id,
                Section.is_deleted.is_(False),
                Section.class_id.is_not(None) if institution_type == InstitutionType.SCHOOL else Section.course_id.is_not(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_section(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> Section:
        await self._validate_section_type(tenant_id, data, creating=True)
        sec = Section(tenant_id=tenant_id, **data)
        self.session.add(sec)
        await self.session.flush()
        return await self.get_section(tenant_id, sec.id)  # type: ignore

    async def update_section(
        self, tenant_id: uuid.UUID, section_id: uuid.UUID, data: Dict[str, Any]
    ) -> Optional[Section]:
        sec = await self.get_section(tenant_id, section_id)
        if not sec:
            return None
        await self._validate_section_type(tenant_id, data)
        for k, v in data.items():
            if v is not None:
                setattr(sec, k, v)
        await self.session.flush()
        return await self.get_section(tenant_id, section_id)

    async def _validate_section_type(self, tenant_id: uuid.UUID, data: Dict[str, Any], *, creating: bool = False) -> None:
        institution_type = await registered_institution_type(self.session, tenant_id)
        if institution_type == InstitutionType.SCHOOL:
            if any(data.get(key) for key in ("course_id", "semester_id", "batch_id")) or (creating and not data.get("class_id")):
                raise BadRequestException("School sections must belong to a class.")
        elif data.get("class_id") or (creating and not data.get("course_id")):
            raise BadRequestException("College sections must belong to a course.")

    async def delete_section(self, tenant_id: uuid.UUID, section_id: uuid.UUID) -> bool:
        sec = await self.get_section(tenant_id, section_id)
        if not sec:
            return False
        sec.is_deleted = True
        sec.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    # ── 7. Courses ────────────────────────────────────────────────────────────

    async def list_courses(
        self,
        tenant_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        degree_id: Optional[uuid.UUID] = None,
    ) -> List[Course]:
        stmt = (
            select(Course)
            .options(
                selectinload(Course.department),
                selectinload(Course.degree),
                selectinload(Course.coordinator_teacher).selectinload(TeacherProfile.user),
                selectinload(Course.semesters),
                selectinload(Course.batches),
            )
            .where(
                Course.tenant_id == tenant_id,
                Course.is_deleted.is_(False),
            )
            .order_by(Course.name.asc())
        )
        if department_id:
            stmt = stmt.where(Course.department_id == department_id)
        if degree_id:
            stmt = stmt.where(Course.degree_id == degree_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_course(
        self, tenant_id: uuid.UUID, course_id: uuid.UUID
    ) -> Optional[Course]:
        stmt = (
            select(Course)
            .options(
                selectinload(Course.department),
                selectinload(Course.degree),
                selectinload(Course.coordinator_teacher).selectinload(TeacherProfile.user),
                selectinload(Course.semesters),
                selectinload(Course.batches),
            )
            .where(
                Course.id == course_id,
                Course.tenant_id == tenant_id,
                Course.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_course(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> Course:
        course = Course(tenant_id=tenant_id, **data)
        self.session.add(course)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            if "uq_courses_tenant_code" not in str(exc.orig):
                raise
            await self.session.rollback()
            raise ConflictException("A course with this code already exists, including deleted courses.") from exc
        return await self.get_course(tenant_id, course.id)  # type: ignore

    async def update_course(
        self, tenant_id: uuid.UUID, course_id: uuid.UUID, data: Dict[str, Any]
    ) -> Optional[Course]:
        course = await self.get_course(tenant_id, course_id)
        if not course:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(course, k, v)
        await self.session.flush()
        return await self.get_course(tenant_id, course_id)

    async def delete_course(self, tenant_id: uuid.UUID, course_id: uuid.UUID) -> bool:
        course = await self.get_course(tenant_id, course_id)
        if not course:
            return False
        course.is_deleted = True
        course.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    # ── 8. College Semesters ──────────────────────────────────────────────────

    async def list_semesters(
        self, tenant_id: uuid.UUID, course_id: Optional[uuid.UUID] = None
    ) -> List[CollegeSemester]:
        stmt = (
            select(CollegeSemester)
            .options(selectinload(CollegeSemester.course))
            .where(
                CollegeSemester.tenant_id == tenant_id,
                CollegeSemester.is_deleted.is_(False),
            )
            .order_by(CollegeSemester.semester_number.asc())
        )
        if course_id:
            stmt = stmt.where(CollegeSemester.course_id == course_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_semester(
        self, tenant_id: uuid.UUID, semester_id: uuid.UUID
    ) -> Optional[CollegeSemester]:
        stmt = (
            select(CollegeSemester)
            .options(selectinload(CollegeSemester.course))
            .where(
                CollegeSemester.id == semester_id,
                CollegeSemester.tenant_id == tenant_id,
                CollegeSemester.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_semester(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> CollegeSemester:
        sem = CollegeSemester(tenant_id=tenant_id, **data)
        self.session.add(sem)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            if "uq_college_semesters_tenant_course_sem" not in str(exc.orig):
                raise
            await self.session.rollback()
            raise ConflictException("This semester already exists for the selected course. Edit the existing semester instead.") from exc
        return await self.get_semester(tenant_id, sem.id)  # type: ignore

    async def update_semester(
        self, tenant_id: uuid.UUID, semester_id: uuid.UUID, data: Dict[str, Any]
    ) -> Optional[CollegeSemester]:
        sem = await self.get_semester(tenant_id, semester_id)
        if not sem:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(sem, k, v)
        await self.session.flush()
        return await self.get_semester(tenant_id, semester_id)

    # ── 9. College Batches ────────────────────────────────────────────────────

    async def list_batches(
        self, tenant_id: uuid.UUID, course_id: Optional[uuid.UUID] = None
    ) -> List[CollegeBatch]:
        stmt = (
            select(CollegeBatch)
            .options(selectinload(CollegeBatch.course))
            .where(
                CollegeBatch.tenant_id == tenant_id,
                CollegeBatch.is_deleted.is_(False),
            )
            .order_by(CollegeBatch.start_year.desc())
        )
        if course_id:
            stmt = stmt.where(CollegeBatch.course_id == course_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_batch(
        self, tenant_id: uuid.UUID, batch_id: uuid.UUID
    ) -> Optional[CollegeBatch]:
        stmt = (
            select(CollegeBatch)
            .options(selectinload(CollegeBatch.course))
            .where(
                CollegeBatch.id == batch_id,
                CollegeBatch.tenant_id == tenant_id,
                CollegeBatch.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_batch(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> CollegeBatch:
        batch = CollegeBatch(tenant_id=tenant_id, **data)
        self.session.add(batch)
        await self.session.flush()
        return await self.get_batch(tenant_id, batch.id)  # type: ignore

    async def update_batch(
        self, tenant_id: uuid.UUID, batch_id: uuid.UUID, data: Dict[str, Any]
    ) -> Optional[CollegeBatch]:
        batch = await self.get_batch(tenant_id, batch_id)
        if not batch:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(batch, k, v)
        await self.session.flush()
        return await self.get_batch(tenant_id, batch_id)

    # ── 10. Subjects ──────────────────────────────────────────────────────────

    async def list_subjects(
        self,
        tenant_id: uuid.UUID,
        department_id: Optional[uuid.UUID] = None,
        subject_type: Optional[str] = None,
    ) -> List[Subject]:
        stmt = (
            select(Subject)
            .options(selectinload(Subject.department))
            .where(
                Subject.tenant_id == tenant_id,
                Subject.is_deleted.is_(False),
            )
            .order_by(Subject.name.asc())
        )
        if department_id:
            stmt = stmt.where(Subject.department_id == department_id)
        if subject_type:
            stmt = stmt.where(Subject.subject_type == subject_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_subject(
        self, tenant_id: uuid.UUID, subject_id: uuid.UUID
    ) -> Optional[Subject]:
        stmt = (
            select(Subject)
            .options(selectinload(Subject.department))
            .where(
                Subject.id == subject_id,
                Subject.tenant_id == tenant_id,
                Subject.is_deleted.is_(False),
            )
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_subject(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> Subject:
        subj = Subject(tenant_id=tenant_id, **data)
        self.session.add(subj)
        await self.session.flush()
        return await self.get_subject(tenant_id, subj.id)  # type: ignore

    async def update_subject(
        self, tenant_id: uuid.UUID, subject_id: uuid.UUID, data: Dict[str, Any]
    ) -> Optional[Subject]:
        subj = await self.get_subject(tenant_id, subject_id)
        if not subj:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(subj, k, v)
        await self.session.flush()
        return await self.get_subject(tenant_id, subject_id)

    async def delete_subject(self, tenant_id: uuid.UUID, subject_id: uuid.UUID) -> bool:
        subj = await self.get_subject(tenant_id, subject_id)
        if not subj:
            return False
        subj.is_deleted = True
        subj.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    # ── 11. Subject Mappings ──────────────────────────────────────────────────

    async def list_subject_mappings(
        self,
        tenant_id: uuid.UUID,
        session_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        semester_id: Optional[uuid.UUID] = None,
    ) -> List[AcademicSubjectMapping]:
        stmt = (
            select(AcademicSubjectMapping)
            .options(
                selectinload(AcademicSubjectMapping.subject),
                selectinload(AcademicSubjectMapping.school_class),
                selectinload(AcademicSubjectMapping.course),
                selectinload(AcademicSubjectMapping.semester),
            )
            .where(
                AcademicSubjectMapping.tenant_id == tenant_id,
                AcademicSubjectMapping.is_deleted.is_(False),
            )
            .order_by(AcademicSubjectMapping.created_at.desc())
        )
        if session_id:
            stmt = stmt.where(AcademicSubjectMapping.academic_session_id == session_id)
        if class_id:
            stmt = stmt.where(AcademicSubjectMapping.class_id == class_id)
        if course_id:
            stmt = stmt.where(AcademicSubjectMapping.course_id == course_id)
        if semester_id:
            stmt = stmt.where(AcademicSubjectMapping.semester_id == semester_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_subject_mapping(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> AcademicSubjectMapping:
        mapping = AcademicSubjectMapping(tenant_id=tenant_id, **data)
        self.session.add(mapping)
        await self.session.flush()
        stmt = (
            select(AcademicSubjectMapping)
            .options(
                selectinload(AcademicSubjectMapping.subject),
                selectinload(AcademicSubjectMapping.school_class),
                selectinload(AcademicSubjectMapping.course),
                selectinload(AcademicSubjectMapping.semester),
            )
            .where(AcademicSubjectMapping.id == mapping.id)
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()  # type: ignore

    async def delete_subject_mapping(
        self, tenant_id: uuid.UUID, mapping_id: uuid.UUID
    ) -> bool:
        stmt = select(AcademicSubjectMapping).where(
            AcademicSubjectMapping.id == mapping_id,
            AcademicSubjectMapping.tenant_id == tenant_id,
            AcademicSubjectMapping.is_deleted.is_(False),
        )
        res = await self.session.execute(stmt)
        obj = res.scalars().first()
        if not obj:
            return False
        obj.is_deleted = True
        obj.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    # ── 12. Teacher Subject Mappings ──────────────────────────────────────────

    async def list_teacher_subject_mappings(
        self,
        tenant_id: uuid.UUID,
        teacher_id: Optional[uuid.UUID] = None,
        session_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
    ) -> List[TeacherSubjectMapping]:
        stmt = (
            select(TeacherSubjectMapping)
            .options(
                selectinload(TeacherSubjectMapping.teacher).selectinload(TeacherProfile.user),
                selectinload(TeacherSubjectMapping.subject),
                selectinload(TeacherSubjectMapping.school_class),
                selectinload(TeacherSubjectMapping.section),
                selectinload(TeacherSubjectMapping.course),
                selectinload(TeacherSubjectMapping.semester),
            )
            .where(
                TeacherSubjectMapping.tenant_id == tenant_id,
                TeacherSubjectMapping.is_deleted.is_(False),
            )
            .order_by(TeacherSubjectMapping.created_at.desc())
        )
        if teacher_id:
            stmt = stmt.where(TeacherSubjectMapping.teacher_id == teacher_id)
        if session_id:
            stmt = stmt.where(TeacherSubjectMapping.academic_session_id == session_id)
        if class_id:
            stmt = stmt.where(TeacherSubjectMapping.class_id == class_id)
        if course_id:
            stmt = stmt.where(TeacherSubjectMapping.course_id == course_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_teacher_subject_mapping(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> TeacherSubjectMapping:
        mapping = TeacherSubjectMapping(tenant_id=tenant_id, **data)
        self.session.add(mapping)
        await self.session.flush()
        stmt = (
            select(TeacherSubjectMapping)
            .options(
                selectinload(TeacherSubjectMapping.teacher).selectinload(TeacherProfile.user),
                selectinload(TeacherSubjectMapping.subject),
                selectinload(TeacherSubjectMapping.school_class),
                selectinload(TeacherSubjectMapping.section),
                selectinload(TeacherSubjectMapping.course),
                selectinload(TeacherSubjectMapping.semester),
            )
            .where(TeacherSubjectMapping.id == mapping.id)
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()  # type: ignore

    async def delete_teacher_subject_mapping(
        self, tenant_id: uuid.UUID, mapping_id: uuid.UUID
    ) -> bool:
        stmt = select(TeacherSubjectMapping).where(
            TeacherSubjectMapping.id == mapping_id,
            TeacherSubjectMapping.tenant_id == tenant_id,
            TeacherSubjectMapping.is_deleted.is_(False),
        )
        res = await self.session.execute(stmt)
        obj = res.scalars().first()
        if not obj:
            return False
        obj.is_deleted = True
        obj.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    # ── 13. Student Enrollments (Common Model) ────────────────────────────────

    async def list_enrollments(
        self,
        tenant_id: uuid.UUID,
        session_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
    ) -> List[StudentAcademicEnrollment]:
        stmt = (
            select(StudentAcademicEnrollment)
            .options(
                selectinload(StudentAcademicEnrollment.student).selectinload(StudentProfile.user),
                selectinload(StudentAcademicEnrollment.academic_session),
                selectinload(StudentAcademicEnrollment.school_detail).selectinload(SchoolEnrollmentDetail.school_class),
                selectinload(StudentAcademicEnrollment.school_detail).selectinload(SchoolEnrollmentDetail.section),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.course),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.department),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.faculty),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.degree),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.batch),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.semester),
            )
            .where(
                StudentAcademicEnrollment.tenant_id == tenant_id,
                StudentAcademicEnrollment.is_deleted.is_(False),
            )
            .order_by(StudentAcademicEnrollment.enrollment_date.desc())
        )
        if session_id:
            stmt = stmt.where(StudentAcademicEnrollment.academic_session_id == session_id)
        if status:
            stmt = stmt.where(StudentAcademicEnrollment.status == status)
        result = await self.session.execute(stmt)
        enrollments = list(result.scalars().all())

        if class_id:
            enrollments = [e for e in enrollments if e.school_detail and e.school_detail.class_id == class_id]
        if course_id:
            enrollments = [e for e in enrollments if e.college_detail and e.college_detail.course_id == course_id]

        return enrollments

    async def get_enrollment(
        self, tenant_id: uuid.UUID, enrollment_id: uuid.UUID
    ) -> Optional[StudentAcademicEnrollment]:
        stmt = (
            select(StudentAcademicEnrollment)
            .options(
                selectinload(StudentAcademicEnrollment.student).selectinload(StudentProfile.user),
                selectinload(StudentAcademicEnrollment.academic_session),
                selectinload(StudentAcademicEnrollment.school_detail).selectinload(SchoolEnrollmentDetail.school_class),
                selectinload(StudentAcademicEnrollment.school_detail).selectinload(SchoolEnrollmentDetail.section),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.course),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.department),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.faculty),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.degree),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.batch),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.semester),
            )
            .where(
                StudentAcademicEnrollment.id == enrollment_id,
                StudentAcademicEnrollment.tenant_id == tenant_id,
                StudentAcademicEnrollment.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_enrollment(
        self,
        tenant_id: uuid.UUID,
        data: Dict[str, Any],
        school_data: Optional[Dict[str, Any]] = None,
        college_data: Optional[Dict[str, Any]] = None,
    ) -> StudentAcademicEnrollment:
        enrollment = StudentAcademicEnrollment(tenant_id=tenant_id, **data)
        self.session.add(enrollment)
        await self.session.flush()

        if school_data:
            sch_det = SchoolEnrollmentDetail(
                tenant_id=tenant_id,
                enrollment_id=enrollment.id,
                **school_data,
            )
            self.session.add(sch_det)
        elif college_data:
            col_det = CollegeEnrollmentDetail(
                tenant_id=tenant_id,
                enrollment_id=enrollment.id,
                **college_data,
            )
            self.session.add(col_det)

        await self.session.flush()
        return await self.get_enrollment(tenant_id, enrollment.id)  # type: ignore

    async def get_student_enrollments(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID
    ) -> List[StudentAcademicEnrollment]:
        stmt = (
            select(StudentAcademicEnrollment)
            .options(
                selectinload(StudentAcademicEnrollment.student).selectinload(StudentProfile.user),
                selectinload(StudentAcademicEnrollment.academic_session),
                selectinload(StudentAcademicEnrollment.school_detail).selectinload(SchoolEnrollmentDetail.school_class),
                selectinload(StudentAcademicEnrollment.school_detail).selectinload(SchoolEnrollmentDetail.section),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.course),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.department),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.faculty),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.degree),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.batch),
                selectinload(StudentAcademicEnrollment.college_detail).selectinload(CollegeEnrollmentDetail.semester),
            )
            .where(
                StudentAcademicEnrollment.tenant_id == tenant_id,
                StudentAcademicEnrollment.student_id == student_id,
                StudentAcademicEnrollment.is_deleted.is_(False),
            )
            .order_by(StudentAcademicEnrollment.enrollment_date.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── 14. Student Promotions ────────────────────────────────────────────────

    async def create_promotion(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> StudentPromotion:
        promo = StudentPromotion(tenant_id=tenant_id, **data)
        self.session.add(promo)
        await self.session.flush()
        stmt = (
            select(StudentPromotion)
            .options(selectinload(StudentPromotion.student).selectinload(StudentProfile.user))
            .where(StudentPromotion.id == promo.id)
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()  # type: ignore

    async def get_student_promotions(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID
    ) -> List[StudentPromotion]:
        stmt = (
            select(StudentPromotion)
            .options(selectinload(StudentPromotion.student).selectinload(StudentProfile.user))
            .where(
                StudentPromotion.tenant_id == tenant_id,
                StudentPromotion.student_id == student_id,
            )
            .order_by(StudentPromotion.promotion_date.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── 15. Academic Hierarchy ────────────────────────────────────────────────

    async def get_or_create_hierarchy(
        self, tenant_id: uuid.UUID
    ) -> AcademicHierarchy:
        institution_type = await registered_institution_type(self.session, tenant_id)
        is_college = institution_type == InstitutionType.COLLEGE
        stmt = select(AcademicHierarchy).where(AcademicHierarchy.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        hier = result.scalars().first()
        if not hier:
            hier = AcademicHierarchy(
                tenant_id=tenant_id,
                institution_type=institution_type.value,
                academic_system="SEMESTER" if is_college else "ANNUAL",
                has_departments=is_college,
                has_faculties=False,
                has_batches=is_college,
                has_sections=True,
                grading_system="PERCENTAGE",
                pass_percentage=40.0,
                allow_cross_department_electives=False,
                max_electives_per_student=2,
                settings={},
            )
            self.session.add(hier)
            await self.session.flush()
        elif hier.institution_type != institution_type.value:
            hier.institution_type = institution_type.value
        return hier

    async def update_hierarchy(
        self, tenant_id: uuid.UUID, data: Dict[str, Any]
    ) -> AcademicHierarchy:
        hier = await self.get_or_create_hierarchy(tenant_id)
        requested_type = data.get("institution_type")
        if requested_type is not None and requested_type != hier.institution_type:
            raise BadRequestException("The registered institution type cannot be changed.")
        for k, v in data.items():
            if k != "institution_type" and v is not None:
                setattr(hier, k, v)
        await self.session.flush()
        return hier


# Dedicated class for backward compatibility with early multi-tenancy tests
class AcademicSessionRepository:
    def __init__(self, session: AsyncSession, tenant_id: Optional[uuid.UUID] = None):
        self.session = session
        self.tenant_id = tenant_id

    async def create(self, **kwargs) -> AcademicSession:
        obj = AcademicSession(tenant_id=self.tenant_id, **kwargs)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_by_id(self, session_id: uuid.UUID) -> Optional[AcademicSession]:
        stmt = select(AcademicSession).where(
            AcademicSession.id == session_id,
            AcademicSession.tenant_id == self.tenant_id,
            AcademicSession.is_deleted.is_(False),
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list(self) -> List[AcademicSession]:
        stmt = (
            select(AcademicSession)
            .where(
                AcademicSession.tenant_id == self.tenant_id,
                AcademicSession.is_deleted.is_(False),
            )
            .order_by(AcademicSession.start_date.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update(self, session_id: uuid.UUID, **kwargs) -> Optional[AcademicSession]:
        obj = await self.get_by_id(session_id)
        if not obj:
            return None
        for k, v in kwargs.items():
            setattr(obj, k, v)
        await self.session.flush()
        return obj

    async def soft_delete(self, session_id: uuid.UUID) -> bool:
        obj = await self.get_by_id(session_id)
        if not obj:
            return False
        obj.is_deleted = True
        obj.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True



