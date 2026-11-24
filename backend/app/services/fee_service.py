from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date, datetime, timezone
from html import escape
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import set_tenant_session_context
from app.core.exceptions import AuthorizationException, BadRequestException, NotFoundException, ValidationException
from app.core.logging import get_logger
from app.models.academic import AcademicSession, Course, SchoolClass, Section, StudentAcademicEnrollment, StudentParent, StudentProfile
from app.models.fee import (
    FeeCategory,
    FeeDiscountScholarship,
    FeeInvoice,
    FeePayment,
    FeeStructure,
    StudentFeeAllocation,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.fee import FeeRepository
from app.schemas.fee import (
    FeeCategoryResponse,
    FeeCollectionLedgerItem,
    FeeCollectionLedgerResponse,
    FeeDashboardStatsResponse,
    FeeDiscountResponse,
    FeeInvoiceResponse,
    FeePaymentResponse,
    FeeReceiptResponse,
    FeeStructureComponentResponse,
    FeeStructureInstallmentResponse,
    FeeStructureResponse,
    OnlineFeePaymentInitiateResponse,
    OutstandingDefaulterItem,
    OutstandingDuesReportResponse,
    StudentFeeAllocationResponse,
)
from app.services.payment_gateway import razorpay_gateway

logger = get_logger(__name__)

DEFAULT_FEE_CATEGORIES = [
    {"name": "Admission Fee", "code": "ADMISSION", "fee_type": "ONE_TIME", "description": "New admission & registration charge"},
    {"name": "Tuition Fee", "code": "TUITION", "fee_type": "ACADEMIC", "description": "Core academic instructional fee"},
    {"name": "Examination Fee", "code": "EXAMINATION", "fee_type": "ACADEMIC", "description": "Term & annual board exam fees"},
    {"name": "Laboratory Fee", "code": "LABORATORY", "fee_type": "ACADEMIC", "description": "Science & computer laboratory consumables"},
    {"name": "Transport Fee", "code": "TRANSPORT", "fee_type": "FACILITY", "description": "School bus / transit facility fee"},
    {"name": "Hostel Fee", "code": "HOSTEL", "fee_type": "FACILITY", "description": "Boarding & lodging accommodation charge"},
    {"name": "Semester Fee", "code": "SEMESTER", "fee_type": "ACADEMIC", "description": "College semester registration & course fee"},
    {"name": "Library Fee", "code": "LIBRARY", "fee_type": "FACILITY", "description": "Library accession & learning resource fee"},
    {"name": "Sports & Activity Fee", "code": "SPORTS", "fee_type": "OPTIONAL", "description": "Athletic facilities & co-curricular charge"},
    {"name": "Custom Fee", "code": "CUSTOM", "fee_type": "OPTIONAL", "description": "Miscellaneous or institutional customized fee"},
]


def number_to_words_indian(num: float) -> str:
    """Converts a monetary number into Indian Currency words (e.g. 'Twenty-Five Thousand Rupees Only')."""
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    n = int(round(num))
    if n == 0:
        return "Zero Rupees Only"

    def two_digits(val: int) -> str:
        if val == 0:
            return ""
        if val < 10:
            return units[val]
        if val < 20:
            return teens[val - 10]
        t = tens[val // 10]
        u = units[val % 10]
        return f"{t} {u}".strip()

    crore = n // 10000000
    n %= 10000000
    lakh = n // 100000
    n %= 100000
    thousand = n // 1000
    n %= 1000
    hundred = n // 100
    rem = n % 100

    parts = []
    if crore:
        parts.append(f"{two_digits(crore)} Crore")
    if lakh:
        parts.append(f"{two_digits(lakh)} Lakh")
    if thousand:
        parts.append(f"{two_digits(thousand)} Thousand")
    if hundred:
        parts.append(f"{units[hundred]} Hundred")
    if rem:
        parts.append(two_digits(rem))

    return f"{' '.join(parts).strip()} Rupees Only"


class FeeService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = FeeRepository(session)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Fee Categories
    # ─────────────────────────────────────────────────────────────────────────

    async def ensure_default_categories(self, tenant_id: uuid.UUID) -> None:
        """Seed standard fee categories if none exist for tenant."""
        existing = await self.repo.list_categories(tenant_id)
        if not existing:
            for cat in DEFAULT_FEE_CATEGORIES:
                await self.repo.create_category(tenant_id, cat)

    async def create_category(self, tenant_id: uuid.UUID, data: Dict[str, Any]) -> FeeCategoryResponse:
        existing = await self.repo.get_category_by_code(tenant_id, data["code"])
        if existing:
            raise BadRequestException(f"Fee category with code '{data['code']}' already exists.")
        cat = await self.repo.create_category(tenant_id, data)
        return FeeCategoryResponse.model_validate(cat)

    async def list_categories(self, tenant_id: uuid.UUID) -> List[FeeCategoryResponse]:
        await self.ensure_default_categories(tenant_id)
        categories = await self.repo.list_categories(tenant_id)
        return [FeeCategoryResponse.model_validate(c) for c in categories]

    async def update_category(self, tenant_id: uuid.UUID, category_id: uuid.UUID, data: Dict[str, Any]) -> FeeCategoryResponse:
        cat = await self.repo.update_category(tenant_id, category_id, data)
        if not cat:
            raise NotFoundException("Fee category not found.")
        return FeeCategoryResponse.model_validate(cat)

    async def delete_category(self, tenant_id: uuid.UUID, category_id: uuid.UUID) -> bool:
        return await self.repo.delete_category(tenant_id, category_id)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Fee Structures
    # ─────────────────────────────────────────────────────────────────────────

    async def create_structure(self, tenant_id: uuid.UUID, data: Dict[str, Any]) -> FeeStructureResponse:
        struct = await self.repo.create_structure(tenant_id, data)
        detailed = await self.repo.get_structure(tenant_id, struct.id)
        return self._format_structure_response(detailed or struct)

    async def get_structure(self, tenant_id: uuid.UUID, structure_id: uuid.UUID) -> FeeStructureResponse:
        struct = await self.repo.get_structure(tenant_id, structure_id)
        if not struct:
            raise NotFoundException("Fee structure not found.")
        return self._format_structure_response(struct)

    async def list_structures(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
    ) -> List[FeeStructureResponse]:
        structs = await self.repo.list_structures(tenant_id, academic_session_id, class_id, course_id)
        return [self._format_structure_response(s) for s in structs]

    async def delete_structure(self, tenant_id: uuid.UUID, structure_id: uuid.UUID) -> bool:
        return await self.repo.delete_structure(tenant_id, structure_id)

    def _format_structure_response(self, s: FeeStructure) -> FeeStructureResponse:
        components = []
        for c in s.components:
            components.append(
                FeeStructureComponentResponse(
                    id=c.id,
                    fee_structure_id=c.fee_structure_id,
                    fee_category_id=c.fee_category_id,
                    category_name=c.category.name if c.category else None,
                    category_code=c.category.code if c.category else None,
                    amount=float(c.amount),
                    is_optional=c.is_optional,
                    description=c.description,
                    created_at=c.created_at,
                )
            )

        installments = [
            FeeStructureInstallmentResponse(
                id=i.id,
                fee_structure_id=i.fee_structure_id,
                installment_number=i.installment_number,
                name=i.name,
                due_date=i.due_date,
                amount=float(i.amount),
                late_fine_amount=float(i.late_fine_amount),
                late_fine_type=i.late_fine_type,
                grace_period_days=i.grace_period_days,
                created_at=i.created_at,
            )
            for i in s.installments
        ]

        return FeeStructureResponse(
            id=s.id,
            tenant_id=s.tenant_id,
            academic_session_id=s.academic_session_id,
            academic_session_name=s.academic_session.name if s.academic_session else None,
            name=s.name,
            institution_type=s.institution_type,
            class_id=s.class_id,
            class_name=s.school_class.name if s.school_class else None,
            course_id=s.course_id,
            course_name=s.course.name if s.course else None,
            semester_id=s.semester_id,
            batch_id=s.batch_id,
            frequency=s.frequency,
            total_amount=float(s.total_amount),
            currency=s.currency,
            due_date=s.due_date,
            is_active=s.is_active,
            components=components,
            installments=installments,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Discounts & Scholarships
    # ─────────────────────────────────────────────────────────────────────────

    async def create_discount(self, tenant_id: uuid.UUID, data: Dict[str, Any]) -> FeeDiscountResponse:
        disc = await self.repo.create_discount(tenant_id, data)
        return FeeDiscountResponse.model_validate(disc)

    async def list_discounts(
        self, tenant_id: uuid.UUID, academic_session_id: Optional[uuid.UUID] = None
    ) -> List[FeeDiscountResponse]:
        discs = await self.repo.list_discounts(tenant_id, academic_session_id)
        return [FeeDiscountResponse.model_validate(d) for d in discs]

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Student Fee Allocations
    # ─────────────────────────────────────────────────────────────────────────

    async def allocate_student_fee(self, tenant_id: uuid.UUID, data: Dict[str, Any]) -> StudentFeeAllocationResponse:
        struct = await self.repo.get_structure(tenant_id, data["fee_structure_id"])
        if not struct:
            raise NotFoundException("Fee structure not found.")

        base_amount = float(struct.total_amount)
        discount_amount = float(data.get("custom_discount_amount", 0.0))

        if data.get("discount_id"):
            disc = await self.repo.get_discount(tenant_id, data["discount_id"])
            if disc:
                if disc.calculation_type == "PERCENTAGE":
                    discount_amount += (base_amount * float(disc.value) / 100.0)
                else:
                    discount_amount += float(disc.value)

        net_amount = max(0.0, base_amount - discount_amount)
        payload = {**data, "net_fee_amount": net_amount}

        alloc = await self.repo.create_allocation(tenant_id, payload)
        return self._format_allocation_response(alloc)

    async def bulk_allocate_fee_structure(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: uuid.UUID,
        fee_structure_id: uuid.UUID,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        student_ids: Optional[List[uuid.UUID]] = None,
    ) -> int:
        struct = await self.repo.get_structure(tenant_id, fee_structure_id)
        if not struct:
            raise NotFoundException("Fee structure not found.")

        # Find target students
        stmt = select(StudentProfile).where(StudentProfile.tenant_id == tenant_id, StudentProfile.is_deleted == False)
        if student_ids:
            stmt = stmt.where(StudentProfile.id.in_(student_ids))
        elif class_id:
            stmt = stmt.where(StudentProfile.class_id == class_id)
            if section_id:
                stmt = stmt.where(StudentProfile.section_id == section_id)
        elif course_id:
            stmt = stmt.where(StudentProfile.course_id == course_id)

        students = list((await self.session.execute(stmt)).scalars().all())
        allocated_count = 0

        for stud in students:
            # Check if allocation already exists
            existing = await self.repo.get_allocation_by_student_session(tenant_id, stud.id, academic_session_id)
            if not existing:
                await self.repo.create_allocation(
                    tenant_id,
                    {
                        "student_id": stud.id,
                        "fee_structure_id": fee_structure_id,
                        "academic_session_id": academic_session_id,
                        "net_fee_amount": float(struct.total_amount),
                    },
                )
                allocated_count += 1

        return allocated_count

    def _format_allocation_response(self, a: StudentFeeAllocation) -> StudentFeeAllocationResponse:
        s_name = a.student.user.full_name if (a.student and a.student.user) else None
        s_adm = a.student.admission_number if a.student else None
        struct_name = a.fee_structure.name if a.fee_structure else None
        d_name = a.discount.name if a.discount else None

        return StudentFeeAllocationResponse(
            id=a.id,
            tenant_id=a.tenant_id,
            student_id=a.student_id,
            student_name=s_name,
            admission_number=s_adm,
            fee_structure_id=a.fee_structure_id,
            fee_structure_name=struct_name,
            academic_session_id=a.academic_session_id,
            discount_id=a.discount_id,
            discount_name=d_name,
            custom_discount_amount=float(a.custom_discount_amount),
            discount_reason=a.discount_reason,
            net_fee_amount=float(a.net_fee_amount),
            status=a.status,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Invoices & Cohort Generation
    # ─────────────────────────────────────────────────────────────────────────

    async def create_invoice(self, tenant_id: uuid.UUID, data: Dict[str, Any]) -> FeeInvoiceResponse:
        line_items = data.get("line_items", [])
        subtotal = sum(float(item["amount"]) for item in line_items)
        payload = {**data, "subtotal": subtotal}
        inv = await self.repo.create_invoice(tenant_id, payload)
        return self._format_invoice_response(inv)

    async def generate_cohort_invoices(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: uuid.UUID,
        fee_structure_id: uuid.UUID,
        title_prefix: str,
        issue_date: date,
        due_date: date,
        installment_number: Optional[int] = None,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
    ) -> List[FeeInvoiceResponse]:
        struct = await self.repo.get_structure(tenant_id, fee_structure_id)
        if not struct:
            raise NotFoundException("Fee structure not found.")

        # Determine target installment or full amount
        installment = None
        if installment_number:
            installment = next((i for i in struct.installments if i.installment_number == installment_number), None)
            if not installment:
                raise BadRequestException(f"Installment number {installment_number} does not exist in structure.")

        # Find target students
        stmt = select(StudentProfile).where(StudentProfile.tenant_id == tenant_id, StudentProfile.is_deleted == False)
        if class_id:
            stmt = stmt.where(StudentProfile.class_id == class_id)
            if section_id:
                stmt = stmt.where(StudentProfile.section_id == section_id)
        elif course_id:
            stmt = stmt.where(StudentProfile.course_id == course_id)

        students = list((await self.session.execute(stmt)).scalars().all())
        invoices: List[FeeInvoiceResponse] = []

        for stud in students:
            # Check student allocation for discounts
            alloc = await self.repo.get_allocation_by_student_session(tenant_id, stud.id, academic_session_id)
            discount_amount = float(alloc.custom_discount_amount) if alloc else 0.0
            scholarship_amount = 0.0

            if alloc and alloc.discount:
                if alloc.discount.calculation_type == "PERCENTAGE":
                    pct = float(alloc.discount.value) / 100.0
                    if installment:
                        scholarship_amount = float(installment.amount) * pct
                    else:
                        scholarship_amount = float(struct.total_amount) * pct
                else:
                    scholarship_amount = float(alloc.discount.value)

            # Build line items
            if installment:
                inv_title = f"{title_prefix} - {installment.name}"
                subtotal = float(installment.amount)
                line_items = [
                    {
                        "category_name": "Installment Fee",
                        "description": f"{installment.name} of {struct.name}",
                        "amount": subtotal,
                    }
                ]
            else:
                inv_title = f"{title_prefix} - {struct.name}"
                subtotal = float(struct.total_amount)
                line_items = [
                    {
                        "category_name": comp.category.name if comp.category else "Academic Fee",
                        "description": comp.description or comp.category.name if comp.category else None,
                        "amount": float(comp.amount),
                    }
                    for comp in struct.components
                ]

            inv = await self.repo.create_invoice(
                tenant_id,
                {
                    "student_id": stud.id,
                    "academic_session_id": academic_session_id,
                    "fee_structure_id": fee_structure_id,
                    "allocation_id": alloc.id if alloc else None,
                    "title": inv_title,
                    "issue_date": issue_date,
                    "due_date": installment.due_date if installment else due_date,
                    "subtotal": subtotal,
                    "discount_amount": discount_amount,
                    "scholarship_amount": scholarship_amount,
                    "line_items": line_items,
                },
            )
            invoices.append(self._format_invoice_response(inv))

        return invoices

    async def get_invoice(
        self, tenant_id: uuid.UUID, invoice_id: uuid.UUID, *, user: User, role: str
    ) -> FeeInvoiceResponse:
        inv = await self.repo.get_invoice(tenant_id, invoice_id)
        if not inv:
            raise NotFoundException("Fee invoice not found.")
        await self._require_fee_access(tenant_id, inv.student_id, user, role)
        return self._format_invoice_response(inv)

    async def list_invoices(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        student_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        class_id: Optional[uuid.UUID] = None,
    ) -> List[FeeInvoiceResponse]:
        invoices = await self.repo.list_invoices(tenant_id, academic_session_id, student_id, status, class_id)
        return [self._format_invoice_response(i) for i in invoices]

    async def cancel_invoice(self, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> FeeInvoiceResponse:
        inv = await self.repo.get_invoice(tenant_id, invoice_id)
        if not inv:
            raise NotFoundException("Fee invoice not found.")
        if inv.paid_amount > 0:
            raise BadRequestException("Cannot cancel an invoice with recorded payments.")
        inv.status = "CANCELLED"
        await self.session.flush()
        return self._format_invoice_response(inv)

    def _format_invoice_response(self, inv: FeeInvoice) -> FeeInvoiceResponse:
        stud_name = inv.student.user.full_name if (inv.student and inv.student.user) else None
        adm_no = inv.student.admission_number if inv.student else None
        roll_no = inv.student.roll_number if inv.student else None
        cls_name = inv.student.school_class.name if (inv.student and inv.student.school_class) else None
        sec_name = inv.student.section.name if (inv.student and inv.student.section) else None
        crs_name = inv.student.course.name if (inv.student and inv.student.course) else None
        struct_name = inv.fee_structure.name if inv.fee_structure else None
        sess_name = inv.academic_session.name if inv.academic_session else None

        return FeeInvoiceResponse(
            id=inv.id,
            tenant_id=inv.tenant_id,
            student_id=inv.student_id,
            student_name=stud_name,
            student_admission_number=adm_no,
            student_roll_number=roll_no,
            class_name=cls_name,
            section_name=sec_name,
            course_name=crs_name,
            fee_structure_id=inv.fee_structure_id,
            fee_structure_name=struct_name,
            academic_session_id=inv.academic_session_id,
            academic_session_name=sess_name,
            invoice_number=inv.invoice_number,
            title=inv.title,
            issue_date=inv.issue_date,
            due_date=inv.due_date,
            subtotal=float(inv.subtotal),
            discount_amount=float(inv.discount_amount),
            scholarship_amount=float(inv.scholarship_amount),
            late_fine_amount=float(inv.late_fine_amount),
            total_amount=float(inv.total_amount),
            paid_amount=float(inv.paid_amount),
            balance_amount=float(inv.balance_amount),
            status=inv.status,
            line_items=inv.line_items or [],
            notes=inv.notes,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Offline Payment Recording & Receipts
    # ─────────────────────────────────────────────────────────────────────────

    async def record_offline_payment(
        self, tenant_id: uuid.UUID, received_by: uuid.UUID, data: Dict[str, Any]
    ) -> FeePaymentResponse:
        inv = await self.repo.get_invoice(tenant_id, data["invoice_id"])
        if not inv:
            raise NotFoundException("Fee invoice not found.")

        if inv.status in ("PAID", "CANCELLED"):
            raise BadRequestException(f"Invoice cannot accept payments as its status is {inv.status}.")

        pay_amount = float(data["amount"])
        if pay_amount > float(inv.balance_amount):
            raise BadRequestException(
                f"Payment amount (₹{pay_amount}) exceeds outstanding balance (₹{inv.balance_amount})."
            )

        payload = {
            "invoice_id": inv.id,
            "student_id": inv.student_id,
            "academic_session_id": inv.academic_session_id,
            "amount": pay_amount,
            "payment_date": data.get("payment_date") or datetime.now(timezone.utc),
            "payment_mode": data.get("payment_mode", "CASH").upper(),
            "status": "SUCCESS",
            "cash_drawer_reference": data.get("cash_drawer_reference"),
            "cheque_number": data.get("cheque_number"),
            "bank_name": data.get("bank_name"),
            "cheque_date": data.get("cheque_date"),
            "transaction_reference": data.get("transaction_reference"),
            "received_by": received_by,
            "reconciliation_status": "RECONCILED",
            "remarks": data.get("remarks"),
        }

        payment = await self.repo.create_payment(tenant_id, payload)
        return self._format_payment_response(payment)

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Online Payment Integration (Razorpay)
    # ─────────────────────────────────────────────────────────────────────────

    async def initiate_online_payment(
        self, tenant_id: uuid.UUID, invoice_id: uuid.UUID, amount: Optional[float] = None, *, user: User, role: str
    ) -> OnlineFeePaymentInitiateResponse:
        inv = await self.repo.get_invoice(tenant_id, invoice_id)
        if not inv:
            raise NotFoundException("Fee invoice not found.")
        await self._require_fee_access(tenant_id, inv.student_id, user, role)

        if inv.status in ("PAID", "CANCELLED"):
            raise BadRequestException(f"Invoice status is {inv.status}; online payment cannot be initiated.")

        pay_amount = float(amount) if amount else float(inv.balance_amount)
        if pay_amount <= 0:
            raise BadRequestException("Payable amount must be greater than zero.")
        if pay_amount > float(inv.balance_amount):
            raise BadRequestException(f"Amount (₹{pay_amount}) exceeds outstanding balance (₹{inv.balance_amount}).")

        # Generate unique receipt string for Razorpay
        receipt_str = f"RCPT_{inv.invoice_number}_{int(datetime.now(timezone.utc).timestamp())}"

        # Create order via Razorpay Gateway
        rzp_order = await asyncio.to_thread(
            razorpay_gateway.create_order,
            amount_in_rupees=pay_amount,
            receipt=receipt_str,
            currency="INR",
            notes={
                "tenant_id": str(tenant_id),
                "invoice_id": str(inv.id),
                "student_id": str(inv.student_id),
                "invoice_number": inv.invoice_number,
            },
        )
        rzp_order_id = rzp_order.get("order_id") or rzp_order.get("id")

        # Create PENDING payment record
        payment = await self.repo.create_payment(
            tenant_id,
            {
                "invoice_id": inv.id,
                "student_id": inv.student_id,
                "academic_session_id": inv.academic_session_id,
                "amount": pay_amount,
                "payment_mode": "RAZORPAY",
                "status": "PENDING",
                "razorpay_order_id": rzp_order_id,
                "reconciliation_status": "UNRECONCILED",
            },
        )

        student_name = inv.student.user.full_name if (inv.student and inv.student.user) else "Student"
        student_email = inv.student.user.email if (inv.student and inv.student.user) else None
        student_phone = inv.student.father_phone or inv.student.guardian_phone if inv.student else None

        return OnlineFeePaymentInitiateResponse(
            payment_id=payment.id,
            invoice_id=inv.id,
            invoice_number=inv.invoice_number,
            amount=pay_amount,
            currency="INR",
            gateway="razorpay",
            razorpay_order_id=rzp_order_id,
            key_id=razorpay_gateway.key_id or "rzp_test_key",
            student_name=student_name,
            student_email=student_email,
            student_phone=student_phone,
        )

    async def verify_online_payment(
        self,
        tenant_id: uuid.UUID,
        payment_id: uuid.UUID,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        *,
        user: User,
        role: str,
    ) -> FeePaymentResponse:
        """
        Cryptographically verifies Razorpay HMAC signature. Never trusts frontend payment confirmation alone.
        """
        payment = await self.repo.get_payment(tenant_id, payment_id)
        if not payment:
            raise NotFoundException("Payment transaction record not found.")
        await self._require_fee_access(tenant_id, payment.student_id, user, role)

        if not payment.razorpay_order_id or payment.razorpay_order_id != razorpay_order_id:
            raise BadRequestException("The Razorpay order does not match this fee payment.")

        if payment.status == "SUCCESS":
            return self._format_payment_response(payment)

        # Signature Verification
        is_valid = razorpay_gateway.verify_payment_signature(
            order_id=razorpay_order_id,
            payment_id=razorpay_payment_id,
            signature=razorpay_signature,
        )
        if not is_valid:
            raise BadRequestException("Razorpay signature verification failed. Untrusted transaction.")

        await razorpay_gateway.require_captured_payment(
            razorpay_order_id, razorpay_payment_id, float(payment.amount), "INR",
        )

        # Mark payment verified & successful
        payment.status = "SUCCESS"
        payment.razorpay_payment_id = razorpay_payment_id
        payment.razorpay_signature = razorpay_signature
        payment.transaction_reference = razorpay_payment_id
        payment.reconciliation_status = "RECONCILED"
        payment.reconciled_at = datetime.now(timezone.utc)
        inv_id = payment.invoice_id
        await self.session.flush()

        # Update invoice balance atomically
        await self.repo.update_invoice_balance(tenant_id, inv_id)

        detailed = await self.repo.get_payment(tenant_id, payment_id)
        return self._format_payment_response(detailed or payment)

    async def process_razorpay_webhook(self, raw_body: bytes, signature: str) -> Dict[str, Any]:
        """
        Idempotent server-side webhook handler for signed Razorpay events.
        """
        if not razorpay_gateway.verify_webhook_signature(raw_body, signature):
            raise BadRequestException("Invalid webhook cryptographic signature.")

        payload = json.loads(raw_body.decode("utf-8"))
        event_id = payload.get("event_id") or payload.get("id") or str(uuid.uuid4())
        event_type = payload.get("event")

        # Extract payment payload
        pay_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = pay_entity.get("order_id")
        notes = pay_entity.get("notes", {})
        tenant_id_str = notes.get("tenant_id")

        if not tenant_id_str:
            return {"status": "ignored", "reason": "No tenant_id in payment notes"}

        tenant_id = uuid.UUID(tenant_id_str)
        await set_tenant_session_context(self.repo.session, tenant_id)

        # Enforce idempotency: prevent duplicate processing
        if await self.repo.has_processed_webhook_event(tenant_id, "RAZORPAY", event_id):
            logger.info("Webhook event already processed (idempotent skip)", event_id=event_id)
            return {"status": "already_processed"}

        if event_type in ("payment.captured", "order.paid"):
            payment = await self.repo.get_payment_by_order_id(order_id)
            if payment and payment.status != "SUCCESS":
                payment.status = "SUCCESS"
                payment.razorpay_payment_id = pay_entity.get("id")
                payment.transaction_reference = pay_entity.get("id")
                payment.reconciliation_status = "RECONCILED"
                payment.reconciled_at = datetime.now(timezone.utc)
                inv_id = payment.invoice_id
                await self.session.flush()
                await self.repo.update_invoice_balance(tenant_id, inv_id)

        await self.repo.record_webhook_event(
            tenant_id=tenant_id,
            provider="RAZORPAY",
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            status="PROCESSED",
        )

        return {"status": "processed", "event_id": event_id}

    # ─────────────────────────────────────────────────────────────────────────
    # 8. Printable / Downloadable Receipts
    # ─────────────────────────────────────────────────────────────────────────

    async def get_receipt(
        self, tenant_id: uuid.UUID, payment_id: uuid.UUID, *, user: User, role: str
    ) -> FeeReceiptResponse:
        payment = await self.repo.get_payment(tenant_id, payment_id)
        if not payment:
            raise NotFoundException("Fee payment receipt not found.")
        await self._require_fee_access(tenant_id, payment.student_id, user, role)
        if payment.status != "SUCCESS":
            raise NotFoundException("A receipt is available after payment is confirmed.")

        inv = payment.invoice
        student = payment.student
        t_stmt = select(Tenant).where(Tenant.id == tenant_id)
        tenant = (await self.session.execute(t_stmt)).scalars().first()

        inst_name = tenant.name if tenant else "Educational Institution"
        inst_addr = f"{tenant.city}, {tenant.state}, {tenant.country}" if (tenant and tenant.city) else "Campus Address"

        stud_name = student.user.full_name if (student and student.user) else "Student"
        adm_no = student.admission_number if student else "N/A"
        roll_no = student.roll_number if student else None
        cls_name = student.school_class.name if (student and student.school_class) else (student.course.name if (student and student.course) else "General")
        sec_name = student.section.name if (student and student.section) else None
        sess_name = inv.academic_session.name if (inv and inv.academic_session) else "Current Session"

        amount_words = number_to_words_indian(float(payment.amount))

        return FeeReceiptResponse(
            receipt_number=payment.receipt_number,
            payment_id=payment.id,
            invoice_number=inv.invoice_number,
            invoice_title=inv.title,
            institution_name=inst_name,
            institution_logo_url=tenant.logo_url if tenant else None,
            institution_address=inst_addr,
            student_name=stud_name,
            admission_number=adm_no,
            roll_number=roll_no,
            class_or_course=cls_name,
            section=sec_name,
            academic_session=sess_name,
            payment_date=payment.payment_date,
            payment_mode=payment.payment_mode,
            amount_paid=float(payment.amount),
            amount_in_words=amount_words,
            subtotal=float(inv.subtotal),
            discount_amount=float(inv.discount_amount),
            fine_amount=float(inv.late_fine_amount),
            total_invoice_amount=float(inv.total_amount),
            remaining_balance=float(inv.balance_amount),
            transaction_reference=payment.transaction_reference or payment.razorpay_payment_id or payment.cheque_number,
            collected_by=payment.receiver.full_name if payment.receiver else "System / Online Gateway",
            line_items=inv.line_items or [],
        )

    async def generate_receipt_html(
        self, tenant_id: uuid.UUID, payment_id: uuid.UUID, *, user: User, role: str
    ) -> str:
        r = await self.get_receipt(tenant_id, payment_id, user=user, role=role)

        rows_html = "".join(
            f"<tr><td style='padding:8px; border:1px solid #ddd;'>{escape(str(item.get('category_name', 'Fee')))}</td>"
            f"<td style='padding:8px; border:1px solid #ddd;'>{escape(str(item.get('description', '-')))}</td>"
            f"<td style='padding:8px; border:1px solid #ddd; text-align:right;'>₹{float(item.get('amount', 0.0)):,.2f}</td></tr>"
            for item in r.line_items
        )

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8" />
          <title>Fee Receipt - {escape(r.receipt_number)}</title>
          <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #333; margin: 40px; }}
            .receipt-box {{ max-width: 800px; margin: auto; padding: 30px; border: 2px solid #1e293b; border-radius: 8px; }}
            .header {{ text-align: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; }}
            .header h1 {{ margin: 0; color: #0f172a; font-size: 26px; }}
            .header p {{ margin: 4px 0; color: #64748b; font-size: 14px; }}
            .meta-grid {{ display: flex; justify-content: space-between; margin: 20px 0; font-size: 14px; }}
            .student-info, .receipt-info {{ width: 48%; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }}
            th {{ background: #f8fafc; border: 1px solid #cbd5e1; padding: 10px; text-align: left; }}
            .summary-box {{ margin-top: 20px; text-align: right; font-size: 15px; }}
            .words-box {{ margin-top: 15px; padding: 10px; background: #f1f5f9; border-radius: 4px; font-weight: bold; font-size: 14px; }}
            .footer {{ margin-top: 40px; display: flex; justify-content: space-between; font-size: 13px; color: #64748b; }}
            .stamp-box {{ border: 1px dashed #94a3b8; padding: 15px 30px; text-align: center; border-radius: 4px; }}
          </style>
        </head>
        <body>
          <div class="receipt-box">
            <div class="header">
              <h1>{escape(r.institution_name)}</h1>
              <p>{escape(r.institution_address or '')}</p>
              <h3 style="margin-top: 10px; color: #2563eb; letter-spacing: 1px;">OFFICIAL FEE RECEIPT</h3>
            </div>

            <div class="meta-grid">
              <div class="student-info">
                <p><strong>Student Name:</strong> {escape(r.student_name)}</p>
                <p><strong>Admission No:</strong> {escape(r.admission_number)}</p>
                <p><strong>Class / Course:</strong> {escape(r.class_or_course)} {f'({escape(r.section)})' if r.section else ''}</p>
                <p><strong>Academic Session:</strong> {escape(r.academic_session)}</p>
              </div>
              <div class="receipt-info" style="text-align: right;">
                <p><strong>Receipt Number:</strong> <span style="color:#2563eb; font-weight:bold;">{escape(r.receipt_number)}</span></p>
                <p><strong>Invoice Number:</strong> {escape(r.invoice_number)}</p>
                <p><strong>Date & Time:</strong> {r.payment_date.strftime('%d-%b-%Y %I:%M %p')}</p>
                <p><strong>Payment Mode:</strong> {escape(r.payment_mode)}</p>
                {f'<p><strong>Ref / UTR:</strong> {escape(r.transaction_reference)}</p>' if r.transaction_reference else ''}
              </div>
            </div>

            <table>
              <thead>
                <tr>
                  <th>Fee Category</th>
                  <th>Description</th>
                  <th style="text-align: right;">Amount (INR)</th>
                </tr>
              </thead>
              <tbody>
                {rows_html if rows_html else f"<tr><td colspan='3' style='padding:10px;'>{escape(r.invoice_title)}</td></tr>"}
              </tbody>
            </table>

            <div class="summary-box">
              <p>Invoice Total: ₹{r.total_invoice_amount:,.2f}</p>
              <p style="font-size: 18px; color: #16a34a; font-weight: bold;">Amount Paid: ₹{r.amount_paid:,.2f}</p>
              <p style="color: {'#dc2626' if r.remaining_balance > 0 else '#64748b'};">
                Remaining Balance: ₹{r.remaining_balance:,.2f}
              </p>
            </div>

            <div class="words-box">
              In Words: {escape(r.amount_in_words)}
            </div>

            <div class="footer">
              <div>
                <p>Collected By: <strong>{escape(r.collected_by)}</strong></p>
                <p>This is a computer generated receipt.</p>
              </div>
              <div class="stamp-box">
                <p style="margin:0; font-size:12px; color:#16a34a; font-weight:bold;">[PAID & RECONCILED]</p>
                <p style="margin:5px 0 0 0; font-size:11px;">Accounts Department</p>
              </div>
            </div>
          </div>
        </body>
        </html>
        """

    # ─────────────────────────────────────────────────────────────────────────
    # 9. Role-based / My Fees for Student / Parent
    # ─────────────────────────────────────────────────────────────────────────

    async def _require_fee_access(self, tenant_id: uuid.UUID, student_id: uuid.UUID, user: User, role: str) -> None:
        if user.is_superadmin or role == "INSTITUTION_ADMIN":
            return
        if role == "STUDENT":
            owned = await self.session.scalar(
                select(StudentProfile.id).where(
                    StudentProfile.tenant_id == tenant_id,
                    StudentProfile.id == student_id,
                    StudentProfile.user_id == user.id,
                    StudentProfile.is_deleted.is_(False),
                )
            )
        elif role == "PARENT":
            owned = await self.session.scalar(
                select(StudentParent.id).where(
                    StudentParent.tenant_id == tenant_id,
                    StudentParent.student_id == student_id,
                    StudentParent.parent_user_id == user.id,
                    StudentParent.status == "VERIFIED",
                    StudentParent.can_pay_fees.is_(True),
                    StudentParent.is_deleted.is_(False),
                )
            )
        else:
            owned = None
        if not owned:
            raise AuthorizationException("You do not have access to this student's fees.")

    async def get_my_fees(self, tenant_id: uuid.UUID, user: User, user_role: str) -> Dict[str, Any]:
        if user_role not in ("STUDENT", "PARENT", "INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"):
            raise BadRequestException("Unauthorized to access student fee ledger.")

        stmt = (
            select(StudentProfile)
            .options(
                selectinload(StudentProfile.user),
                selectinload(StudentProfile.school_class),
                selectinload(StudentProfile.course),
                selectinload(StudentProfile.section),
            )
            .where(StudentProfile.tenant_id == tenant_id, StudentProfile.is_deleted.is_(False))
        )
        if user_role == "PARENT":
            stmt = (
                stmt.join(StudentParent, StudentParent.student_id == StudentProfile.id)
                .where(
                    StudentParent.tenant_id == tenant_id,
                    StudentParent.parent_user_id == user.id,
                    StudentParent.status == "VERIFIED",
                    StudentParent.can_pay_fees.is_(True),
                    StudentParent.is_deleted.is_(False),
                )
                .order_by(StudentParent.is_primary.desc(), StudentProfile.id)
            )
        else:
            stmt = stmt.where(StudentProfile.user_id == user.id)
        student = await self.session.scalar(stmt.limit(1))

        if not student:
            # Clean fallback for admins, teachers, or students/parents without linked profiles
            return {
                "student": None,
                "invoices": [],
                "payments": [],
                "total_invoiced": 0.0,
                "total_paid": 0.0,
                "total_due": 0.0,
            }

        invoices = await self.repo.list_invoices(tenant_id, student_id=student.id)
        payments = await self.repo.list_payments(tenant_id, student_id=student.id)

        tot_inv = sum(float(i.total_amount) for i in invoices)
        tot_paid = sum(float(p.amount) for p in payments if p.status == "SUCCESS")
        tot_due = sum(float(i.balance_amount) for i in invoices)

        cls_name = student.school_class.name if student.school_class else (student.course.name if student.course else "General")

        return {
            "student": {
                "id": str(student.id),
                "name": student.user.full_name if student.user else "Student",
                "admission_number": student.admission_number,
                "roll_number": student.roll_number,
                "class_or_course": cls_name,
                "section": student.section.name if student.section else None,
            },
            "invoices": [self._format_invoice_response(i) for i in invoices],
            "payments": [self._format_payment_response(p) for p in payments],
            "total_invoiced": tot_inv,
            "total_paid": tot_paid,
            "total_due": tot_due,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 10. Dashboard & Defaulters Reports
    # ─────────────────────────────────────────────────────────────────────────

    async def get_dashboard_stats(
        self, tenant_id: uuid.UUID, academic_session_id: Optional[uuid.UUID] = None
    ) -> FeeDashboardStatsResponse:
        data = await self.repo.get_dashboard_stats(tenant_id, academic_session_id)
        return FeeDashboardStatsResponse(**data)

    async def get_outstanding_defaulters_report(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
    ) -> OutstandingDuesReportResponse:
        defaulters_data = await self.repo.get_outstanding_defaulters(tenant_id, academic_session_id, class_id)
        items = [OutstandingDefaulterItem(**d) for d in defaulters_data]
        total_amt = sum(item.total_due_amount for item in items)
        return OutstandingDuesReportResponse(
            total_defaulters_count=len(items),
            total_outstanding_amount=total_amt,
            defaulters=items,
        )

    async def get_collection_ledger(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        payment_mode: Optional[str] = None,
    ) -> FeeCollectionLedgerResponse:
        payments = await self.repo.list_payments(tenant_id, academic_session_id, None, from_date, to_date, payment_mode)
        items = []
        tot = 0.0

        for p in payments:
            if p.status == "SUCCESS":
                tot += float(p.amount)
            s_name = p.student.user.full_name if (p.student and p.student.user) else "Student"
            adm = p.student.admission_number if p.student else "N/A"
            cls_str = p.student.school_class.name if (p.student and p.student.school_class) else "General"

            items.append(
                FeeCollectionLedgerItem(
                    payment_id=p.id,
                    receipt_number=p.receipt_number,
                    payment_date=p.payment_date,
                    student_name=s_name,
                    admission_number=adm,
                    class_or_course=cls_str,
                    amount=float(p.amount),
                    payment_mode=p.payment_mode,
                    transaction_reference=p.transaction_reference or p.razorpay_payment_id or p.cheque_number,
                    collected_by=p.receiver.full_name if p.receiver else "Online Gateway",
                    reconciliation_status=p.reconciliation_status,
                )
            )

        return FeeCollectionLedgerResponse(
            total_count=len(items),
            total_amount_collected=tot,
            items=items,
        )

    def _format_payment_response(self, p: FeePayment) -> FeePaymentResponse:
        s_name = p.student.user.full_name if (p.student and p.student.user) else None
        s_adm = p.student.admission_number if p.student else None
        inv_num = p.invoice.invoice_number if p.invoice else None
        rec_by = p.receiver.full_name if p.receiver else None

        return FeePaymentResponse(
            id=p.id,
            tenant_id=p.tenant_id,
            invoice_id=p.invoice_id,
            invoice_number=inv_num,
            student_id=p.student_id,
            student_name=s_name,
            student_admission_number=s_adm,
            receipt_number=p.receipt_number,
            amount=float(p.amount),
            payment_date=p.payment_date,
            payment_mode=p.payment_mode,
            status=p.status,
            cash_drawer_reference=p.cash_drawer_reference,
            cheque_number=p.cheque_number,
            bank_name=p.bank_name,
            cheque_date=p.cheque_date,
            clearance_date=p.clearance_date,
            transaction_reference=p.transaction_reference,
            razorpay_order_id=p.razorpay_order_id,
            razorpay_payment_id=p.razorpay_payment_id,
            received_by_name=rec_by,
            reconciliation_status=p.reconciliation_status,
            remarks=p.remarks,
            created_at=p.created_at,
        )
