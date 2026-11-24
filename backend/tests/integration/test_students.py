from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.academic import AcademicSession, SchoolClass, Section, StudentProfile
from app.models.auth import Membership, Role
from app.models.enums import BillingCycle, InstitutionType, MembershipStatus, RoleScope, SubscriptionStatus, TenantStatus
from app.models.subscription import Subscription, SubscriptionPlan
from app.models.tenant import Tenant
from app.models.user import User
from app.services.subscription_service import SubscriptionService


@pytest.fixture
async def setup_student_test_data(db_session: AsyncSession):
    # 1. Tenant
    tenant = Tenant(
        name="Oakridge International",
        slug=f"oakridge-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.SCHOOL,
        status=TenantStatus.ACTIVE,
        email=f"admin_{uuid.uuid4().hex[:6]}@oakridge.edu",
    )
    db_session.add(tenant)
    await db_session.flush()

    # 2. Academic Session, Class & Section
    session_obj = AcademicSession(
        tenant_id=tenant.id,
        name="2026-2027",
        code="AY-2026-27",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
    )
    db_session.add(session_obj)

    next_session = AcademicSession(
        tenant_id=tenant.id,
        name="2027-2028",
        code="AY-2027-28",
        start_date=date(2027, 4, 1),
        end_date=date(2028, 3, 31),
        is_current=False,
    )
    db_session.add(next_session)

    school_class = SchoolClass(
        tenant_id=tenant.id,
        name="Grade 10",
        code="G10",
        order_index=10,
    )
    db_session.add(school_class)

    class_11 = SchoolClass(
        tenant_id=tenant.id,
        name="Grade 11",
        code="G11",
        order_index=11,
    )
    db_session.add(class_11)
    await db_session.flush()

    section = Section(
        tenant_id=tenant.id,
        class_id=school_class.id,
        name="A",
        capacity=40,
    )
    db_session.add(section)

    section_11a = Section(
        tenant_id=tenant.id,
        class_id=class_11.id,
        name="A",
        capacity=40,
    )
    db_session.add(section_11a)

    # 3. Admin User
    admin_user = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@oakridge.edu",
        password_hash=hash_password("Password123!"),
        full_name="Oakridge Administrator",
        is_superadmin=False,
        is_active=True,
    )
    db_session.add(admin_user)
    await db_session.flush()

    # 4. Role & Membership
    role = (await db_session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))).scalars().first()
    if not role:
        role = Role(name="Institution Admin", code="INSTITUTION_ADMIN", scope=RoleScope.TENANT, is_system_role=True)
        db_session.add(role)
        await db_session.flush()

    membership = Membership(
        user_id=admin_user.id,
        tenant_id=tenant.id,
        role_id=role.id,
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(membership)

    # 5. Plan with student limit 300
    sub_service = SubscriptionService(db_session)
    await sub_service.seed_default_plans_if_needed()

    starter_plan = (await db_session.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.code == "STARTER_SCHOOL")
    )).scalars().first()

    now = datetime.now(timezone.utc)
    sub = Subscription(
        tenant_id=tenant.id,
        plan_id=starter_plan.id,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        is_auto_renew=True,
    )
    db_session.add(sub)
    await db_session.commit()

    admin_token = create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        tenant_id=tenant.id,
        role="INSTITUTION_ADMIN",
        permissions=["*:*"],
    )

    return {
        "tenant": tenant,
        "admin": admin_user,
        "admin_token": admin_token,
        "session": session_obj,
        "next_session": next_session,
        "class": school_class,
        "class_11": class_11,
        "section": section,
        "section_11a": section_11a,
        "plan": starter_plan,
    }


