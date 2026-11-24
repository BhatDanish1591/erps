import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# A. LIBRARY SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class LibraryCategoryCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    description: Optional[str] = None


class LibraryCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    code: str
    description: Optional[str] = None
    created_at: datetime


class LibraryBookCopyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    book_id: uuid.UUID
    accession_number: str
    status: str
    condition_notes: Optional[str] = None
    created_at: datetime


class LibraryBookCreate(BaseModel):
    category_id: uuid.UUID
    title: str = Field(..., max_length=255)
    author: str = Field(..., max_length=255)
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    edition: Optional[str] = None
    publication_year: Optional[int] = None
    total_copies: int = 1
    shelf_location: Optional[str] = None
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    accession_numbers: Optional[List[str]] = Field(default_factory=list, description="Optional custom barcode/accession numbers for initial copies")


class LibraryBookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    category_id: uuid.UUID
    title: str
    author: str
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    edition: Optional[str] = None
    publication_year: Optional[int] = None
    total_copies: int
    available_copies: int
    shelf_location: Optional[str] = None
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    category_name: Optional[str] = None
    created_at: datetime


class BookIssueRequest(BaseModel):
    copy_id: uuid.UUID
    borrower_user_id: uuid.UUID
    borrower_type: str = "STUDENT"  # STUDENT, TEACHER, STAFF
    student_id: Optional[uuid.UUID] = None
    teacher_id: Optional[uuid.UUID] = None
    due_days: int = 14
    notes: Optional[str] = None


class BookReturnRequest(BaseModel):
    copy_id: uuid.UUID
    fine_amount: Decimal = Decimal("0.00")
    fine_paid: bool = False
    condition_notes: Optional[str] = None


class LibraryBorrowRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    copy_id: uuid.UUID
    book_id: uuid.UUID
    book_title: Optional[str] = None
    accession_number: Optional[str] = None
    borrower_type: str
    borrower_name: Optional[str] = None
    issue_date: date
    due_date: date
    return_date: Optional[date] = None
    status: str
    fine_amount: Decimal
    fine_paid: bool
    notes: Optional[str] = None
    created_at: datetime


class LibraryReportResponse(BaseModel):
    total_books: int
    total_copies: int
    available_copies: int
    issued_copies: int
    overdue_copies: int
    total_fines_collected: Decimal
    pending_fines: Decimal


# ─────────────────────────────────────────────────────────────────────────────
# B. TRANSPORT SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class TransportVehicleCreate(BaseModel):
    registration_number: str = Field(..., max_length=50)
    vehicle_model: str = Field(..., max_length=100)
    seating_capacity: int = Field(..., ge=1)
    fuel_type: str = "DIESEL"
    insurance_number: Optional[str] = None
    insurance_expiry: Optional[date] = None
    fitness_certificate_expiry: Optional[date] = None
    gps_device_id: Optional[str] = None
    status: str = "ACTIVE"


class TransportVehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    registration_number: str
    vehicle_model: str
    seating_capacity: int
    fuel_type: str
    insurance_number: Optional[str] = None
    insurance_expiry: Optional[date] = None
    fitness_certificate_expiry: Optional[date] = None
    gps_device_id: Optional[str] = None
    status: str
    created_at: datetime


class TransportDriverCreate(BaseModel):
    full_name: str = Field(..., max_length=150)
    phone: str = Field(..., max_length=50)
    license_number: str = Field(..., max_length=100)
    license_expiry: Optional[date] = None
    emergency_contact: Optional[str] = None
    experience_years: int = 0
    is_active: bool = True


class TransportDriverResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    full_name: str
    phone: str
    license_number: str
    license_expiry: Optional[date] = None
    emergency_contact: Optional[str] = None
    experience_years: int
    is_active: bool
    created_at: datetime


class TransportStopCreate(BaseModel):
    name: str = Field(..., max_length=150)
    stop_order: int = Field(..., ge=1)
    pickup_time: time
    drop_time: time
    stop_fee: Decimal = Decimal("0.00")
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None


class TransportStopResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    route_id: uuid.UUID
    name: str
    stop_order: int
    pickup_time: time
    drop_time: time
    stop_fee: Decimal
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None


class TransportRouteCreate(BaseModel):
    name: str = Field(..., max_length=150)
    code: str = Field(..., max_length=50)
    start_location: str = Field(..., max_length=150)
    end_location: str = Field(..., max_length=150)
    vehicle_id: Optional[uuid.UUID] = None
    driver_id: Optional[uuid.UUID] = None
    total_distance_km: Optional[Decimal] = None
    monthly_fare: Decimal = Decimal("0.00")
    stops: Optional[List[TransportStopCreate]] = Field(default_factory=list)


class TransportRouteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    code: str
    start_location: str
    end_location: str
    vehicle_id: Optional[uuid.UUID] = None
    vehicle_registration: Optional[str] = None
    driver_id: Optional[uuid.UUID] = None
    driver_name: Optional[str] = None
    total_distance_km: Optional[Decimal] = None
    monthly_fare: Decimal
    status: str
    stops: List[TransportStopResponse] = Field(default_factory=list)
    created_at: datetime


class StudentTransportAllocationCreate(BaseModel):
    student_id: uuid.UUID
    route_id: uuid.UUID
    stop_id: uuid.UUID
    pickup_drop_type: str = "BOTH"  # PICKUP_ONLY, DROP_ONLY, BOTH
    monthly_fee: Optional[Decimal] = None
    start_date: date
    end_date: Optional[date] = None


class StudentTransportAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    admission_number: Optional[str] = None
    route_id: uuid.UUID
    route_name: Optional[str] = None
    stop_id: uuid.UUID
    stop_name: Optional[str] = None
    pickup_time: Optional[time] = None
    drop_time: Optional[time] = None
    pickup_drop_type: str
    monthly_fee: Decimal
    start_date: date
    end_date: Optional[date] = None
    status: str
    created_at: datetime


class TransportMaintenanceLogCreate(BaseModel):
    vehicle_id: uuid.UUID
    maintenance_date: date
    maintenance_type: str = Field(..., max_length=50)
    cost: Decimal
    odometer_reading: Optional[int] = None
    description: str
    service_center: Optional[str] = None
    next_service_due: Optional[date] = None


class TransportMaintenanceLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    vehicle_id: uuid.UUID
    maintenance_date: date
    maintenance_type: str
    cost: Decimal
    odometer_reading: Optional[int] = None
    description: str
    service_center: Optional[str] = None
    next_service_due: Optional[date] = None
    created_at: datetime


class TransportGpsLogCreate(BaseModel):
    vehicle_id: uuid.UUID
    latitude: Decimal
    longitude: Decimal
    speed_kmh: Decimal = Decimal("0.00")
    recorded_at: Optional[datetime] = None


class TransportGpsLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    vehicle_id: uuid.UUID
    latitude: Decimal
    longitude: Decimal
    speed_kmh: Decimal
    recorded_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# C. HOSTEL SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class HostelBuildingCreate(BaseModel):
    name: str = Field(..., max_length=150)
    code: str = Field(..., max_length=50)
    hostel_type: str = "BOYS"  # BOYS, GIRLS, CO_ED
    total_floors: int = 3
    warden_name: str = Field(..., max_length=150)
    warden_phone: str = Field(..., max_length=50)
    warden_email: Optional[str] = None
    address: Optional[str] = None


class HostelBuildingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    code: str
    hostel_type: str
    total_floors: int
    warden_name: str
    warden_phone: str
    warden_email: Optional[str] = None
    address: Optional[str] = None
    total_rooms: Optional[int] = None
    total_capacity: Optional[int] = None
    occupied_beds: Optional[int] = None
    created_at: datetime


class HostelRoomCreate(BaseModel):
    building_id: uuid.UUID
    room_number: str = Field(..., max_length=50)
    floor: int = 1
    room_type: str = "DOUBLE"  # SINGLE, DOUBLE, TRIPLE, FOUR_SHARING, DORMITORY
    is_ac: bool = False
    capacity: int = Field(2, ge=1)
    rent_per_term: Decimal = Decimal("0.00")


class HostelRoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    building_id: uuid.UUID
    building_name: Optional[str] = None
    room_number: str
    floor: int
    room_type: str
    is_ac: bool
    capacity: int
    occupied_beds: int
    available_beds: Optional[int] = None
    rent_per_term: Decimal
    status: str
    created_at: datetime


class HostelRoomAllocationCreate(BaseModel):
    building_id: uuid.UUID
    room_id: uuid.UUID
    student_id: uuid.UUID
    bed_number: str = "Bed-1"
    check_in_date: date
    rent_amount: Optional[Decimal] = None
    notes: Optional[str] = None


class HostelRoomAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    building_id: uuid.UUID
    building_name: Optional[str] = None
    room_id: uuid.UUID
    room_number: Optional[str] = None
    student_id: uuid.UUID
    student_name: Optional[str] = None
    admission_number: Optional[str] = None
    bed_number: str
    check_in_date: date
    check_out_date: Optional[date] = None
    rent_amount: Decimal
    status: str
    notes: Optional[str] = None
    created_at: datetime


class HostelAttendanceCreate(BaseModel):
    building_id: uuid.UUID
    student_id: uuid.UUID
    attendance_date: date
    status: str = "PRESENT"  # PRESENT, ABSENT, NIGHT_OUT, LEAVE
    in_time: Optional[time] = None
    out_time: Optional[time] = None
    remarks: Optional[str] = None


class HostelAttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    building_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    attendance_date: date
    status: str
    in_time: Optional[time] = None
    out_time: Optional[time] = None
    remarks: Optional[str] = None
    created_at: datetime


class HostelVisitorCreate(BaseModel):
    building_id: uuid.UUID
    student_id: uuid.UUID
    visitor_name: str = Field(..., max_length=150)
    relation: str = Field(..., max_length=50)
    phone: str = Field(..., max_length=50)
    visit_date: date
    in_time: datetime
    purpose: str = Field(..., max_length=255)


class HostelVisitorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    building_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    visitor_name: str
    relation: str
    phone: str
    visit_date: date
    in_time: datetime
    out_time: Optional[datetime] = None
    purpose: str
    created_at: datetime


class HostelMaintenanceRequestCreate(BaseModel):
    building_id: uuid.UUID
    room_id: uuid.UUID
    reported_by_student_id: Optional[uuid.UUID] = None
    issue_type: str = "ELECTRICAL"  # ELECTRICAL, PLUMBING, CARPENTRY, CLEANING, OTHER
    description: str
    priority: str = "MEDIUM"  # LOW, MEDIUM, HIGH, EMERGENCY


class HostelMaintenanceRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    building_id: uuid.UUID
    room_id: uuid.UUID
    room_number: Optional[str] = None
    reported_by_student_id: Optional[uuid.UUID] = None
    issue_type: str
    description: str
    status: str
    priority: str
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
