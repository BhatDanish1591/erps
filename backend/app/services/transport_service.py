import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.models.transport import (
    StudentTransportAllocation,
    TransportDriver,
    TransportGpsLog,
    TransportMaintenanceLog,
    TransportRoute,
    TransportVehicle,
)
from app.repositories.transport import TransportRepository
from app.schemas.advanced_modules import (
    StudentTransportAllocationCreate,
    TransportDriverCreate,
    TransportGpsLogCreate,
    TransportMaintenanceLogCreate,
    TransportRouteCreate,
    TransportVehicleCreate,
)


class TransportService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TransportRepository(session)

    # Vehicles
    async def create_vehicle(
        self, tenant_id: uuid.UUID, data: TransportVehicleCreate
    ) -> TransportVehicle:
        veh = await self.repo.create_vehicle(
            tenant_id=tenant_id,
            registration_number=data.registration_number,
            vehicle_model=data.vehicle_model,
            seating_capacity=data.seating_capacity,
            fuel_type=data.fuel_type,
            insurance_number=data.insurance_number,
            insurance_expiry=data.insurance_expiry,
            fitness_certificate_expiry=data.fitness_certificate_expiry,
            gps_device_id=data.gps_device_id,
            status=data.status,
        )
        await self.session.commit()
        return veh

    async def list_vehicles(self, tenant_id: uuid.UUID) -> List[TransportVehicle]:
        return await self.repo.list_vehicles(tenant_id)

    # Drivers
    async def create_driver(
        self, tenant_id: uuid.UUID, data: TransportDriverCreate
    ) -> TransportDriver:
        drv = await self.repo.create_driver(
            tenant_id=tenant_id,
            full_name=data.full_name,
            phone=data.phone,
            license_number=data.license_number,
            license_expiry=data.license_expiry,
            emergency_contact=data.emergency_contact,
            experience_years=data.experience_years,
        )
        await self.session.commit()
        return drv

    async def list_drivers(self, tenant_id: uuid.UUID) -> List[TransportDriver]:
        return await self.repo.list_drivers(tenant_id)

    # Routes
    async def create_route(
        self, tenant_id: uuid.UUID, data: TransportRouteCreate
    ) -> TransportRoute:
        stops_payload = (
            [s.model_dump() for s in data.stops] if data.stops else None
        )
        route = await self.repo.create_route(
            tenant_id=tenant_id,
            name=data.name,
            code=data.code,
            start_location=data.start_location,
            end_location=data.end_location,
            vehicle_id=data.vehicle_id,
            driver_id=data.driver_id,
            total_distance_km=data.total_distance_km,
            monthly_fare=data.monthly_fare,
            stops_data=stops_payload,
        )
        await self.session.commit()
        return await self.repo.get_route_by_id(tenant_id, route.id)

    async def list_routes(self, tenant_id: uuid.UUID) -> List[TransportRoute]:
        return await self.repo.list_routes(tenant_id)

    async def get_route(
        self, tenant_id: uuid.UUID, route_id: uuid.UUID
    ) -> TransportRoute:
        route = await self.repo.get_route_by_id(tenant_id, route_id)
        if not route:
            raise NotFoundException(message=f"Route {route_id} not found")
        return route

    # Student Transport Allocations
    async def allocate_student(
        self, tenant_id: uuid.UUID, data: StudentTransportAllocationCreate
    ) -> StudentTransportAllocation:
        alloc = await self.repo.allocate_student_transport(
            tenant_id=tenant_id,
            student_id=data.student_id,
            route_id=data.route_id,
            stop_id=data.stop_id,
            pickup_drop_type=data.pickup_drop_type,
            monthly_fee=data.monthly_fee,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        await self.session.commit()
        return await self.repo.get_student_transport_allocation_by_id(tenant_id, alloc.id)

    async def list_student_allocations(
        self,
        tenant_id: uuid.UUID,
        student_id: Optional[uuid.UUID] = None,
        route_id: Optional[uuid.UUID] = None,
    ) -> List[StudentTransportAllocation]:
        return await self.repo.list_student_transport_allocations(
            tenant_id=tenant_id,
            student_id=student_id,
            route_id=route_id,
        )

    # Maintenance & GPS
    async def add_maintenance(
        self, tenant_id: uuid.UUID, data: TransportMaintenanceLogCreate
    ) -> TransportMaintenanceLog:
        log = await self.repo.add_maintenance_log(
            tenant_id=tenant_id,
            vehicle_id=data.vehicle_id,
            maintenance_date=data.maintenance_date,
            maintenance_type=data.maintenance_type,
            cost=data.cost,
            description=data.description,
            odometer_reading=data.odometer_reading,
            service_center=data.service_center,
            next_service_due=data.next_service_due,
        )
        await self.session.commit()
        return log

    async def record_gps(
        self, tenant_id: uuid.UUID, data: TransportGpsLogCreate
    ) -> TransportGpsLog:
        gps = await self.repo.record_gps_ping(
            tenant_id=tenant_id,
            vehicle_id=data.vehicle_id,
            latitude=data.latitude,
            longitude=data.longitude,
            speed_kmh=data.speed_kmh,
            recorded_at=data.recorded_at,
        )
        await self.session.commit()
        return gps

    async def get_latest_gps(
        self, tenant_id: uuid.UUID, vehicle_id: uuid.UUID
    ) -> Optional[TransportGpsLog]:
        return await self.repo.get_latest_gps_location(tenant_id, vehicle_id)