@pytest.mark.asyncio
async def test_create_student_success(client: AsyncClient, setup_student_test_data):
    data = setup_student_test_data
    token = data["admin_token"]

    payload = {
        "full_name": "Aarav Sharma",
        "email": f"aarav_{uuid.uuid4().hex[:6]}@example.com",
        "phone": "+919876543210",
        "roll_number": "101",
        "gender": "MALE",
        "date_of_birth": "2010-05-15",
        "blood_group": "B+",
        "class_id": str(data["class"].id),
        "section_id": str(data["section"].id),
        "father_name": "Rajesh Sharma",
        "father_phone": "+919876543211",
        "address_line1": "Flat 402, Lotus Towers",
        "city": "Mumbai",
        "state": "Maharashtra",
        "postal_code": "400001",
    }

    res = await client.post(
        "/api/v1/students",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 201
    body = res.json()
    assert body["success"] is True
    student = body["data"]
    assert student["full_name"] == "Aarav Sharma"
    assert student["admission_number"].startswith("ADM-")
    assert student["status"] == "ACTIVE"
    assert student["blood_group"] == "B+"


@pytest.mark.asyncio
async def test_duplicate_admission_number_rejected(client: AsyncClient, setup_student_test_data):
    data = setup_student_test_data
    token = data["admin_token"]

    payload1 = {
        "full_name": "Priya Patel",
        "admission_number": "ADM-2026-CUSTOM-01",
        "class_id": str(data["class"].id),
    }
    res1 = await client.post(
        "/api/v1/students",
        json=payload1,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 201

    # Try creating with duplicate admission number
    payload2 = {
        "full_name": "Rohan Patel",
        "admission_number": "ADM-2026-CUSTOM-01",
        "class_id": str(data["class"].id),
    }
    res2 = await client.post(
        "/api/v1/students",
        json=payload2,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 409
    body2 = res2.json()
    assert body2["error"]["code"] == "DUPLICATE_ADMISSION_NUMBER"


@pytest.mark.asyncio
async def test_list_and_search_students(client: AsyncClient, setup_student_test_data):
    data = setup_student_test_data
    token = data["admin_token"]

    # Create 2 students
    await client.post(
        "/api/v1/students",
        json={"full_name": "Ishaan Verma", "roll_number": "201", "class_id": str(data["class"].id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        "/api/v1/students",
        json={"full_name": "Ananya Gupta", "roll_number": "202", "class_id": str(data["class"].id)},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Search by query
    res = await client.get(
        "/api/v1/students?search=Ishaan",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert any("Ishaan" in s["full_name"] for s in body["data"]["items"])


@pytest.mark.asyncio
async def test_student_detail_and_update(client: AsyncClient, setup_student_test_data):
    data = setup_student_test_data
    token = data["admin_token"]

    create_res = await client.post(
        "/api/v1/students",
        json={"full_name": "Kabir Das", "roll_number": "301", "blood_group": "O+"},
        headers={"Authorization": f"Bearer {token}"},
    )
    student_id = create_res.json()["data"]["id"]

    # Get detail
    detail_res = await client.get(
        f"/api/v1/students/{student_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["full_name"] == "Kabir Das"

    # Update detail
    update_res = await client.put(
        f"/api/v1/students/{student_id}",
        json={"full_name": "Kabir Das Updated", "blood_group": "AB+"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["full_name"] == "Kabir Das Updated"
    assert update_res.json()["data"]["blood_group"] == "AB+"


@pytest.mark.asyncio
async def test_student_promotion(client: AsyncClient, setup_student_test_data):
    data = setup_student_test_data
    token = data["admin_token"]

    # Create a student in Class 10
    create_res = await client.post(
        "/api/v1/students",
        json={
            "full_name": "Aditi Roy",
            "class_id": str(data["class"].id),
            "section_id": str(data["section"].id),
            "academic_session_id": str(data["session"].id),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    student_id = create_res.json()["data"]["id"]

    # Promote to Class 11 in Next Academic Session
    promo_payload = {
        "target_academic_session_id": str(data["next_session"].id),
        "target_class_id": str(data["class_11"].id),
        "target_section_id": str(data["section_11a"].id),
        "student_ids": [student_id],
        "action": "PROMOTE",
        "remarks": "Promoted after successful board exam",
    }
    promo_res = await client.post(
        "/api/v1/students/promote",
        json=promo_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert promo_res.status_code == 200
    assert promo_res.json()["data"]["processed_students"] == 1

    # Verify student now has target class
    updated_res = await client.get(
        f"/api/v1/students/{student_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    updated_data = updated_res.json()["data"]
    assert updated_data["class_id"] == str(data["class_11"].id)
    assert updated_data["academic_session_id"] == str(data["next_session"].id)


@pytest.mark.asyncio
async def test_student_id_card_generation(client: AsyncClient, setup_student_test_data):
    data = setup_student_test_data
    token = data["admin_token"]

    create_res = await client.post(
        "/api/v1/students",
        json={
            "full_name": "Devansh Singhania",
            "roll_number": "505",
            "class_id": str(data["class"].id),
            "section_id": str(data["section"].id),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    student_id = create_res.json()["data"]["id"]

    # JSON ID Card
    card_json_res = await client.get(
        f"/api/v1/students/{student_id}/id-card",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert card_json_res.status_code == 200
    card_data = card_json_res.json()["data"]
    assert card_data["full_name"] == "Devansh Singhania"
    assert "barcode_data" in card_data

    # HTML ID Card
    card_html_res = await client.get(
        f"/api/v1/students/{student_id}/id-card/html",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert card_html_res.status_code == 200
    assert "text/html" in card_html_res.headers["content-type"]
    assert "Devansh Singhania" in card_html_res.text


@pytest.mark.asyncio
async def test_export_and_bulk_import_students(client: AsyncClient, setup_student_test_data):
    data = setup_student_test_data
    token = data["admin_token"]

    # 1. Export CSV
    export_res = await client.get(
        "/api/v1/students/export",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers["content-type"]

    # 2. Bulk import CSV
    csv_content = """full_name,email,phone,class,section,roll_number,gender
Vikram Malhotra,vikram.m@test.edu,9988776655,Grade 10,A,11,MALE
Meera Nair,meera.n@test.edu,9988776654,Grade 10,A,12,FEMALE
"""
    files = {"file": ("students.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}

    import_res = await client.post(
        "/api/v1/students/import",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert import_res.status_code == 200
    import_data = import_res.json()["data"]
    assert import_data["total_processed"] == 2
    assert import_data["successful"] == 2
    assert import_data["failed"] == 0

@pytest.mark.asyncio
async def test_student_admission_with_photo(client: AsyncClient, setup_student_test_data, tmp_path, monkeypatch):
    from app.utils.storage import storage_service

    monkeypatch.setattr(storage_service, "backend", "local")
    monkeypatch.setattr(storage_service, "local_dir", tmp_path)
    data = setup_student_test_data
    headers = {"Authorization": f"Bearer {data['admin_token']}"}
    image = b"\x89PNG\r\n\x1a\n" + b"test image"
    invalid = await client.post("/api/v1/students/photo", headers=headers, files={"file": ("bad.png", b"not an image", "image/png")})
    assert invalid.status_code == 400
    upload = await client.post("/api/v1/students/photo", headers=headers, files={"file": ("photo.png", image, "image/png")})
    assert upload.status_code == 201, upload.text
    key = upload.json()["data"]["photo_key"]
    result = await client.post("/api/v1/students", headers=headers, json={
        "full_name": "Photo Student", "class_id": str(data["class"].id),
        "section_id": str(data["section"].id), "photo_url": key,
    })
    assert result.status_code == 201, result.text
    student_id = result.json()["data"]["id"]
    detail = await client.get(f"/api/v1/students/{student_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    photo_url = detail.json()["data"]["photo_url"]
    response = await client.get(photo_url)
    assert response.status_code == 200
    assert response.content == image

    replacement_image = b"\xff\xd8\xff" + b"replacement image"
    replacement = await client.post(
        "/api/v1/students/photo", headers=headers,
        files={"file": ("replacement.jpg", replacement_image, "image/jpeg")},
    )
    assert replacement.status_code == 201, replacement.text
    updated = await client.put(f"/api/v1/students/{student_id}", headers=headers, json={
        "full_name": "Photo Student", "class_id": str(data["class"].id),
        "section_id": str(data["section"].id), "date_of_birth": "2010-05-15",
        "photo_url": replacement.json()["data"]["photo_key"],
    })
    assert updated.status_code == 200, updated.text
    new_photo = await client.get(updated.json()["data"]["photo_url"])
    assert new_photo.status_code == 200
    assert new_photo.content == replacement_image
