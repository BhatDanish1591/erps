from __future__ import annotations

import hmac
import hashlib
import json
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.models.academic import AcademicSession, SchoolClass, Section, StudentProfile
from app.models.auth import Membership, Role
from app.models.user import User
from app.models.fee import (
    FeeCategory,
    FeeDiscountScholarship,
    FeeInvoice,
    FeePayment,
    FeeStructure,
    StudentFeeAllocation,
)
from app.models.tenant import Tenant
from app.services.payment_gateway import razorpay_gateway


@pytest.mark.asyncio
async def test_fee_categories_structures_and_discounts(
    client: AsyncClient,
    db_session: AsyncSession,
):
    session = db_session
    # Setup Tenant and Admin
    tenant = Tenant(name="Fee Tech Academy", slug=f"fee-tech-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    await session.flush()

    user = User(
        email=f"admin-{uuid.uuid4().hex[:6]}@feetech.edu",
        password_hash="hashed_dummy_password",
        full_name="Finance Director",
        is_active=True,
    )
    session.add(user)
    await session.flush()

    admin_role = (await session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))).scalars().first()
    session.add(Membership(tenant_id=tenant.id, user_id=user.id, role_id=admin_role.id))

    academic_session = AcademicSession(
        tenant_id=tenant.id,
        name="Academic Year 2026-2027",
        code=f"AY-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 6, 1),
        end_date=date(2027, 5, 31),
        is_current=True,
    )
    session.add(academic_session)

    school_class = SchoolClass(
        tenant_id=tenant.id,
        name="Grade 10",
        code=f"G10-{uuid.uuid4().hex[:4]}",
        order_index=10,
    )
    session.add(school_class)
    await session.commit()

    token = create_access_token(
        user_id=user.id, email=user.email, tenant_id=tenant.id, role="INSTITUTION_ADMIN"
    )
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant.id)}

    # 1. Verify default categories are auto-seeded
    cat_res = await client.get("/api/v1/fees/categories", headers=headers)
    assert cat_res.status_code == 200
    categories = cat_res.json()
    assert len(categories) >= 8
    codes = [c["code"] for c in categories]
    assert "TUITION" in codes
    assert "ADMISSION" in codes
    assert "EXAMINATION" in codes
    assert "LABORATORY" in codes
    assert "TRANSPORT" in codes
    assert "HOSTEL" in codes

    tuition_cat = next(c for c in categories if c["code"] == "TUITION")
    lab_cat = next(c for c in categories if c["code"] == "LABORATORY")
    exam_cat = next(c for c in categories if c["code"] == "EXAMINATION")

    # 2. Create Custom Category
    custom_res = await client.post(
        "/api/v1/fees/categories",
        json={
            "name": "Robotics Club Fee",
            "code": f"ROBOTICS_{uuid.uuid4().hex[:4]}",
            "fee_type": "OPTIONAL",
            "description": "Annual robotics kit and competition fee",
            "is_refundable": False,
        },
        headers=headers,
    )
    assert custom_res.status_code == 201

    # 3. Create Discounts & Scholarships
    disc_res = await client.post(
        "/api/v1/fees/discounts",
        json={
            "academic_session_id": str(academic_session.id),
            "name": "Merit Scholarship 20%",
            "discount_type": "SCHOLARSHIP",
            "calculation_type": "PERCENTAGE",
            "value": 20.0,
            "applicable_categories": ["TUITION"],
            "criteria": "Scored >90% in previous grade",
        },
        headers=headers,
    )
    assert disc_res.status_code == 201
    disc_data = disc_res.json()
    assert disc_data["value"] == 20.0

    # 4. Create Fee Structure with components & installments
    struct_payload = {
        "academic_session_id": str(academic_session.id),
        "name": "Grade 10 Annual Comprehensive Fee Structure",
        "institution_type": "SCHOOL",
        "class_id": str(school_class.id),
        "frequency": "ANNUAL",
        "currency": "INR",
        "due_date": "2026-07-15",
        "components": [
            {"fee_category_id": tuition_cat["id"], "amount": 60000.0, "is_optional": False},
            {"fee_category_id": lab_cat["id"], "amount": 15000.0, "is_optional": False},
            {"fee_category_id": exam_cat["id"], "amount": 5000.0, "is_optional": False},
        ],
        "installments": [
            {
                "installment_number": 1,
                "name": "Term 1 Installment",
                "due_date": "2026-07-15",
                "amount": 40000.0,
                "late_fine_amount": 500.0,
                "late_fine_type": "FIXED",
                "grace_period_days": 7,
            },
            {
                "installment_number": 2,
                "name": "Term 2 Installment",
                "due_date": "2026-11-15",
                "amount": 40000.0,
                "late_fine_amount": 500.0,
                "late_fine_type": "FIXED",
                "grace_period_days": 7,
            },
        ],
    }

    struct_res = await client.post("/api/v1/fees/structures", json=struct_payload, headers=headers)
    assert struct_res.status_code == 201
    struct_data = struct_res.json()
    assert struct_data["total_amount"] == 80000.0
    assert len(struct_data["components"]) == 3
    assert len(struct_data["installments"]) == 2


