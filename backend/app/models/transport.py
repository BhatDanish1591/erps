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


class TransportVehicle(BaseModel, SoftDeleteMixin):
    """
    Fleet asset representation (bus, van, cab) with seating, documents, and GPS tracking link.
    """
    __tablename__ = "transport_vehicles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    registration_number: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_model: Mapped[str] = mapped_column(String(100), nullable=False)
    seating_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    fuel_type: Mapped[str] = mapped_column(String(30), default="DIESEL", nullable=False)
    insurance_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    insurance_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    fitness_certificate_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gps_device_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="ACTIVE", nullable=False
    )  # ACTIVE, IN_SERVICE, MAINTENANCE, RETIRED

    routes: Mapped[List["TransportRoute"]] = relationship("TransportRoute", back_populates="vehicle")
    maintenance_logs: Mapped[List["TransportMaintenanceLog"]] = relationship(
        "TransportMaintenanceLog", back_populates="vehicle", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "registration_number", name="uq_transport_vehicles_tenant_reg"),
        Index("ix_transport_vehicles_tenant_reg", "tenant_id", "registration_number"),
    )


class TransportDriver(BaseModel, SoftDeleteMixin):
    """
    Driver profile with licensing, contact, and experience records.
    """
    __tablename__ = "transport_drivers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    license_number: Mapped[str] = mapped_column(String(100), nullable=False)
    license_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    emergency_contact: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    experience_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    routes: Mapped[List["TransportRoute"]] = relationship("TransportRoute", back_populates="driver")


class TransportRoute(BaseModel, SoftDeleteMixin):
    """
    Designated transit route connecting neighborhoods to institution campus.
    """
    __tablename__ = "transport_routes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    start_location: Mapped[str] = mapped_column(String(150), nullable=False)
    end_location: Mapped[str] = mapped_column(String(150), nullable=False)
    vehicle_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transport_vehicles.id", ondelete="SET NULL"), nullable=True
    )
    driver_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transport_drivers.id", ondelete="SET NULL"), nullable=True
    )
    total_distance_km: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    monthly_fare: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)

    vehicle: Mapped[Optional["TransportVehicle"]] = relationship("TransportVehicle", back_populates="routes")
    driver: Mapped[Optional["TransportDriver"]] = relationship("TransportDriver", back_populates="routes")
    stops: Mapped[List["TransportStop"]] = relationship(
        "TransportStop", back_populates="route", cascade="all, delete-orphan", order_by="TransportStop.stop_order"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_transport_routes_tenant_code"),
        Index("ix_transport_routes_tenant_code", "tenant_id", "code"),
    )


class TransportStop(BaseModel, SoftDeleteMixin):
    """
    Boarding / drop-off points with timetable schedules and coordinates.
    """
    __tablename__ = "transport_stops"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transport_routes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    stop_order: Mapped[int] = mapped_column(Integer, nullable=False)
    pickup_time: Mapped[time] = mapped_column(Time, nullable=False)
    drop_time: Mapped[time] = mapped_column(Time, nullable=False)
    stop_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)

    route: Mapped["TransportRoute"] = relationship("TransportRoute", back_populates="stops")

    __table_args__ = (
        Index("ix_transport_stops_route_order", "tenant_id", "route_id", "stop_order"),
    )


class StudentTransportAllocation(BaseModel, SoftDeleteMixin):
    """
    Student subscription to a route and bus stop, with automatic transport fee assignment.
    """
    __tablename__ = "student_transport_allocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transport_routes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    stop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transport_stops.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    pickup_drop_type: Mapped[str] = mapped_column(
        String(20), default="BOTH", nullable=False
    )  # PICKUP_ONLY, DROP_ONLY, BOTH
    monthly_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="ACTIVE", nullable=False
    )  # ACTIVE, SUSPENDED, CANCELLED

    student: Mapped["StudentProfile"] = relationship("StudentProfile")
    route: Mapped["TransportRoute"] = relationship("TransportRoute")
    stop: Mapped["TransportStop"] = relationship("TransportStop")

    __table_args__ = (
        Index("ix_transport_alloc_tenant_student", "tenant_id", "student_id"),
        Index("ix_transport_alloc_tenant_route", "tenant_id", "route_id"),
    )


class TransportMaintenanceLog(BaseModel, SoftDeleteMixin):
    """
    Vehicle servicing, fitness, odometer, and maintenance cost logging.
    """
    __tablename__ = "transport_maintenance_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transport_vehicles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    maintenance_date: Mapped[date] = mapped_column(Date, nullable=False)
    maintenance_type: Mapped[str] = mapped_column(String(50), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    odometer_reading: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    service_center: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    next_service_due: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    vehicle: Mapped["TransportVehicle"] = relationship("TransportVehicle", back_populates="maintenance_logs")


class TransportGpsLog(BaseModel):
    """
    Real-time or telemetry GPS tracking point for student transit safety.
    """
    __tablename__ = "transport_gps_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transport_vehicles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    speed_kmh: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    vehicle: Mapped["TransportVehicle"] = relationship("TransportVehicle")

    __table_args__ = (
        Index("ix_transport_gps_veh_time", "tenant_id", "vehicle_id", "recorded_at"),
    )
