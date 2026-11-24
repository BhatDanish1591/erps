import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.academic import StudentProfile
from app.models.auth import Membership, Role
from app.models.enums import InstitutionType
from app.models.tenant import Tenant, TenantSetting
from app.models.user import User


async def _setup_tenant_and_admin(
    session: AsyncSession, enable_features: list[str] | None = None,
    institution_type: InstitutionType = InstitutionType.SCHOOL,
):
    tenant = Tenant(name="Vanguard Global Academy", slug=f"vanguard-{uuid.uuid4().hex[:6]}", institution_type=institution_type)
    session.add(tenant)
    await session.flush()

    admin_role = (await session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))).scalars().first()
    admin_user = User(
        email=f"admin-{uuid.uuid4().hex[:6]}@vanguard.edu",
        password_hash="pw",
        full_name="Dr. Elizabeth Vance",
        is_active=True,
    )
    session.add(admin_user)
    await session.flush()

    session.add(Membership(tenant_id=tenant.id, user_id=admin_user.id, role_id=admin_role.id))

    if enable_features:
        features_dict = {f: True for f in enable_features}
        setting = TenantSetting(
            tenant_id=tenant.id,
            key="features",
            value=features_dict,
            is_public=False,
        )
        session.add(setting)

    await session.commit()

    token = create_access_token(
        user_id=admin_user.id, email=admin_user.email, tenant_id=tenant.id, role="INSTITUTION_ADMIN"
    )
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant.id)}
    return tenant, admin_user, headers


