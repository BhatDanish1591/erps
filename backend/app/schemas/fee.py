from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# 1. Fee Category Schemas
# ─────────────────────────────────────────────────────────────────────────────

class FeeCategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    fee_type: str = Field("ACADEMIC", max_length=30)  # ACADEMIC, FACILITY, ONE_TIME, RECURRING, OPTIONAL
    description: Optional[str] = Field(None, max_length=255)
    is_refundable: bool = False
    is_active: bool = True


class FeeCategoryCreate(FeeCategoryBase):
    pass


class FeeCategoryUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    fee_type: Optional[str] = None
    description: Optional[str] = None
    is_refundable: Optional[bool] = None
    is_active: Optional[bool] = None


class FeeCategoryResponse(FeeCategoryBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Fee Structure Schemas (with Components & Installments)
# ─────────────────────────────────────────────────────────────────────────────

class FeeStructureComponentCreate(BaseModel):
    fee_category_id: uuid.UUID
    amount: float = Field(..., ge=0)
    is_optional: bool = False
    description: Optional[str] = None


class FeeStructureComponentResponse(BaseModel):
    id: uuid.UUID
    fee_structure_id: uuid.UUID
    fee_category_id: uuid.UUID
    category_name: Optional[str] = None
    category_code: Optional[str] = None
    amount: float
    is_optional: bool
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeeStructureInstallmentCreate(BaseModel):
    installment_number: int = Field(..., ge=1)
    name: str = Field(..., max_length=100)
    due_date: date
    amount: float = Field(..., ge=0)
    late_fine_amount: float = 0.0
    late_fine_type: str = "NONE"  # FIXED, DAILY_PERCENTAGE, NONE
    grace_period_days: int = 0


class FeeStructureInstallmentResponse(BaseModel):
    id: uuid.UUID
    fee_structure_id: uuid.UUID
    installment_number: int
    name: str
    due_date: date
    amount: float
    late_fine_amount: float
    late_fine_type: str
    grace_period_days: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeeStructureCreate(BaseModel):
    academic_session_id: uuid.UUID
    name: str = Field(..., max_length=150)
    institution_type: str = "SCHOOL"  # SCHOOL | COLLEGE
    class_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    frequency: str = "ANNUAL"  # ONE_TIME, MONTHLY, QUARTERLY, SEMESTER_WISE, ANNUAL
    currency: str = "INR"
    due_date: Optional[date] = None
    components: List[FeeStructureComponentCreate] = []
    installments: List[FeeStructureInstallmentCreate] = []


class FeeStructureUpdate(BaseModel):
    name: Optional[str] = None
    frequency: Optional[str] = None
    due_date: Optional[date] = None
    is_active: Optional[bool] = None
    components: Optional[List[FeeStructureComponentCreate]] = None
    installments: Optional[List[FeeStructureInstallmentCreate]] = None


class FeeStructureResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    academic_session_id: uuid.UUID
    academic_session_name: Optional[str] = None
    name: str
    institution_type: str
    class_id: Optional[uuid.UUID] = None
    class_name: Optional[str] = None
    course_id: Optional[uuid.UUID] = None
    course_name: Optional[str] = None
    semester_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    frequency: str
    total_amount: float
    currency: str
    due_date: Optional[date] = None
    is_active: bool
    components: List[FeeStructureComponentResponse] = []
    installments: List[FeeStructureInstallmentResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Discounts & Scholarships
# ─────────────────────────────────────────────────────────────────────────────

class FeeDiscountCreate(BaseModel):
    academic_session_id: uuid.UUID
    name: str = Field(..., max_length=150)
    discount_type: str = "DISCOUNT"  # SCHOLARSHIP, CONCESSION, DISCOUNT
    calculation_type: str = "PERCENTAGE"  # PERCENTAGE, FIXED_AMOUNT
    value: float = Field(..., ge=0)
    applicable_categories: List[str] = ["ALL"]
    criteria: Optional[str] = None
    is_active: bool = True


class FeeDiscountUpdate(BaseModel):
    name: Optional[str] = None
    discount_type: Optional[str] = None
    calculation_type: Optional[str] = None
    value: Optional[float] = None
    applicable_categories: Optional[List[str]] = None
    criteria: Optional[str] = None
    is_active: Optional[bool] = None


class FeeDiscountResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    academic_session_id: uuid.UUID
    name: str
    discount_type: str
    calculation_type: str
    value: float
    applicable_categories: List[str]
    criteria: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Student Fee Allocations
# ─────────────────────────────────────────────────────────────────────────────

class StudentFeeAllocationCreate(BaseModel):
    student_id: uuid.UUID
    fee_structure_id: uuid.UUID
    academic_session_id: uuid.UUID
    discount_id: Optional[uuid.UUID] = None
    custom_discount_amount: float = 0.0
    discount_reason: Optional[str] = None


class BulkStudentFeeAllocationCreate(BaseModel):
    academic_session_id: uuid.UUID
    fee_structure_id: uuid.UUID
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None
    student_ids: Optional[List[uuid.UUID]] = None


class StudentFeeAllocationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    admission_number: Optional[str] = None
    fee_structure_id: uuid.UUID
    fee_structure_name: Optional[str] = None
    academic_session_id: uuid.UUID
    discount_id: Optional[uuid.UUID] = None
    discount_name: Optional[str] = None
    custom_discount_amount: float
    discount_reason: Optional[str] = None
    net_fee_amount: float
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Fee Invoices
# ─────────────────────────────────────────────────────────────────────────────

class FeeInvoiceLineItem(BaseModel):
    category_id: Optional[str] = None
    category_name: str
    description: Optional[str] = None
    amount: float


class FeeInvoiceCreate(BaseModel):
    student_id: uuid.UUID
    academic_session_id: uuid.UUID
    fee_structure_id: Optional[uuid.UUID] = None
    allocation_id: Optional[uuid.UUID] = None
    title: str = Field(..., max_length=200)
    issue_date: date
    due_date: date
    line_items: List[FeeInvoiceLineItem]
    discount_amount: float = 0.0
    scholarship_amount: float = 0.0
    notes: Optional[str] = None


class CohortInvoiceGenerateRequest(BaseModel):
    academic_session_id: uuid.UUID
    fee_structure_id: uuid.UUID
    title_prefix: str = "Term Fee Invoice"
    issue_date: date
    due_date: date
    installment_number: Optional[int] = None
    class_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    course_id: Optional[uuid.UUID] = None


class FeeInvoiceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    student_admission_number: Optional[str] = None
    student_roll_number: Optional[str] = None
    class_name: Optional[str] = None
    section_name: Optional[str] = None
    course_name: Optional[str] = None
    fee_structure_id: Optional[uuid.UUID] = None
    fee_structure_name: Optional[str] = None
    academic_session_id: uuid.UUID
    academic_session_name: Optional[str] = None
    invoice_number: str
    title: str
    issue_date: date
    due_date: date
    subtotal: float
    discount_amount: float
    scholarship_amount: float
    late_fine_amount: float
    total_amount: float
    paid_amount: float
    balance_amount: float
    status: str  # DRAFT, ISSUED, PARTIALLY_PAID, PAID, OVERDUE, WAIVED, CANCELLED
    line_items: List[Dict[str, Any]] = []
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Fee Payments & Receipts
# ─────────────────────────────────────────────────────────────────────────────

class OfflineFeePaymentCreate(BaseModel):
    invoice_id: uuid.UUID
    amount: float = Field(..., gt=0)
    payment_mode: str = Field("CASH")  # CASH, CHEQUE, BANK_TRANSFER, UPI, CARD
    payment_date: Optional[datetime] = None
    cash_drawer_reference: Optional[str] = None
    cheque_number: Optional[str] = None
    bank_name: Optional[str] = None
    cheque_date: Optional[date] = None
    transaction_reference: Optional[str] = None  # UTR, IMPS, POS slip
    remarks: Optional[str] = None


class OnlineFeePaymentInitiateRequest(BaseModel):
    invoice_id: uuid.UUID
    amount: Optional[float] = None  # None = pay full balance


class OnlineFeePaymentInitiateResponse(BaseModel):
    payment_id: uuid.UUID
    invoice_id: uuid.UUID
    invoice_number: str
    amount: float
    currency: str
    gateway: str
    razorpay_order_id: str
    key_id: Optional[str] = None
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    student_phone: Optional[str] = None


class OnlineFeePaymentVerifyRequest(BaseModel):
    payment_id: uuid.UUID
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class FeePaymentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    invoice_id: uuid.UUID
    invoice_number: Optional[str] = None
    student_id: uuid.UUID
    student_name: Optional[str] = None
    student_admission_number: Optional[str] = None
    receipt_number: str
    amount: float
    payment_date: datetime
    payment_mode: str
    status: str
    cash_drawer_reference: Optional[str] = None
    cheque_number: Optional[str] = None
    bank_name: Optional[str] = None
    cheque_date: Optional[date] = None
    clearance_date: Optional[date] = None
    transaction_reference: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    received_by_name: Optional[str] = None
    reconciliation_status: str
    remarks: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeeReceiptResponse(BaseModel):
    receipt_number: str
    payment_id: uuid.UUID
    invoice_number: str
    invoice_title: str
    institution_name: str
    institution_logo_url: Optional[str] = None
    institution_address: Optional[str] = None
    student_name: str
    admission_number: str
    roll_number: Optional[str] = None
    class_or_course: str
    section: Optional[str] = None
    academic_session: str
    payment_date: datetime
    payment_mode: str
    amount_paid: float
    amount_in_words: str
    subtotal: float
    discount_amount: float
    fine_amount: float
    total_invoice_amount: float
    remaining_balance: float
    transaction_reference: Optional[str] = None
    collected_by: Optional[str] = None
    line_items: List[Dict[str, Any]] = []


# ─────────────────────────────────────────────────────────────────────────────
# 7. Reports & Finance Dashboard
# ─────────────────────────────────────────────────────────────────────────────

class FeeDashboardStatsResponse(BaseModel):
    total_invoiced_amount: float
    total_collected_amount: float
    total_pending_dues: float
    collection_rate_percent: float
    overdue_invoices_count: int
    overdue_amount: float
    today_collection_amount: float
    active_students_billed_count: int
    collection_by_payment_mode: Dict[str, float]
    collection_by_category: Dict[str, float]
    monthly_collection_trend: List[Dict[str, Any]]


class OutstandingDefaulterItem(BaseModel):
    student_id: uuid.UUID
    student_name: str
    admission_number: str
    roll_number: Optional[str] = None
    class_or_course: str
    section: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    unpaid_invoices_count: int
    oldest_due_date: date
    total_due_amount: float
    overdue_days: int


class OutstandingDuesReportResponse(BaseModel):
    total_defaulters_count: int
    total_outstanding_amount: float
    defaulters: List[OutstandingDefaulterItem]


class FeeCollectionLedgerItem(BaseModel):
    payment_id: uuid.UUID
    receipt_number: str
    payment_date: datetime
    student_name: str
    admission_number: str
    class_or_course: str
    amount: float
    payment_mode: str
    transaction_reference: Optional[str] = None
    collected_by: Optional[str] = None
    reconciliation_status: str


class FeeCollectionLedgerResponse(BaseModel):
    total_count: int
    total_amount_collected: float
    items: List[FeeCollectionLedgerItem]
