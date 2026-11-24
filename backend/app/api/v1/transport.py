from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.permissions.rbac import (
    get_active_tenant_id,
    get_current_user,
    get_current_user_claims,
    require_any_role,
)
from app.schemas.advanced_modules import (
    StudentTransportAllocationCreate,
    StudentTransportAllocationResponse,
    TransportDriverCreate,
    TransportDriverResponse,
    TransportGpsLogCreate,
    TransportGpsLogResponse,
    TransportMaintenanceLogCreate,
    TransportMaintenanceLogResponse,
    TransportRouteCreate,
    TransportRouteResponse,
    TransportStopResponse,
    TransportVehicleCreate,
    TransportVehicleResponse,
)
from app.services.entitlement_service import require_feature
from app.services.transport_service import TransportService

router = APIRouter(
    prefix="/transport",
    tags=["Transport Management"],
    dependencies=[Depends(require_feature("TRANSPORT_MANAGEMENT"))],
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Vehicles
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/vehicles", response_model=List[TransportVehicleResponse])
async def list_vehicles(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
):
    service = TransportService(session)
    return await service.list_vehicles(tenant_id)


@router.post(
    "/vehicles",
    response_model=TransportVehicleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_vehicle(
    payload: TransportVehicleCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = TransportService(session)
    return await service.create_vehicle(tenant_id, payload)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Drivers
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/drivers", response_model=List[TransportDriverResponse])
async def list_drivers(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
):
    service = TransportService(session)
    return await service.list_drivers(tenant_id)


@router.post(
    "/drivers",
    response_model=TransportDriverResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_driver(
    payload: TransportDriverCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = TransportService(session)
    return await service.create_driver(tenant_id, payload)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Routes & Stops
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/routes", response_model=List[TransportRouteResponse])
async def list_routes(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = TransportService(session)
    routes = await service.list_routes(tenant_id)
    result = []
    for r in routes:
        res = TransportRouteResponse.model_validate(r)
        if "vehicle" in r.__dict__ and r.vehicle:
            res.vehicle_registration = r.vehicle.registration_number
        if "driver" in r.__dict__ and r.driver:
            res.driver_name = r.driver.full_name
        if "stops" in r.__dict__ and r.stops:
            res.stops = [TransportStopResponse.model_validate(s) for s in r.stops]
        result.append(res)
    return result


@router.post(
    "/routes",
    response_model=TransportRouteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_route(
    payload: TransportRouteCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = TransportService(session)
    route = await service.create_route(tenant_id, payload)
    res = TransportRouteResponse.model_validate(route)
    if "vehicle" in route.__dict__ and route.vehicle:
        res.vehicle_registration = route.vehicle.registration_number
    if "driver" in route.__dict__ and route.driver:
        res.driver_name = route.driver.full_name
    if "stops" in route.__dict__ and route.stops:
        res.stops = [TransportStopResponse.model_validate(s) for s in route.stops]
    return res


@router.get("/routes/{route_id}", response_model=TransportRouteResponse)
async def get_route(
    route_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = TransportService(session)
    route = await service.get_route(tenant_id, route_id)
    res = TransportRouteResponse.model_validate(route)
    if "vehicle" in route.__dict__ and route.vehicle:
        res.vehicle_registration = route.vehicle.registration_number
    if "driver" in route.__dict__ and route.driver:
        res.driver_name = route.driver.full_name
    if "stops" in route.__dict__ and route.stops:
        res.stops = [TransportStopResponse.model_validate(s) for s in route.stops]
    return res


# ─────────────────────────────────────────────────────────────────────────────
# 4. Student Allocations
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/allocations", response_model=List[StudentTransportAllocationResponse])
async def list_student_allocations(
    student_id: Optional[uuid.UUID] = Query(None),
    route_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = TransportService(session)
    allocations = await service.list_student_allocations(
        tenant_id=tenant_id,
        student_id=student_id,
        route_id=route_id,
    )
    result = []
    for a in allocations:
        res = StudentTransportAllocationResponse.model_validate(a)
        if "student" in a.__dict__ and a.student:
            if "user" in a.student.__dict__ and a.student.user:
                res.student_name = a.student.user.full_name
            res.admission_number = a.student.admission_number
        if "route" in a.__dict__ and a.route:
            res.route_name = a.route.name
        if "stop" in a.__dict__ and a.stop:
            res.stop_name = a.stop.name
            res.pickup_time = a.stop.pickup_time
            res.drop_time = a.stop.drop_time
        result.append(res)
    return result


@router.post(
    "/allocations",
    response_model=StudentTransportAllocationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def allocate_student(
    payload: StudentTransportAllocationCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = TransportService(session)
    alloc = await service.allocate_student(tenant_id, payload)
    res = StudentTransportAllocationResponse.model_validate(alloc)
    if "student" in alloc.__dict__ and alloc.student:
        if "user" in alloc.student.__dict__ and alloc.student.user:
            res.student_name = alloc.student.user.full_name
        res.admission_number = alloc.student.admission_number
    if "route" in alloc.__dict__ and alloc.route:
        res.route_name = alloc.route.name
    if "stop" in alloc.__dict__ and alloc.stop:
        res.stop_name = alloc.stop.name
        res.pickup_time = alloc.stop.pickup_time
        res.drop_time = alloc.stop.drop_time
    return res


# ─────────────────────────────────────────────────────────────────────────────
# 5. Maintenance & GPS Tracking
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/maintenance",
    response_model=TransportMaintenanceLogResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_maintenance(
    payload: TransportMaintenanceLogCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = TransportService(session)
    return await service.add_maintenance(tenant_id, payload)


@router.post(
    "/gps/ping",
    response_model=TransportGpsLogResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_gps_ping(
    payload: TransportGpsLogCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
):
    service = TransportService(session)
    return await service.record_gps(tenant_id, payload)


@router.get(
    "/vehicles/{vehicle_id}/live-location",
    response_model=Optional[TransportGpsLogResponse],
)
async def get_live_location(
    vehicle_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = TransportService(session)
    return await service.get_latest_gps(tenant_id, vehicle_id)
