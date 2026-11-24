from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.permissions.rbac import get_active_tenant_id, get_current_user, get_current_user_claims, require_any_role
from app.schemas.fee import (
    BulkStudentFeeAllocationCreate,
    CohortInvoiceGenerateRequest,
    FeeCategoryCreate,
    FeeCategoryResponse,
    FeeCategoryUpdate,
    FeeCollectionLedgerResponse,
    FeeDashboardStatsResponse,
    FeeDiscountCreate,
    FeeDiscountResponse,
    FeeDiscountUpdate,
    FeeInvoiceCreate,
    FeeInvoiceResponse,
    FeePaymentResponse,
    FeeReceiptResponse,
    FeeStructureCreate,
    FeeStructureResponse,
    FeeStructureUpdate,
    OfflineFeePaymentCreate,
    OnlineFeePaymentInitiateRequest,
    OnlineFeePaymentInitiateResponse,
    OnlineFeePaymentVerifyRequest,
    OutstandingDuesReportResponse,
    StudentFeeAllocationCreate,
    StudentFeeAllocationResponse,
)
from app.services.fee_service import FeeService

router = APIRouter(prefix="/fees", tags=["Student Fees & Finance Management"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. Fee Categories
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/categories", response_model=List[FeeCategoryResponse])
async def list_fee_categories(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.list_categories(tenant_id)


@router.post("/categories", response_model=FeeCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_fee_category(
    payload: FeeCategoryCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.create_category(tenant_id, payload.model_dump())


@router.put("/categories/{category_id}", response_model=FeeCategoryResponse)
async def update_fee_category(
    category_id: uuid.UUID,
    payload: FeeCategoryUpdate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.update_category(tenant_id, category_id, payload.model_dump(exclude_unset=True))


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_fee_category(
    category_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Response:
    service = FeeService(session)
    deleted = await service.delete_category(tenant_id, category_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Fee category not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Fee Structures
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/structures", response_model=List[FeeStructureResponse])
async def list_fee_structures(
    academic_session_id: Optional[uuid.UUID] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    course_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.list_structures(tenant_id, academic_session_id, class_id, course_id)


@router.post("/structures", response_model=FeeStructureResponse, status_code=status.HTTP_201_CREATED)
async def create_fee_structure(
    payload: FeeStructureCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.create_structure(tenant_id, payload.model_dump())


@router.get("/structures/{structure_id}", response_model=FeeStructureResponse)
async def get_fee_structure(
    structure_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.get_structure(tenant_id, structure_id)


@router.delete("/structures/{structure_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_fee_structure(
    structure_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Response:
    service = FeeService(session)
    deleted = await service.delete_structure(tenant_id, structure_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Fee structure not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Discounts & Scholarships
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/discounts", response_model=List[FeeDiscountResponse])
async def list_fee_discounts(
    academic_session_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.list_discounts(tenant_id, academic_session_id)


@router.post("/discounts", response_model=FeeDiscountResponse, status_code=status.HTTP_201_CREATED)
async def create_fee_discount(
    payload: FeeDiscountCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.create_discount(tenant_id, payload.model_dump())


# ─────────────────────────────────────────────────────────────────────────────
# 4. Student Fee Allocations
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/allocations", response_model=StudentFeeAllocationResponse, status_code=status.HTTP_201_CREATED)
async def allocate_student_fee(
    payload: StudentFeeAllocationCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.allocate_student_fee(tenant_id, payload.model_dump())


@router.post("/allocations/bulk", response_model=Dict[str, Any])
async def bulk_allocate_fee_structure(
    payload: BulkStudentFeeAllocationCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    count = await service.bulk_allocate_fee_structure(
        tenant_id=tenant_id,
        academic_session_id=payload.academic_session_id,
        fee_structure_id=payload.fee_structure_id,
        class_id=payload.class_id,
        section_id=payload.section_id,
        course_id=payload.course_id,
        student_ids=payload.student_ids,
    )
    return {"message": f"Successfully allocated fee structure to {count} students.", "count": count}


# ─────────────────────────────────────────────────────────────────────────────
# 5. Invoices
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/invoices", response_model=List[FeeInvoiceResponse])
async def list_fee_invoices(
    academic_session_id: Optional[uuid.UUID] = Query(None),
    student_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.list_invoices(tenant_id, academic_session_id, student_id, status, class_id)


@router.post("/invoices", response_model=FeeInvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_single_invoice(
    payload: FeeInvoiceCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.create_invoice(tenant_id, payload.model_dump())


@router.post("/invoices/generate-cohort", response_model=List[FeeInvoiceResponse], status_code=status.HTTP_201_CREATED)
async def generate_cohort_invoices(
    payload: CohortInvoiceGenerateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.generate_cohort_invoices(
        tenant_id=tenant_id,
        academic_session_id=payload.academic_session_id,
        fee_structure_id=payload.fee_structure_id,
        title_prefix=payload.title_prefix,
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        installment_number=payload.installment_number,
        class_id=payload.class_id,
        section_id=payload.section_id,
        course_id=payload.course_id,
    )


@router.get("/invoices/{invoice_id}", response_model=FeeInvoiceResponse)
async def get_fee_invoice(
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "STUDENT", "PARENT"])),
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.get_invoice(tenant_id, invoice_id, user=current_user, role=claims.get("role", ""))


@router.post("/invoices/{invoice_id}/cancel", response_model=FeeInvoiceResponse)
async def cancel_fee_invoice(
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.cancel_invoice(tenant_id, invoice_id)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Payment Collection & Online Razorpay
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/payments/offline", response_model=FeePaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_offline_payment(
    payload: OfflineFeePaymentCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.record_offline_payment(tenant_id, current_user.id, payload.model_dump())


@router.post("/payments/razorpay/order", response_model=OnlineFeePaymentInitiateResponse)
async def initiate_razorpay_fee_payment(
    payload: OnlineFeePaymentInitiateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "STUDENT", "PARENT"])),
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.initiate_online_payment(
        tenant_id, payload.invoice_id, payload.amount, user=current_user, role=claims.get("role", ""),
    )


@router.post("/payments/razorpay/verify", response_model=FeePaymentResponse)
async def verify_razorpay_fee_payment(
    payload: OnlineFeePaymentVerifyRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "STUDENT", "PARENT"])),
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.verify_online_payment(
        tenant_id=tenant_id,
        payment_id=payload.payment_id,
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_signature=payload.razorpay_signature,
        user=current_user,
        role=claims.get("role", ""),
    )


@router.post("/payments/razorpay/webhook")
async def razorpay_fee_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    session: AsyncSession = Depends(get_db),
):
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header.")
    raw_body = await request.body()
    service = FeeService(session)
    return await service.process_razorpay_webhook(raw_body, x_razorpay_signature)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Receipts
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/receipts/{payment_id}", response_model=FeeReceiptResponse)
async def get_fee_receipt(
    payment_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "STUDENT", "PARENT"])),
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.get_receipt(tenant_id, payment_id, user=current_user, role=claims.get("role", ""))


@router.get("/receipts/{payment_id}/html", response_class=HTMLResponse)
async def get_fee_receipt_html(
    payment_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "STUDENT", "PARENT"])),
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    html_content = await service.generate_receipt_html(tenant_id, payment_id, user=current_user, role=claims.get("role", ""))
    return HTMLResponse(content=html_content)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Student / Parent Portal (/my-fees)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/my-fees", response_model=Dict[str, Any])
async def get_my_fees(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
):
    role = claims.get("role", "STUDENT")
    service = FeeService(session)
    return await service.get_my_fees(tenant_id, current_user, role)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Reports & Finance Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=FeeDashboardStatsResponse)
async def get_fee_dashboard_stats(
    academic_session_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.get_dashboard_stats(tenant_id, academic_session_id)


@router.get("/reports/defaulters", response_model=OutstandingDuesReportResponse)
async def get_outstanding_defaulters_report(
    academic_session_id: Optional[uuid.UUID] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.get_outstanding_defaulters_report(tenant_id, academic_session_id, class_id)


@router.get("/reports/collection-ledger", response_model=FeeCollectionLedgerResponse)
async def get_fee_collection_ledger(
    academic_session_id: Optional[uuid.UUID] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    payment_mode: Optional[str] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = FeeService(session)
    return await service.get_collection_ledger(tenant_id, academic_session_id, from_date, to_date, payment_mode)
