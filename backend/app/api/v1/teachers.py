from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException, AuthorizationException
from app.dependencies.tenant import get_registered_institution_type
from app.models.enums import InstitutionType
from app.models.academic import Department, TeacherProfile
from app.models.auth import Membership, Role
from app.models.enums import MembershipStatus
from app.models.user import User
from app.permissions.rbac import ACADEMIC_STAFF_ROLES, get_active_tenant_id, get_current_user_claims, require_any_role
from app.schemas.teacher import (
    TeacherAssignmentCreateRequest,
    StaffAccessUpdate,
    TeacherAttendanceRecordRequest,
    TeacherAttendanceResponse,
    TeacherCreateRequest,
    TeacherDashboardSummary,
    TeacherDocumentCreateRequest,
    TeacherDocumentResponse,
    TeacherLeaveApplyRequest,
    TeacherLeaveResponse,
    TeacherLeaveReviewRequest,
    TeacherResponse,
    TeacherUpdateRequest,
    TimetableEntryCreateRequest,
    TimetableEntrySchema,
)
from app.services.teacher_service import TeacherService
from app.services.staff_access_service import StaffAccess, assign_staff_access, load_staff_access

router = APIRouter(prefix="/teachers", tags=["Teachers & Staff"])
STAFF_MANAGERS = ["INSTITUTION_ADMIN", "SUPER_ADMIN", "PRINCIPAL", "HOD"]


@router.delete("/{teacher_id}", response_model=Dict[str, Any])
async def delete_teacher(
    teacher_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    teacher = await session.scalar(select(TeacherProfile).where(
        TeacherProfile.id == teacher_id, TeacherProfile.tenant_id == tenant_id,
        TeacherProfile.is_deleted.is_(False),
    ).with_for_update())
    if not teacher:
        raise AppException(404, "TEACHER_NOT_FOUND", "Faculty member not found.")
    if teacher.user_id == current_user.id:
        raise AuthorizationException("You cannot remove your own faculty profile.")
    membership = await session.scalar(select(Membership).join(Role, Role.id == Membership.role_id).where(
        Membership.tenant_id == tenant_id, Membership.user_id == teacher.user_id,
        Membership.is_deleted.is_(False), Role.code.in_(ACADEMIC_STAFF_ROLES),
    ).with_for_update(of=Membership))
    if membership:
        membership.status = MembershipStatus.SUSPENDED
    teacher.is_deleted = True
    teacher.deleted_at = datetime.now(timezone.utc)
    teacher.status = "INACTIVE"
    await session.execute(update(Department).where(
        Department.tenant_id == tenant_id, Department.hod_teacher_id == teacher_id,
    ).values(hod_teacher_id=None))
    service = TeacherService(session)
    await service.repo.log_audit(tenant_id=tenant_id, user_id=current_user.id,
        action="TEACHER_DELETED", entity_id=str(teacher.id), changes={})
    await session.commit()
    return {"success": True, "message": "Faculty member removed."}


async def get_staff_access(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role([*STAFF_MANAGERS, "TEACHER"])),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
) -> StaffAccess:
    role = "SUPER_ADMIN" if current_user.is_superadmin else claims["role"]
    return await load_staff_access(session, tenant_id, current_user.id, role)


