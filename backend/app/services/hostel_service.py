import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.models.hostel import (
    HostelAttendance,
    HostelBuilding,
    HostelMaintenanceRequest,
    HostelRoom,
    HostelRoomAllocation,
    HostelVisitor,
)
from app.repositories.hostel import HostelRepository
from app.schemas.advanced_modules import (
    HostelAttendanceCreate,
    HostelBuildingCreate,
    HostelMaintenanceRequestCreate,
    HostelRoomAllocationCreate,
    HostelRoomCreate,
    HostelVisitorCreate,
)


class HostelService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = HostelRepository(session)

    # Buildings
    async def create_building(
        self, tenant_id: uuid.UUID, data: HostelBuildingCreate
    ) -> HostelBuilding:
        bld = await self.repo.create_building(
            tenant_id=tenant_id,
            name=data.name,
            code=data.code,
            hostel_type=data.hostel_type,
            total_floors=data.total_floors,
            warden_name=data.warden_name,
            warden_phone=data.warden_phone,
            warden_email=data.warden_email,
            address=data.address,
        )
        await self.session.commit()
        return bld

    async def list_buildings(self, tenant_id: uuid.UUID) -> List[HostelBuilding]:
        return await self.repo.list_buildings(tenant_id)

    async def get_building(
        self, tenant_id: uuid.UUID, building_id: uuid.UUID
    ) -> HostelBuilding:
        bld = await self.repo.get_building_by_id(tenant_id, building_id)
        if not bld:
            raise NotFoundException(message=f"Hostel building {building_id} not found")
        return bld

    # Rooms
    async def create_room(
        self, tenant_id: uuid.UUID, data: HostelRoomCreate
    ) -> HostelRoom:
        bld = await self.repo.get_building_by_id(tenant_id, data.building_id)
        if not bld:
            raise NotFoundException(message=f"Hostel building {data.building_id} not found")

        room = await self.repo.create_room(
            tenant_id=tenant_id,
            building_id=data.building_id,
            room_number=data.room_number,
            floor=data.floor,
            room_type=data.room_type,
            is_ac=data.is_ac,
            capacity=data.capacity,
            rent_per_term=data.rent_per_term,
        )
        await self.session.commit()
        return room

    async def list_rooms(
        self,
        tenant_id: uuid.UUID,
        building_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
    ) -> List[HostelRoom]:
        return await self.repo.list_rooms(tenant_id, building_id, status)

    # Allocations
    async def allocate_room(
        self, tenant_id: uuid.UUID, data: HostelRoomAllocationCreate
    ) -> HostelRoomAllocation:
        try:
            alloc = await self.repo.allocate_room(
                tenant_id=tenant_id,
                building_id=data.building_id,
                room_id=data.room_id,
                student_id=data.student_id,
                bed_number=data.bed_number,
                check_in_date=data.check_in_date,
                rent_amount=data.rent_amount,
                notes=data.notes,
            )
            await self.session.commit()
            return await self.repo.get_allocation_by_id(tenant_id, alloc.id)
        except ValueError as ex:
            raise ValidationException(message=str(ex))

    async def list_allocations(
        self,
        tenant_id: uuid.UUID,
        building_id: Optional[uuid.UUID] = None,
        student_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
    ) -> List[HostelRoomAllocation]:
        return await self.repo.list_allocations(
            tenant_id=tenant_id,
            building_id=building_id,
            student_id=student_id,
            status=status,
        )

    # Attendance
    async def record_attendance(
        self, tenant_id: uuid.UUID, data: HostelAttendanceCreate
    ) -> HostelAttendance:
        att = await self.repo.record_attendance(
            tenant_id=tenant_id,
            building_id=data.building_id,
            student_id=data.student_id,
            attendance_date=data.attendance_date,
            status=data.status,
            in_time=data.in_time,
            out_time=data.out_time,
            remarks=data.remarks,
        )
        await self.session.commit()
        return att

    async def list_attendance(
        self,
        tenant_id: uuid.UUID,
        building_id: Optional[uuid.UUID] = None,
        student_id: Optional[uuid.UUID] = None,
        attendance_date: Optional[date] = None,
    ) -> List[HostelAttendance]:
        return await self.repo.list_attendance(
            tenant_id=tenant_id,
            building_id=building_id,
            student_id=student_id,
            attendance_date=attendance_date,
        )

    # Visitors
    async def log_visitor(
        self, tenant_id: uuid.UUID, data: HostelVisitorCreate
    ) -> HostelVisitor:
        vis = await self.repo.log_visitor(
            tenant_id=tenant_id,
            building_id=data.building_id,
            student_id=data.student_id,
            visitor_name=data.visitor_name,
            relation=data.relation,
            phone=data.phone,
            visit_date=data.visit_date,
            in_time=data.in_time,
            purpose=data.purpose,
        )
        await self.session.commit()
        return vis

    async def list_visitors(
        self,
        tenant_id: uuid.UUID,
        building_id: Optional[uuid.UUID] = None,
        student_id: Optional[uuid.UUID] = None,
    ) -> List[HostelVisitor]:
        return await self.repo.list_visitors(tenant_id, building_id, student_id)

    # Maintenance
    async def request_maintenance(
        self, tenant_id: uuid.UUID, data: HostelMaintenanceRequestCreate
    ) -> HostelMaintenanceRequest:
        req = await self.repo.create_maintenance_request(
            tenant_id=tenant_id,
            building_id=data.building_id,
            room_id=data.room_id,
            issue_type=data.issue_type,
            description=data.description,
            reported_by_student_id=data.reported_by_student_id,
            priority=data.priority,
        )
        await self.session.commit()
        return req

    async def list_maintenance(
        self,
        tenant_id: uuid.UUID,
        building_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
    ) -> List[HostelMaintenanceRequest]:
        return await self.repo.list_maintenance_requests(tenant_id, building_id, status)
