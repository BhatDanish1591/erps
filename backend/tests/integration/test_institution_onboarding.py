from __future__ import annotations

import io
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.auth import Role
from app.models.enums import RoleScope


@pytest.mark.asyncio
async def test_check_subdomain_availability(client: AsyncClient):
    # 1. Fresh slug should be available
    unique_slug = f"test-campus-{uuid.uuid4().hex[:6]}"
    res = await client.get(f"/api/v1/institutions/check-subdomain?slug={unique_slug}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["available"] is True
    assert data["slug"] == unique_slug


@pytest.mark.asyncio
async def test_institution_registration_and_admin_invitation_flow(client: AsyncClient, db_session: AsyncSession):
    # Ensure roles exist
    slug = f"delhi-public-{uuid.uuid4().hex[:6]}"
    principal_email = f"principal_{uuid.uuid4().hex[:6]}@dps.edu"

    # 1. Register institution
    reg_payload = {
        "name": "Delhi Public Global School",
        "slug": slug,
        "institution_type": "SCHOOL",
        "email": f"info_{uuid.uuid4().hex[:6]}@dps.edu",
        "phone": "+919876543210",
        "city": "New Delhi",
        "state": "Delhi",
        "country": "India",
        "principal_name": "Dr. Rajesh K. Malhotra",
        "principal_email": principal_email,
        "principal_phone": "+919876543211",
    }
    reg_res = await client.post("/api/v1/institutions/register", json=reg_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()["data"]
    assert reg_data["status"] == "PENDING"
    assert "tenant_id" in reg_data
    token = reg_data["invitation_token"]
    tenant_id = uuid.UUID(reg_data["tenant_id"])

    # 2. Check slug is now marked taken
    slug_res = await client.get(f"/api/v1/institutions/check-subdomain?slug={slug}")
    assert slug_res.status_code == 200
    assert slug_res.json()["data"]["available"] is False
    assert slug_res.json()["data"]["suggestion"] is not None

    # 3. Verify invitation token
    ver_res = await client.get(f"/api/v1/institutions/invitations/verify?token={token}")
    assert ver_res.status_code == 200
    ver_data = ver_res.json()["data"]
    assert ver_data["valid"] is True
    assert ver_data["email"] == principal_email
    assert ver_data["institution_name"] == "Delhi Public Global School"

    # 4. Accept invitation and create password
    accept_payload = {
        "token": token,
        "password": "SecurePassword123!",
        "full_name": "Dr. Rajesh K. Malhotra",
        "phone": "+919876543211",
    }
    acc_res = await client.post("/api/v1/institutions/invitations/accept", json=accept_payload)
    assert acc_res.status_code == 200
    user_id = uuid.UUID(acc_res.json()["data"]["user_id"])

    # 5. Login with newly activated account
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"identifier": principal_email, "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200
    login_body = login_res.json()["data"]
    access_token = login_body["access_token"]
    assert access_token is not None


@pytest.mark.asyncio
async def test_onboarding_wizard_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # Register and activate institution
    slug = f"apex-tech-{uuid.uuid4().hex[:6]}"
    principal_email = f"dean_{uuid.uuid4().hex[:6]}@apex.edu"

    reg_res = await client.post(
        "/api/v1/institutions/register",
        json={
            "name": "Apex Institute of Technology",
            "slug": slug,
            "institution_type": "COLLEGE",
            "email": f"contact_{uuid.uuid4().hex[:6]}@apex.edu",
            "principal_name": "Prof. S. Ramanathan",
            "principal_email": principal_email,
        },
    )
    assert reg_res.status_code == 201
    tenant_id = uuid.UUID(reg_res.json()["data"]["tenant_id"])
    token = reg_res.json()["data"]["invitation_token"]

    # Activate
    await client.post(
        "/api/v1/institutions/invitations/accept",
        json={"token": token, "password": "DeanPassword123!"},
    )

    # Login to get tenant token
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"identifier": principal_email, "password": "DeanPassword123!"},
    )
    auth_token = login_res.json()["data"]["access_token"]
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "X-Tenant-ID": str(tenant_id),
    }

    # 1. Check initial onboarding status
    status_res = await client.get("/api/v1/institutions/onboarding/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["data"]["is_completed"] is False

    # 2. Step 2: Academic Session Setup
    session_res = await client.post(
        "/api/v1/institutions/onboarding/academic-session",
        headers=headers,
        json={
            "name": "Academic Year 2026-2027",
            "code": f"AY-26-27-{uuid.uuid4().hex[:4]}",
            "start_date": "2026-06-01",
            "end_date": "2027-05-31",
        },
    )
    assert session_res.status_code == 200

    # 3. Step 3: College Departments & Courses Structure
    struct_res = await client.post(
        "/api/v1/institutions/onboarding/structure",
        headers=headers,
        json={
            "items": [
                {
                    "name": "Computer Science & Engineering",
                    "code": f"CSE-{uuid.uuid4().hex[:4]}",
                    "sub_items": ["B.Tech CS", "M.Tech AI"],
                },
                {
                    "name": "Electronics Engineering",
                    "code": f"ECE-{uuid.uuid4().hex[:4]}",
                    "sub_items": ["B.Tech ECE"],
                },
            ]
        },
    )
    assert struct_res.status_code == 200

    # 4. Step 4: Subjects
    subj_res = await client.post(
        "/api/v1/institutions/onboarding/subjects",
        headers=headers,
        json={
            "subjects": [
                {"name": "Discrete Mathematics", "code": f"MATH-{uuid.uuid4().hex[:4]}", "subject_type": "THEORY"},
                {"name": "Operating Systems Lab", "code": f"CS-{uuid.uuid4().hex[:4]}", "subject_type": "PRACTICAL"},
            ]
        },
    )
    assert subj_res.status_code == 200

    # 5. Step 5: Invite Teachers
    t_invite_res = await client.post(
        "/api/v1/institutions/onboarding/teachers",
        headers=headers,
        json={
            "teachers": [
                {
                    "email": f"faculty_{uuid.uuid4().hex[:6]}@apex.edu",
                    "full_name": "Dr. Ananya Sen",
                    "designation": "Associate Professor",
                }
            ]
        },
    )
    assert t_invite_res.status_code == 200

    # 6. Step 6: Bulk Import Students via CSV
    csv_content = (
        "admission_number,full_name,email,gender,class_or_department,section_or_course\n"
        f"APEX-2026-01,Aryan Verma,aryan_{uuid.uuid4().hex[:6]}@example.com,Male,CSE,B.Tech CS\n"
        f"APEX-2026-02,Meera Iyer,meera_{uuid.uuid4().hex[:6]}@example.com,Female,CSE,B.Tech CS\n"
    )
    files = {"file": ("students.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    import_res = await client.post("/api/v1/institutions/import/students", headers=headers, files=files)
    assert import_res.status_code == 200
    assert import_res.json()["data"]["imported_count"] == 2

    # 7. Step 7: Notification Setup
    notif_res = await client.post(
        "/api/v1/institutions/onboarding/notifications",
        headers=headers,
        json={"email_notifications": True, "sms_notifications": False, "whatsapp_notifications": False},
    )
    assert notif_res.status_code == 200

    # 8. Complete Onboarding
    complete_res = await client.post("/api/v1/institutions/onboarding/complete", headers=headers)
    assert complete_res.status_code == 200

    # 9. Verify final onboarding status is true
    final_status = await client.get("/api/v1/institutions/onboarding/status", headers=headers)
    assert final_status.status_code == 200
    assert final_status.json()["data"]["is_completed"] is True
