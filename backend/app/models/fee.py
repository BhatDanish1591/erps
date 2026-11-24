from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.academic import AcademicSession, CollegeBatch, CollegeSemester, Course, SchoolClass, StudentProfile
    from app.models.tenant import Tenant
    from app.models.user import User


class FeeCategory(BaseModel, SoftDeleteMixin):
    """
    Standard fee categories (e.g. Tuition, Admission, Exam, Lab, Transport, Hostel).
    """
    __tablename__ = "fee_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    fee_type: Mapped[str] = mapped_column(String(30), nullable=False, default="ACADEMIC")  # ACADEMIC, FACILITY, ONE_TIME, RECURRING, OPTIONAL
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_refundable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_fee_categories_tenant_code"),
    )


class FeeStructure(BaseModel, SoftDeleteMixin):
    """
    Fee structure master for a class or course within an academic session.
    """
    __tablename__ = "fee_structures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    institution_type: Mapped[str] = mapped_column(String(20), default="SCHOOL", nullable=False)  # SCHOOL | COLLEGE
    class_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("school_classes.id", ondelete="SET NULL"),
        nullable=True,
    )
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
    )
    semester_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_semesters.id", ondelete="SET NULL"),
        nullable=True,
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("college_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    frequency: Mapped[str] = mapped_column(String(30), default="ANNUAL", nullable=False)  # ONE_TIME, MONTHLY, QUARTERLY, SEMESTER_WISE, ANNUAL
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.00, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    academic_session: Mapped["AcademicSession"] = relationship("AcademicSession")
    school_class: Mapped[Optional["SchoolClass"]] = relationship("SchoolClass")
    course: Mapped[Optional["Course"]] = relationship("Course")
    components: Mapped[List["FeeStructureComponent"]] = relationship(
        "FeeStructureComponent", back_populates="fee_structure", cascade="all, delete-orphan"
    )
    installments: Mapped[List["FeeStructureInstallment"]] = relationship(
        "FeeStructureInstallment", back_populates="fee_structure", cascade="all, delete-orphan", order_by="FeeStructureInstallment.installment_number"
    )

    __table_args__ = (
        Index("ix_fee_structures_tenant_session", "tenant_id", "academic_session_id"),
    )


class FeeStructureComponent(BaseModel):
    """
    Sub-component of a fee structure linking a fee category with an amount.
    """
    __tablename__ = "fee_structure_components"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fee_structure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fee_structures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fee_category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fee_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.00, nullable=False)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    fee_structure: Mapped["FeeStructure"] = relationship("FeeStructure", back_populates="components")
    category: Mapped["FeeCategory"] = relationship("FeeCategory")


class FeeStructureInstallment(BaseModel):
    """
    Configured installment schedule for a fee structure with due dates and late penalties.
    """
    __tablename__ = "fee_structure_installments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fee_structure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fee_structures.id", ondelete="CASCADE"),
        nullable=False,
    )
    installment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    late_fine_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.00, nullable=False)
    late_fine_type: Mapped[str] = mapped_column(String(30), default="NONE", nullable=False)  # FIXED, DAILY_PERCENTAGE, NONE
    grace_period_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    fee_structure: Mapped["FeeStructure"] = relationship("FeeStructure", back_populates="installments")

    __table_args__ = (
        Index("ix_fee_structure_installments_structure", "fee_structure_id", "installment_number"),
    )


class FeeDiscountScholarship(BaseModel, SoftDeleteMixin):
    """
    Discounts, concessions, and scholarships applicable to student fees.
    """
    __tablename__ = "fee_discounts_scholarships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    discount_type: Mapped[str] = mapped_column(String(30), default="DISCOUNT", nullable=False)  # SCHOLARSHIP, CONCESSION, DISCOUNT
    calculation_type: Mapped[str] = mapped_column(String(30), default="PERCENTAGE", nullable=False)  # PERCENTAGE, FIXED_AMOUNT
    value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    applicable_categories: Mapped[list] = mapped_column(JSONB, default=lambda: ["ALL"], nullable=False)
    criteria: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class StudentFeeAllocation(BaseModel):
    """
    Assigns a specific fee structure and applicable scholarship/discount to a student.
    """
    __tablename__ = "student_fee_allocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    fee_structure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fee_structures.id", ondelete="CASCADE"),
        nullable=False,
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    discount_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fee_discounts_scholarships.id", ondelete="SET NULL"),
        nullable=True,
    )
    custom_discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.00, nullable=False)
    discount_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    net_fee_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)  # ACTIVE, WAIVED, CANCELLED

    student: Mapped["StudentProfile"] = relationship("StudentProfile")
    fee_structure: Mapped["FeeStructure"] = relationship("FeeStructure")
    discount: Mapped[Optional["FeeDiscountScholarship"]] = relationship("FeeDiscountScholarship")

    __table_args__ = (
        Index("ix_student_fee_allocations_tenant_student", "tenant_id", "student_id", "academic_session_id"),
    )