@pytest.mark.asyncio
async def test_student_allocation_and_cohort_invoicing(
    client: AsyncClient,
    db_session: AsyncSession,
):
    session = db_session
    tenant = Tenant(name="Finance Test School", slug=f"fin-sch-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    await session.flush()

    admin_user = User(
        email=f"admin-{uuid.uuid4().hex[:6]}@school.edu",
        password_hash="hashed_dummy_password",
        full_name="Bursar Admin",
        is_active=True,
    )
    session.add(admin_user)
    await session.flush()

    admin_role = (await session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))).scalars().first()
    session.add(Membership(tenant_id=tenant.id, user_id=admin_user.id, role_id=admin_role.id))

    academic_session = AcademicSession(
        tenant_id=tenant.id,
        name="Session 2026-27",
        code=f"S26-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 6, 1),
        end_date=date(2027, 5, 31),
        is_current=True,
    )
    session.add(academic_session)

    school_class = SchoolClass(
        tenant_id=tenant.id,
        name="Grade 9",
        code=f"G9-{uuid.uuid4().hex[:4]}",
        order_index=9,
    )
    session.add(school_class)
    await session.flush()

    section = Section(tenant_id=tenant.id, class_id=school_class.id, name="A")
    session.add(section)

    # Create 2 Students
    stud_user_1 = User(email=f"s1-{uuid.uuid4().hex[:6]}@school.edu", password_hash="pw", full_name="Aarav Sharma")
    stud_user_2 = User(email=f"s2-{uuid.uuid4().hex[:6]}@school.edu", password_hash="pw", full_name="Diya Patel")
    session.add_all([stud_user_1, stud_user_2])
    await session.flush()

    student_1 = StudentProfile(
        tenant_id=tenant.id,
        user_id=stud_user_1.id,
        admission_number=f"ADM-{uuid.uuid4().hex[:6].upper()}",
        class_id=school_class.id,
        section_id=section.id,
        father_name="Rajesh Sharma",
        father_phone="+919876543210",
    )
    student_2 = StudentProfile(
        tenant_id=tenant.id,
        user_id=stud_user_2.id,
        admission_number=f"ADM-{uuid.uuid4().hex[:6].upper()}",
        class_id=school_class.id,
        section_id=section.id,
        father_name="Kishore Patel",
        father_phone="+919876543211",
    )
    session.add_all([student_1, student_2])

    # Fee Category & Structure
    cat = FeeCategory(tenant_id=tenant.id, name="Tuition Fee", code="TUITION", fee_type="ACADEMIC")
    session.add(cat)
    await session.flush()

    fee_struct = FeeStructure(
        tenant_id=tenant.id,
        academic_session_id=academic_session.id,
        name="Grade 9 Fee Structure",
        class_id=school_class.id,
        total_amount=50000.0,
    )
    session.add(fee_struct)
    await session.flush()

    # Scholarship for Student 1
    scholarship = FeeDiscountScholarship(
        tenant_id=tenant.id,
        academic_session_id=academic_session.id,
        name="Merit 10%",
        discount_type="SCHOLARSHIP",
        calculation_type="PERCENTAGE",
        value=10.0,
    )
    session.add(scholarship)
    await session.commit()

    token = create_access_token(
        user_id=admin_user.id, email=admin_user.email, tenant_id=tenant.id, role="INSTITUTION_ADMIN"
    )
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant.id)}

    # 1. Allocate fee structure to student 1 with scholarship
    alloc_res = await client.post(
        "/api/v1/fees/allocations",
        json={
            "student_id": str(student_1.id),
            "fee_structure_id": str(fee_struct.id),
            "academic_session_id": str(academic_session.id),
            "discount_id": str(scholarship.id),
        },
        headers=headers,
    )
    assert alloc_res.status_code == 201
    alloc_data = alloc_res.json()
    assert alloc_data["net_fee_amount"] == 45000.0  # 50,000 - 10% (5,000)

    # 2. Bulk Cohort Invoice Generation for Class
    cohort_payload = {
        "academic_session_id": str(academic_session.id),
        "fee_structure_id": str(fee_struct.id),
        "title_prefix": "Term 1 Invoice 2026",
        "issue_date": "2026-07-01",
        "due_date": "2026-07-20",
        "class_id": str(school_class.id),
    }

    gen_res = await client.post("/api/v1/fees/invoices/generate-cohort", json=cohort_payload, headers=headers)
    assert gen_res.status_code == 201
    generated_invoices = gen_res.json()
    assert len(generated_invoices) == 2

    # Verify sequential invoice numbering
    inv1 = generated_invoices[0]
    inv2 = generated_invoices[1]
    assert inv1["invoice_number"].startswith("INV-")
    assert inv2["invoice_number"].startswith("INV-")
    assert inv1["invoice_number"] != inv2["invoice_number"]

    # Student 1 invoice has 10% scholarship deducted
    s1_inv = next(i for i in generated_invoices if i["student_id"] == str(student_1.id))
    assert s1_inv["scholarship_amount"] == 5000.0
    assert s1_inv["total_amount"] == 45000.0
    assert s1_inv["balance_amount"] == 45000.0


