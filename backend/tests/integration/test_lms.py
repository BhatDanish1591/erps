from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.academic import (
    AcademicSession,
    SchoolClass,
    SchoolEnrollmentDetail,
    Section,
    StudentAcademicEnrollment,
    StudentProfile,
    Subject,
    TeacherProfile,
)
from app.models.auth import Membership, Role
from app.models.enums import BillingCycle, InstitutionType, MembershipStatus, RoleScope, TenantStatus
from app.models.subscription import Subscription, SubscriptionPlan
from app.models.tenant import Tenant
from app.models.user import User


@pytest.fixture
async def setup_lms_data(db_session: AsyncSession):
    # 1. Tenant
    tenant = Tenant(
        name="St. Xavier's International Academy",
        slug=f"lms-school-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.SCHOOL,
        status=TenantStatus.ACTIVE,
        email=f"xavier_lms_{uuid.uuid4().hex[:6]}@school.edu",
    )
    db_session.add(tenant)
    await db_session.flush()

    # 2. Subscription
    plan = SubscriptionPlan(
        name="Enterprise LMS Plan",
        code=f"ENT-LMS-{uuid.uuid4().hex[:4]}",
        institution_type=InstitutionType.SCHOOL,
        billing_cycle=BillingCycle.MONTHLY,
        price=4999.0,
        max_students=3000,
        max_teachers=200,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.flush()

    sub = Subscription(
        tenant_id=tenant.id,
        plan_id=plan.id,
        status="ACTIVE",
        billing_cycle=BillingCycle.MONTHLY,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(sub)

    # 3. Roles
    admin_role = (await db_session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))).scalars().first()
    if not admin_role:
        admin_role = Role(name="Institution Admin", code="INSTITUTION_ADMIN", scope=RoleScope.TENANT, is_system_role=True)
        db_session.add(admin_role)
        await db_session.flush()

    teacher_role = (await db_session.execute(select(Role).where(Role.code == "TEACHER"))).scalars().first()
    if not teacher_role:
        teacher_role = Role(name="Teacher", code="TEACHER", scope=RoleScope.TENANT, is_system_role=True)
        db_session.add(teacher_role)
        await db_session.flush()

    student_role = (await db_session.execute(select(Role).where(Role.code == "STUDENT"))).scalars().first()
    if not student_role:
        student_role = Role(name="Student", code="STUDENT", scope=RoleScope.TENANT, is_system_role=True)
        db_session.add(student_role)
        await db_session.flush()

    # 4. Users
    admin_user = User(
        email=f"lms_admin_{uuid.uuid4().hex[:6]}@xavier.edu",
        password_hash=hash_password("AdminPass123!"),
        full_name="Rev. Principal",
        is_active=True,
    )
    db_session.add(admin_user)
    await db_session.flush()
    db_session.add(Membership(user_id=admin_user.id, tenant_id=tenant.id, role_id=admin_role.id, status=MembershipStatus.ACTIVE))

    teacher_user = User(
        email=f"lms_teacher_{uuid.uuid4().hex[:6]}@xavier.edu",
        password_hash=hash_password("TeacherPass123!"),
        full_name="Prof. Walter White",
        is_active=True,
    )
    db_session.add(teacher_user)
    await db_session.flush()
    db_session.add(Membership(user_id=teacher_user.id, tenant_id=tenant.id, role_id=teacher_role.id, status=MembershipStatus.ACTIVE))

    teacher_profile = TeacherProfile(
        tenant_id=tenant.id,
        user_id=teacher_user.id,
        employee_id=f"TCH-{uuid.uuid4().hex[:4].upper()}",
        status="ACTIVE",
    )
    db_session.add(teacher_profile)

    student_user = User(
        email=f"lms_student_{uuid.uuid4().hex[:6]}@xavier.edu",
        password_hash=hash_password("StudentPass123!"),
        full_name="Jesse Pinkman",
        is_active=True,
    )
    db_session.add(student_user)
    await db_session.flush()
    db_session.add(Membership(user_id=student_user.id, tenant_id=tenant.id, role_id=student_role.id, status=MembershipStatus.ACTIVE))

    student_profile = StudentProfile(
        tenant_id=tenant.id,
        user_id=student_user.id,
        admission_number=f"ADM-{uuid.uuid4().hex[:6].upper()}",
        gender="MALE",
        date_of_birth=date(2008, 1, 15),
        admission_date=date(2025, 4, 1),
        status="ACTIVE",
    )
    db_session.add(student_profile)

    # 5. Academic session, class, section, subject
    session = AcademicSession(
        tenant_id=tenant.id,
        name="2026-2027",
        code=f"SESS-{uuid.uuid4().hex[:4].upper()}",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
    )
    db_session.add(session)
    await db_session.flush()

    school_class = SchoolClass(
        tenant_id=tenant.id,
        name="Grade 11 - Science",
        code=f"G11-SCI-{uuid.uuid4().hex[:4]}",
    )
    db_session.add(school_class)
    await db_session.flush()

    section = Section(
        tenant_id=tenant.id,
        class_id=school_class.id,
        name="Section A",
        capacity=40,
    )
    db_session.add(section)
    await db_session.flush()

    subject = Subject(
        tenant_id=tenant.id,
        name="Advanced Chemistry",
        code="CHEM-101",
        credits=4,
    )
    db_session.add(subject)
    await db_session.flush()

    # 6. Student Enrollment
    enrollment = StudentAcademicEnrollment(
        tenant_id=tenant.id,
        student_id=student_profile.id,
        academic_session_id=session.id,
        enrollment_type="SCHOOL",
        enrollment_number=f"ENR-{uuid.uuid4().hex[:6].upper()}",
        enrollment_date=date(2026, 4, 1),
        status="ACTIVE",
    )
    db_session.add(enrollment)
    await db_session.flush()

    school_detail = SchoolEnrollmentDetail(
        tenant_id=tenant.id,
        enrollment_id=enrollment.id,
        class_id=school_class.id,
        section_id=section.id,
    )
    db_session.add(school_detail)
    await db_session.commit()

    # Auth headers
    admin_token = create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        tenant_id=tenant.id,
        role="INSTITUTION_ADMIN",
        permissions=["materials.create", "materials.view", "assignments.create", "assignments.view"],
    )
    teacher_token = create_access_token(
        user_id=teacher_user.id,
        email=teacher_user.email,
        tenant_id=tenant.id,
        role="TEACHER",
        permissions=["materials.create", "materials.view", "assignments.create", "assignments.view", "assignments.evaluate"],
    )
    student_token = create_access_token(
        user_id=student_user.id,
        email=student_user.email,
        tenant_id=tenant.id,
        role="STUDENT",
        permissions=["materials.view", "assignments.view", "assignments.submit"],
    )

    return {
        "tenant": tenant,
        "session": session,
        "class": school_class,
        "section": section,
        "subject": subject,
        "teacher": teacher_user,
        "student": student_user,
        "student_profile": student_profile,
        "admin_headers": {"Authorization": f"Bearer {admin_token}", "X-Tenant-Id": str(tenant.id)},
        "teacher_headers": {"Authorization": f"Bearer {teacher_token}", "X-Tenant-Id": str(tenant.id)},
        "student_headers": {"Authorization": f"Bearer {student_token}", "X-Tenant-Id": str(tenant.id)},
    }


