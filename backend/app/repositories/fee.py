from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import AcademicSession, CollegeBatch, Course, SchoolClass, Section, StudentProfile
from app.models.fee import (
    FeeCategory,
    FeeDiscountScholarship,
    FeeInvoice,
    FeePayment,
    FeePaymentWebhookEvent,
    FeeStructure,
    FeeStructureComponent,
    FeeStructureInstallment,
    StudentFeeAllocation,
)
from app.models.user import User


class FeeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Fee Categories
    # ─────────────────────────────────────────────────────────────────────────

    async def create_category(self, tenant_id: uuid.UUID, data: Dict[str, Any]) -> FeeCategory:
        cat = FeeCategory(
            tenant_id=tenant_id,
            name=data["name"],
            code=data["code"].upper(),
            fee_type=data.get("fee_type", "ACADEMIC"),
            description=data.get("description"),
            is_refundable=data.get("is_refundable", False),
            is_active=data.get("is_active", True),
        )
        self.session.add(cat)
        await self.session.flush()
        await self.session.refresh(cat)
        return cat

    async def get_category(self, tenant_id: uuid.UUID, category_id: uuid.UUID) -> Optional[FeeCategory]:
        stmt = select(FeeCategory).where(
            FeeCategory.tenant_id == tenant_id,
            FeeCategory.id == category_id,
            FeeCategory.is_deleted == False,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_category_by_code(self, tenant_id: uuid.UUID, code: str) -> Optional[FeeCategory]:
        stmt = select(FeeCategory).where(
            FeeCategory.tenant_id == tenant_id,
            FeeCategory.code == code.upper(),
            FeeCategory.is_deleted == False,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_categories(self, tenant_id: uuid.UUID, is_active: Optional[bool] = None) -> List[FeeCategory]:
        stmt = select(FeeCategory).where(FeeCategory.tenant_id == tenant_id, FeeCategory.is_deleted == False)
        if is_active is not None:
            stmt = stmt.where(FeeCategory.is_active == is_active)
        stmt = stmt.order_by(FeeCategory.name.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def update_category(self, tenant_id: uuid.UUID, category_id: uuid.UUID, data: Dict[str, Any]) -> Optional[FeeCategory]:
        cat = await self.get_category(tenant_id, category_id)
        if not cat:
            return None
        for k, v in data.items():
            if v is not None and hasattr(cat, k):
                setattr(cat, k, v)
        cat.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(cat)
        return cat

    async def delete_category(self, tenant_id: uuid.UUID, category_id: uuid.UUID) -> bool:
        cat = await self.get_category(tenant_id, category_id)
        if not cat:
            return False
        cat.is_deleted = True
        cat.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Fee Structures
    # ─────────────────────────────────────────────────────────────────────────

    async def create_structure(self, tenant_id: uuid.UUID, data: Dict[str, Any]) -> FeeStructure:
        struct = FeeStructure(
            tenant_id=tenant_id,
            academic_session_id=data["academic_session_id"],
            name=data["name"],
            institution_type=data.get("institution_type", "SCHOOL"),
            class_id=data.get("class_id"),
            course_id=data.get("course_id"),
            semester_id=data.get("semester_id"),
            batch_id=data.get("batch_id"),
            frequency=data.get("frequency", "ANNUAL"),
            total_amount=data.get("total_amount", 0.0),
            currency=data.get("currency", "INR"),
            due_date=data.get("due_date"),
            is_active=data.get("is_active", True),
        )
        self.session.add(struct)
        await self.session.flush()

        # Add components
        components = data.get("components", [])
        total_calc = 0.0
        for comp in components:
            c_obj = FeeStructureComponent(
                fee_structure_id=struct.id,
                fee_category_id=comp["fee_category_id"],
                amount=comp["amount"],
                is_optional=comp.get("is_optional", False),
                description=comp.get("description"),
            )
            self.session.add(c_obj)
            total_calc += float(comp["amount"])

        # Add installments
        installments = data.get("installments", [])
        for inst in installments:
            i_obj = FeeStructureInstallment(
                fee_structure_id=struct.id,
                installment_number=inst["installment_number"],
                name=inst["name"],
                due_date=inst["due_date"],
                amount=inst["amount"],
                late_fine_amount=inst.get("late_fine_amount", 0.0),
                late_fine_type=inst.get("late_fine_type", "NONE"),
                grace_period_days=inst.get("grace_period_days", 0),
            )
            self.session.add(i_obj)

        if total_calc > 0 and struct.total_amount == 0:
            struct.total_amount = total_calc

        await self.session.flush()
        await self.session.refresh(struct)
        return struct

    async def get_structure(self, tenant_id: uuid.UUID, structure_id: uuid.UUID) -> Optional[FeeStructure]:
        stmt = (
            select(FeeStructure)
            .where(
                FeeStructure.tenant_id == tenant_id,
                FeeStructure.id == structure_id,
                FeeStructure.is_deleted == False,
            )
            .options(
                selectinload(FeeStructure.academic_session),
                selectinload(FeeStructure.school_class),
                selectinload(FeeStructure.course),
                selectinload(FeeStructure.components).selectinload(FeeStructureComponent.category),
                selectinload(FeeStructure.installments),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_structures(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
    ) -> List[FeeStructure]:
        stmt = (
            select(FeeStructure)
            .where(FeeStructure.tenant_id == tenant_id, FeeStructure.is_deleted == False)
            .options(
                selectinload(FeeStructure.academic_session),
                selectinload(FeeStructure.school_class),
                selectinload(FeeStructure.course),
                selectinload(FeeStructure.components).selectinload(FeeStructureComponent.category),
                selectinload(FeeStructure.installments),
            )
            .order_by(FeeStructure.created_at.desc())
        )
        if academic_session_id:
            stmt = stmt.where(FeeStructure.academic_session_id == academic_session_id)
        if class_id:
            stmt = stmt.where(FeeStructure.class_id == class_id)
        if course_id:
            stmt = stmt.where(FeeStructure.course_id == course_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_structure(self, tenant_id: uuid.UUID, structure_id: uuid.UUID) -> bool:
        struct = await self.get_structure(tenant_id, structure_id)
        if not struct:
            return False
        struct.is_deleted = True
        struct.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Discounts & Scholarships
    # ─────────────────────────────────────────────────────────────────────────

    async def create_discount(self, tenant_id: uuid.UUID, data: Dict[str, Any]) -> FeeDiscountScholarship:
        disc = FeeDiscountScholarship(
            tenant_id=tenant_id,
            academic_session_id=data["academic_session_id"],
            name=data["name"],
            discount_type=data.get("discount_type", "DISCOUNT"),
            calculation_type=data.get("calculation_type", "PERCENTAGE"),
            value=data["value"],
            applicable_categories=data.get("applicable_categories", ["ALL"]),
            criteria=data.get("criteria"),
            is_active=data.get("is_active", True),
        )
        self.session.add(disc)
        await self.session.flush()
        await self.session.refresh(disc)
        return disc

    async def get_discount(self, tenant_id: uuid.UUID, discount_id: uuid.UUID) -> Optional[FeeDiscountScholarship]:
        stmt = select(FeeDiscountScholarship).where(
            FeeDiscountScholarship.tenant_id == tenant_id,
            FeeDiscountScholarship.id == discount_id,
            FeeDiscountScholarship.is_deleted == False,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_discounts(
        self, tenant_id: uuid.UUID, academic_session_id: Optional[uuid.UUID] = None
    ) -> List[FeeDiscountScholarship]:
        stmt = select(FeeDiscountScholarship).where(
            FeeDiscountScholarship.tenant_id == tenant_id,
            FeeDiscountScholarship.is_deleted == False,
        )
        if academic_session_id:
            stmt = stmt.where(FeeDiscountScholarship.academic_session_id == academic_session_id)
        stmt = stmt.order_by(FeeDiscountScholarship.name.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Student Fee Allocations
    # ─────────────────────────────────────────────────────────────────────────

    async def create_allocation(self, tenant_id: uuid.UUID, data: Dict[str, Any]) -> StudentFeeAllocation:
        alloc = StudentFeeAllocation(
            tenant_id=tenant_id,
            student_id=data["student_id"],
            fee_structure_id=data["fee_structure_id"],
            academic_session_id=data["academic_session_id"],
            discount_id=data.get("discount_id"),
            custom_discount_amount=data.get("custom_discount_amount", 0.0),
            discount_reason=data.get("discount_reason"),
            net_fee_amount=data["net_fee_amount"],
            status="ACTIVE",
        )
        self.session.add(alloc)
        await self.session.flush()
        return await self.get_allocation(tenant_id, alloc.id) or alloc

    async def get_allocation(self, tenant_id: uuid.UUID, allocation_id: uuid.UUID) -> Optional[StudentFeeAllocation]:
        stmt = (
            select(StudentFeeAllocation)
            .where(StudentFeeAllocation.tenant_id == tenant_id, StudentFeeAllocation.id == allocation_id)
            .options(
                selectinload(StudentFeeAllocation.student).selectinload(StudentProfile.user),
                selectinload(StudentFeeAllocation.fee_structure),
                selectinload(StudentFeeAllocation.discount),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_allocation_by_student_session(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID, academic_session_id: uuid.UUID
    ) -> Optional[StudentFeeAllocation]:
        stmt = (
            select(StudentFeeAllocation)
            .where(
                StudentFeeAllocation.tenant_id == tenant_id,
                StudentFeeAllocation.student_id == student_id,
                StudentFeeAllocation.academic_session_id == academic_session_id,
                StudentFeeAllocation.status == "ACTIVE",
            )
            .options(
                selectinload(StudentFeeAllocation.student).selectinload(StudentProfile.user),
                selectinload(StudentFeeAllocation.fee_structure),
                selectinload(StudentFeeAllocation.discount),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_allocations(
        self, tenant_id: uuid.UUID, academic_session_id: Optional[uuid.UUID] = None, fee_structure_id: Optional[uuid.UUID] = None
    ) -> List[StudentFeeAllocation]:
        stmt = (
            select(StudentFeeAllocation)
            .where(StudentFeeAllocation.tenant_id == tenant_id, StudentFeeAllocation.status == "ACTIVE")
            .options(
                selectinload(StudentFeeAllocation.student).selectinload(StudentProfile.user),
                selectinload(StudentFeeAllocation.fee_structure),
                selectinload(StudentFeeAllocation.discount),
            )
            .order_by(StudentFeeAllocation.created_at.desc())
        )
        if academic_session_id:
            stmt = stmt.where(StudentFeeAllocation.academic_session_id == academic_session_id)
        if fee_structure_id:
            stmt = stmt.where(StudentFeeAllocation.fee_structure_id == fee_structure_id)
        return list((await self.session.execute(stmt)).scalars().all())

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Invoices & Sequential Numbering
    # ─────────────────────────────────────────────────────────────────────────

    async def generate_next_invoice_number(self, tenant_id: uuid.UUID) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"INV-{year}-"
        stmt = (
            select(func.count(FeeInvoice.id))
            .where(
                FeeInvoice.tenant_id == tenant_id,
                FeeInvoice.invoice_number.like(f"{prefix}%"),
            )
        )
        count = (await self.session.execute(stmt)).scalar() or 0
        return f"{prefix}{(count + 1):05d}"

    async def create_invoice(self, tenant_id: uuid.UUID, data: Dict[str, Any]) -> FeeInvoice:
        inv_num = data.get("invoice_number") or await self.generate_next_invoice_number(tenant_id)
        subtotal = float(data["subtotal"])
        disc = float(data.get("discount_amount", 0.0))
        schol = float(data.get("scholarship_amount", 0.0))
        fine = float(data.get("late_fine_amount", 0.0))
        total = max(0.0, subtotal - disc - schol + fine)

        invoice = FeeInvoice(
            tenant_id=tenant_id,
            student_id=data["student_id"],
            fee_structure_id=data.get("fee_structure_id"),
            allocation_id=data.get("allocation_id"),
            academic_session_id=data["academic_session_id"],
            invoice_number=inv_num,
            title=data["title"],
            issue_date=data["issue_date"],
            due_date=data["due_date"],
            subtotal=subtotal,
            discount_amount=disc,
            scholarship_amount=schol,
            late_fine_amount=fine,
            total_amount=total,
            paid_amount=0.0,
            balance_amount=total,
            status="ISSUED",
            line_items=data.get("line_items", []),
            notes=data.get("notes"),
        )
        self.session.add(invoice)
        await self.session.flush()
        return await self.get_invoice(tenant_id, invoice.id) or invoice

    async def get_invoice(self, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> Optional[FeeInvoice]:
        stmt = (
            select(FeeInvoice)
            .where(FeeInvoice.tenant_id == tenant_id, FeeInvoice.id == invoice_id, FeeInvoice.is_deleted == False)
            .options(
                selectinload(FeeInvoice.student).selectinload(StudentProfile.user),
                selectinload(FeeInvoice.student).selectinload(StudentProfile.school_class),
                selectinload(FeeInvoice.student).selectinload(StudentProfile.section),
                selectinload(FeeInvoice.student).selectinload(StudentProfile.course),
                selectinload(FeeInvoice.fee_structure),
                selectinload(FeeInvoice.academic_session),
                selectinload(FeeInvoice.payments),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_invoice_by_number(self, tenant_id: uuid.UUID, invoice_number: str) -> Optional[FeeInvoice]:
        stmt = (
            select(FeeInvoice)
            .where(FeeInvoice.tenant_id == tenant_id, FeeInvoice.invoice_number == invoice_number, FeeInvoice.is_deleted == False)
            .options(
                selectinload(FeeInvoice.student).selectinload(StudentProfile.user),
                selectinload(FeeInvoice.fee_structure),
                selectinload(FeeInvoice.academic_session),
                selectinload(FeeInvoice.payments),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_invoices(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        student_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        class_id: Optional[uuid.UUID] = None,
    ) -> List[FeeInvoice]:
        stmt = (
            select(FeeInvoice)
            .where(FeeInvoice.tenant_id == tenant_id, FeeInvoice.is_deleted == False)
            .options(
                selectinload(FeeInvoice.student).selectinload(StudentProfile.user),
                selectinload(FeeInvoice.student).selectinload(StudentProfile.school_class),
                selectinload(FeeInvoice.student).selectinload(StudentProfile.section),
                selectinload(FeeInvoice.student).selectinload(StudentProfile.course),
                selectinload(FeeInvoice.fee_structure),
                selectinload(FeeInvoice.academic_session),
            )
            .order_by(FeeInvoice.issue_date.desc(), FeeInvoice.created_at.desc())
        )
        if academic_session_id:
            stmt = stmt.where(FeeInvoice.academic_session_id == academic_session_id)
        if student_id:
            stmt = stmt.where(FeeInvoice.student_id == student_id)
        if status:
            stmt = stmt.where(FeeInvoice.status == status)
        if class_id:
            stmt = stmt.join(FeeInvoice.student).where(StudentProfile.class_id == class_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def update_invoice_balance(self, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> Optional[FeeInvoice]:
        invoice = await self.get_invoice(tenant_id, invoice_id)
        if not invoice:
            return None

        # Sum up all successful payments
        pay_stmt = select(func.coalesce(func.sum(FeePayment.amount), 0.0)).where(
            FeePayment.tenant_id == tenant_id,
            FeePayment.invoice_id == invoice_id,
            FeePayment.status == "SUCCESS",
        )
        total_paid = float((await self.session.execute(pay_stmt)).scalar() or 0.0)

        invoice.paid_amount = total_paid
        invoice.balance_amount = max(0.0, float(invoice.total_amount) - total_paid)

        if invoice.balance_amount == 0 and total_paid > 0:
            invoice.status = "PAID"
        elif total_paid > 0:
            invoice.status = "PARTIALLY_PAID"
        elif invoice.due_date < date.today() and invoice.status != "CANCELLED":
            invoice.status = "OVERDUE"
        else:
            invoice.status = "ISSUED"

        invoice.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(invoice)
        return invoice

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Fee Payments & Sequential Receipts
    # ─────────────────────────────────────────────────────────────────────────

    async def generate_next_receipt_number(self, tenant_id: uuid.UUID) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"REC-{year}-"
        stmt = (
            select(func.count(FeePayment.id))
            .where(
                FeePayment.tenant_id == tenant_id,
                FeePayment.receipt_number.like(f"{prefix}%"),
            )
        )
        count = (await self.session.execute(stmt)).scalar() or 0
        return f"{prefix}{(count + 1):05d}"

    async def create_payment(self, tenant_id: uuid.UUID, data: Dict[str, Any]) -> FeePayment:
        rec_num = data.get("receipt_number") or await self.generate_next_receipt_number(tenant_id)
        payment = FeePayment(
            tenant_id=tenant_id,
            invoice_id=data["invoice_id"],
            student_id=data["student_id"],
            academic_session_id=data["academic_session_id"],
            receipt_number=rec_num,
            amount=data["amount"],
            payment_date=data.get("payment_date") or datetime.now(timezone.utc),
            payment_mode=data.get("payment_mode", "CASH"),
            status=data.get("status", "SUCCESS"),
            cash_drawer_reference=data.get("cash_drawer_reference"),
            cheque_number=data.get("cheque_number"),
            bank_name=data.get("bank_name"),
            cheque_date=data.get("cheque_date"),
            clearance_date=data.get("clearance_date"),
            transaction_reference=data.get("transaction_reference"),
            razorpay_order_id=data.get("razorpay_order_id"),
            razorpay_payment_id=data.get("razorpay_payment_id"),
            razorpay_signature=data.get("razorpay_signature"),
            received_by=data.get("received_by"),
            reconciliation_status=data.get("reconciliation_status", "RECONCILED"),
            reconciled_at=datetime.now(timezone.utc) if data.get("reconciliation_status") == "RECONCILED" else None,
            remarks=data.get("remarks"),
        )
        self.session.add(payment)
        await self.session.flush()

        # Reconcile invoice balance
        if payment.status == "SUCCESS":
            await self.update_invoice_balance(tenant_id, payment.invoice_id)

        return await self.get_payment(tenant_id, payment.id) or payment

    async def get_payment(self, tenant_id: uuid.UUID, payment_id: uuid.UUID) -> Optional[FeePayment]:
        stmt = (
            select(FeePayment)
            .where(FeePayment.tenant_id == tenant_id, FeePayment.id == payment_id)
            .options(
                selectinload(FeePayment.invoice).selectinload(FeeInvoice.academic_session),
                selectinload(FeePayment.student).selectinload(StudentProfile.user),
                selectinload(FeePayment.student).selectinload(StudentProfile.school_class),
                selectinload(FeePayment.student).selectinload(StudentProfile.section),
                selectinload(FeePayment.student).selectinload(StudentProfile.course),
                selectinload(FeePayment.receiver),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_payment_by_order_id(self, razorpay_order_id: str) -> Optional[FeePayment]:
        stmt = (
            select(FeePayment)
            .where(FeePayment.razorpay_order_id == razorpay_order_id)
            .options(
                selectinload(FeePayment.invoice),
                selectinload(FeePayment.student).selectinload(StudentProfile.user),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_payments(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        student_id: Optional[uuid.UUID] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        payment_mode: Optional[str] = None,
    ) -> List[FeePayment]:
        stmt = (
            select(FeePayment)
            .where(FeePayment.tenant_id == tenant_id)
            .options(
                selectinload(FeePayment.invoice),
                selectinload(FeePayment.student).selectinload(StudentProfile.user),
                selectinload(FeePayment.student).selectinload(StudentProfile.school_class),
                selectinload(FeePayment.student).selectinload(StudentProfile.section),
                selectinload(FeePayment.student).selectinload(StudentProfile.course),
                selectinload(FeePayment.receiver),
            )
            .order_by(FeePayment.payment_date.desc())
        )
        if academic_session_id:
            stmt = stmt.where(FeePayment.academic_session_id == academic_session_id)
        if student_id:
            stmt = stmt.where(FeePayment.student_id == student_id)
        if from_date:
            stmt = stmt.where(FeePayment.payment_date >= from_date)
        if to_date:
            stmt = stmt.where(FeePayment.payment_date <= to_date)
        if payment_mode:
            stmt = stmt.where(FeePayment.payment_mode == payment_mode)
        return list((await self.session.execute(stmt)).scalars().all())

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Webhook Idempotency
    # ─────────────────────────────────────────────────────────────────────────

    async def has_processed_webhook_event(self, tenant_id: uuid.UUID, provider: str, event_id: str) -> bool:
        stmt = select(FeePaymentWebhookEvent).where(
            FeePaymentWebhookEvent.tenant_id == tenant_id,
            FeePaymentWebhookEvent.provider == provider,
            FeePaymentWebhookEvent.event_id == event_id,
            FeePaymentWebhookEvent.status == "PROCESSED",
        )
        return (await self.session.execute(stmt)).scalars().first() is not None

    async def record_webhook_event(
        self,
        tenant_id: uuid.UUID,
        provider: str,
        event_id: str,
        event_type: str,
        payload: Dict[str, Any],
        status: str = "PROCESSED",
        error_message: Optional[str] = None,
    ) -> FeePaymentWebhookEvent:
        event = FeePaymentWebhookEvent(
            tenant_id=tenant_id,
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            status=status,
            error_message=error_message,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    # ─────────────────────────────────────────────────────────────────────────
    # 8. Reports & Analytics Queries
    # ─────────────────────────────────────────────────────────────────────────

    async def get_dashboard_stats(
        self, tenant_id: uuid.UUID, academic_session_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        base_inv = select(FeeInvoice).where(FeeInvoice.tenant_id == tenant_id, FeeInvoice.is_deleted == False)
        if academic_session_id:
            base_inv = base_inv.where(FeeInvoice.academic_session_id == academic_session_id)

        # Total invoiced & collected
        tot_stmt = select(
            func.coalesce(func.sum(FeeInvoice.total_amount), 0.0),
            func.coalesce(func.sum(FeeInvoice.paid_amount), 0.0),
            func.coalesce(func.sum(FeeInvoice.balance_amount), 0.0),
            func.count(FeeInvoice.id),
        ).where(FeeInvoice.tenant_id == tenant_id, FeeInvoice.is_deleted == False)
        if academic_session_id:
            tot_stmt = tot_stmt.where(FeeInvoice.academic_session_id == academic_session_id)

        invoiced, collected, balance, inv_count = (await self.session.execute(tot_stmt)).first() or (0.0, 0.0, 0.0, 0)
        invoiced = float(invoiced)
        collected = float(collected)
        balance = float(balance)

        # Overdue stats
        today = date.today()
        od_stmt = select(
            func.count(FeeInvoice.id),
            func.coalesce(func.sum(FeeInvoice.balance_amount), 0.0),
        ).where(
            FeeInvoice.tenant_id == tenant_id,
            FeeInvoice.is_deleted == False,
            FeeInvoice.due_date < today,
            FeeInvoice.balance_amount > 0,
            FeeInvoice.status != "CANCELLED",
        )
        if academic_session_id:
            od_stmt = od_stmt.where(FeeInvoice.academic_session_id == academic_session_id)
        od_count, od_amt = (await self.session.execute(od_stmt)).first() or (0, 0.0)

        # Today's collection
        start_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        t_pay_stmt = select(func.coalesce(func.sum(FeePayment.amount), 0.0)).where(
            FeePayment.tenant_id == tenant_id,
            FeePayment.payment_date >= start_today,
            FeePayment.status == "SUCCESS",
        )
        today_coll = float((await self.session.execute(t_pay_stmt)).scalar() or 0.0)

        # Collection by payment mode
        mode_stmt = (
            select(FeePayment.payment_mode, func.coalesce(func.sum(FeePayment.amount), 0.0))
            .where(FeePayment.tenant_id == tenant_id, FeePayment.status == "SUCCESS")
            .group_by(FeePayment.payment_mode)
        )
        by_mode = {r[0]: float(r[1]) for r in (await self.session.execute(mode_stmt)).all()}

        # Active students billed count
        stud_stmt = select(func.count(func.distinct(FeeInvoice.student_id))).where(
            FeeInvoice.tenant_id == tenant_id, FeeInvoice.is_deleted == False
        )
        if academic_session_id:
            stud_stmt = stud_stmt.where(FeeInvoice.academic_session_id == academic_session_id)
        students_billed = (await self.session.execute(stud_stmt)).scalar() or 0

        rate = (collected / invoiced * 100) if invoiced > 0 else 0.0

        return {
            "total_invoiced_amount": invoiced,
            "total_collected_amount": collected,
            "total_pending_dues": balance,
            "collection_rate_percent": round(rate, 2),
            "overdue_invoices_count": od_count,
            "overdue_amount": float(od_amt),
            "today_collection_amount": today_coll,
            "active_students_billed_count": students_billed,
            "collection_by_payment_mode": by_mode,
            "collection_by_category": {},
            "monthly_collection_trend": [],
        }

    async def get_outstanding_defaulters(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        today = date.today()
        stmt = (
            select(
                StudentProfile,
                func.count(FeeInvoice.id).label("unpaid_count"),
                func.min(FeeInvoice.due_date).label("oldest_due"),
                func.sum(FeeInvoice.balance_amount).label("total_due"),
            )
            .join(FeeInvoice, FeeInvoice.student_id == StudentProfile.id)
            .where(
                StudentProfile.tenant_id == tenant_id,
                FeeInvoice.tenant_id == tenant_id,
                FeeInvoice.is_deleted == False,
                FeeInvoice.balance_amount > 0,
                FeeInvoice.due_date < today,
                FeeInvoice.status != "CANCELLED",
            )
            .options(
                selectinload(StudentProfile.user),
                selectinload(StudentProfile.school_class),
                selectinload(StudentProfile.section),
                selectinload(StudentProfile.course),
            )
            .group_by(StudentProfile.id)
            .order_by(desc("total_due"))
        )
        if academic_session_id:
            stmt = stmt.where(FeeInvoice.academic_session_id == academic_session_id)
        if class_id:
            stmt = stmt.where(StudentProfile.class_id == class_id)

        rows = (await self.session.execute(stmt)).all()
        defaulters = []
        for student, unpaid_count, oldest_due, total_due in rows:
            cls_name = student.school_class.name if student.school_class else (student.course.name if student.course else "General")
            sec_name = student.section.name if student.section else None
            overdue_days = (today - oldest_due).days if oldest_due else 0

            defaulters.append({
                "student_id": student.id,
                "student_name": student.user.full_name if student.user else "Student",
                "admission_number": student.admission_number,
                "roll_number": student.roll_number,
                "class_or_course": cls_name,
                "section": sec_name,
                "parent_name": student.father_name or student.guardian_name,
                "parent_phone": student.father_phone or student.guardian_phone,
                "unpaid_invoices_count": unpaid_count,
                "oldest_due_date": oldest_due,
                "total_due_amount": float(total_due),
                "overdue_days": max(0, overdue_days),
            })
        return defaulters