class FeeInvoice(BaseModel, SoftDeleteMixin):
    """
    Official student fee invoice. Real money ledger record completely separate from SaaS billing.
    """
    __tablename__ = "fee_invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fee_structure_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fee_structures.id", ondelete="SET NULL"),
        nullable=True,
    )
    allocation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_fee_allocations.id", ondelete="SET NULL"),
        nullable=True,
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.00, nullable=False)
    scholarship_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.00, nullable=False)
    late_fine_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.00, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    paid_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.00, nullable=False)
    balance_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ISSUED", nullable=False, index=True)  # DRAFT, ISSUED, PARTIALLY_PAID, PAID, OVERDUE, WAIVED, CANCELLED
    line_items: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    student: Mapped["StudentProfile"] = relationship("StudentProfile")
    fee_structure: Mapped[Optional["FeeStructure"]] = relationship("FeeStructure")
    academic_session: Mapped["AcademicSession"] = relationship("AcademicSession")
    payments: Mapped[List["FeePayment"]] = relationship(
        "FeePayment", back_populates="invoice", cascade="all, delete-orphan", order_by="FeePayment.payment_date"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_number", name="uq_fee_invoices_tenant_number"),
        Index("ix_fee_invoices_tenant_student", "tenant_id", "student_id"),
        Index("ix_fee_invoices_tenant_status", "tenant_id", "status"),
        Index("ix_fee_invoices_due_date", "tenant_id", "due_date"),
    )


class FeePayment(BaseModel):
    """
    Immutable ledger transaction for received fee payments (Cash, Cheque, Bank Transfer, UPI, Card, Razorpay).
    """
    __tablename__ = "fee_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fee_invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    receipt_number: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(30), default="CASH", nullable=False)  # CASH, CHEQUE, BANK_TRANSFER, UPI, CARD, RAZORPAY
    status: Mapped[str] = mapped_column(String(30), default="SUCCESS", nullable=False)  # SUCCESS, PENDING, FAILED, BOUNCED, REFUNDED

    # Offline Payment Fields
    cash_drawer_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cheque_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cheque_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    clearance_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # Online Payment (Razorpay) Fields
    razorpay_order_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    razorpay_signature: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    received_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reconciliation_status: Mapped[str] = mapped_column(String(30), default="RECONCILED", nullable=False)  # RECONCILED, UNRECONCILED, DISCREPANCY
    reconciled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    invoice: Mapped["FeeInvoice"] = relationship("FeeInvoice", back_populates="payments")
    student: Mapped["StudentProfile"] = relationship("StudentProfile")
    receiver: Mapped[Optional["User"]] = relationship("User")

    __table_args__ = (
        UniqueConstraint("tenant_id", "receipt_number", name="uq_fee_payments_tenant_receipt"),
        Index("ix_fee_payments_tenant_invoice", "tenant_id", "invoice_id"),
        Index("ix_fee_payments_tenant_student", "tenant_id", "student_id"),
        Index("ix_fee_payments_payment_date", "tenant_id", "payment_date"),
    )


class FeePaymentWebhookEvent(BaseModel):
    """
    Log of payment provider webhook events to enforce idempotency and prevent duplicate crediting.
    """
    __tablename__ = "fee_payment_webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), default="RAZORPAY", nullable=False)
    event_id: Mapped[str] = mapped_column(String(150), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PROCESSED", nullable=False)  # PROCESSED, IGNORED, FAILED
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", "event_id", name="uq_fee_webhook_event"),
        Index("ix_fee_webhook_events_tenant", "tenant_id", "event_id"),
    )
