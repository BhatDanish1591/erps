from __future__ import annotations

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
    TeacherAssignment,
    TeacherProfile,
)
from app.models.auth import Membership, Role
from app.models.enums import BillingCycle, InstitutionType, MembershipStatus, RoleScope, TenantStatus
from app.models.examination import Examination
from app.models.subscription import Subscription, SubscriptionPlan
from app.models.tenant import Tenant
from app.models.user import User


@pytest.fixture
async def setup_results_data(db_session: AsyncSession):
    # 1. Tenant
    tenant = Tenant(
        name="St. Xavier's Model Academy",
        slug=f"xavier-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.SCHOOL,
        status=TenantStatus.ACTIVE,
        email=f"xavier_{uuid.uuid4().hex[:6]}@school.edu",
    )
    db_session.add(tenant)
    await db_session.flush()

    # 2. Subscription
    plan = SubscriptionPlan(
        name="Enterprise School Plan",
        code=f"ENT-SCH-{uuid.uuid4().hex[:4]}",
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

    # 4. Users & Profiles
    admin_user = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@xavier.edu",
        password_hash=hash_password("XavierAdmin123!"),
        full_name="Rev. Fr. Principal",
        is_active=True,
    )
    db_session.add(admin_user)
    await db_session.flush()
    db_session.add(Membership(user_id=admin_user.id, tenant_id=tenant.id, role_id=admin_role.id, status=MembershipStatus.ACTIVE))

    teacher_user = User(
        email=f"teacher_{uuid.uuid4().hex[:6]}@xavier.edu",
        password_hash=hash_password("XavierTeacher123!"),
        full_name="Robert Langdon",
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
        email=f"student_{uuid.uuid4().hex[:6]}@xavier.edu",
        password_hash=hash_password("XavierStudent123!"),
        full_name="Peter Parker",
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
        date_of_birth=date(2008, 9, 18),
        admission_date=date(2025, 4, 1),
        status="ACTIVE",
    )
    db_session.add(student_profile)

    # 5. Academic Session, Class, Section, Subject
    session = AcademicSession(
        tenant_id=tenant.id,
        name="2026-2027",
        code=f"SESS-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
    )
    db_session.add(session)
    await db_session.flush()

    school_class = SchoolClass(
        tenant_id=tenant.id,
        name="Grade 10",
        code=f"G10-{uuid.uuid4().hex[:4]}",
    )
    db_session.add(school_class)
    await db_session.flush()

    section = Section(
        tenant_id=tenant.id,
        class_id=school_class.id,
        name="A",
    )
    db_session.add(section)
    await db_session.flush()
    db_session.add(TeacherAssignment(
        tenant_id=tenant.id, teacher_id=teacher_profile.id, academic_session_id=session.id,
        class_id=school_class.id, section_id=section.id,
    ))

    subject_math = Subject(
        tenant_id=tenant.id,
        name="Advanced Mathematics",
        code=f"MATH-{uuid.uuid4().hex[:4]}",
        subject_type="THEORY",
    )
    subject_physics = Subject(
        tenant_id=tenant.id,
        name="Physics",
        code=f"PHYS-{uuid.uuid4().hex[:4]}",
        subject_type="THEORY",
    )
    db_session.add_all([subject_math, subject_physics])
    await db_session.flush()

    # 6. Enrollment
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

    school_enrollment = SchoolEnrollmentDetail(
        tenant_id=tenant.id,
        enrollment_id=enrollment.id,
        class_id=school_class.id,
        section_id=section.id,
    )
    db_session.add(school_enrollment)

    # 7. Examination
    exam = Examination(
        tenant_id=tenant.id,
        academic_session_id=session.id,
        title="Mid-Term Examination 2026",
        code=f"EXAM-MID-{uuid.uuid4().hex[:4]}",
        exam_type="MID_TERM",
        mode="OFFLINE",
        class_id=school_class.id,
        section_id=section.id,
        total_marks=Decimal("100.00"),
        passing_marks=Decimal("35.00"),
        start_datetime=datetime.now(timezone.utc) - timedelta(days=5),
        end_datetime=datetime.now(timezone.utc) - timedelta(days=1),
        status="COMPLETED",
        created_by=admin_user.id,
    )
    db_session.add(exam)
    await db_session.flush()

    await db_session.commit()

    admin_token = create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        tenant_id=tenant.id,
        role="INSTITUTION_ADMIN",
        permissions=["results.create", "results.view", "results.publish", "results.approve"],
    )
    teacher_token = create_access_token(
        user_id=teacher_user.id,
        email=teacher_user.email,
        tenant_id=tenant.id,
        role="TEACHER",
        permissions=["results.create", "results.view"],
    )
    student_token = create_access_token(
        user_id=student_user.id,
        email=student_user.email,
        tenant_id=tenant.id,
        role="STUDENT",
        permissions=["results.view"],
    )

    return {
        "tenant": tenant,
        "admin_user": admin_user,
        "teacher_user": teacher_user,
        "student_user": student_user,
        "teacher_profile": teacher_profile,
        "student_profile": student_profile,
        "session": session,
        "school_class": school_class,
        "section": section,
        "subject_math": subject_math,
        "subject_physics": subject_physics,
        "exam": exam,
        "admin_headers": {"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": str(tenant.id)},
        "teacher_headers": {"Authorization": f"Bearer {teacher_token}", "X-Tenant-ID": str(tenant.id)},
        "student_headers": {"Authorization": f"Bearer {student_token}", "X-Tenant-ID": str(tenant.id)},
    }


