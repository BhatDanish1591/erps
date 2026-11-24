from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException, BadRequestException
from app.dependencies.tenant import get_registered_institution_type, require_institution_type
from app.models.enums import InstitutionType
from app.models.academic import AcademicSession, CollegeSemester, Course, Department, SchoolClass, Section, Subject
from app.models.user import User
from app.permissions.rbac import get_active_tenant_id, get_current_user, get_current_user_claims, require_any_role
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
from app.services.academic_service import AcademicService
from app.services.staff_access_service import load_staff_access

router = APIRouter(prefix="/academics", tags=["Academic Management"])


async def delete_academic_record(session: AsyncSession, model: Any, tenant_id: uuid.UUID, record_id: uuid.UUID) -> None:
    record = await session.scalar(select(model).where(
        model.id == record_id, model.tenant_id == tenant_id, model.is_deleted.is_(False),
    ).with_for_update())
    if not record:
        raise AppException(404, "NOT_FOUND", "Academic record not found.")
    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)
    if isinstance(record, AcademicSession):
        record.is_current = False
    await session.commit()


@router.delete("/sessions/{session_id}")
async def delete_academic_session(
    session_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await delete_academic_record(session, AcademicSession, tenant_id, session_id)
    return {"success": True, "message": "Academic session deleted."}


@router.patch("/semesters/{semester_id}", dependencies=[Depends(require_institution_type(InstitutionType.COLLEGE))])
async def update_semester(
    semester_id: uuid.UUID, payload: CollegeSemesterUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    semester = await session.scalar(select(CollegeSemester).where(
        CollegeSemester.id == semester_id, CollegeSemester.tenant_id == tenant_id,
        CollegeSemester.is_deleted.is_(False),
    ).with_for_update())
    if not semester:
        raise AppException(404, "NOT_FOUND", "Semester not found.")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("credits_required") is not None and not 1 <= changes["credits_required"] <= 100:
        raise BadRequestException("Credits must be between 1 and 100.")
    if "academic_session_id" in changes and changes["academic_session_id"] is not None:
        valid_session = await session.scalar(select(AcademicSession.id).where(
            AcademicSession.id == changes["academic_session_id"], AcademicSession.tenant_id == tenant_id,
            AcademicSession.is_deleted.is_(False),
        ))
        if not valid_session:
            raise BadRequestException("Academic session not found.")
    for field, value in changes.items():
        if value is not None or field == "academic_session_id":
            setattr(semester, field, value)
    await session.commit()
    return {"success": True, "message": "Semester updated."}


@router.delete("/semesters/{semester_id}", dependencies=[Depends(require_institution_type(InstitutionType.COLLEGE))])
async def delete_semester(
    semester_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await delete_academic_record(session, CollegeSemester, tenant_id, semester_id)
    return {"success": True, "message": "Semester deleted."}


@router.get("/staff-overview")
async def staff_academic_overview(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    user: User = Depends(require_any_role(["PRINCIPAL", "HOD", "INSTITUTION_ADMIN"])),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
    institution_type: InstitutionType = Depends(get_registered_institution_type),
) -> Dict[str, Any]:
    access = await load_staff_access(session, tenant_id, user.id, "SUPER_ADMIN" if user.is_superadmin else claims["role"])
    if institution_type == InstitutionType.SCHOOL:
        if access.department_ids is not None:
            return {"success": True, "data": []}
        classes = await session.execute(
            select(SchoolClass.id, SchoolClass.name, SchoolClass.code)
            .where(SchoolClass.tenant_id == tenant_id, SchoolClass.is_deleted.is_(False))
            .order_by(SchoolClass.order_index, SchoolClass.name)
        )
        groups = {row["id"]: {**row, "sections": []} for row in classes.mappings()}
        sections = await session.execute(
            select(Section.id, Section.name, Section.class_id)
            .where(Section.tenant_id == tenant_id, Section.is_deleted.is_(False), Section.class_id.in_(groups))
            .order_by(Section.name)
        )
        for section_id, name, class_id in sections:
            groups[class_id]["sections"].append({"id": section_id, "name": name})
        return {"success": True, "data": list(groups.values())}
    departments = select(Department.id, Department.name, Department.code).where(
        Department.tenant_id == tenant_id, Department.is_deleted.is_(False)
    )
    if access.department_ids is not None:
        departments = departments.where(Department.id.in_(access.department_ids))
    rows = (await session.execute(departments.order_by(Department.name))).mappings().all()
    catalog = {row["id"]: {**row, "courses": [], "subjects": []} for row in rows}
    for model, key in ((Course, "courses"), (Subject, "subjects")):
        items = await session.execute(
            select(model.id, model.department_id, model.name, model.code)
            .where(model.tenant_id == tenant_id, model.is_deleted.is_(False), model.department_id.in_(catalog))
            .order_by(model.name, model.id)
        )
        for item_id, department_id, name, code in items:
            catalog[department_id][key].append({"id": item_id, "name": name, "code": code})
    return {"success": True, "data": list(catalog.values())}


# ── 1. Academic Sessions ──────────────────────────────────────────────────────

@router.get("/sessions", response_model=Dict[str, Any])
async def list_academic_sessions(
    is_current: Optional[bool] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "PRINCIPAL", "HOD", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    items = await svc.list_sessions(tenant_id, is_current=is_current)
    return {"success": True, "data": [i.model_dump() for i in items]}


@router.post("/sessions", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_academic_session(
    payload: AcademicSessionCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.create_session(tenant_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Academic session created successfully."}


@router.patch("/sessions/{session_id}", response_model=Dict[str, Any])
async def update_academic_session(
    session_id: uuid.UUID,
    payload: AcademicSessionUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.update_session(tenant_id, session_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Academic session updated successfully."}


# ── 2. Academic Faculties ─────────────────────────────────────────────────────

@router.get("/faculties", response_model=Dict[str, Any])
async def list_faculties(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
    institution_type: InstitutionType = Depends(get_registered_institution_type),
) -> Dict[str, Any]:
    if institution_type != InstitutionType.COLLEGE:
        return {"success": True, "data": []}
    svc = AcademicService(session)
    items = await svc.list_faculties(tenant_id)
    return {"success": True, "data": [i.model_dump() for i in items]}


@router.post("/faculties", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_institution_type(InstitutionType.COLLEGE))])
async def create_faculty(
    payload: AcademicFacultyCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.create_faculty(tenant_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Academic faculty created successfully."}


@router.patch("/faculties/{faculty_id}", response_model=Dict[str, Any], dependencies=[Depends(require_institution_type(InstitutionType.COLLEGE))])
async def update_faculty(
    faculty_id: uuid.UUID,
    payload: AcademicFacultyUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.update_faculty(tenant_id, faculty_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Academic faculty updated successfully."}


@router.delete("/faculties/{faculty_id}", response_model=Dict[str, Any], dependencies=[Depends(require_institution_type(InstitutionType.COLLEGE))])
async def delete_faculty(
    faculty_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    await svc.delete_faculty(tenant_id, faculty_id)
    return {"success": True, "message": "Academic faculty deleted successfully."}


# ── 3. Academic Degrees ───────────────────────────────────────────────────────

@router.get("/degrees", response_model=Dict[str, Any])
async def list_degrees(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
    institution_type: InstitutionType = Depends(get_registered_institution_type),
) -> Dict[str, Any]:
    if institution_type != InstitutionType.COLLEGE:
        return {"success": True, "data": []}
    svc = AcademicService(session)
    items = await svc.list_degrees(tenant_id)
    return {"success": True, "data": [i.model_dump() for i in items]}


@router.post("/degrees", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_institution_type(InstitutionType.COLLEGE))])
async def create_degree(
    payload: AcademicDegreeCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.create_degree(tenant_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Academic degree created successfully."}


# ── 4. Departments ────────────────────────────────────────────────────────────

@router.get("/departments", response_model=Dict[str, Any])
async def list_departments(
    faculty_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "PRINCIPAL", "HOD", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
    institution_type: InstitutionType = Depends(get_registered_institution_type),
) -> Dict[str, Any]:
    if institution_type != InstitutionType.COLLEGE:
        return {"success": True, "data": []}
    svc = AcademicService(session)
    items = await svc.list_departments(tenant_id, faculty_id=faculty_id)
    return {"success": True, "data": [i.model_dump() for i in items]}


@router.post("/departments", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_institution_type(InstitutionType.COLLEGE))])
async def create_department(
    payload: DepartmentCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.create_department(tenant_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Department created successfully."}


@router.patch("/departments/{department_id}", response_model=Dict[str, Any], dependencies=[Depends(require_institution_type(InstitutionType.COLLEGE))])
async def update_department(
    department_id: uuid.UUID,
    payload: DepartmentUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.update_department(tenant_id, department_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Department updated successfully."}


@router.delete("/departments/{department_id}", response_model=Dict[str, Any], dependencies=[Depends(require_institution_type(InstitutionType.COLLEGE))])
async def delete_department(
    department_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    await svc.delete_department(tenant_id, department_id)
    return {"success": True, "message": "Department deleted successfully."}


# ── 5. School Classes ─────────────────────────────────────────────────────────

@router.get("/classes", response_model=Dict[str, Any])
async def list_classes(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "PRINCIPAL", "HOD", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
    institution_type: InstitutionType = Depends(get_registered_institution_type),
) -> Dict[str, Any]:
    if institution_type != InstitutionType.SCHOOL:
        return {"success": True, "data": []}
    svc = AcademicService(session)
    items = await svc.list_classes(tenant_id)
    return {"success": True, "data": [i.model_dump() for i in items]}


@router.post("/classes", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_institution_type(InstitutionType.SCHOOL))])
async def create_class(
    payload: SchoolClassCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.create_class(tenant_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Class created successfully."}


@router.patch("/classes/{class_id}", response_model=Dict[str, Any], dependencies=[Depends(require_institution_type(InstitutionType.SCHOOL))])
async def update_class(
    class_id: uuid.UUID,
    payload: SchoolClassUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.update_class(tenant_id, class_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Class updated successfully."}


@router.delete("/classes/{class_id}", response_model=Dict[str, Any], dependencies=[Depends(require_institution_type(InstitutionType.SCHOOL))])
async def delete_class(
    class_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    await svc.delete_class(tenant_id, class_id)
    return {"success": True, "message": "Class deleted successfully."}


# ── 6. Sections ───────────────────────────────────────────────────────────────

@router.get("/sections", response_model=Dict[str, Any])
async def list_sections(
    class_id: Optional[uuid.UUID] = Query(None),
    course_id: Optional[uuid.UUID] = Query(None),
    semester_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "PRINCIPAL", "HOD", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    items = await svc.list_sections(tenant_id, class_id=class_id, course_id=course_id, semester_id=semester_id)
    return {"success": True, "data": [i.model_dump() for i in items]}


@router.post("/sections", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_section(
    payload: SectionCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.create_section(tenant_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Section created successfully."}


@router.patch("/sections/{section_id}", response_model=Dict[str, Any])
async def update_section(
    section_id: uuid.UUID,
    payload: SectionUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.update_section(tenant_id, section_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Section updated successfully."}


@router.delete("/sections/{section_id}", response_model=Dict[str, Any])
async def delete_section(
    section_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    await svc.delete_section(tenant_id, section_id)
    return {"success": True, "message": "Section deleted successfully."}


# ── 7. Courses ────────────────────────────────────────────────────────────────

@router.get("/courses", response_model=Dict[str, Any])
async def list_courses(
    department_id: Optional[uuid.UUID] = Query(None),
    degree_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "PRINCIPAL", "HOD", "TEACHER", "STUDENT"])),
    session: AsyncSession = Depends(get_db),
    institution_type: InstitutionType = Depends(get_registered_institution_type),
) -> Dict[str, Any]:
    if institution_type != InstitutionType.COLLEGE:
        return {"success": True, "data": []}
    svc = AcademicService(session)
    items = await svc.list_courses(tenant_id, department_id=department_id, degree_id=degree_id)
    return {"success": True, "data": [i.model_dump() for i in items]}


@router.post("/courses", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_institution_type(InstitutionType.COLLEGE))])
async def create_course(
    payload: CourseCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.create_course(tenant_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Course created successfully with default semesters."}


@router.patch("/courses/{course_id}", response_model=Dict[str, Any], dependencies=[Depends(require_institution_type(InstitutionType.COLLEGE))])
async def update_course(
    course_id: uuid.UUID,
    payload: CourseUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.update_course(tenant_id, course_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Course updated successfully."}


@router.delete("/courses/{course_id}", response_model=Dict[str, Any], dependencies=[Depends(require_institution_type(InstitutionType.COLLEGE))])
async def delete_course(
    course_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    await svc.delete_course(tenant_id, course_id)
    return {"success": True, "message": "Course deleted successfully."}


# ── 8. College Semesters ──────────────────────────────────────────────────────

@router.get("/semesters", response_model=Dict[str, Any])
async def list_semesters(
    course_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "PRINCIPAL", "HOD", "TEACHER", "STUDENT"])),
    session: AsyncSession = Depends(get_db),
    institution_type: InstitutionType = Depends(get_registered_institution_type),
) -> Dict[str, Any]:
    if institution_type != InstitutionType.COLLEGE:
        return {"success": True, "data": []}
    svc = AcademicService(session)
    items = await svc.list_semesters(tenant_id, course_id=course_id)
    return {"success": True, "data": [i.model_dump() for i in items]}


@router.post("/semesters", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_institution_type(InstitutionType.COLLEGE))])
async def create_semester(
    payload: CollegeSemesterCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.create_semester(tenant_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Semester created successfully."}


# ── 9. College Batches ────────────────────────────────────────────────────────

@router.get("/batches", response_model=Dict[str, Any])
async def list_batches(
    course_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT"])),
    session: AsyncSession = Depends(get_db),
    institution_type: InstitutionType = Depends(get_registered_institution_type),
) -> Dict[str, Any]:
    if institution_type != InstitutionType.COLLEGE:
        return {"success": True, "data": []}
    svc = AcademicService(session)
    items = await svc.list_batches(tenant_id, course_id=course_id)
    return {"success": True, "data": [i.model_dump() for i in items]}


@router.post("/batches", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_institution_type(InstitutionType.COLLEGE))])
async def create_batch(
    payload: CollegeBatchCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.create_batch(tenant_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Batch created successfully."}


# ── 10. Subjects ──────────────────────────────────────────────────────────────

@router.get("/subjects", response_model=Dict[str, Any])
async def list_subjects(
    department_id: Optional[uuid.UUID] = Query(None),
    subject_type: Optional[str] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    items = await svc.list_subjects(tenant_id, department_id=department_id, subject_type=subject_type)
    return {"success": True, "data": [i.model_dump() for i in items]}


@router.post("/subjects", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_subject(
    payload: SubjectCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.create_subject(tenant_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Subject created successfully."}


@router.patch("/subjects/{subject_id}", response_model=Dict[str, Any])
async def update_subject(
    subject_id: uuid.UUID,
    payload: SubjectUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.update_subject(tenant_id, subject_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Subject updated successfully."}


@router.delete("/subjects/{subject_id}", response_model=Dict[str, Any])
async def delete_subject(
    subject_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    await svc.delete_subject(tenant_id, subject_id)
    return {"success": True, "message": "Subject deleted successfully."}


# ── 11. Academic Subject Mappings ─────────────────────────────────────────────

@router.get("/subject-mappings", response_model=Dict[str, Any])
async def list_subject_mappings(
    session_id: Optional[uuid.UUID] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    course_id: Optional[uuid.UUID] = Query(None),
    semester_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    items = await svc.list_subject_mappings(
        tenant_id, session_id=session_id, class_id=class_id, course_id=course_id, semester_id=semester_id
    )
    return {"success": True, "data": [i.model_dump() for i in items]}


@router.post("/subject-mappings", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_subject_mapping(
    payload: AcademicSubjectMappingCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.create_subject_mapping(tenant_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Subject mapped to class/course successfully."}


@router.delete("/subject-mappings/{mapping_id}", response_model=Dict[str, Any])
async def delete_subject_mapping(
    mapping_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    await svc.delete_subject_mapping(tenant_id, mapping_id)
    return {"success": True, "message": "Subject mapping removed successfully."}


# ── 12. Teacher Subject Mappings ──────────────────────────────────────────────

@router.get("/teacher-subject-mappings", response_model=Dict[str, Any])
async def list_teacher_subject_mappings(
    teacher_id: Optional[uuid.UUID] = Query(None),
    session_id: Optional[uuid.UUID] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    course_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    items = await svc.list_teacher_subject_mappings(
        tenant_id, teacher_id=teacher_id, session_id=session_id, class_id=class_id, course_id=course_id
    )
    return {"success": True, "data": [i.model_dump() for i in items]}


@router.post("/teacher-subject-mappings", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_teacher_subject_mapping(
    payload: TeacherSubjectMappingCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.create_teacher_subject_mapping(tenant_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Teacher assigned to subject successfully."}


@router.delete("/teacher-subject-mappings/{mapping_id}", response_model=Dict[str, Any])
async def delete_teacher_subject_mapping(
    mapping_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    await svc.delete_teacher_subject_mapping(tenant_id, mapping_id)
    return {"success": True, "message": "Teacher subject mapping removed successfully."}


# ── 13. Student Enrollments (Common Model) ────────────────────────────────────

@router.get("/enrollments", response_model=Dict[str, Any])
async def list_enrollments(
    session_id: Optional[uuid.UUID] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    course_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    items = await svc.list_enrollments(
        tenant_id, session_id=session_id, class_id=class_id, course_id=course_id, status=status_filter
    )
    return {"success": True, "data": [i.model_dump() for i in items]}


@router.post("/enrollments", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_student_enrollment(
    payload: StudentEnrollmentCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
    institution_type: InstitutionType = Depends(get_registered_institution_type),
) -> Dict[str, Any]:
    if payload.enrollment_type != institution_type.value:
        raise BadRequestException("Enrollment type must match the registered institution type.")
    svc = AcademicService(session)
    res = await svc.create_enrollment(tenant_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Student enrolled successfully."}


# ── 14. Student Promotion ─────────────────────────────────────────────────────

@router.post("/promotions", response_model=Dict[str, Any])
async def promote_students(
    payload: CohortPromotionRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
    institution_type: InstitutionType = Depends(get_registered_institution_type),
) -> Dict[str, Any]:
    if payload.enrollment_type != institution_type.value:
        raise BadRequestException("Promotion type must match the registered institution type.")
    svc = AcademicService(session)
    records = await svc.promote_cohort(tenant_id, payload, performed_by_user_id=current_user.id)
    return {
        "success": True,
        "data": [r.model_dump() for r in records],
        "message": f"Successfully processed {payload.action.lower()} for {len(records)} student(s).",
    }


# ── 15. Academic Hierarchy Configuration ──────────────────────────────────────

@router.get("/hierarchy", response_model=Dict[str, Any])
async def get_academic_hierarchy(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.get_hierarchy(tenant_id)
    return {"success": True, "data": res.model_dump()}


@router.put("/hierarchy", response_model=Dict[str, Any])
async def update_academic_hierarchy(
    payload: AcademicHierarchyUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.update_hierarchy(tenant_id, payload)
    return {"success": True, "data": res.model_dump(), "message": "Academic hierarchy configuration updated successfully."}


# ── 16. Student Academic History ──────────────────────────────────────────────

@router.get("/students/{student_id}/history", response_model=Dict[str, Any])
async def get_student_academic_history(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    svc = AcademicService(session)
    res = await svc.get_student_history(tenant_id, student_id)
    return {"success": True, "data": res.model_dump()}