@pytest.mark.asyncio
async def test_entitlement_gating_blocks_unauthorized_institutions(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies that tenants without library, transport, or hostel entitlements
    receive HTTP 403 with error code FEATURE_NOT_ENTITLED.
    """
    tenant, admin, headers = await _setup_tenant_and_admin(
        db_session, enable_features=[], institution_type=InstitutionType.COLLEGE,
    )

    # 1. Library check
    res = await client.get("/api/v1/library/categories", headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FEATURE_NOT_ENTITLED"

    # 2. Transport check
    res = await client.get("/api/v1/transport/vehicles", headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FEATURE_NOT_ENTITLED"

    # 3. Hostel check
    res = await client.get("/api/v1/hostel/buildings", headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FEATURE_NOT_ENTITLED"


@pytest.mark.asyncio
async def test_school_has_no_hostel_access_even_when_enabled(client: AsyncClient, db_session: AsyncSession):
    _, _, headers = await _setup_tenant_and_admin(db_session, enable_features=["HOSTEL_MANAGEMENT"])
    response = await client.get("/api/v1/hostel/buildings", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_library_management_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Tests complete Library lifecycle:
    Category -> Book with auto-generated copies -> Copy listing -> Issue book ->
    Return book with fine -> Borrows list -> Library summary report.
    """
    tenant, admin, headers = await _setup_tenant_and_admin(
        db_session, enable_features=["LIBRARY_MANAGEMENT"]
    )

    # 1. Create category
    cat_res = await client.post(
        "/api/v1/library/categories",
        headers=headers,
        json={
            "name": "Science & Technology",
            "code": "SCI-TECH",
            "description": "Scientific books and journals",
        },
    )
    assert cat_res.status_code == 201
    cat_data = cat_res.json()
    category_id = cat_data["id"]

    # 2. Create Book with 3 copies and custom accession numbers
    book_res = await client.post(
        "/api/v1/library/books",
        headers=headers,
        json={
            "category_id": category_id,
            "title": "Quantum Physics Principles",
            "author": "Dr. Richard Feynman",
            "isbn": "978-0131103627",
            "publisher": "Academic Press",
            "edition": "3rd",
            "publication_year": 2024,
            "total_copies": 3,
            "shelf_location": "Row 4, Shelf B",
            "description": "Comprehensive textbook on quantum phenomena.",
            "accession_numbers": ["PHY-001", "PHY-002", "PHY-003"],
        },
    )
    assert book_res.status_code == 201
    book_data = book_res.json()
    book_id = book_data["id"]
    assert book_data["total_copies"] == 3
    assert book_data["available_copies"] == 3

    # 3. List book copies
    copies_res = await client.get(f"/api/v1/library/books/{book_id}/copies", headers=headers)
    assert copies_res.status_code == 200
    copies = copies_res.json()
    assert len(copies) == 3
    assert {c["accession_number"] for c in copies} == {"PHY-001", "PHY-002", "PHY-003"}
    issued_copy = copies[0]

    # 4. Issue Copy PHY-001 to the user
    issue_res = await client.post(
        "/api/v1/library/issue",
        headers=headers,
        json={
            "copy_id": issued_copy["id"],
            "borrower_user_id": str(admin.id),
            "borrower_type": "TEACHER",
            "due_days": 14,
            "notes": "Research for advanced seminar",
        },
    )
    assert issue_res.status_code == 201
    issue_data = issue_res.json()
    assert issue_data["status"] == "ISSUED"
    assert issue_data["accession_number"] == issued_copy["accession_number"]

    # Verify available copies decreased to 2
    book_check = await client.get(f"/api/v1/library/books/{book_id}", headers=headers)
    assert book_check.json()["available_copies"] == 2

    # 5. Return book with overdue fine of 50.00
    return_res = await client.post(
        "/api/v1/library/return",
        headers=headers,
        json={
            "copy_id": issued_copy["id"],
            "fine_amount": "50.00",
            "fine_paid": True,
            "condition_notes": "Returned in perfect condition",
        },
    )
    assert return_res.status_code == 200
    return_data = return_res.json()
    assert return_data["status"] == "RETURNED"
    assert Decimal(str(return_data["fine_amount"])) == Decimal("50.00")
    assert return_data["fine_paid"] is True

    # Verify available copies restored to 3
    book_check2 = await client.get(f"/api/v1/library/books/{book_id}", headers=headers)
    assert book_check2.json()["available_copies"] == 3

    # 6. Verify Borrow records
    borrows_res = await client.get("/api/v1/library/borrows", headers=headers)
    assert borrows_res.status_code == 200
    assert len(borrows_res.json()) >= 1

    # 7. Summary Report
    report_res = await client.get("/api/v1/library/reports/summary", headers=headers)
    assert report_res.status_code == 200
    rep = report_res.json()
    assert rep["total_books"] == 1
    assert rep["total_copies"] == 3
    assert rep["available_copies"] == 3
    assert rep["issued_copies"] == 0
    assert Decimal(str(rep["total_fines_collected"])) == Decimal("50.00")


@pytest.mark.asyncio
async def test_transport_management_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Tests complete Transport lifecycle:
    Vehicle -> Driver -> Route with stops -> Student allocation ->
    Maintenance log -> GPS tracking ping & live location lookup.
    """
    tenant, admin, headers = await _setup_tenant_and_admin(
        db_session, enable_features=["TRANSPORT_MANAGEMENT"]
    )

    # 1. Create vehicle
    veh_res = await client.post(
        "/api/v1/transport/vehicles",
        headers=headers,
        json={
            "registration_number": f"DL-01-EXP-{uuid.uuid4().hex[:4].upper()}",
            "vehicle_model": "Tata Starbus 40-Seater",
            "seating_capacity": 40,
            "fuel_type": "DIESEL",
            "insurance_number": "POL-987654",
            "insurance_expiry": "2027-12-31",
            "fitness_certificate_expiry": "2027-06-30",
            "gps_device_id": "GPS-TRACKER-009",
            "status": "ACTIVE",
        },
    )
    assert veh_res.status_code == 201
    veh_data = veh_res.json()
    vehicle_id = veh_data["id"]

    # 2. Create driver
    drv_res = await client.post(
        "/api/v1/transport/drivers",
        headers=headers,
        json={
            "full_name": "Rajesh Kumar",
            "phone": "+91-9811223344",
            "license_number": "DL-COMM-2020-00129",
            "license_expiry": "2030-05-15",
            "emergency_contact": "+91-9811223399",
            "experience_years": 8,
            "is_active": True,
        },
    )
    assert drv_res.status_code == 201
    drv_data = drv_res.json()
    driver_id = drv_data["id"]

    # 3. Create Route with 2 stops
    route_res = await client.post(
        "/api/v1/transport/routes",
        headers=headers,
        json={
            "name": "North Campus Morning Express",
            "code": "R-101",
            "start_location": "Central Metro Station",
            "end_location": "Vanguard Main Gate",
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
            "total_distance_km": "22.50",
            "monthly_fare": "2500.00",
            "stops": [
                {
                    "name": "City Center Circle",
                    "stop_order": 1,
                    "pickup_time": "07:15:00",
                    "drop_time": "15:45:00",
                    "stop_fee": "2200.00",
                    "latitude": "28.6139",
                    "longitude": "77.2090",
                },
                {
                    "name": "Oakridge Junction",
                    "stop_order": 2,
                    "pickup_time": "07:35:00",
                    "drop_time": "15:25:00",
                    "stop_fee": "2500.00",
                    "latitude": "28.6250",
                    "longitude": "77.2180",
                },
            ],
        },
    )
    assert route_res.status_code == 201
    route_data = route_res.json()
    assert len(route_data["stops"]) == 2
    stop_id = route_data["stops"][0]["id"]

    # 4. Create student & allocate to route
    student_user = User(
        email=f"stu-{uuid.uuid4().hex[:6]}@vanguard.edu",
        password_hash="pw",
        full_name="Vivaan Sharma",
        is_active=True,
    )
    db_session.add(student_user)
    await db_session.flush()

    student_profile = StudentProfile(
        tenant_id=tenant.id,
        user_id=student_user.id,
        admission_number=f"ADM-{uuid.uuid4().hex[:5].upper()}",
        admission_date=date(2025, 6, 1),
    )
    db_session.add(student_profile)
    await db_session.commit()

    alloc_res = await client.post(
        "/api/v1/transport/allocations",
        headers=headers,
        json={
            "student_id": str(student_profile.id),
            "route_id": route_data["id"],
            "stop_id": stop_id,
            "pickup_drop_type": "BOTH",
            "monthly_fee": "2200.00",
            "start_date": "2026-04-01",
        },
    )
    assert alloc_res.status_code == 201
    alloc_data = alloc_res.json()
    assert alloc_data["student_name"] == "Vivaan Sharma"
    assert alloc_data["route_name"] == "North Campus Morning Express"

    # 5. Add maintenance log
    maint_res = await client.post(
        "/api/v1/transport/maintenance",
        headers=headers,
        json={
            "vehicle_id": vehicle_id,
            "maintenance_date": "2026-11-15",
            "maintenance_type": "Brake pad replacement and oil service",
            "cost": "6500.00",
            "odometer_reading": 34200,
            "description": "Routine quarterly inspection and genuine Bosch brake pad install",
            "service_center": "Authorized Tata Motors Center",
            "next_service_due": "2027-02-15",
        },
    )
    assert maint_res.status_code == 201
    assert Decimal(str(maint_res.json()["cost"])) == Decimal("6500.00")

    # 6. Record GPS ping & verify live location
    gps_res = await client.post(
        "/api/v1/transport/gps/ping",
        headers=headers,
        json={
            "vehicle_id": vehicle_id,
            "latitude": "28.6145",
            "longitude": "77.2095",
            "speed_kmh": "38.50",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert gps_res.status_code == 201

    live_res = await client.get(
        f"/api/v1/transport/vehicles/{vehicle_id}/live-location",
        headers=headers,
    )
    assert live_res.status_code == 200
    live_data = live_res.json()
    assert Decimal(str(live_data["latitude"])) == Decimal("28.6145")
    assert Decimal(str(live_data["speed_kmh"])) == Decimal("38.50")


@pytest.mark.asyncio
async def test_hostel_management_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Tests complete Hostel lifecycle:
    Building -> Room -> Room capacity allocation -> Night curfew attendance ->
    Visitor record -> Maintenance request.
    """
    tenant, admin, headers = await _setup_tenant_and_admin(
        db_session, enable_features=["HOSTEL_MANAGEMENT"], institution_type=InstitutionType.COLLEGE,
    )

    # 1. Create Building
    bld_res = await client.post(
        "/api/v1/hostel/buildings",
        headers=headers,
        json={
            "name": "Kaveri Senior Hostel",
            "code": "KAV-01",
            "hostel_type": "BOYS",
            "total_floors": 4,
            "warden_name": "Major Arvind Singh",
            "warden_phone": "+91-9876500112",
            "warden_email": "warden.kaveri@vanguard.edu",
            "address": "Campus South Sector, Gate 3",
        },
    )
    assert bld_res.status_code == 201
    building_id = bld_res.json()["id"]

    # 2. Create Room (Double sharing, capacity: 2)
    room_res = await client.post(
        "/api/v1/hostel/rooms",
        headers=headers,
        json={
            "building_id": building_id,
            "room_number": "204",
            "floor": 2,
            "room_type": "DOUBLE",
            "is_ac": True,
            "capacity": 2,
            "rent_per_term": "45000.00",
        },
    )
    assert room_res.status_code == 201
    room_data = room_res.json()
    room_id = room_data["id"]
    assert room_data["capacity"] == 2
    assert room_data["occupied_beds"] == 0

    # 3. Create two students and allocate Bed-1 and Bed-2
    students = []
    for i in range(2):
        u = User(
            email=f"hostel_stu_{i}_{uuid.uuid4().hex[:5]}@vanguard.edu",
            password_hash="pw",
            full_name=f"Hostel Resident {i+1}",
            is_active=True,
        )
        db_session.add(u)
        await db_session.flush()
        sp = StudentProfile(
            tenant_id=tenant.id,
            user_id=u.id,
            admission_number=f"RES-{uuid.uuid4().hex[:5].upper()}",
            admission_date=date(2025, 6, 1),
        )
        db_session.add(sp)
        students.append(sp)
    await db_session.commit()

    # Allocate Bed-1
    alloc1_res = await client.post(
        "/api/v1/hostel/allocations",
        headers=headers,
        json={
            "building_id": building_id,
            "room_id": room_id,
            "student_id": str(students[0].id),
            "bed_number": "Bed-A",
            "check_in_date": "2026-07-01",
            "rent_amount": "45000.00",
            "notes": "Medical condition: None",
        },
    )
    assert alloc1_res.status_code == 201

    # Allocate Bed-2
    alloc2_res = await client.post(
        "/api/v1/hostel/allocations",
        headers=headers,
        json={
            "building_id": building_id,
            "room_id": room_id,
            "student_id": str(students[1].id),
            "bed_number": "Bed-B",
            "check_in_date": "2026-07-01",
            "rent_amount": "45000.00",
        },
    )
    assert alloc2_res.status_code == 201

    # Attempt Bed-3 (Should fail: room capacity exceeded)
    u3 = User(
        email=f"hostel_stu_3_{uuid.uuid4().hex[:5]}@vanguard.edu",
        password_hash="pw",
        full_name="Hostel Resident 3",
        is_active=True,
    )
    db_session.add(u3)
    await db_session.flush()
    sp3 = StudentProfile(
        tenant_id=tenant.id,
        user_id=u3.id,
        admission_number=f"RES-{uuid.uuid4().hex[:5].upper()}",
        admission_date=date(2025, 6, 1),
    )
    db_session.add(sp3)
    await db_session.commit()

    alloc3_res = await client.post(
        "/api/v1/hostel/allocations",
        headers=headers,
        json={
            "building_id": building_id,
            "room_id": room_id,
            "student_id": str(sp3.id),
            "bed_number": "Bed-C",
            "check_in_date": "2026-07-01",
        },
    )
    assert alloc3_res.status_code == 422
    assert "capacity" in alloc3_res.json()["error"]["message"].lower()

    # 4. Night Curfew Attendance
    att_res = await client.post(
        "/api/v1/hostel/attendance",
        headers=headers,
        json={
            "building_id": building_id,
            "student_id": str(students[0].id),
            "attendance_date": "2026-11-19",
            "status": "PRESENT",
            "in_time": "21:15:00",
            "remarks": "On time before 9:30 PM curfew",
        },
    )
    assert att_res.status_code == 201
    assert att_res.json()["status"] == "PRESENT"

    # 5. Log Visitor
    vis_res = await client.post(
        "/api/v1/hostel/visitors",
        headers=headers,
        json={
            "building_id": building_id,
            "student_id": str(students[0].id),
            "visitor_name": "Suresh Sharma",
            "relation": "FATHER",
            "phone": "+91-9876543200",
            "visit_date": "2026-11-19",
            "in_time": datetime.now(timezone.utc).isoformat(),
            "purpose": "Delivering winter clothes and laptop",
        },
    )
    assert vis_res.status_code == 201
    assert vis_res.json()["visitor_name"] == "Suresh Sharma"

    # 6. Maintenance Request
    maint_req_res = await client.post(
        "/api/v1/hostel/maintenance",
        headers=headers,
        json={
            "building_id": building_id,
            "room_id": room_id,
            "reported_by_student_id": str(students[0].id),
            "issue_type": "ELECTRICAL",
            "description": "Ceiling fan regulator not working in Bed-A position",
            "priority": "MEDIUM",
        },
    )
    assert maint_req_res.status_code == 201
    assert maint_req_res.json()["status"] == "PENDING"
    assert maint_req_res.json()["issue_type"] == "ELECTRICAL"
