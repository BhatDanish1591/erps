import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import StudentProfile
from app.models.transport import (
    StudentTransportAllocation,
    TransportDriver,
    TransportGpsLog,
    TransportMaintenanceLog,
    TransportRoute,
    TransportStop,
    TransportVehicle,
)


class TransportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Vehicles ───────────────────────────────────────────────────────────────
    async def get_vehicle_by_id(
        self, tenant_id: uuid.UUID, vehicle_id: uuid.UUID
    ) -> Optional[TransportVehicle]:
        stmt = select(TransportVehicle).where(
            TransportVehicle.tenant_id == tenant_id,
            TransportVehicle.id == vehicle_id,
            TransportVehicle.is_deleted == False,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_vehicles(self, tenant_id: uuid.UUID) -> List[TransportVehicle]:
        stmt = (
            select(TransportVehicle)
            .where(
                TransportVehicle.tenant_id == tenant_id,
                TransportVehicle.is_deleted == False,
            )
            .order_by(TransportVehicle.registration_number)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def create_vehicle(
        self,
        tenant_id: uuid.UUID,
        registration_number: str,
        vehicle_model: str,
        seating_capacity: int,
        fuel_type: str = "DIESEL",
        insurance_number: Optional[str] = None,
        insurance_expiry: Optional[date] = None,
        fitness_certificate_expiry: Optional[date] = None,
        gps_device_id: Optional[str] = None,
        status: str = "ACTIVE",
    ) -> TransportVehicle:
        veh = TransportVehicle(
            tenant_id=tenant_id,
            registration_number=registration_number.upper(),
            vehicle_model=vehicle_model,
            seating_capacity=seating_capacity,
            fuel_type=fuel_type,
            insurance_number=insurance_number,
            insurance_expiry=insurance_expiry,
            fitness_certificate_expiry=fitness_certificate_expiry,
            gps_device_id=gps_device_id,
            status=status,
        )
        self.session.add(veh)
        await self.session.flush()
        return veh

    # ── Drivers ────────────────────────────────────────────────────────────────
    async def get_driver_by_id(
        self, tenant_id: uuid.UUID, driver_id: uuid.UUID
    ) -> Optional[TransportDriver]:
        stmt = select(TransportDriver).where(
            TransportDriver.tenant_id == tenant_id,
            TransportDriver.id == driver_id,
            TransportDriver.is_deleted == False,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_drivers(self, tenant_id: uuid.UUID) -> List[TransportDriver]:
        stmt = (
            select(TransportDriver)
            .where(
                TransportDriver.tenant_id == tenant_id,
                TransportDriver.is_deleted == False,
            )
            .order_by(TransportDriver.full_name)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def create_driver(
        self,
        tenant_id: uuid.UUID,
        full_name: str,
        phone: str,
        license_number: str,
        license_expiry: Optional[date] = None,
        emergency_contact: Optional[str] = None,
        experience_years: int = 0,
    ) -> TransportDriver:
        drv = TransportDriver(
            tenant_id=tenant_id,
            full_name=full_name,
            phone=phone,
            license_number=license_number,
            license_expiry=license_expiry,
            emergency_contact=emergency_contact,
            experience_years=experience_years,
            is_active=True,
        )
        self.session.add(drv)
        await self.session.flush()
        return drv

    # ── Routes & Stops ─────────────────────────────────────────────────────────
    async def get_route_by_id(
        self, tenant_id: uuid.UUID, route_id: uuid.UUID
    ) -> Optional[TransportRoute]:
        stmt = (
            select(TransportRoute)
            .where(
                TransportRoute.tenant_id == tenant_id,
                TransportRoute.id == route_id,
                TransportRoute.is_deleted == False,
            )
            .options(
                selectinload(TransportRoute.vehicle),
                selectinload(TransportRoute.driver),
                selectinload(TransportRoute.stops),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_routes(self, tenant_id: uuid.UUID) -> List[TransportRoute]:
        stmt = (
            select(TransportRoute)
            .where(
                TransportRoute.tenant_id == tenant_id,
                TransportRoute.is_deleted == False,
            )
            .options(
                selectinload(TransportRoute.vehicle),
                selectinload(TransportRoute.driver),
                selectinload(TransportRoute.stops),
            )
            .order_by(TransportRoute.name)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def create_route(
        self,
        tenant_id: uuid.UUID,
        name: str,
        code: str,
        start_location: str,
        end_location: str,
        vehicle_id: Optional[uuid.UUID] = None,
        driver_id: Optional[uuid.UUID] = None,
        total_distance_km: Optional[Decimal] = None,
        monthly_fare: Decimal = Decimal("0.00"),
        stops_data: Optional[List[Dict[str, Any]]] = None,
    ) -> TransportRoute:
        route = TransportRoute(
            tenant_id=tenant_id,
            name=name,
            code=code.upper(),
            start_location=start_location,
            end_location=end_location,
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            total_distance_km=total_distance_km,
            monthly_fare=monthly_fare,
            status="ACTIVE",
        )
        self.session.add(route)
        await self.session.flush()

        if stops_data:
            for s in stops_data:
                stop = TransportStop(
                    tenant_id=tenant_id,
                    route_id=route.id,
                    name=s["name"],
                    stop_order=s["stop_order"],
                    pickup_time=s["pickup_time"],
                    drop_time=s["drop_time"],
                    stop_fee=s.get("stop_fee", Decimal("0.00")),
                    latitude=s.get("latitude"),
                    longitude=s.get("longitude"),
                )
                self.session.add(stop)
            await self.session.flush()

        return route

    # ── Allocations ────────────────────────────────────────────────────────────
    async def allocate_student_transport(
        self,
        tenant_id: uuid.UUID,
        student_id: uuid.UUID,
        route_id: uuid.UUID,
        stop_id: uuid.UUID,
        pickup_drop_type: str = "BOTH",
        monthly_fee: Optional[Decimal] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> StudentTransportAllocation:
        if monthly_fee is None:
            stop = await self.session.get(TransportStop, stop_id)
            monthly_fee = stop.stop_fee if stop else Decimal("0.00")

        alloc = StudentTransportAllocation(
            tenant_id=tenant_id,
            student_id=student_id,
            route_id=route_id,
            stop_id=stop_id,
            pickup_drop_type=pickup_drop_type,
            monthly_fee=monthly_fee,
            start_date=start_date or date.today(),
            end_date=end_date,
            status="ACTIVE",
        )
        self.session.add(alloc)
        await self.session.flush()
        return alloc

    async def get_student_transport_allocation_by_id(
        self, tenant_id: uuid.UUID, allocation_id: uuid.UUID
    ) -> Optional[StudentTransportAllocation]:
        stmt = (
            select(StudentTransportAllocation)
            .where(
                StudentTransportAllocation.tenant_id == tenant_id,
                StudentTransportAllocation.id == allocation_id,
                StudentTransportAllocation.is_deleted == False,
            )
            .options(
                selectinload(StudentTransportAllocation.student).selectinload(StudentProfile.user),
                selectinload(StudentTransportAllocation.route),
                selectinload(StudentTransportAllocation.stop),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_student_transport_allocations(
        self,
        tenant_id: uuid.UUID,
        student_id: Optional[uuid.UUID] = None,
        route_id: Optional[uuid.UUID] = None,
    ) -> List[StudentTransportAllocation]:
        stmt = (
            select(StudentTransportAllocation)
            .where(
                StudentTransportAllocation.tenant_id == tenant_id,
                StudentTransportAllocation.is_deleted == False,
            )
            .options(
                selectinload(StudentTransportAllocation.student).selectinload(StudentProfile.user),
                selectinload(StudentTransportAllocation.route),
                selectinload(StudentTransportAllocation.stop),
            )
        )
        if student_id:
            stmt = stmt.where(StudentTransportAllocation.student_id == student_id)
        if route_id:
            stmt = stmt.where(StudentTransportAllocation.route_id == route_id)
        return list((await self.session.execute(stmt)).scalars().all())

    # ── Maintenance & GPS ──────────────────────────────────────────────────────
    async def add_maintenance_log(
        self,
        tenant_id: uuid.UUID,
        vehicle_id: uuid.UUID,
        maintenance_date: date,
        maintenance_type: str,
        cost: Decimal,
        description: str,
        odometer_reading: Optional[int] = None,
        service_center: Optional[str] = None,
        next_service_due: Optional[date] = None,
    ) -> TransportMaintenanceLog:
        log = TransportMaintenanceLog(
            tenant_id=tenant_id,
            vehicle_id=vehicle_id,
            maintenance_date=maintenance_date,
            maintenance_type=maintenance_type,
            cost=cost,
            description=description,
            odometer_reading=odometer_reading,
            service_center=service_center,
            next_service_due=next_service_due,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def record_gps_ping(
        self,
        tenant_id: uuid.UUID,
        vehicle_id: uuid.UUID,
        latitude: Decimal,
        longitude: Decimal,
        speed_kmh: Decimal = Decimal("0.00"),
        recorded_at: Optional[datetime] = None,
    ) -> TransportGpsLog:
        gps = TransportGpsLog(
            tenant_id=tenant_id,
            vehicle_id=vehicle_id,
            latitude=latitude,
            longitude=longitude,
            speed_kmh=speed_kmh,
            recorded_at=recorded_at or datetime.now(timezone.utc),
        )
        self.session.add(gps)
        await self.session.flush()
        return gps

    async def get_latest_gps_location(
        self, tenant_id: uuid.UUID, vehicle_id: uuid.UUID
    ) -> Optional[TransportGpsLog]:
        stmt = (
            select(TransportGpsLog)
            .where(
                TransportGpsLog.tenant_id == tenant_id,
                TransportGpsLog.vehicle_id == vehicle_id,
            )
            .order_by(TransportGpsLog.recorded_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().first()
