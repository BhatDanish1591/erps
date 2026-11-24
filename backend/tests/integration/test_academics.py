from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.academic import (
    AcademicFaculty,
    AcademicSession,
    Department,
    SchoolClass,
    Section,
    StudentProfile,
    Subject,
    TeacherProfile,
)
from app.models.auth import Membership, Role
from app.models.enums import BillingCycle, InstitutionType, MembershipStatus, RoleScope, SubscriptionStatus, TenantStatus
from app.models.subscription import Subscription, SubscriptionPlan
from app.models.tenant import Tenant
from app.models.user import User


@pytest.fixture
async def setup_academic_test_data(db_session: AsyncSession, request: pytest.FixtureRequest):
    # 1. Tenant
    tenant = Tenant(
        name="Global University & Model School",
        slug=f"global-{uuid.uuid4().hex[:6]}",
        institution_type=getattr(request, "param", InstitutionType.COLLEGE),
        status=TenantStatus.ACTIVE,
        email=f"admin_{uuid.uuid4().hex[:6]}@global.edu",
    )
    db_session.add(tenant)
    await db_session.flush()

    # 2. Subscription Plan & Active Subscription
    plan = SubscriptionPlan(
        name="Enterprise College Plan",
        code=f"ENT-COL-{uuid.uuid4().hex[:4]}",
        institution_type=InstitutionType.COLLEGE,
        billing_cycle=BillingCycle.YEARLY,
        price=9999.0,
        max_students=5000,
        max_teachers=400,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.flush()

    sub = Subscription(
        tenant_id=tenant.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=365),
    )
    db_session.add(sub)

    # 3. Roles
    role_stmt = select(Role).where(Role.code == "INSTITUTION_ADMIN")
    admin_role = (await db_session.execute(role_stmt)).scalars().first()
    if not admin_role:
        admin_role = Role(name="Institution Admin", code="INSTITUTION_ADMIN", scope=RoleScope.TENANT, is_system_role=True)
        db_session.add(admin_role)
        await db_session.flush()

    t_role_stmt = select(Role).where(Role.code == "TEACHER")
    teacher_role = (await db_session.execute(t_role_stmt)).scalars().first()
    if not teacher_role:
        teacher_role = Role(name="Teacher", code="TEACHER", scope=RoleScope.TENANT, is_system_role=True)
        db_session.add(teacher_role)
        await db_session.flush()

    s_role_stmt = select(Role).where(Role.code == "STUDENT")
    student_role = (await db_session.execute(s_role_stmt)).scalars().first()
    if not student_role:
        student_role = Role(name="Student", code="STUDENT", scope=RoleScope.TENANT, is_system_role=True)
        db_session.add(student_role)
        await db_session.flush()

    # 4. Admin User
    admin_user = User(
        email=f"acad_admin_{uuid.uuid4().hex[:6]}@global.edu",
        password_hash=hash_password("AdminPass123!"),
        full_name="Academic Director",
        is_active=True,
    )
    db_session.add(admin_user)
    await db_session.flush()

    admin_membership = Membership(
        user_id=admin_user.id,
        tenant_id=tenant.id,
        role_id=admin_role.id,
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(admin_membership)

    # 5. Teacher User & Profile
    teacher_user = User(
        email=f"prof_alan_{uuid.uuid4().hex[:6]}@global.edu",
        password_hash=hash_password("TeacherPass123!"),
        full_name="Dr. Alan Turing",
        is_active=True,
    )
    db_session.add(teacher_user)
    await db_session.flush()

    teacher_membership = Membership(
        user_id=teacher_user.id,
        tenant_id=tenant.id,
        role_id=teacher_role.id,
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(teacher_membership)

    teacher_prof = TeacherProfile(
        tenant_id=tenant.id,
        user_id=teacher_user.id,
        employee_id="EMP-2026-0001",
        designation="Professor & HOD",
        qualification="Ph.D. Computer Science",
        status="ACTIVE",
    )
    db_session.add(teacher_prof)

    # 6. Student User & Profile
    student_user = User(
        email=f"stu_alice_{uuid.uuid4().hex[:6]}@global.edu",
        password_hash=hash_password("StudentPass123!"),
        full_name="Alice Smith",
        is_active=True,
    )
    db_session.add(student_user)
    await db_session.flush()

    student_membership = Membership(
        user_id=student_user.id,
        tenant_id=tenant.id,
        role_id=student_role.id,
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(student_membership)

    student_prof = StudentProfile(
        tenant_id=tenant.id,
        user_id=student_user.id,
        admission_number="ADM-2026-0001",
        status="ACTIVE",
    )
    db_session.add(student_prof)

    await db_session.commit()

    token = create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        tenant_id=tenant.id,
        role="INSTITUTION_ADMIN",
        permissions=["*:*"],
    )

    return {
        "tenant": tenant,
        "admin_user": admin_user,
        "teacher_prof": teacher_prof,
        "student_prof": student_prof,
        "token": token,
        "headers": {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(tenant.id),
        },
    }


@pytest.mark.asyncio
async def test_academic_session_and_hierarchy_configuration(
    client: AsyncClient, setup_academic_test_data: dict
):
    headers = setup_academic_test_data["headers"]

    # 1. Create Academic Session
    sess_payload = {
        "name": "2026-2027 Academic Session",
        "code": "AY-2026-27",
        "start_date": "2026-06-01",
        "end_date": "2027-05-31",
        "is_current": True,
        "description": "Main annual session",
    }
    res = await client.post("/api/v1/academics/sessions", json=sess_payload, headers=headers)
    assert res.status_code == 201
    sess_data = res.json()["data"]
    assert sess_data["code"] == "AY-2026-27"
    assert sess_data["is_current"] is True
    session_id = sess_data["id"]

    # 2. Verify invalid date range rejected
    bad_sess = {
        "name": "Invalid Session",
        "code": "AY-BAD",
        "start_date": "2027-06-01",
        "end_date": "2026-05-31",  # end before start
    }
    bad_res = await client.post("/api/v1/academics/sessions", json=bad_sess, headers=headers)
    assert bad_res.status_code == 400

    # 3. List Sessions
    list_res = await client.get("/api/v1/academics/sessions", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # 4. Get and Update Academic Hierarchy
    hier_get = await client.get("/api/v1/academics/hierarchy", headers=headers)
    assert hier_get.status_code == 200
    assert hier_get.json()["data"]["institution_type"] == "COLLEGE"

    for invalid_type in ("HYBRID", "SCHOOL"):
        blocked = await client.put("/api/v1/academics/hierarchy", json={"institution_type": invalid_type}, headers=headers)
        assert blocked.status_code == 400

    hier_update = {
        "academic_system": "SEMESTER",
        "has_faculties": True,
        "has_departments": True,
        "has_batches": True,
        "grading_system": "GPA_10",
        "pass_percentage": 50.0,
        "allow_cross_department_electives": True,
        "max_electives_per_student": 3,
    }
    hier_put = await client.put("/api/v1/academics/hierarchy", json=hier_update, headers=headers)
    assert hier_put.status_code == 200
    updated_hier = hier_put.json()["data"]
    assert updated_hier["institution_type"] == "COLLEGE"
    assert updated_hier["grading_system"] == "GPA_10"
    assert updated_hier["pass_percentage"] == 50.0


@pytest.mark.asyncio
@pytest.mark.parametrize("setup_academic_test_data", [InstitutionType.SCHOOL], indirect=True)
async def test_school_academic_structure(
    client: AsyncClient, setup_academic_test_data: dict
):
    headers = setup_academic_test_data["headers"]
    blocked = await client.post("/api/v1/academics/departments", json={"name": "Science", "code": "SCI"}, headers=headers)
    assert blocked.status_code == 403
    teacher_id = str(setup_academic_test_data["teacher_prof"].id)

    # 1. Create School Classes (Not restricted to 1-12: e.g. Pre-KG, Grade 10)
    pkg_res = await client.post(
        "/api/v1/academics/classes",
        json={"name": "Pre-KG Early Childhood", "code": "PKG", "order_index": 0, "category": "PRE_PRIMARY"},
        headers=headers,
    )
    assert pkg_res.status_code == 201
    pkg_id = pkg_res.json()["data"]["id"]

    g10_res = await client.post(
        "/api/v1/academics/classes",
        json={
            "name": "Standard 10",
            "code": "STD-10",
            "order_index": 10,
            "category": "SECONDARY",
            "class_teacher_id": teacher_id,
        },
        headers=headers,
    )
    assert g10_res.status_code == 201
    g10_id = g10_res.json()["data"]["id"]
    assert g10_res.json()["data"]["class_teacher_id"] == teacher_id

    # 2. Create Sections
    sec_a = await client.post(
        "/api/v1/academics/sections",
        json={"name": "Section A", "capacity": 35, "class_id": g10_id, "room_number": "Room 101", "class_teacher_id": teacher_id},
        headers=headers,
    )
    assert sec_a.status_code == 201
    sec_a_id = sec_a.json()["data"]["id"]

    # 3. Create Subject
    subj_res = await client.post(
        "/api/v1/academics/subjects",
        json={"name": "Advanced Mathematics", "code": "MATH-10", "subject_type": "THEORY", "credits": 4, "hours_per_week": 5},
        headers=headers,
    )
    assert subj_res.status_code == 201
    subj_id = subj_res.json()["data"]["id"]

    # 4. List Classes and Sections
    classes_list = await client.get("/api/v1/academics/classes", headers=headers)
    assert classes_list.status_code == 200
    assert len(classes_list.json()["data"]) >= 2

    sections_list = await client.get(f"/api/v1/academics/sections?class_id={g10_id}", headers=headers)
    assert sections_list.status_code == 200
    assert len(sections_list.json()["data"]) == 1


@pytest.mark.asyncio
async def test_college_academic_structure(
    client: AsyncClient, setup_academic_test_data: dict
):
    headers = setup_academic_test_data["headers"]
    teacher_id = str(setup_academic_test_data["teacher_prof"].id)

    # 1. Create Academic Faculty (Division)
    fac_res = await client.post(
        "/api/v1/academics/faculties",
        json={
            "name": "Faculty of Engineering & Technology",
            "code": "FOET",
            "dean_teacher_id": teacher_id,
            "description": "Engineering disciplines and research",
        },
        headers=headers,
    )
    assert fac_res.status_code == 201
    faculty_id = fac_res.json()["data"]["id"]

    # 2. Create Academic Degree
    deg_res = await client.post(
        "/api/v1/academics/degrees",
        json={"name": "Bachelor of Technology", "code": "B.TECH", "level": "UNDERGRADUATE"},
        headers=headers,
    )
    assert deg_res.status_code == 201
    degree_id = deg_res.json()["data"]["id"]

    # 3. Create Department linked to Faculty
    dept_res = await client.post(
        "/api/v1/academics/departments",
        json={
            "name": "Computer Science & Engineering",
            "code": "CSE",
            "faculty_id": faculty_id,
            "hod_teacher_id": teacher_id,
        },
        headers=headers,
    )
    assert dept_res.status_code == 201
    dept_id = dept_res.json()["data"]["id"]

    # 4. Create Course with 8 semesters (Dynamic semesters generation)
    btech_res = await client.post(
        "/api/v1/academics/courses",
        json={
            "name": "B.Tech Computer Science & Engineering",
            "code": "BT-CSE",
            "department_id": dept_id,
            "degree_id": degree_id,
            "duration_years": 4.0,
            "duration_semesters": 8,
            "coordinator_teacher_id": teacher_id,
        },
        headers=headers,
    )
    assert btech_res.status_code == 201
    btech_id = btech_res.json()["data"]["id"]

    # Verify that exactly 8 default semesters were automatically generated for B.Tech
    sem_list = await client.get(f"/api/v1/academics/semesters?course_id={btech_id}", headers=headers)
    assert sem_list.status_code == 200
    assert len(sem_list.json()["data"]) == 8

    # 5. Create Course with 6 semesters (BCA - testing non-uniform semester duration)
    bca_res = await client.post(
        "/api/v1/academics/courses",
        json={
            "name": "Bachelor of Computer Applications",
            "code": "BCA",
            "department_id": dept_id,
            "degree_id": degree_id,
            "duration_years": 3.0,
            "duration_semesters": 6,
        },
        headers=headers,
    )
    assert bca_res.status_code == 201
    bca_id = bca_res.json()["data"]["id"]
    bca_sems = await client.get(f"/api/v1/academics/semesters?course_id={bca_id}", headers=headers)
    assert len(bca_sems.json()["data"]) == 6

    # 6. Create College Batch
    batch_res = await client.post(
        "/api/v1/academics/batches",
        json={
            "course_id": btech_id,
            "name": "Batch 2024-2028",
            "start_year": 2024,
            "end_year": 2028,
            "current_semester_number": 1,
            "is_active": True,
        },
        headers=headers,
    )
    assert batch_res.status_code == 201
    assert batch_res.json()["data"]["name"] == "Batch 2024-2028"


@pytest.mark.asyncio
@pytest.mark.parametrize("setup_academic_test_data", [InstitutionType.SCHOOL], indirect=True)
async def test_subject_and_teacher_subject_mappings(
    client: AsyncClient, setup_academic_test_data: dict
):
    headers = setup_academic_test_data["headers"]
    teacher_id = str(setup_academic_test_data["teacher_prof"].id)

    # 1. Setup Session, Class, Section, Subject
    sess = await client.post(
        "/api/v1/academics/sessions",
        json={"name": "2026-2027", "code": f"AY-{uuid.uuid4().hex[:4]}", "start_date": "2026-06-01", "end_date": "2027-05-31"},
        headers=headers,
    )
    session_id = sess.json()["data"]["id"]

    cls_res = await client.post(
        "/api/v1/academics/classes",
        json={"name": "Class 12", "code": f"C12-{uuid.uuid4().hex[:4]}", "order_index": 12},
        headers=headers,
    )
    class_id = cls_res.json()["data"]["id"]

    sec_res = await client.post(
        "/api/v1/academics/sections",
        json={"name": "Section Alpha", "capacity": 40, "class_id": class_id},
        headers=headers,
    )
    section_id = sec_res.json()["data"]["id"]

    subj_res = await client.post(
        "/api/v1/academics/subjects",
        json={"name": "Physics", "code": f"PHY-{uuid.uuid4().hex[:4]}", "subject_type": "THEORY", "credits": 4},
        headers=headers,
    )
    subject_id = subj_res.json()["data"]["id"]

    # 2. Map Subject to Class
    map_res = await client.post(
        "/api/v1/academics/subject-mappings",
        json={
            "academic_session_id": session_id,
            "subject_id": subject_id,
            "class_id": class_id,
            "is_elective": False,
            "credits": 4,
            "weekly_hours": 5,
        },
        headers=headers,
    )
    assert map_res.status_code == 201
    mapping_id = map_res.json()["data"]["id"]

    # 3. Map Teacher to Subject and Section
    t_map = await client.post(
        "/api/v1/academics/teacher-subject-mappings",
        json={
            "academic_session_id": session_id,
            "teacher_id": teacher_id,
            "subject_id": subject_id,
            "class_id": class_id,
            "section_id": section_id,
            "is_primary": True,
        },
        headers=headers,
    )
    assert t_map.status_code == 201
    assert t_map.json()["data"]["is_primary"] is True
    t_map_id = t_map.json()["data"]["id"]

    # 4. List and Delete Mapping
    list_t_map = await client.get(f"/api/v1/academics/teacher-subject-mappings?teacher_id={teacher_id}", headers=headers)
    assert list_t_map.status_code == 200
    assert len(list_t_map.json()["data"]) >= 1

    del_res = await client.delete(f"/api/v1/academics/teacher-subject-mappings/{t_map_id}", headers=headers)
    assert del_res.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("setup_academic_test_data", [InstitutionType.SCHOOL], indirect=True)
async def test_common_student_enrollment_model(
    client: AsyncClient, setup_academic_test_data: dict
):
    headers = setup_academic_test_data["headers"]
    student_id = str(setup_academic_test_data["student_prof"].id)

    # 1. Session & School Class
    sess = await client.post(
        "/api/v1/academics/sessions",
        json={"name": "2026-2027", "code": f"AY-{uuid.uuid4().hex[:4]}", "start_date": "2026-06-01", "end_date": "2027-05-31"},
        headers=headers,
    )
    session_id = sess.json()["data"]["id"]

    cls_res = await client.post(
        "/api/v1/academics/classes",
        json={"name": "Grade 9", "code": f"G9-{uuid.uuid4().hex[:4]}", "order_index": 9},
        headers=headers,
    )
    class_id = cls_res.json()["data"]["id"]

    sec_res = await client.post(
        "/api/v1/academics/sections",
        json={"name": "Section Blue", "capacity": 40, "class_id": class_id},
        headers=headers,
    )
    section_id = sec_res.json()["data"]["id"]

    # 2. School Enrollment
    enr_payload = {
        "student_id": student_id,
        "academic_session_id": session_id,
        "enrollment_type": "SCHOOL",
        "roll_number": "15",
        "school_detail": {
            "class_id": class_id,
            "section_id": section_id,
            "stream": "General",
        },
    }
    enr_res = await client.post("/api/v1/academics/enrollments", json=enr_payload, headers=headers)
    assert enr_res.status_code == 201
    enr_data = enr_res.json()["data"]
    assert enr_data["enrollment_type"] == "SCHOOL"
    assert enr_data["enrollment_number"].startswith("ENR-")
    assert enr_data["school_detail"]["class_id"] == class_id
    assert enr_data["school_detail"]["section_id"] == section_id

    # 3. List Enrollments
    enr_list = await client.get(f"/api/v1/academics/enrollments?session_id={session_id}", headers=headers)
    assert enr_list.status_code == 200
    assert len(enr_list.json()["data"]) >= 1


@pytest.mark.asyncio
@pytest.mark.parametrize("setup_academic_test_data", [InstitutionType.SCHOOL], indirect=True)
async def test_student_promotion_and_academic_history(
    client: AsyncClient, setup_academic_test_data: dict
):
    headers = setup_academic_test_data["headers"]
    student_id = str(setup_academic_test_data["student_prof"].id)

    # 1. Setup Session 1 (2026-2027) and Session 2 (2027-2028)
    s1 = await client.post(
        "/api/v1/academics/sessions",
        json={"name": "Session 2026-2027", "code": f"AY1-{uuid.uuid4().hex[:4]}", "start_date": "2026-06-01", "end_date": "2027-05-31"},
        headers=headers,
    )
    session_1_id = s1.json()["data"]["id"]

    s2 = await client.post(
        "/api/v1/academics/sessions",
        json={"name": "Session 2027-2028", "code": f"AY2-{uuid.uuid4().hex[:4]}", "start_date": "2027-06-01", "end_date": "2028-05-31"},
        headers=headers,
    )
    session_2_id = s2.json()["data"]["id"]

    # 2. Classes for S1 and S2
    c9 = await client.post(
        "/api/v1/academics/classes",
        json={"name": "Grade 9", "code": f"G9-{uuid.uuid4().hex[:4]}", "order_index": 9},
        headers=headers,
    )
    c9_id = c9.json()["data"]["id"]
    sec9 = await client.post(
        "/api/v1/academics/sections",
        json={"name": "Sec A", "capacity": 40, "class_id": c9_id},
        headers=headers,
    )
    sec9_id = sec9.json()["data"]["id"]

    c10 = await client.post(
        "/api/v1/academics/classes",
        json={"name": "Grade 10", "code": f"G10-{uuid.uuid4().hex[:4]}", "order_index": 10},
        headers=headers,
    )
    c10_id = c10.json()["data"]["id"]
    sec10 = await client.post(
        "/api/v1/academics/sections",
        json={"name": "Sec A", "capacity": 40, "class_id": c10_id},
        headers=headers,
    )
    sec10_id = sec10.json()["data"]["id"]

    # 3. Enroll in Grade 9 for Session 1
    enr1 = await client.post(
        "/api/v1/academics/enrollments",
        json={
            "student_id": student_id,
            "academic_session_id": session_1_id,
            "enrollment_type": "SCHOOL",
            "school_detail": {"class_id": c9_id, "section_id": sec9_id},
        },
        headers=headers,
    )
    assert enr1.status_code == 201

    # 4. Cohort Promotion: Grade 9 -> Grade 10 in Session 2
    promo_payload = {
        "from_session_id": session_1_id,
        "to_session_id": session_2_id,
        "enrollment_type": "SCHOOL",
        "student_ids": [student_id],
        "target_class_id": c10_id,
        "target_section_id": sec10_id,
        "action": "PROMOTED",
        "remarks": "Promoted with distinction",
    }
    promo_res = await client.post("/api/v1/academics/promotions", json=promo_payload, headers=headers)
    assert promo_res.status_code == 200
    promo_data = promo_res.json()["data"]
    assert len(promo_data) == 1
    assert promo_data[0]["action"] == "PROMOTED"

    # 5. Check Student Academic History
    hist_res = await client.get(f"/api/v1/academics/students/{student_id}/history", headers=headers)
    assert hist_res.status_code == 200
    hist = hist_res.json()["data"]
    assert hist["student_id"] == student_id
    assert len(hist["enrollments"]) >= 2  # S1 Grade 9 and S2 Grade 10
    assert len(hist["promotions"]) >= 1

@pytest.mark.asyncio
async def test_edit_and_delete_semester_and_session(client: AsyncClient, setup_academic_test_data):
    headers = setup_academic_test_data["headers"]
    session = await client.post("/api/v1/academics/sessions", headers=headers, json={
        "name": "Academic year", "code": "TEST-YEAR", "start_date": "2026-01-01", "end_date": "2026-12-31",
    })
    assert session.status_code == 201, session.text
    session_id = session.json()["data"]["id"]
    course = await client.post("/api/v1/academics/courses", headers=headers, json={"name": "Science", "code": "SCI"})
    assert course.status_code == 201, course.text
    semesters = await client.get("/api/v1/academics/semesters", headers=headers, params={"course_id": course.json()["data"]["id"]})
    assert semesters.status_code == 200, semesters.text
    semester_id = semesters.json()["data"][0]["id"]
    changed = await client.patch(f"/api/v1/academics/semesters/{semester_id}", headers=headers, json={"name": "First term", "credits_required": 24})
    assert changed.status_code == 200, changed.text
    listing = await client.get("/api/v1/academics/semesters", headers=headers)
    assert any(row["id"] == semester_id and row["name"] == "First term" for row in listing.json()["data"])
    assert (await client.delete(f"/api/v1/academics/semesters/{semester_id}", headers=headers)).status_code == 200
    assert (await client.patch(f"/api/v1/academics/semesters/{semester_id}", headers=headers, json={"name": "Other"})).status_code == 404
    assert (await client.patch(f"/api/v1/academics/sessions/{session_id}", headers=headers, json={"name": "Revised year"})).status_code == 200
    assert (await client.delete(f"/api/v1/academics/sessions/{session_id}", headers=headers)).status_code == 200
    listing = await client.get("/api/v1/academics/sessions", headers=headers)
    assert all(row["id"] != session_id for row in listing.json()["data"])

@pytest.mark.asyncio
async def test_duplicate_academic_creations_return_useful_conflicts(client: AsyncClient, setup_academic_test_data):
    headers = setup_academic_test_data["headers"]
    session_payload = {"name": "Year", "code": "YEAR-X", "start_date": "2026-01-01", "end_date": "2026-12-31", "is_current": True}
    first = await client.post("/api/v1/academics/sessions", headers=headers, json=session_payload)
    assert first.status_code == 201, first.text
    duplicate = await client.post("/api/v1/academics/sessions", headers=headers, json=session_payload)
    assert duplicate.status_code == 409, duplicate.text
    listed = await client.get("/api/v1/academics/sessions", headers=headers)
    assert any(row["id"] == first.json()["data"]["id"] and row["is_current"] for row in listed.json()["data"])

    dept = await client.post("/api/v1/academics/departments", headers=headers, json={"name": "Sciences", "code": "SCI"})
    assert dept.status_code == 201, dept.text
    course_payload = {"name": "Science Degree", "code": "SCI-1", "department_id": dept.json()["data"]["id"], "duration_semesters": 2}
    course = await client.post("/api/v1/academics/courses", headers=headers, json=course_payload)
    assert course.status_code == 201, course.text
    duplicate_course = await client.post("/api/v1/academics/courses", headers=headers, json=course_payload)
    assert duplicate_course.status_code == 409, duplicate_course.text
    course_id = course.json()["data"]["id"]
    semester_payload = {"course_id": course_id, "semester_number": 1, "name": "Semester 1", "credits_required": 20}
    duplicate_semester = await client.post("/api/v1/academics/semesters", headers=headers, json=semester_payload)
    assert duplicate_semester.status_code == 409, duplicate_semester.text
    assert "already exists" in duplicate_semester.json()["error"]["message"]
    semester_payload.update(semester_number=3, name="Semester 3")
    created = await client.post("/api/v1/academics/semesters", headers=headers, json=semester_payload)
    assert created.status_code == 201, created.text

@pytest.mark.asyncio
async def test_college_subject_catalog_and_course_assignment(client: AsyncClient, setup_academic_test_data):
    headers = setup_academic_test_data["headers"]
    department = await client.post("/api/v1/academics/departments", headers=headers, json={"name": "Computing", "code": "CS"})
    assert department.status_code == 201, department.text
    department_id = department.json()["data"]["id"]
    course = await client.post("/api/v1/academics/courses", headers=headers, json={"name": "Computer Science", "code": "BSC", "department_id": department_id, "duration_semesters": 2})
    assert course.status_code == 201, course.text
    course_id = course.json()["data"]["id"]
    year = await client.post("/api/v1/academics/sessions", headers=headers, json={"name": "Year", "code": "YEAR", "start_date": "2026-01-01", "end_date": "2026-12-31"})
    assert year.status_code == 201, year.text
    subject = await client.post("/api/v1/academics/subjects", headers=headers, json={"name": "Algorithms", "code": "CS101", "department_id": department_id})
    assert subject.status_code == 201, subject.text
    subject_id = subject.json()["data"]["id"]
    duplicate = await client.post("/api/v1/academics/subjects", headers=headers, json={"name": "Other", "code": "CS101", "department_id": department_id})
    assert duplicate.status_code == 409, duplicate.text
    semesters = await client.get("/api/v1/academics/semesters", headers=headers, params={"course_id": course_id})
    semester_id = semesters.json()["data"][0]["id"]
    payload = {"subject_id": subject_id, "academic_session_id": year.json()["data"]["id"], "course_id": course_id, "semester_id": semester_id}
    assignment = await client.post("/api/v1/academics/subject-mappings", headers=headers, json=payload)
    assert assignment.status_code == 201, assignment.text
    assert assignment.json()["data"]["semester_number"] == 1
    repeated = await client.post("/api/v1/academics/subject-mappings", headers=headers, json=payload)
    assert repeated.status_code == 409, repeated.text
    updated = await client.patch(f"/api/v1/academics/subjects/{subject_id}", headers=headers, json={"name": "Advanced Algorithms"})
    assert updated.status_code == 200, updated.text
    deleted = await client.delete(f"/api/v1/academics/subject-mappings/{assignment.json()['data']['id']}", headers=headers)
    assert deleted.status_code == 200
    removed = await client.delete(f"/api/v1/academics/subjects/{subject_id}", headers=headers)
    assert removed.status_code == 200
