import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin


class HostelBuilding(BaseModel, SoftDeleteMixin):
    """
    Hostel residential facility (hall of residence, boys/girls blocks).
    """
    __tablename__ = "hostel_buildings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    hostel_type: Mapped[str] = mapped_column(String(30), default="BOYS", nullable=False)  # BOYS, GIRLS, CO_ED
    total_floors: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    warden_name: Mapped[str] = mapped_column(String(150), nullable=False)
    warden_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    warden_email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    rooms: Mapped[List["HostelRoom"]] = relationship(
        "HostelRoom", back_populates="building", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_hostel_buildings_tenant_code"),
        Index("ix_hostel_buildings_tenant_code", "tenant_id", "code"),
    )


class HostelRoom(BaseModel, SoftDeleteMixin):
    """
    Living quarters unit with capacity, occupancy count, and amenity configuration.
    """
    __tablename__ = "hostel_rooms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hostel_buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_number: Mapped[str] = mapped_column(String(50), nullable=False)
    floor: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    room_type: Mapped[str] = mapped_column(
        String(50), default="DOUBLE", nullable=False
    )  # SINGLE, DOUBLE, TRIPLE, FOUR_SHARING, DORMITORY
    is_ac: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    occupied_beds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rent_per_term: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="AVAILABLE", nullable=False
    )  # AVAILABLE, FULL, MAINTENANCE

    building: Mapped["HostelBuilding"] = relationship("HostelBuilding", back_populates="rooms")
    allocations: Mapped[List["HostelRoomAllocation"]] = relationship(
        "HostelRoomAllocation", back_populates="room"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "building_id", "room_number", name="uq_hostel_rooms_building_num"),
        Index("ix_hostel_rooms_tenant_bld_status", "tenant_id", "building_id", "status"),
    )


class HostelRoomAllocation(BaseModel, SoftDeleteMixin):
    """
    Student bed allocation record with check-in, check-out, and occupancy status.
    """
    __tablename__ = "hostel_room_allocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hostel_buildings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hostel_rooms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bed_number: Mapped[str] = mapped_column(String(20), default="Bed-1", nullable=False)
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_out_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    rent_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="ACTIVE", nullable=False
    )  # ACTIVE, VACATED, TRANSFERRED
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    building: Mapped["HostelBuilding"] = relationship("HostelBuilding")
    room: Mapped["HostelRoom"] = relationship("HostelRoom", back_populates="allocations")
    student: Mapped["StudentProfile"] = relationship("StudentProfile")

    __table_args__ = (
        Index("ix_hostel_alloc_tenant_student", "tenant_id", "student_id"),
        Index("ix_hostel_alloc_tenant_room", "tenant_id", "room_id"),
    )


class HostelAttendance(BaseModel):
    """
    Night roll call and curfew tracking for boarding residents.
    """
    __tablename__ = "hostel_attendance"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hostel_buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="PRESENT", nullable=False
    )  # PRESENT, ABSENT, NIGHT_OUT, LEAVE
    in_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    out_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    student: Mapped["StudentProfile"] = relationship("StudentProfile")
    building: Mapped["HostelBuilding"] = relationship("HostelBuilding")

    __table_args__ = (
        UniqueConstraint("tenant_id", "building_id", "student_id", "attendance_date", name="uq_hostel_att_tenant_bld_st_date"),
        Index("ix_hostel_att_tenant_date", "tenant_id", "attendance_date"),
    )


class HostelVisitor(BaseModel):
    """
    Visitor registry logging external guests, check-in, check-out, and purpose.
    """
    __tablename__ = "hostel_visitors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hostel_buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visitor_name: Mapped[str] = mapped_column(String(150), nullable=False)
    relation: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    in_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    out_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)

    student: Mapped["StudentProfile"] = relationship("StudentProfile")
    building: Mapped["HostelBuilding"] = relationship("HostelBuilding")

    __table_args__ = (
        Index("ix_hostel_visitors_tenant_date", "tenant_id", "visit_date"),
    )


class HostelMaintenanceRequest(BaseModel, SoftDeleteMixin):
    """
    Room maintenance ticket (electrical, plumbing, carpentry, cleaning).
    """
    __tablename__ = "hostel_maintenance_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hostel_buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hostel_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reported_by_student_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ELECTRICAL, PLUMBING, CARPENTRY, CLEANING, OTHER
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="PENDING", nullable=False
    )  # PENDING, IN_PROGRESS, RESOLVED, CANCELLED
    priority: Mapped[str] = mapped_column(
        String(20), default="MEDIUM", nullable=False
    )  # LOW, MEDIUM, HIGH, EMERGENCY
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    building: Mapped["HostelBuilding"] = relationship("HostelBuilding")
    room: Mapped["HostelRoom"] = relationship("HostelRoom")
    reported_by_student: Mapped[Optional["StudentProfile"]] = relationship("StudentProfile")

    __table_args__ = (
        Index("ix_hostel_maint_tenant_status", "tenant_id", "status"),
    )