@pytest.mark.asyncio
async def test_grading_scales_and_defaults(client: AsyncClient, setup_results_data):
    data = setup_results_data
    headers = data["admin_headers"]

    # 1. Fetch default grading scale
    get_res = await client.get("/api/v1/results/grading-scales", headers=headers)
    assert get_res.status_code == 200, get_res.text
    default_scale = get_res.json()["data"]
    assert "Standard" in default_scale["name"]
    assert len(default_scale["grades"]) >= 8

    # 2. Create a custom grading scale
    create_payload = {
        "name": "Higher Secondary Honours Scale",
        "scale_type": "CBSE_9_POINT",
        "is_default": False,
        "grades": [
            {"grade": "A1", "min_percentage": 91.0, "max_percentage": 100.0, "grade_point": 10.0, "description": "Outstanding"},
            {"grade": "A2", "min_percentage": 81.0, "max_percentage": 90.99, "grade_point": 9.0, "description": "Excellent"},
            {"grade": "B1", "min_percentage": 71.0, "max_percentage": 80.99, "grade_point": 8.0, "description": "Very Good"},
            {"grade": "B2", "min_percentage": 61.0, "max_percentage": 70.99, "grade_point": 7.0, "description": "Good"},
            {"grade": "C1", "min_percentage": 51.0, "max_percentage": 60.99, "grade_point": 6.0, "description": "Fair"},
            {"grade": "C2", "min_percentage": 41.0, "max_percentage": 50.99, "grade_point": 5.0, "description": "Average"},
            {"grade": "D", "min_percentage": 33.0, "max_percentage": 40.99, "grade_point": 4.0, "description": "Pass"},
            {"grade": "E", "min_percentage": 0.0, "max_percentage": 32.99, "grade_point": 0.0, "description": "Needs Improvement"},
        ],
    }

    res = await client.post("/api/v1/results/grading-scales", json=create_payload, headers=headers)
    assert res.status_code == 201, res.text
    scale_data = res.json()["data"]
    assert scale_data["name"] == "Higher Secondary Honours Scale"