@pytest.mark.asyncio
async def test_payments_receipts_and_reconciliation(
    client: AsyncClient,
    db_session: AsyncSession,
):
    session = db_session
    tenant = Tenant(name="Finance College Institute", slug=f"fin-col-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    await session.flush()

    admin_user = User(
        email=f"accountant-{uuid.uuid4().hex[:6]}@college.edu",
        password_hash="hashed_dummy_password",
        full_name="Chief Cashier",
        is_active=True,
    )
    session.add(admin_user)
    await session.flush()

    admin_role = (await session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))).scalars().first()
    session.add(Membership(tenant_id=tenant.id, user_id=admin_user.id, role_id=admin_role.id))

    academic_session = AcademicSession(
        tenant_id=tenant.id,
        name="College AY 2026-27",
        code=f"CAY-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 7, 1),
        end_date=date(2027, 6, 30),
        is_current=True,
    )
    session.add(academic_session)

    school_class = SchoolClass(
        tenant_id=tenant.id,
        name="Senior Secondary",
        code=f"SS-{uuid.uuid4().hex[:4]}",
        order_index=12,
    )
    session.add(school_class)
    await session.flush()

    student_user = User(email=f"stud-{uuid.uuid4().hex[:6]}@college.edu", password_hash="pw", full_name="Rahul Verma")
    session.add(student_user)
    await session.flush()

    student = StudentProfile(
        tenant_id=tenant.id,
        user_id=student_user.id,
        admission_number=f"COL-{uuid.uuid4().hex[:6].upper()}",
        class_id=school_class.id,
        father_name="Sanjay Verma",
        father_phone="+919876543299",
    )
    session.add(student)
    await session.flush()

    # Create Invoice directly
    invoice = FeeInvoice(
        tenant_id=tenant.id,
        student_id=student.id,
        academic_session_id=academic_session.id,
        invoice_number=f"INV-2026-{uuid.uuid4().hex[:5].upper()}",
        title="College Annual Tuition & Lab Fee",
        issue_date=date(2026, 7, 1),
        due_date=date(2026, 7, 25),
        subtotal=50000.0,
        discount_amount=0.0,
        scholarship_amount=0.0,
        late_fine_amount=0.0,
        total_amount=50000.0,
        paid_amount=0.0,
        balance_amount=50000.0,
        status="ISSUED",
        line_items=[
            {"category_name": "Tuition", "description": "Annual tuition", "amount": 40000.0},
            {"category_name": "Lab", "description": "Lab fee", "amount": 10000.0},
        ],
    )
    session.add(invoice)
    await session.commit()

    admin_token = create_access_token(
        user_id=admin_user.id, email=admin_user.email, tenant_id=tenant.id, role="INSTITUTION_ADMIN"
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": str(tenant.id)}

    student_role = (await session.execute(select(Role).where(Role.code == "STUDENT"))).scalars().first()
    session.add(Membership(tenant_id=tenant.id, user_id=student_user.id, role_id=student_role.id))
    await session.commit()

    student_token = create_access_token(
        user_id=student_user.id, email=student_user.email, tenant_id=tenant.id, role="STUDENT"
    )
    student_headers = {"Authorization": f"Bearer {student_token}", "X-Tenant-ID": str(tenant.id)}

    # 1. Record Partial Cash Payment (₹20,000)
    pay1_res = await client.post(
        "/api/v1/fees/payments/offline",
        json={
            "invoice_id": str(invoice.id),
            "amount": 20000.0,
            "payment_mode": "CASH",
            "cash_drawer_reference": "DRAWER-COUNTER-01",
            "remarks": "First installment paid in cash",
        },
        headers=admin_headers,
    )
    assert pay1_res.status_code == 201
    pay1_data = pay1_res.json()
    assert pay1_data["receipt_number"].startswith("REC-")
    assert pay1_data["amount"] == 20000.0
    assert pay1_data["status"] == "SUCCESS"

    # Verify Invoice is now PARTIALLY_PAID with balance ₹30,000
    inv_check = await client.get(f"/api/v1/fees/invoices/{invoice.id}", headers=admin_headers)
    assert inv_check.status_code == 200
    inv_data = inv_check.json()
    assert inv_data["status"] == "PARTIALLY_PAID"
    assert inv_data["paid_amount"] == 20000.0
    assert inv_data["balance_amount"] == 30000.0

    # 2. Record Cheque Payment for the remaining balance (₹30,000)
    pay2_res = await client.post(
        "/api/v1/fees/payments/offline",
        json={
            "invoice_id": str(invoice.id),
            "amount": 30000.0,
            "payment_mode": "CHEQUE",
            "cheque_number": "CHQ-889901",
            "bank_name": "State Bank of India",
            "cheque_date": "2026-07-10",
            "remarks": "Final clearance via cheque",
        },
        headers=admin_headers,
    )
    assert pay2_res.status_code == 201
    pay2_data = pay2_res.json()
    assert pay2_data["receipt_number"].startswith("REC-")
    assert pay2_data["receipt_number"] != pay1_data["receipt_number"]

    # Verify Invoice is now completely PAID with balance 0.0
    inv_check2 = await client.get(f"/api/v1/fees/invoices/{invoice.id}", headers=admin_headers)
    assert inv_check2.json()["status"] == "PAID"
    assert inv_check2.json()["balance_amount"] == 0.0

    # 3. Attempt to overpay beyond balance raises 400
    overpay_res = await client.post(
        "/api/v1/fees/payments/offline",
        json={"invoice_id": str(invoice.id), "amount": 500.0, "payment_mode": "CASH"},
        headers=admin_headers,
    )
    assert overpay_res.status_code == 400

    # 4. View Printable HTML Receipt
    receipt_html = await client.get(f"/api/v1/fees/receipts/{pay1_data['id']}/html", headers=admin_headers)
    assert receipt_html.status_code == 200
    assert "OFFICIAL FEE RECEIPT" in receipt_html.text
    assert "Rahul Verma" in receipt_html.text
    assert pay1_data["receipt_number"] in receipt_html.text

    # 5. Student / Parent Portal (/my-fees)
    my_fees_res = await client.get("/api/v1/fees/my-fees", headers=student_headers)
    assert my_fees_res.status_code == 200
    my_fees_data = my_fees_res.json()
    assert my_fees_data["student"]["name"] == "Rahul Verma"
    assert len(my_fees_data["invoices"]) == 1
    assert len(my_fees_data["payments"]) == 2
    assert my_fees_data["total_paid"] == 50000.0
    assert my_fees_data["total_due"] == 0.0

    # 6. Finance Dashboard Stats
    dash_res = await client.get("/api/v1/fees/dashboard", headers=admin_headers)
    assert dash_res.status_code == 200
    stats = dash_res.json()
    assert stats["total_invoiced_amount"] >= 50000.0
    assert stats["total_collected_amount"] >= 50000.0
    assert "CASH" in stats["collection_by_payment_mode"]
    assert "CHEQUE" in stats["collection_by_payment_mode"]

    # 7. Collection Ledger
    ledger_res = await client.get("/api/v1/fees/reports/collection-ledger", headers=admin_headers)
    assert ledger_res.status_code == 200
    assert ledger_res.json()["total_count"] >= 2


@pytest.mark.asyncio
async def test_razorpay_online_payment_verification_and_webhook_idempotency(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    session = db_session
    tenant = Tenant(name="Online Pay College", slug=f"onl-pay-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    await session.flush()

    student_user = User(
        email=f"online-{uuid.uuid4().hex[:6]}@pay.edu",
        password_hash="pw",
        full_name="Online Pay Student",
    )
    session.add(student_user)
    await session.flush()

    student_role = (await session.execute(select(Role).where(Role.code == "STUDENT"))).scalars().first()
    session.add(Membership(tenant_id=tenant.id, user_id=student_user.id, role_id=student_role.id))

    academic_session = AcademicSession(
        tenant_id=tenant.id,
        name="AY 2026-27",
        code=f"OP-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 6, 1),
        end_date=date(2027, 5, 31),
        is_current=True,
    )
    session.add(academic_session)

    student = StudentProfile(
        tenant_id=tenant.id,
        user_id=student_user.id,
        admission_number=f"OP-{uuid.uuid4().hex[:6].upper()}",
    )
    session.add(student)
    await session.flush()

    invoice = FeeInvoice(
        tenant_id=tenant.id,
        student_id=student.id,
        academic_session_id=academic_session.id,
        invoice_number=f"INV-2026-{uuid.uuid4().hex[:5].upper()}",
        title="Semester 1 Online Registration Fee",
        issue_date=date(2026, 7, 1),
        due_date=date(2026, 7, 30),
        subtotal=25000.0,
        total_amount=25000.0,
        paid_amount=0.0,
        balance_amount=25000.0,
        status="ISSUED",
        line_items=[{"category_name": "Tuition", "amount": 25000.0}],
    )
    session.add(invoice)
    await session.commit()

    token = create_access_token(
        user_id=student_user.id, email=student_user.email, tenant_id=tenant.id, role="STUDENT"
    )
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant.id)}

    # 1. Initiate Razorpay Order
    init_res = await client.post(
        "/api/v1/fees/payments/razorpay/order",
        json={"invoice_id": str(invoice.id), "amount": 25000.0},
        headers=headers,
    )
    assert init_res.status_code == 200
    order_data = init_res.json()
    order_id = order_data["razorpay_order_id"]
    payment_id = order_data["payment_id"]
    assert order_id.startswith("order_")
    assert order_data["amount"] == 25000.0

    # 2. Verify Razorpay Payment: Invalid signature rejected (Never trust frontend response)
    fake_verify_res = await client.post(
        "/api/v1/fees/payments/razorpay/verify",
        json={
            "payment_id": str(payment_id),
            "razorpay_order_id": order_id,
            "razorpay_payment_id": "pay_fake_998877",
            "razorpay_signature": "invalid_forged_signature_hex",
        },
        headers=headers,
    )
    assert fake_verify_res.status_code == 400
    assert "Razorpay signature verification failed" in fake_verify_res.json()["error"]["message"]

    # 3. Verify Razorpay Payment: Valid cryptographic HMAC-SHA256 signature accepted
    key_secret = razorpay_gateway.key_secret or "mock_secret"
    rzp_payment_id = f"pay_{uuid.uuid4().hex[:14]}"
    body_to_sign = f"{order_id}|{rzp_payment_id}".encode("utf-8")
    valid_signature = hmac.new(key_secret.encode("utf-8"), body_to_sign, hashlib.sha256).hexdigest()

    valid_verify_res = await client.post(
        "/api/v1/fees/payments/razorpay/verify",
        json={
            "payment_id": str(payment_id),
            "razorpay_order_id": order_id,
            "razorpay_payment_id": rzp_payment_id,
            "razorpay_signature": valid_signature,
        },
        headers=headers,
    )
    assert valid_verify_res.status_code == 200
    verified_data = valid_verify_res.json()
    assert verified_data["status"] == "SUCCESS"
    assert verified_data["razorpay_payment_id"] == rzp_payment_id

    # Verify Invoice is now completely PAID
    inv_res = await client.get(f"/api/v1/fees/invoices/{invoice.id}", headers=headers)
    assert inv_res.json()["status"] == "PAID"
    assert inv_res.json()["balance_amount"] == 0.0

    # 4. Webhook idempotency test
    webhook_secret = "test_fee_webhook_secret"
    monkeypatch.setattr(razorpay_gateway, "webhook_secret", webhook_secret)
    webhook_payload = {
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": rzp_payment_id,
                    "order_id": order_id,
                    "amount": 2500000,
                    "notes": {"tenant_id": str(tenant.id)},
                }
            }
        },
    }
    raw_payload_bytes = json.dumps(webhook_payload).encode("utf-8")
    webhook_sig = hmac.new(webhook_secret.encode("utf-8"), raw_payload_bytes, hashlib.sha256).hexdigest()

    # First webhook submission -> Processed
    wh_res_1 = await client.post(
        "/api/v1/fees/payments/razorpay/webhook",
        content=raw_payload_bytes,
        headers={"X-Razorpay-Signature": webhook_sig},
    )
    assert wh_res_1.status_code == 200
    assert wh_res_1.json()["status"] == "processed"

    # Duplicate webhook submission -> Idempotently handled
    wh_res_2 = await client.post(
        "/api/v1/fees/payments/razorpay/webhook",
        content=raw_payload_bytes,
        headers={"X-Razorpay-Signature": webhook_sig},
    )
    assert wh_res_2.status_code == 200
    assert wh_res_2.json()["status"] == "already_processed"
