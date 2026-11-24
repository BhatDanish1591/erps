import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import StudentProfile
from app.models.hostel import (
    HostelAttendance,
    HostelBuilding,
    HostelMaintenanceRequest,
    HostelRoom,
    HostelRoomAllocation,
    HostelVisitor,
)


class HostelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Buildings ──────────────────────────────────────────────────────────────
    async def get_building_by_id(
        self, tenant_id: uuid.UUID, building_id: uuid.UUID
    ) -> Optional[HostelBuilding]:
        stmt = (
            select(HostelBuilding)
            .where(
                HostelBuilding.tenant_id == tenant_id,
                HostelBuilding.id == building_id,
                HostelBuilding.is_deleted == False,
            )
            .options(selectinload(HostelBuilding.rooms))
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_buildings(self, tenant_id: uuid.UUID) -> List[HostelBuilding]:
        stmt = (
            select(HostelBuilding)
            .where(
                HostelBuilding.tenant_id == tenant_id,
                HostelBuilding.is_deleted == False,
            )
            .options(selectinload(HostelBuilding.rooms))
            .order_by(HostelBuilding.name)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def create_building(
        self,
        tenant_id: uuid.UUID,
        name: str,
        code: str,
        hostel_type: str = "BOYS",
        total_floors: int = 3,
        warden_name: str = "Hostel Warden",
        warden_phone: str = "9876543210",
        warden_email: Optional[str] = None,
        address: Optional[str] = None,
    ) -> HostelBuilding:
        bld = HostelBuilding(
            tenant_id=tenant_id,
            name=name,
            code=code.upper(),
            hostel_type=hostel_type,
            total_floors=total_floors,
            warden_name=warden_name,
            warden_phone=warden_phone,
            warden_email=warden_email,
            address=address,
        )
        self.session.add(bld)
        await self.session.flush()
        return bld

    # ── Rooms ──────────────────────────────────────────────────────────────────
    async def get_room_by_id(
        self, tenant_id: uuid.UUID, room_id: uuid.UUID
    ) -> Optional[HostelRoom]:
        stmt = (
            select(HostelRoom)
            .where(
                HostelRoom.tenant_id == tenant_id,
                HostelRoom.id == room_id,
                HostelRoom.is_deleted == False,
            )
            .options(selectinload(HostelRoom.building))
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_rooms(
        self,
        tenant_id: uuid.UUID,
        building_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
    ) -> List[HostelRoom]:
        stmt = (
            select(HostelRoom)
            .where(
                HostelRoom.tenant_id == tenant_id,
                HostelRoom.is_deleted == False,
            )
            .options(selectinload(HostelRoom.building))
        )
        if building_id:
            stmt = stmt.where(HostelRoom.building_id == building_id)
        if status:
            stmt = stmt.where(HostelRoom.status == status)
        stmt = stmt.order_by(HostelRoom.room_number)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create_room(
        self,
        tenant_id: uuid.UUID,
        building_id: uuid.UUID,
        room_number: str,
        floor: int = 1,
        room_type: str = "DOUBLE",
        is_ac: bool = False,
        capacity: int = 2,
        rent_per_term: Decimal = Decimal("0.00"),
    ) -> HostelRoom:
        room = HostelRoom(
            tenant_id=tenant_id,
            building_id=building_id,
            room_number=room_number,
            floor=floor,
            room_type=room_type,
            is_ac=is_ac,
            capacity=capacity,
            occupied_beds=0,
            rent_per_term=rent_per_term,
            status="AVAILABLE",
        )
        self.session.add(room)
        await self.session.flush()
        return room

    # ── Room Allocations ───────────────────────────────────────────────────────
    async def allocate_room(
        self,
        tenant_id: uuid.UUID,
        building_id: uuid.UUID,
        room_id: uuid.UUID,
        student_id: uuid.UUID,
        bed_number: str = "Bed-1",
        check_in_date: Optional[date] = None,
        rent_amount: Optional[Decimal] = None,
        notes: Optional[str] = None,
    ) -> HostelRoomAllocation:
        room = await self.get_room_by_id(tenant_id, room_id)
        if not room or room.occupied_beds >= room.capacity:
            raise ValueError("Selected room is not available or at full capacity")

        if rent_amount is None:
            rent_amount = room.rent_per_term

        alloc = HostelRoomAllocation(
            tenant_id=tenant_id,
            building_id=building_id,
            room_id=room_id,
            student_id=student_id,
            bed_number=bed_number,
            check_in_date=check_in_date or date.today(),
            rent_amount=rent_amount,
            status="ACTIVE",
            notes=notes,
        )
        room.occupied_beds += 1
        if room.occupied_beds >= room.capacity:
            room.status = "FULL"

        self.session.add(alloc)
        await self.session.flush()
        return alloc

    async def get_allocation_by_id(
        self, tenant_id: uuid.UUID, allocation_id: uuid.UUID
    ) -> Optional[HostelRoomAllocation]:
        stmt = (
            select(HostelRoomAllocation)
            .where(
                HostelRoomAllocation.tenant_id == tenant_id,
                HostelRoomAllocation.id == allocation_id,
                HostelRoomAllocation.is_deleted == False,
            )
            .options(
                selectinload(HostelRoomAllocation.building),
                selectinload(HostelRoomAllocation.room),
                selectinload(HostelRoomAllocation.student).selectinload(StudentProfile.user),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_allocations(
        self,
        tenant_id: uuid.UUID,
        building_id: Optional[uuid.UUID] = None,
        student_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
    ) -> List[HostelRoomAllocation]:
        stmt = (
            select(HostelRoomAllocation)
            .where(
                HostelRoomAllocation.tenant_id == tenant_id,
                HostelRoomAllocation.is_deleted == False,
            )
            .options(
                selectinload(HostelRoomAllocation.building),
                selectinload(HostelRoomAllocation.room),
                selectinload(HostelRoomAllocation.student).selectinload(StudentProfile.user),
            )
        )
        if building_id:
            stmt = stmt.where(HostelRoomAllocation.building_id == building_id)
        if student_id:
            stmt = stmt.where(HostelRoomAllocation.student_id == student_id)
        if status:
            stmt = stmt.where(HostelRoomAllocation.status == status)
        stmt = stmt.order_by(HostelRoomAllocation.check_in_date.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    # ── Attendance & Curfew ────────────────────────────────────────────────────
    async def record_attendance(
        self,
        tenant_id: uuid.UUID,
        building_id: uuid.UUID,
        student_id: uuid.UUID,
        attendance_date: date,
        status: str = "PRESENT",
        in_time: Optional[time] = None,
        out_time: Optional[time] = None,
        remarks: Optional[str] = None,
    ) -> HostelAttendance:
        # Check if record already exists for this day
        stmt = select(HostelAttendance).where(
            HostelAttendance.tenant_id == tenant_id,
            HostelAttendance.building_id == building_id,
            HostelAttendance.student_id == student_id,
            HostelAttendance.attendance_date == attendance_date,
        )
        att = (await self.session.execute(stmt)).scalars().first()
        if att:
            att.status = status
            att.in_time = in_time
            att.out_time = out_time
            att.remarks = remarks
        else:
            att = HostelAttendance(
                tenant_id=tenant_id,
                building_id=building_id,
                student_id=student_id,
                attendance_date=attendance_date,
                status=status,
                in_time=in_time,
                out_time=out_time,
                remarks=remarks,
            )
            self.session.add(att)
        await self.session.flush()
        return att

    async def list_attendance(
        self,
        tenant_id: uuid.UUID,
        building_id: Optional[uuid.UUID] = None,
        student_id: Optional[uuid.UUID] = None,
        attendance_date: Optional[date] = None,
    ) -> List[HostelAttendance]:
        stmt = (
            select(HostelAttendance)
            .where(HostelAttendance.tenant_id == tenant_id)
            .options(
                selectinload(HostelAttendance.student).selectinload(StudentProfile.user)
            )
        )
        if building_id:
            stmt = stmt.where(HostelAttendance.building_id == building_id)
        if student_id:
            stmt = stmt.where(HostelAttendance.student_id == student_id)
        if attendance_date:
            stmt = stmt.where(HostelAttendance.attendance_date == attendance_date)
        stmt = stmt.order_by(HostelAttendance.attendance_date.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    # ── Visitors & Maintenance ────────────────────────────────────────────────
    async def log_visitor(
        self,
        tenant_id: uuid.UUID,
        building_id: uuid.UUID,
        student_id: uuid.UUID,
        visitor_name: str,
        relation: str,
        phone: str,
        visit_date: date,
        in_time: datetime,
        purpose: str,
    ) -> HostelVisitor:
        vis = HostelVisitor(
            tenant_id=tenant_id,
            building_id=building_id,
            student_id=student_id,
            visitor_name=visitor_name,
            relation=relation,
            phone=phone,
            visit_date=visit_date,
            in_time=in_time,
            purpose=purpose,
        )
        self.session.add(vis)
        await self.session.flush()
        return vis

    async def list_visitors(
        self,
        tenant_id: uuid.UUID,
        building_id: Optional[uuid.UUID] = None,
        student_id: Optional[uuid.UUID] = None,
    ) -> List[HostelVisitor]:
        stmt = (
            select(HostelVisitor)
            .where(HostelVisitor.tenant_id == tenant_id)
            .options(
                selectinload(HostelVisitor.student).selectinload(StudentProfile.user)
            )
            .order_by(HostelVisitor.in_time.desc())
        )
        if building_id:
            stmt = stmt.where(HostelVisitor.building_id == building_id)
        if student_id:
            stmt = stmt.where(HostelVisitor.student_id == student_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create_maintenance_request(
        self,
        tenant_id: uuid.UUID,
        building_id: uuid.UUID,
        room_id: uuid.UUID,
        issue_type: str,
        description: str,
        reported_by_student_id: Optional[uuid.UUID] = None,
        priority: str = "MEDIUM",
    ) -> HostelMaintenanceRequest:
        req = HostelMaintenanceRequest(
            tenant_id=tenant_id,
            building_id=building_id,
            room_id=room_id,
            issue_type=issue_type,
            description=description,
            reported_by_student_id=reported_by_student_id,
            priority=priority,
            status="PENDING",
        )
        self.session.add(req)
        await self.session.flush()
        return req

    async def list_maintenance_requests(
        self,
        tenant_id: uuid.UUID,
        building_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
    ) -> List[HostelMaintenanceRequest]:
        stmt = (
            select(HostelMaintenanceRequest)
            .where(
                HostelMaintenanceRequest.tenant_id == tenant_id,
                HostelMaintenanceRequest.is_deleted == False,
            )
            .options(
                selectinload(HostelMaintenanceRequest.room),
                selectinload(HostelMaintenanceRequest.building),
            )
            .order_by(HostelMaintenanceRequest.created_at.desc())
        )
        if building_id:
            stmt = stmt.where(HostelMaintenanceRequest.building_id == building_id)
        if status:
            stmt = stmt.where(HostelMaintenanceRequest.status == status)
        return list((await self.session.execute(stmt)).scalars().all())