@pytest.mark.asyncio
async def test_bulk_marks_entry_calculations_and_recalculation(client: AsyncClient, setup_results_data):
    data = setup_results_data
    teacher_headers = data["teacher_headers"]
    admin_headers = data["admin_headers"]

    # 1. Bulk marks entry for Mathematics
    math_payload = {
        "exam_id": str(data["exam"].id),
        "academic_session_id": str(data["session"].id),
        "subject_id": str(data["subject_math"].id),
        "class_id": str(data["school_class"].id),
        "section_id": str(data["section"].id),
        "entries": [
            {
                "student_id": str(data["student_profile"].id),
                "theory_marks": 68.0,
                "theory_max_marks": 70.0,
                "practical_marks": 0.0,
                "practical_max_marks": 0.0,
                "internal_marks": 19.0,
                "internal_max_marks": 20.0,
                "assignment_marks": 9.0,
                "assignment_max_marks": 10.0,
                "credits": 4.0,
                "remarks": "Solid performance in algebra",
            }
        ],
    }

    res_math = await client.post("/api/v1/results/marks/bulk", json=math_payload, headers=teacher_headers)
    assert res_math.status_code == 200, res_math.text
    entered_math = res_math.json()["data"]
    assert len(entered_math) == 1
    # 68 + 0 + 19 + 9 = 96.0 / 100 -> 96.0%, Grade A1
    assert float(entered_math[0]["total_marks"]) == 96.0
    assert float(entered_math[0]["percentage"]) == 96.0
    assert entered_math[0]["is_passed"] is True
    assert entered_math[0]["grade"] == "A1"

    roster_response = await client.get(
        f"/api/v1/results/exams/{data['exam'].id}/marks-roster",
        params={"subject_id": str(data["subject_math"].id)},
        headers=teacher_headers,
    )
    assert roster_response.status_code == 200, roster_response.text
    roster = roster_response.json()["data"]
    assert [row["student_id"] for row in roster] == [str(data["student_profile"].id)]
    assert roster[0]["theory_marks"] == 68.0

    # 2. Bulk marks entry for Physics
    phys_payload = {
        "exam_id": str(data["exam"].id),
        "academic_session_id": str(data["session"].id),
        "subject_id": str(data["subject_physics"].id),
        "class_id": str(data["school_class"].id),
        "section_id": str(data["section"].id),
        "entries": [
            {
                "student_id": str(data["student_profile"].id),
                "theory_marks": 50.0,
                "theory_max_marks": 70.0,
                "practical_marks": 20.0,
                "practical_max_marks": 20.0,
                "internal_marks": 10.0,
                "internal_max_marks": 10.0,
                "assignment_marks": 0.0,
                "assignment_max_marks": 0.0,
                "credits": 4.0,
                "remarks": "Excellent lab experiment write-up",
            }
        ],
    }

    res_phys = await client.post("/api/v1/results/marks/bulk", json=phys_payload, headers=teacher_headers)
    assert res_phys.status_code == 200, res_phys.text
    entered_phys = res_phys.json()["data"]
    # 50 + 20 + 10 = 80.0 / 100 -> 80.0%, Grade B1
    assert float(entered_phys[0]["total_marks"]) == 80.0
    assert float(entered_phys[0]["percentage"]) == 80.0
    assert entered_phys[0]["is_passed"] is True
    assert entered_phys[0]["grade"] == "B1"

    # 3. Fetch Report Card / Term Result
    report_res = await client.get(
        f"/api/v1/results/exams/{data['exam'].id}/students/{data['student_profile'].id}",
        headers=admin_headers,
    )
    assert report_res.status_code == 200, report_res.text
    term_res = report_res.json()["data"]

    # Total: 96 + 80 = 176 out of 200 -> 88.0%, Overall Grade A2
    assert float(term_res["total_obtained"]) == 176.0
    assert float(term_res["total_max"]) == 200.0
    assert float(term_res["overall_percentage"]) == 88.0
    assert term_res["overall_grade"] == "A2"
    assert term_res["approval_status"] == "DRAFT"
    assert term_res["is_passed"] is True
    assert len(term_res["subject_results"]) == 2