# ── Teacher Dedicated Dashboard Summary ───────────────────────────────────────
@router.get("/dashboard", response_model=Dict[str, Any])
async def get_teacher_dashboard(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role([*ACADEMIC_STAFF_ROLES, "INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TeacherService(session)
    summary = await service.get_teacher_dashboard(tenant_id=tenant_id, user_id=current_user.id)
    return {"success": True, "data": summary.model_dump()}


# ── List Teachers ─────────────────────────────────────────────────────────────
@router.get("", response_model=Dict[str, Any])
async def list_teachers(
    search: Optional[str] = Query(None, description="Search by name, email, employee ID, designation"),
    department_id: Optional[uuid.UUID] = Query(None, description="Filter by department"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, INACTIVE)"),
    employment_type: Optional[str] = Query(None, description="Filter by employment type"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    _: User = Depends(require_any_role(STAFF_MANAGERS)),
    access: StaffAccess = Depends(get_staff_access),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TeacherService(session)
    teachers, total = await service.list_teachers(
        tenant_id=tenant_id,
        search=search,
        department_id=department_id,
        status=status,
        employment_type=employment_type,
        page=page,
        size=size,
        access=access,
    )
    return {
        "success": True,
        "data": {
            "items": [t.model_dump() for t in teachers],
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size if size > 0 else 1,
        },
    }


@router.get("/departments")
async def list_staff_departments(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    _: User = Depends(require_any_role(STAFF_MANAGERS)),
    access: StaffAccess = Depends(get_staff_access),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    query = select(Department.id, Department.name).where(
        Department.tenant_id == tenant_id, Department.is_deleted.is_(False)
    )
    if access.department_ids is not None:
        query = query.where(Department.id.in_(access.department_ids))
    rows = await session.execute(query.order_by(Department.name))
    return {"success": True, "data": [{"id": department_id, "name": name} for department_id, name in rows]}


@router.get("/leaves")
async def list_pending_leaves(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    _: User = Depends(require_any_role(STAFF_MANAGERS)),
    access: StaffAccess = Depends(get_staff_access),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    leaves = await TeacherService(session).list_pending_leaves(tenant_id, access)
    return {"success": True, "data": [leave.model_dump() for leave in leaves]}


# ── Create Teacher ────────────────────────────────────────────────────────────
@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_teacher(
    payload: TeacherCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TeacherService(session)
    teacher = await service.create_teacher(
        tenant_id=tenant_id,
        payload=payload,
        actor_user_id=current_user.id,
    )
    return {
        "success": True,
        "data": teacher.model_dump(),
        "message": f"Teacher '{teacher.full_name}' created successfully with Employee ID '{teacher.employee_id}'.",
    }


# ── Review Leave Application ──────────────────────────────────────────────────
@router.put("/leaves/{leave_id}/review", response_model=Dict[str, Any])
async def review_leave(
    leave_id: uuid.UUID,
    payload: TeacherLeaveReviewRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(STAFF_MANAGERS)),
    access: StaffAccess = Depends(get_staff_access),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TeacherService(session)
    res = await service.review_leave(
        tenant_id=tenant_id,
        leave_id=leave_id,
        payload=payload,
        actor_user_id=current_user.id,
        access=access,
    )
    return {"success": True, "data": res.model_dump(), "message": f"Leave application {payload.status.lower()}."}


# ── Get Teacher Detail ────────────────────────────────────────────────────────
@router.get("/{teacher_id}", response_model=Dict[str, Any])
async def get_teacher_detail(
    teacher_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    access: StaffAccess = Depends(get_staff_access),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TeacherService(session)
    teacher = await service.get_teacher_detail(tenant_id=tenant_id, teacher_id=teacher_id, access=access)
    return {"success": True, "data": teacher.model_dump()}


@router.put("/{teacher_id}/access")
async def set_staff_access(
    teacher_id: uuid.UUID,
    payload: StaffAccessUpdate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    institution_type: InstitutionType = Depends(get_registered_institution_type),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if institution_type == InstitutionType.SCHOOL and payload.role == "HOD":
        raise AppException(422, "ROLE_UNAVAILABLE", "The HOD role is available for colleges.")
    await assign_staff_access(session, tenant_id, teacher_id, payload, current_user.id)
    return {"success": True, "data": {"role": payload.role}}


# ── Update Teacher Profile ────────────────────────────────────────────────────
@router.put("/{teacher_id}", response_model=Dict[str, Any])
async def update_teacher(
    teacher_id: uuid.UUID,
    payload: TeacherUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TeacherService(session)
    teacher = await service.update_teacher(
        tenant_id=tenant_id,
        teacher_id=teacher_id,
        payload=payload,
        actor_user_id=current_user.id,
    )
    return {"success": True, "data": teacher.model_dump(), "message": "Teacher profile updated successfully."}


# ── Assign Academic Resources (Classes, Subjects, Sections) ───────────────────
@router.post("/{teacher_id}/assignments", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def assign_resource(
    teacher_id: uuid.UUID,
    payload: TeacherAssignmentCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TeacherService(session)
    assignment = await service.assign_resource(
        tenant_id=tenant_id,
        teacher_id=teacher_id,
        payload=payload,
        actor_user_id=current_user.id,
    )
    return {
        "success": True,
        "data": {"id": str(assignment.id)},
        "message": "Academic resource assigned to teacher successfully.",
    }


# ── Remove Academic Resource Assignment ───────────────────────────────────────
@router.delete("/{teacher_id}/assignments/{assignment_id}", response_model=Dict[str, Any])
async def remove_assignment(
    teacher_id: uuid.UUID,
    assignment_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TeacherService(session)
    await service.remove_assignment(
        tenant_id=tenant_id,
        teacher_id=teacher_id,
        assignment_id=assignment_id,
        actor_user_id=current_user.id,
    )
    return {"success": True, "message": "Assignment unlinked successfully."}


# ── Timetable Entries ─────────────────────────────────────────────────────────
@router.get("/{teacher_id}/timetable", response_model=Dict[str, Any])
async def list_teacher_timetable(
    teacher_id: uuid.UUID,
    day_of_week: Optional[str] = Query(None, description="MONDAY, TUESDAY, etc."),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    access: StaffAccess = Depends(get_staff_access),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TeacherService(session)
    await service.get_teacher_detail(tenant_id, teacher_id, access=access)
    entries = await service.list_timetable(
        tenant_id=tenant_id,
        teacher_id=teacher_id,
        day_of_week=day_of_week,
    )
    return {"success": True, "data": [e.model_dump() for e in entries]}


@router.post("/{teacher_id}/timetable", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_timetable_entry(
    teacher_id: uuid.UUID,
    payload: TimetableEntryCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TeacherService(session)
    entry = await service.create_timetable_entry(
        tenant_id=tenant_id,
        teacher_id=teacher_id,
        payload=payload,
        actor_user_id=current_user.id,
    )
    return {
        "success": True,
        "data": {"id": str(entry.id)},
        "message": "Timetable slot configured successfully.",
    }


# ── Teacher Attendance Punch ──────────────────────────────────────────────────
@router.post("/{teacher_id}/attendance", response_model=Dict[str, Any])
async def record_attendance(
    teacher_id: uuid.UUID,
    payload: TeacherAttendanceRecordRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TeacherService(session)
    record = await service.record_attendance(
        tenant_id=tenant_id,
        teacher_id=teacher_id,
        payload=payload,
        actor_user_id=current_user.id,
    )
    return {"success": True, "data": record.model_dump(), "message": "Teacher attendance recorded."}


# ── Teacher Leave Application ─────────────────────────────────────────────────
@router.post("/{teacher_id}/leaves", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def apply_leave(
    teacher_id: uuid.UUID,
    payload: TeacherLeaveApplyRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    access: StaffAccess = Depends(get_staff_access),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TeacherService(session)
    await service.require_own_staff_record(tenant_id, teacher_id, access)
    leave = await service.apply_leave(
        tenant_id=tenant_id,
        teacher_id=teacher_id,
        payload=payload,
    )
    return {"success": True, "data": leave.model_dump(), "message": "Leave application submitted."}


# ── Upload Teacher Document ───────────────────────────────────────────────────
@router.post("/{teacher_id}/documents", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def upload_teacher_document(
    teacher_id: uuid.UUID,
    payload: TeacherDocumentCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    access: StaffAccess = Depends(get_staff_access),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TeacherService(session)
    await service.require_own_staff_record(tenant_id, teacher_id, access)
    doc = await service.upload_document(
        tenant_id=tenant_id,
        teacher_id=teacher_id,
        payload=payload,
    )
    return {"success": True, "data": doc.model_dump(), "message": "Teacher credential document stored."}


# ── Activate / Deactivate Teacher ─────────────────────────────────────────────
@router.post("/{teacher_id}/status", response_model=Dict[str, Any])
async def set_teacher_status(
    teacher_id: uuid.UUID,
    status: str = Query(..., description="ACTIVE or INACTIVE"),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = TeacherService(session)
    res = await service.set_teacher_status(
        tenant_id=tenant_id,
        teacher_id=teacher_id,
        status=status,
        actor_user_id=current_user.id,
    )
    return res
