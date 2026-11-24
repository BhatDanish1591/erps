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
    TeacherProfile,
)
from app.models.auth import Membership, Role
from app.models.enums import BillingCycle, InstitutionType, MembershipStatus, RoleScope, TenantStatus
from app.models.examination import (
    Examination,
    ExaminationQuestion,
    QuestionBank,
    StudentExamAnswer,
    StudentExamAttempt,
)
from app.models.subscription import Subscription, SubscriptionPlan
from app.models.tenant import Tenant
from app.models.user import User


@pytest.fixture
async def setup_exam_data(db_session: AsyncSession):
    # 1. Tenant
    tenant = Tenant(
        name="Apex Science Academy",
        slug=f"apex-sci-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.SCHOOL,
        status=TenantStatus.ACTIVE,
        email=f"sci_{uuid.uuid4().hex[:6]}@apex.edu",
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
        email=f"admin_{uuid.uuid4().hex[:6]}@apex.edu",
        password_hash=hash_password("ApexAdmin123!"),
        full_name="Dr. Charles Xavier",
        is_active=True,
    )
    db_session.add(admin_user)
    await db_session.flush()
    db_session.add(Membership(user_id=admin_user.id, tenant_id=tenant.id, role_id=admin_role.id, status=MembershipStatus.ACTIVE))

    teacher_user = User(
        email=f"teacher_{uuid.uuid4().hex[:6]}@apex.edu",
        password_hash=hash_password("ApexTeacher123!"),
        full_name="Professor Hank McCoy",
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
        email=f"student_{uuid.uuid4().hex[:6]}@apex.edu",
        password_hash=hash_password("ApexStudent123!"),
        full_name="Scott Summers",
        is_active=True,
    )
    db_session.add(student_user)
    await db_session.flush()
    db_session.add(Membership(user_id=student_user.id, tenant_id=tenant.id, role_id=student_role.id, status=MembershipStatus.ACTIVE))

    student_profile = StudentProfile(
        tenant_id=tenant.id,
        user_id=student_user.id,
        admission_number=f"ADM-{uuid.uuid4().hex[:4].upper()}",
        gender="MALE",
        date_of_birth=date(2008, 9, 18),
        admission_date=date(2025, 4, 1),
        status="ACTIVE",
    )
    db_session.add(student_profile)

    # 5. Academic Session, Class, Section, Subject
    acad_session = AcademicSession(
        tenant_id=tenant.id,
        name="2026-2027",
        code=f"SESS-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
    )
    db_session.add(acad_session)
    await db_session.flush()

    s_class = SchoolClass(
        tenant_id=tenant.id,
        name="Grade 11",
        code=f"G11-{uuid.uuid4().hex[:4]}",
        order_index=11,
    )
    db_session.add(s_class)
    await db_session.flush()

    section = Section(
        tenant_id=tenant.id,
        class_id=s_class.id,
        name="Section A",
    )
    db_session.add(section)
    await db_session.flush()

    subject = Subject(
        tenant_id=tenant.id,
        name="Physics",
        code=f"PHYS-{uuid.uuid4().hex[:4]}",
        subject_type="THEORY",
    )
    db_session.add(subject)
    await db_session.flush()

    # Enroll Student
    enrollment = StudentAcademicEnrollment(
        tenant_id=tenant.id,
        student_id=student_profile.id,
        academic_session_id=acad_session.id,
        enrollment_type="SCHOOL",
        enrollment_number=f"ENR-{uuid.uuid4().hex[:6].upper()}",
        enrollment_date=date(2026, 4, 1),
        status="ACTIVE",
    )
    db_session.add(enrollment)
    await db_session.flush()

    sch_detail = SchoolEnrollmentDetail(
        tenant_id=tenant.id,
        enrollment_id=enrollment.id,
        class_id=s_class.id,
        section_id=section.id,
    )
    db_session.add(sch_detail)
    await db_session.commit()

    # JWT Tokens
    admin_token = create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        tenant_id=tenant.id,
        role="INSTITUTION_ADMIN",
        permissions=["examinations.create", "examinations.view", "results.publish"],
    )
    teacher_token = create_access_token(
        user_id=teacher_user.id,
        email=teacher_user.email,
        tenant_id=tenant.id,
        role="TEACHER",
        permissions=["examinations.create", "examinations.view"],
    )
    student_token = create_access_token(
        user_id=student_user.id,
        email=student_user.email,
        tenant_id=tenant.id,
        role="STUDENT",
        permissions=["examinations.view"],
    )

    return {
        "tenant": tenant,
        "admin_user": admin_user,
        "teacher_user": teacher_user,
        "student_user": student_user,
        "student_profile": student_profile,
        "acad_session": acad_session,
        "class": s_class,
        "section": section,
        "subject": subject,
        "admin_headers": {"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": str(tenant.id)},
        "teacher_headers": {"Authorization": f"Bearer {teacher_token}", "X-Tenant-ID": str(tenant.id)},
        "student_headers": {"Authorization": f"Bearer {student_token}", "X-Tenant-ID": str(tenant.id)},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Integration Test Suite
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_question_bank_crud(client: AsyncClient, setup_exam_data):
    data = setup_exam_data
    headers = data["teacher_headers"]

    # 1. Create Question in Question Bank
    create_payload = {
        "subject_id": str(data["subject"].id),
        "category": "Thermodynamics",
        "difficulty": "MEDIUM",
        "question_type": "MCQ",
        "question_text": "What is the SI unit of thermodynamic temperature?",
        "options": [
            {"id": "opt_a", "text": "Celsius"},
            {"id": "opt_b", "text": "Fahrenheit"},
            {"id": "opt_c", "text": "Kelvin"},
            {"id": "opt_d", "text": "Rankine"},
        ],
        "correct_answer": "opt_c",
        "explanation": "Kelvin is the primary unit of temperature in the International System of Units.",
        "default_marks": 2.0,
        "default_negative_marks": 0.5,
        "is_active": True,
    }

    res = await client.post("/api/v1/examinations/questions", json=create_payload, headers=headers)
    assert res.status_code == 201, res.text
    res_data = res.json()
    assert res_data["success"] is True
    q_id = res_data["data"]["id"]
    assert res_data["data"]["category"] == "Thermodynamics"
    assert res_data["data"]["correct_answer"] == "opt_c"

    # 2. List Questions
    list_res = await client.get("/api/v1/examinations/questions?difficulty=MEDIUM", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 3. Get Question Detail
    get_res = await client.get(f"/api/v1/examinations/questions/{q_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["question_text"] == create_payload["question_text"]

    # 4. Update Question
    update_res = await client.put(
        f"/api/v1/examinations/questions/{q_id}",
        json={"difficulty": "HARD", "default_marks": 4.0},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["difficulty"] == "HARD"
    assert float(update_res.json()["data"]["default_marks"]) == 4.0


@pytest.mark.asyncio
async def test_examination_creation_and_question_linking(client: AsyncClient, setup_exam_data):
    data = setup_exam_data
    headers = data["admin_headers"]

    # First add a question in the bank
    bank_res = await client.post(
        "/api/v1/examinations/questions",
        json={
            "subject_id": str(data["subject"].id),
            "category": "Kinematics",
            "difficulty": "EASY",
            "question_type": "TRUE_FALSE",
            "question_text": "Acceleration is a vector quantity.",
            "options": [{"id": "true", "text": "True"}, {"id": "false", "text": "False"}],
            "correct_answer": "true",
            "default_marks": 1.0,
            "default_negative_marks": 0.0,
        },
        headers=headers,
    )
    assert bank_res.status_code == 201
    bank_q_id = bank_res.json()["data"]["id"]

    # Create Examination
    exam_payload = {
        "academic_session_id": str(data["acad_session"].id),
        "title": "Physics Mid-Term Exam 2026",
        "code": "PHYS-MID-01",
        "exam_type": "MID_TERM",
        "mode": "ONLINE",
        "subject_id": str(data["subject"].id),
        "class_id": str(data["class"].id),
        "section_id": str(data["section"].id),
        "total_marks": 50.0,
        "passing_marks": 20.0,
        "duration_minutes": 90,
        "shuffle_questions": True,
        "shuffle_options": True,
        "status": "SCHEDULED",
        "is_published": True,
        "question_ids": [bank_q_id],
    }

    create_res = await client.post("/api/v1/examinations/", json=exam_payload, headers=headers)
    assert create_res.status_code == 201, create_res.text
    exam = create_res.json()["data"]
    assert exam["title"] == "Physics Mid-Term Exam 2026"
    assert exam["questions_count"] == 1
    exam_id = exam["id"]

    # Add an ad-hoc custom question to the examination
    custom_q_payload = {
        "question_type": "NUMERICAL",
        "custom_question_text": "If a car travels 100 meters in 5 seconds, what is its speed in m/s?",
        "custom_correct_answer": {"value": 20, "tolerance": 0.1},
        "custom_explanation": "Speed = Distance / Time = 100 / 5 = 20 m/s",
        "marks": 5.0,
        "negative_marks": 1.0,
        "order_index": 2,
    }
    add_q_res = await client.post(
        f"/api/v1/examinations/{exam_id}/questions", json=custom_q_payload, headers=headers
    )
    assert add_q_res.status_code == 201, add_q_res.text
    assert add_q_res.json()["data"]["question_type"] == "NUMERICAL"


@pytest.mark.asyncio
async def test_student_exam_taking_security_timer_and_autosave(client: AsyncClient, setup_exam_data):
    data = setup_exam_data
    admin_headers = data["admin_headers"]
    student_headers = data["student_headers"]

    # Create exam with MCQ question
    bank_res = await client.post(
        "/api/v1/examinations/questions",
        json={
            "subject_id": str(data["subject"].id),
            "category": "Optics",
            "difficulty": "EASY",
            "question_type": "MCQ",
            "question_text": "What is the speed of light in vacuum?",
            "options": [
                {"id": "a", "text": "3 x 10^8 m/s"},
                {"id": "b", "text": "3 x 10^6 m/s"},
                {"id": "c", "text": "3 x 10^4 m/s"},
            ],
            "correct_answer": "a",
            "explanation": "Speed of light in vacuum is approximately 300,000,000 m/s.",
            "default_marks": 5.0,
            "default_negative_marks": 1.0,
        },
        headers=admin_headers,
    )
    q_id = bank_res.json()["data"]["id"]

    exam_res = await client.post(
        "/api/v1/examinations/",
        json={
            "academic_session_id": str(data["acad_session"].id),
            "title": "Optics Quick Quiz",
            "exam_type": "DAILY_TEST",
            "mode": "ONLINE",
            "subject_id": str(data["subject"].id),
            "class_id": str(data["class"].id),
            "section_id": str(data["section"].id),
            "total_marks": 10.0,
            "passing_marks": 4.0,
            "duration_minutes": 30,
            "is_published": True,
            "question_ids": [q_id],
        },
        headers=admin_headers,
    )
    exam_id = exam_res.json()["data"]["id"]

    # 1. Student Starts Exam
    start_res = await client.post(f"/api/v1/examinations/{exam_id}/start", headers=student_headers)
    assert start_res.status_code == 200, start_res.text
    attempt = start_res.json()["data"]
    attempt_id = attempt["attempt_id"]
    assert attempt["status"] == "IN_PROGRESS"
    assert attempt["remaining_seconds"] > 0
    assert len(attempt["questions"]) == 1

    # CRITICAL SECURITY VERIFICATION: correct_answer & explanation MUST NOT be revealed to student!
    stu_q = attempt["questions"][0]
    assert "correct_answer" not in stu_q or stu_q["correct_answer"] is None
    assert "explanation" not in stu_q or stu_q["explanation"] is None

    # 2. Student Autosaves draft answer
    exam_q_id = stu_q["id"]
    autosave_res = await client.post(
        f"/api/v1/examinations/attempts/{attempt_id}/autosave",
        json={"answers": [{"question_id": exam_q_id, "student_answer": "a"}]},
        headers=student_headers,
    )
    assert autosave_res.status_code == 200, autosave_res.text
    assert autosave_res.json()["data"]["autosaved_count"] == 1

    # 3. Student Submits Exam
    submit_res = await client.post(
        f"/api/v1/examinations/attempts/{attempt_id}/submit",
        json={"submission_hash": "hash-test-123", "final_answers": []},
        headers=student_headers,
    )
    assert submit_res.status_code == 200, submit_res.text
    sub_data = submit_res.json()["data"]
    assert sub_data["status"] == "EVALUATED"
    assert float(sub_data["instant_score"]) == 5.0
    assert sub_data["is_evaluated"] is True

    # 4. Idempotent re-submission should succeed without double-evaluation
    re_submit = await client.post(
        f"/api/v1/examinations/attempts/{attempt_id}/submit",
        json={"submission_hash": "hash-test-123"},
        headers=student_headers,
    )
    assert re_submit.status_code == 200
    assert re_submit.json()["data"]["status"] == "EVALUATED"


@pytest.mark.asyncio
async def test_subjective_evaluation_and_results_publication(client: AsyncClient, setup_exam_data):
    data = setup_exam_data
    admin_headers = data["admin_headers"]
    teacher_headers = data["teacher_headers"]
    student_headers = data["student_headers"]

    # 1. Create Exam with Subjective (Long Answer) Question
    exam_res = await client.post(
        "/api/v1/examinations/",
        json={
            "academic_session_id": str(data["acad_session"].id),
            "title": "Quantum Mechanics Essay Test",
            "exam_type": "UNIT_TEST",
            "mode": "ONLINE",
            "subject_id": str(data["subject"].id),
            "class_id": str(data["class"].id),
            "section_id": str(data["section"].id),
            "total_marks": 20.0,
            "passing_marks": 8.0,
            "duration_minutes": 60,
            "is_published": True,
        },
        headers=admin_headers,
    )
    exam_id = exam_res.json()["data"]["id"]

    # Add Long Answer Question
    q_res = await client.post(
        f"/api/v1/examinations/{exam_id}/questions",
        json={
            "question_type": "LONG_ANSWER",
            "custom_question_text": "Explain the wave-particle duality and photoelectric effect.",
            "custom_explanation": "Wave-particle duality posits that every particle exhibits both wave and particle properties.",
            "marks": 20.0,
            "negative_marks": 0.0,
        },
        headers=admin_headers,
    )
    assert q_res.status_code == 201
    exam_q_id = q_res.json()["data"]["id"]

    # 2. Student starts and submits answer
    start_res = await client.post(f"/api/v1/examinations/{exam_id}/start", headers=student_headers)
    attempt_id = start_res.json()["data"]["attempt_id"]

    sub_res = await client.post(
        f"/api/v1/examinations/attempts/{attempt_id}/submit",
        json={
            "final_answers": [
                {
                    "question_id": exam_q_id,
                    "student_answer": "Light behaves as both a continuous wave and discrete packets of energy called photons.",
                }
            ]
        },
        headers=student_headers,
    )
    assert sub_res.status_code == 200
    # Status should be SUBMITTED, not EVALUATED yet because question is subjective
    assert sub_res.json()["data"]["status"] == "SUBMITTED"
    assert sub_res.json()["data"]["is_evaluated"] is False

    # 3. Teacher views attempt for evaluation
    eval_view_res = await client.get(
        f"/api/v1/examinations/attempts/{attempt_id}/evaluation", headers=teacher_headers
    )
    assert eval_view_res.status_code == 200
    eval_data = eval_view_res.json()["data"]
    assert eval_data["status"] == "SUBMITTED"
    assert len(eval_data["answers"]) == 1
    answer_id = eval_data["answers"][0]["id"]

    # 4. Teacher submits evaluation
    grade_res = await client.post(
        f"/api/v1/examinations/attempts/{attempt_id}/evaluate",
        json={
            "evaluations": [
                {
                    "answer_id": answer_id,
                    "marks_awarded": 18.0,
                    "teacher_feedback": "Excellent explanation of photons and wave properties!",
                }
            ]
        },
        headers=teacher_headers,
    )
    assert grade_res.status_code == 200
    graded_data = grade_res.json()["data"]
    assert graded_data["status"] == "EVALUATED"
    assert float(graded_data["total_score"]) == 18.0
    assert graded_data["is_passed"] is True

    # 5. Result Release Guard:
    # Student views result when results NOT yet published -> score returned, but review_questions is null
    res_unpublished = await client.get(
        f"/api/v1/examinations/attempts/{attempt_id}/result", headers=student_headers
    )
    assert res_unpublished.status_code == 200
    assert res_unpublished.json()["data"]["is_results_published"] is False
    assert res_unpublished.json()["data"]["review_questions"] is None

    # Admin publishes results
    pub_res = await client.put(
        f"/api/v1/examinations/{exam_id}", json={"is_results_published": True}, headers=admin_headers
    )
    assert pub_res.status_code == 200

    # Student views result when results ARE published -> full review breakdown is visible!
    res_published = await client.get(
        f"/api/v1/examinations/attempts/{attempt_id}/result", headers=student_headers
    )
    assert res_published.status_code == 200
    pub_data = res_published.json()["data"]
    assert pub_data["is_results_published"] is True
    assert len(pub_data["review_questions"]) == 1
    assert pub_data["review_questions"][0]["teacher_feedback"] == "Excellent explanation of photons and wave properties!"

    # 6. Analytics
    analytics_res = await client.get(f"/api/v1/examinations/{exam_id}/analytics", headers=admin_headers)
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()["data"]
    assert analytics["total_attempts"] == 1
    assert analytics["evaluated_count"] == 1
    assert analytics["highest_score"] == 18.0
    assert analytics["pass_percentage"] == 100.0