@pytest.mark.asyncio
async def test_workflow_state_transitions_and_immutability(client: AsyncClient, setup_results_data):
    data = setup_results_data
    teacher_headers = data["teacher_headers"]
    admin_headers = data["admin_headers"]
    student_headers = data["student_headers"]

    # Step 1: Teacher enters marks
    bulk_payload = {
        "exam_id": str(data["exam"].id),
        "academic_session_id": str(data["session"].id),
        "subject_id": str(data["subject_math"].id),
        "class_id": str(data["school_class"].id),
        "section_id": str(data["section"].id),
        "entries": [
            {
                "student_id": str(data["student_profile"].id),
                "theory_marks": 65.0,
                "theory_max_marks": 70.0,
                "internal_marks": 10.0,
                "internal_max_marks": 10.0,
                "practical_marks": 0.0,
                "practical_max_marks": 0.0,
                "assignment_marks": 0.0,
                "assignment_max_marks": 0.0,
                "credits": 4.0,
            }
        ],
    }
    await client.post("/api/v1/results/marks/bulk", json=bulk_payload, headers=teacher_headers)

    # Step 2: Student cannot view draft results (403 Forbidden)
    stud_view = await client.get(
        f"/api/v1/results/exams/{data['exam'].id}/students/{data['student_profile'].id}",
        headers=student_headers,
    )
    assert stud_view.status_code == 403

    early_publish = await client.post("/api/v1/results/approval-workflow", headers=admin_headers, json={
        "exam_id": str(data["exam"].id), "action": "PUBLISH",
    })
    assert early_publish.status_code == 400

    # Step 3: Teacher submits for review
    submit_res = await client.post(
        "/api/v1/results/approval-workflow",
        json={"exam_id": str(data["exam"].id), "action": "SUBMIT_FOR_REVIEW", "comments": "Ready for administrative review"},
        headers=teacher_headers,
    )
    assert submit_res.status_code == 200
    assert submit_res.json()["data"]["status"] == "SUBMITTED"
    unauthorized_approval = await client.post("/api/v1/results/approval-workflow", headers=teacher_headers, json={
        "exam_id": str(data["exam"].id), "action": "APPROVE",
    })
    assert unauthorized_approval.status_code == 403

    # Step 4: Admin approves
    approve_res = await client.post(
        "/api/v1/results/approval-workflow",
        json={"exam_id": str(data["exam"].id), "action": "APPROVE"},
        headers=admin_headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["data"]["status"] == "APPROVED"

    # Step 5: Admin publishes results
    publish_res = await client.post(
        "/api/v1/results/approval-workflow",
        json={"exam_id": str(data["exam"].id), "action": "PUBLISH", "comments": "Official results published"},
        headers=admin_headers,
    )
    assert publish_res.status_code == 200
    assert publish_res.json()["data"]["status"] == "PUBLISHED"

    # Step 6: Student can now view published results
    stud_view_published = await client.get(
        f"/api/v1/results/exams/{data['exam'].id}/students/{data['student_profile'].id}",
        headers=student_headers,
    )
    assert stud_view_published.status_code == 200
    assert float(stud_view_published.json()["data"]["overall_percentage"]) == 93.75

    # Step 7: Immutability guard - Teacher attempting direct bulk modification on published results fails
    fail_edit = await client.post(
        "/api/v1/results/marks/bulk",
        json=bulk_payload,
        headers=teacher_headers,
    )
    assert fail_edit.status_code == 400
    assert "published" in fail_edit.text.lower()


@pytest.mark.asyncio
async def test_result_revision_history_and_re_evaluation(client: AsyncClient, setup_results_data):
    data = setup_results_data
    teacher_headers = data["teacher_headers"]
    admin_headers = data["admin_headers"]
    student_headers = data["student_headers"]

    # 1. Enter initial marks
    bulk_payload = {
        "exam_id": str(data["exam"].id),
        "academic_session_id": str(data["session"].id),
        "subject_id": str(data["subject_math"].id),
        "class_id": str(data["school_class"].id),
        "section_id": str(data["section"].id),
        "entries": [
            {
                "student_id": str(data["student_profile"].id),
                "theory_marks": 50.0,
                "theory_max_marks": 70.0,
                "internal_marks": 10.0,
                "internal_max_marks": 10.0,
                "practical_marks": 0.0,
                "practical_max_marks": 0.0,
                "assignment_marks": 0.0,
                "assignment_max_marks": 0.0,
                "credits": 4.0,
            }
        ],
    }
    marks_res = await client.post("/api/v1/results/marks/bulk", json=bulk_payload, headers=teacher_headers)
    subject_result_id = marks_res.json()["data"][0]["id"]

    # Publish result
    for action in ("SUBMIT_FOR_REVIEW", "APPROVE", "PUBLISH"):
        step = await client.post(
            "/api/v1/results/approval-workflow",
            json={"exam_id": str(data["exam"].id), "action": action},
            headers=admin_headers,
        )
        assert step.status_code == 200, step.text

    # 2. Student applies for re-evaluation
    appeal_payload = {
        "subject_result_id": subject_result_id,
        "reason": "Requesting re-checking of Section B calculus questions.",
    }
    appeal_res = await client.post("/api/v1/results/re-evaluations", json=appeal_payload, headers=student_headers)
    assert appeal_res.status_code == 201, appeal_res.text
    appeal_data = appeal_res.json()["data"]
    assert appeal_data["status"] == "PENDING"
    re_eval_id = appeal_data["id"]

    # 3. Admin reviews and resolves re-evaluation with updated marks
    resolution_payload = {
        "status": "APPROVED_UPDATED",
        "reviewer_remarks": "Verified: Question 7 marks were missed in manual totaling (+10 marks).",
        "updated_theory_marks": 60.0,
        "updated_practical_marks": 0.0,
        "updated_internal_marks": 10.0,
    }
    resolve_res = await client.post(
        f"/api/v1/results/re-evaluations/{re_eval_id}/resolve",
        json=resolution_payload,
        headers=admin_headers,
    )
    assert resolve_res.status_code == 200, resolve_res.text
    resolved_data = resolve_res.json()["data"]
    assert resolved_data["status"] == "APPROVED_UPDATED"

    # 4. Verify revision history log was recorded
    history_res = await client.get(
        f"/api/v1/results/revisions/{subject_result_id}",
        headers=admin_headers,
    )
    assert history_res.status_code == 200
    revisions = history_res.json()["data"]
    assert len(revisions) >= 1
    latest_rev = revisions[0]
    assert float(latest_rev["new_marks"]["theory_marks"]) == 60.0
    assert "re-evaluation" in latest_rev["revision_reason"].lower() or "verified" in latest_rev["revision_reason"].lower()

    # 5. Verify updated term result percentage
    updated_term = await client.get(
        f"/api/v1/results/exams/{data['exam'].id}/students/{data['student_profile'].id}",
        headers=admin_headers,
    )
    assert updated_term.status_code == 200
    assert float(updated_term.json()["data"]["total_obtained"]) == 70.0


@pytest.mark.asyncio
async def test_pdf_report_card_download(client: AsyncClient, setup_results_data):
    data = setup_results_data
    teacher_headers = data["teacher_headers"]
    admin_headers = data["admin_headers"]

    # Setup marks and publish
    bulk_payload = {
        "exam_id": str(data["exam"].id),
        "academic_session_id": str(data["session"].id),
        "subject_id": str(data["subject_math"].id),
        "class_id": str(data["school_class"].id),
        "section_id": str(data["section"].id),
        "entries": [
            {
                "student_id": str(data["student_profile"].id),
                "theory_marks": 68.0,
                "theory_max_marks": 70.0,
                "internal_marks": 10.0,
                "internal_max_marks": 10.0,
                "practical_marks": 0.0,
                "practical_max_marks": 0.0,
                "assignment_marks": 0.0,
                "assignment_max_marks": 0.0,
                "credits": 4.0,
            }
        ],
    }
    await client.post("/api/v1/results/marks/bulk", json=bulk_payload, headers=teacher_headers)

    for action in ("SUBMIT_FOR_REVIEW", "APPROVE", "PUBLISH"):
        step = await client.post(
            "/api/v1/results/approval-workflow",
            json={"exam_id": str(data["exam"].id), "action": action},
            headers=admin_headers,
        )
        assert step.status_code == 200, step.text

    # Download PDF
    pdf_res = await client.get(
        f"/api/v1/results/exams/{data['exam'].id}/students/{data['student_profile'].id}/pdf",
        headers=admin_headers,
    )
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in pdf_res.headers["content-disposition"]
    assert pdf_res.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_class_analytics_and_statistics(client: AsyncClient, setup_results_data):
    data = setup_results_data
    teacher_headers = data["teacher_headers"]
    admin_headers = data["admin_headers"]

    # Setup marks and publish
    bulk_payload = {
        "exam_id": str(data["exam"].id),
        "academic_session_id": str(data["session"].id),
        "subject_id": str(data["subject_math"].id),
        "class_id": str(data["school_class"].id),
        "section_id": str(data["section"].id),
        "entries": [
            {
                "student_id": str(data["student_profile"].id),
                "theory_marks": 68.0,
                "theory_max_marks": 70.0,
                "internal_marks": 10.0,
                "internal_max_marks": 10.0,
                "practical_marks": 0.0,
                "practical_max_marks": 0.0,
                "assignment_marks": 0.0,
                "assignment_max_marks": 0.0,
                "credits": 4.0,
            }
        ],
    }
    await client.post("/api/v1/results/marks/bulk", json=bulk_payload, headers=teacher_headers)

    # Get examination analytics
    analytics_res = await client.get(
        f"/api/v1/results/exams/{data['exam'].id}/analytics",
        headers=admin_headers,
    )
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()["data"]
    assert analytics["total_students"] >= 1
    assert analytics["passed_students"] >= 1
    assert float(analytics["pass_percentage"]) == 100.0
