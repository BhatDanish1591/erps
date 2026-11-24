from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.tenant import require_institution_type
from app.models.enums import InstitutionType
from app.models.user import User
from app.permissions.rbac import (
    get_active_tenant_id,
    get_current_user,
    get_current_user_claims,
    require_any_role,
)
from app.schemas.advanced_modules import (
    HostelAttendanceCreate,
    HostelAttendanceResponse,
    HostelBuildingCreate,
    HostelBuildingResponse,
    HostelMaintenanceRequestCreate,
    HostelMaintenanceRequestResponse,
    HostelRoomAllocationCreate,
    HostelRoomAllocationResponse,
    HostelRoomCreate,
    HostelRoomResponse,
    HostelVisitorCreate,
    HostelVisitorResponse,
)
from app.services.entitlement_service import require_feature
from app.services.hostel_service import HostelService

router = APIRouter(
    prefix="/hostel",
    tags=["Hostel Management"],
    dependencies=[Depends(require_institution_type(InstitutionType.COLLEGE)), Depends(require_feature("HOSTEL_MANAGEMENT"))],
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Buildings
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/buildings", response_model=List[HostelBuildingResponse])
async def list_buildings(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = HostelService(session)
    return await service.list_buildings(tenant_id)


@router.post(
    "/buildings",
    response_model=HostelBuildingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_building(
    payload: HostelBuildingCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = HostelService(session)
    return await service.create_building(tenant_id, payload)


@router.get("/buildings/{building_id}", response_model=HostelBuildingResponse)
async def get_building(
    building_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = HostelService(session)
    return await service.get_building(tenant_id, building_id)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Rooms
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/rooms", response_model=List[HostelRoomResponse])
async def list_rooms(
    building_id: Optional[uuid.UUID] = Query(None),
    room_status: Optional[str] = Query(None, alias="status"),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = HostelService(session)
    rooms = await service.list_rooms(tenant_id, building_id=building_id, status=room_status)
    result = []
    for r in rooms:
        res = HostelRoomResponse.model_validate(r)
        if "building" in r.__dict__ and r.building:
            res.building_name = r.building.name
        res.available_beds = max(0, r.capacity - r.occupied_beds)
        result.append(res)
    return result


@router.post(
    "/rooms",
    response_model=HostelRoomResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_room(
    payload: HostelRoomCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = HostelService(session)
    room = await service.create_room(tenant_id, payload)
    res = HostelRoomResponse.model_validate(room)
    if "building" in room.__dict__ and room.building:
        res.building_name = room.building.name
    res.available_beds = max(0, room.capacity - room.occupied_beds)
    return res


# ─────────────────────────────────────────────────────────────────────────────
# 3. Allocations
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/allocations", response_model=List[HostelRoomAllocationResponse])
async def list_allocations(
    building_id: Optional[uuid.UUID] = Query(None),
    student_id: Optional[uuid.UUID] = Query(None),
    alloc_status: Optional[str] = Query(None, alias="status"),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = HostelService(session)
    allocations = await service.list_allocations(
        tenant_id=tenant_id,
        building_id=building_id,
        student_id=student_id,
        status=alloc_status,
    )
    result = []
    for a in allocations:
        res = HostelRoomAllocationResponse.model_validate(a)
        if "building" in a.__dict__ and a.building:
            res.building_name = a.building.name
        if "room" in a.__dict__ and a.room:
            res.room_number = a.room.room_number
        if "student" in a.__dict__ and a.student:
            if "user" in a.student.__dict__ and a.student.user:
                res.student_name = a.student.user.full_name
            res.admission_number = a.student.admission_number
        result.append(res)
    return result


@router.post(
    "/allocations",
    response_model=HostelRoomAllocationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def allocate_room(
    payload: HostelRoomAllocationCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = HostelService(session)
    alloc = await service.allocate_room(tenant_id, payload)
    res = HostelRoomAllocationResponse.model_validate(alloc)
    if "building" in alloc.__dict__ and alloc.building:
        res.building_name = alloc.building.name
    if "room" in alloc.__dict__ and alloc.room:
        res.room_number = alloc.room.room_number
    if "student" in alloc.__dict__ and alloc.student:
        if "user" in alloc.student.__dict__ and alloc.student.user:
            res.student_name = alloc.student.user.full_name
        res.admission_number = alloc.student.admission_number
    return res


# ─────────────────────────────────────────────────────────────────────────────
# 4. Night Curfew Attendance
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/attendance", response_model=List[HostelAttendanceResponse])
async def list_attendance(
    building_id: Optional[uuid.UUID] = Query(None),
    student_id: Optional[uuid.UUID] = Query(None),
    attendance_date: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = HostelService(session)
    records = await service.list_attendance(
        tenant_id=tenant_id,
        building_id=building_id,
        student_id=student_id,
        attendance_date=attendance_date,
    )
    result = []
    for r in records:
        res = HostelAttendanceResponse.model_validate(r)
        if "student" in r.__dict__ and r.student:
            if "user" in r.student.__dict__ and r.student.user:
                res.student_name = r.student.user.full_name
        result.append(res)
    return result


@router.post(
    "/attendance",
    response_model=HostelAttendanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_attendance(
    payload: HostelAttendanceCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
):
    service = HostelService(session)
    att = await service.record_attendance(tenant_id, payload)
    res = HostelAttendanceResponse.model_validate(att)
    if "student" in att.__dict__ and att.student:
        if "user" in att.student.__dict__ and att.student.user:
            res.student_name = att.student.user.full_name
    return res


# ─────────────────────────────────────────────────────────────────────────────
# 5. Visitor Logging
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/visitors", response_model=List[HostelVisitorResponse])
async def list_visitors(
    building_id: Optional[uuid.UUID] = Query(None),
    student_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = HostelService(session)
    visitors = await service.list_visitors(tenant_id, building_id, student_id)
    result = []
    for v in visitors:
        res = HostelVisitorResponse.model_validate(v)
        if "student" in v.__dict__ and v.student:
            if "user" in v.student.__dict__ and v.student.user:
                res.student_name = v.student.user.full_name
        result.append(res)
    return result


@router.post(
    "/visitors",
    response_model=HostelVisitorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def log_visitor(
    payload: HostelVisitorCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
):
    service = HostelService(session)
    vis = await service.log_visitor(tenant_id, payload)
    res = HostelVisitorResponse.model_validate(vis)
    if "student" in vis.__dict__ and vis.student:
        if "user" in vis.student.__dict__ and vis.student.user:
            res.student_name = vis.student.user.full_name
    return res


# ─────────────────────────────────────────────────────────────────────────────
# 6. Maintenance Requests
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/maintenance", response_model=List[HostelMaintenanceRequestResponse])
async def list_maintenance(
    building_id: Optional[uuid.UUID] = Query(None),
    request_status: Optional[str] = Query(None, alias="status"),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = HostelService(session)
    requests = await service.list_maintenance(tenant_id, building_id, status=request_status)
    result = []
    for m in requests:
        res = HostelMaintenanceRequestResponse.model_validate(m)
        if "room" in m.__dict__ and m.room:
            res.room_number = m.room.room_number
        result.append(res)
    return result


@router.post(
    "/maintenance",
    response_model=HostelMaintenanceRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_maintenance(
    payload: HostelMaintenanceRequestCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = HostelService(session)
    req = await service.request_maintenance(tenant_id, payload)
    res = HostelMaintenanceRequestResponse.model_validate(req)
    if "room" in req.__dict__ and req.room:
        res.room_number = req.room.room_number
    return res