@pytest.mark.asyncio
async def test_create_and_upload_study_material(client: AsyncClient, setup_lms_data: dict):
    data = setup_lms_data
    headers = data["teacher_headers"]

    # 1. Create external video lecture study material via JSON
    video_payload = {
        "title": "Quantum Mechanics & Atomic Orbitals Video Lecture",
        "academic_session_id": str(data["session"].id),
        "subject_id": str(data["subject"].id),
        "class_id": str(data["class"].id),
        "section_id": str(data["section"].id),
        "chapter": "Chapter 2: Electronic Configuration",
        "material_type": "VIDEO_LINK",
        "category": "LECTURE_NOTE",
        "external_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "tags": ["chemistry", "quantum", "orbitals"],
        "is_published": True,
    }
    res = await client.post("/api/v1/materials", json=video_payload, headers=headers)
    assert res.status_code == 201
    res_data = res.json()["data"]
    assert res_data["title"] == video_payload["title"]
    assert res_data["material_type"] == "VIDEO_LINK"
    assert res_data["download_url"] == video_payload["external_url"]

    # 2. Upload file-based study material via multipart upload
    file_content = b"%PDF-1.4 Mock PDF content for Organic Chemistry reaction pathways."
    files = {"file": ("organic_reactions.pdf", io.BytesIO(file_content), "application/pdf")}
    form_data = {
        "title": "Organic Reactions & Mechanisms Notes",
        "academic_session_id": str(data["session"].id),
        "subject_id": str(data["subject"].id),
        "class_id": str(data["class"].id),
        "section_id": str(data["section"].id),
        "chapter": "Chapter 5: Hydrocarbons",
        "material_type": "PDF",
        "category": "LECTURE_NOTE",
        "tags_json": '["organic", "reactions", "exam-prep"]',
        "is_published": "true",
    }
    upload_res = await client.post("/api/v1/materials/upload", data=form_data, files=files, headers=headers)
    assert upload_res.status_code == 201
    uploaded_item = upload_res.json()["data"]
    assert uploaded_item["file_name"] == "organic_reactions.pdf"
    assert uploaded_item["download_url"] is not None
    assert uploaded_item["preview_url"] is not None
    material_id = uploaded_item["id"]

    # 3. Fetch single material and verify view count
    get_res = await client.get(f"/api/v1/materials/{material_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["view_count"] >= 1

    # 4. Upload new version 2 of the material
    v2_content = b"%PDF-1.4 Updated PDF content with solved examples and practice questions."
    v2_files = {"file": ("organic_reactions_v2.pdf", io.BytesIO(v2_content), "application/pdf")}
    v2_form = {"change_summary": "Added solved examples from previous 5 years exams."}
    v2_res = await client.post(
        f"/api/v1/materials/{material_id}/versions", data=v2_form, files=v2_files, headers=headers
    )
    assert v2_res.status_code == 200
    v2_data = v2_res.json()["data"]
    assert v2_data["version"] == 2
    assert v2_data["file_name"] == "organic_reactions_v2.pdf"
    assert len(v2_data["versions"]) >= 2

    # 5. List and filter study materials
    list_res = await client.get(
        f"/api/v1/materials?subject_id={data['subject'].id}&search=Organic", headers=headers
    )
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # 6. Student access (ensure student can list and view)
    student_res = await client.get("/api/v1/materials", headers=data["student_headers"])
    assert student_res.status_code == 200
    assert len(student_res.json()["data"]) >= 2

    # 7. Download endpoint (returns signed download URL / stream)
    dl_res = await client.get(f"/api/v1/materials/{material_id}/download?redirect=false", headers=headers)
    assert dl_res.status_code == 200
    dl_url = dl_res.json()["data"]["url"]
    assert dl_url is not None

    # Verify stream endpoint works with the generated local stream URL
    if "/api/v1/materials/files/stream" in dl_url:
        stream_res = await client.get(dl_url, headers=headers)
        assert stream_res.status_code == 200
        assert b"Updated PDF content" in stream_res.content

    # 8. Delete study material
    del_res = await client.delete(f"/api/v1/materials/{material_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Verify material is no longer returned in list
    check_del = await client.get(f"/api/v1/materials/{material_id}", headers=headers)
    assert check_del.status_code == 404


@pytest.mark.asyncio
async def test_assignments_lifecycle(client: AsyncClient, setup_lms_data: dict):
    data = setup_lms_data
    teacher_headers = data["teacher_headers"]
    student_headers = data["student_headers"]

    # 1. Teacher creates an assignment with deadline and late penalty
    due_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    assign_payload = {
        "title": "Stoichiometry & Titration Lab Report",
        "description": "Calculate molarity and write detailed lab report including error margins.",
        "academic_session_id": str(data["session"].id),
        "subject_id": str(data["subject"].id),
        "class_id": str(data["class"].id),
        "section_id": str(data["section"].id),
        "due_datetime": due_date,
        "allow_late_submission": True,
        "late_penalty_percent": "10.00",
        "total_marks": "50.00",
        "passing_marks": "20.00",
        "status": "PUBLISHED",
    }
    create_res = await client.post("/api/v1/assignments", json=assign_payload, headers=teacher_headers)
    assert create_res.status_code == 201
    assign_data = create_res.json()["data"]
    assignment_id = assign_data["id"]
    assert assign_data["total_marks"] == "50.00"

    # 2. Student submits assignment response with attachment
    sub_file = b"%PDF-1.4 Jesse Pinkman Lab Report: 0.1M HCl vs 0.1M NaOH titration curve."
    files = {"file": ("titration_report.pdf", io.BytesIO(sub_file), "application/pdf")}
    sub_form = {
        "submission_text": "Here is my completed titration report with calculated molar concentrations."
    }
    submit_res = await client.post(
        f"/api/v1/assignments/{assignment_id}/submit",
        data=sub_form,
        files=files,
        headers=student_headers,
    )
    assert submit_res.status_code == 201
    sub_data = submit_res.json()["data"]
    assert sub_data["status"] == "SUBMITTED"
    assert sub_data["is_late"] is False
    assert sub_data["attachment_file_name"] == "titration_report.pdf"
    assert sub_data["attachment_download_url"] is not None
    submission_id = sub_data["id"]

    # 3. Student checks their own submission
    my_sub_res = await client.get(f"/api/v1/assignments/{assignment_id}/my-submission", headers=student_headers)
    assert my_sub_res.status_code == 200
    assert my_sub_res.json()["data"]["id"] == submission_id

    # 4. Teacher lists submissions for the assignment
    subs_list_res = await client.get(f"/api/v1/assignments/{assignment_id}/submissions", headers=teacher_headers)
    assert subs_list_res.status_code == 200
    assert len(subs_list_res.json()["data"]) >= 1

    # 5. Teacher evaluates the submission
    eval_payload = {
        "marks_obtained": "46.00",
        "grade": "A+",
        "teacher_feedback": "Excellent titration graph, accurate stoichiometry calculation and error analysis.",
        "status": "EVALUATED",
    }
    eval_res = await client.post(
        f"/api/v1/assignments/submissions/{submission_id}/evaluate",
        json=eval_payload,
        headers=teacher_headers,
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()["data"]
    assert eval_data["status"] == "EVALUATED"
    assert eval_data["marks_obtained"] == "46.00"
    assert eval_data["grade"] == "A+"

    # 6. Verify assignment report analytics
    report_res = await client.get(f"/api/v1/assignments/{assignment_id}/report", headers=teacher_headers)
    assert report_res.status_code == 200
    report = report_res.json()["data"]
    assert report["total_submitted"] >= 1
    assert report["total_evaluated"] >= 1
    assert report["submission_rate_percent"] > 0
    assert report["average_score"] == 46.0
    assert report["pass_percentage"] == 100.0


@pytest.mark.asyncio
async def test_late_submission_penalty(client: AsyncClient, setup_lms_data: dict):
    data = setup_lms_data
    teacher_headers = data["teacher_headers"]
    student_headers = data["student_headers"]

    # Create assignment whose deadline has already passed
    past_due = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    assign_payload = {
        "title": "Thermodynamics Problem Set",
        "description": "Calculate Gibbs free energy and enthalpy changes.",
        "academic_session_id": str(data["session"].id),
        "subject_id": str(data["subject"].id),
        "class_id": str(data["class"].id),
        "section_id": str(data["section"].id),
        "due_datetime": past_due,
        "allow_late_submission": True,
        "late_penalty_percent": "20.00",  # 20% penalty
        "total_marks": "100.00",
        "passing_marks": "40.00",
        "status": "PUBLISHED",
    }
    create_res = await client.post("/api/v1/assignments", json=assign_payload, headers=teacher_headers)
    assert create_res.status_code == 201
    assignment_id = create_res.json()["data"]["id"]

    # Student submits late
    sub_form = {"submission_text": "Late submission with enthalpy and entropy derivations."}
    submit_res = await client.post(
        f"/api/v1/assignments/{assignment_id}/submit",
        data=sub_form,
        headers=student_headers,
    )
    assert submit_res.status_code == 201
    sub_data = submit_res.json()["data"]
    assert sub_data["is_late"] is True
    submission_id = sub_data["id"]

    # Teacher awards 100.00, but 20% late penalty should reduce marks to 80.00
    eval_payload = {
        "marks_obtained": "100.00",
        "grade": "B+",
        "teacher_feedback": "Perfect solutions, but submitted past deadline.",
        "status": "EVALUATED",
    }
    eval_res = await client.post(
        f"/api/v1/assignments/submissions/{submission_id}/evaluate",
        json=eval_payload,
        headers=teacher_headers,
    )
    assert eval_res.status_code == 200
    # 100.00 - 20% = 80.00
    assert eval_res.json()["data"]["marks_obtained"] == "80.00"
