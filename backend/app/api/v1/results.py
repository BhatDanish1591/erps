from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import Response as RawResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException, AuthorizationException
from app.models.user import User
from app.permissions.rbac import get_active_tenant_id, get_current_user, get_current_user_claims, get_teacher_scope_user, require_any_role
from app.schemas.result import (
    BulkSubjectMarksEntryRequest,
    ClassPerformanceAnalytics,
    GradingScaleCreate,
    GradingScaleResponse,
    ReEvaluationActionRequest,
    ReEvaluationRequestCreate,
    ReEvaluationResponse,
    ResultApprovalWorkflowRequest,
    ResultRevisionHistoryResponse,
    ResultRevisionRequest,
    StudentSubjectResultResponse,
    StudentTermResultResponse,
)
from app.services.result_service import ResultService

router = APIRouter(prefix="/results", tags=["Results & Report Card Management"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. Grading Scale Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/grading-scales", response_model=Dict[str, Any])
async def get_default_grading_scale(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ResultService(session)
    scale = await service.get_or_create_grading_scale(tenant_id)
    return {"success": True, "data": scale.model_dump()}


@router.post("/grading-scales", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_grading_scale(
    data: GradingScaleCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ResultService(session)
    scale = await service.create_grading_scale(tenant_id, data)
    return {"success": True, "data": scale.model_dump()}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Subject Marks Entry
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/exams/{exam_id}/marks-roster")
async def get_marks_roster(
    exam_id: uuid.UUID,
    subject_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    teacher_user_id: Optional[uuid.UUID] = Depends(get_teacher_scope_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    data = await ResultService(session).load_marks_roster(tenant_id, exam_id, subject_id, teacher_user_id)
    return {"success": True, "data": data}


@router.post("/marks/bulk", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def bulk_enter_subject_marks(
    data: BulkSubjectMarksEntryRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    teacher_user_id: Optional[uuid.UUID] = Depends(get_teacher_scope_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ResultService(session)
    results = await service.enter_subject_marks_bulk(tenant_id, data, current_user, teacher_user_id)
    return {"success": True, "data": [r.model_dump() for r in results], "count": len(results)}


# ─────────────────────────────────────────────────────────────────────────────
# 3. Overall Term Results & Listings
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/exams/{exam_id}", response_model=Dict[str, Any])
async def list_exam_results(
    exam_id: uuid.UUID,
    class_id: Optional[uuid.UUID] = Query(None),
    section_id: Optional[uuid.UUID] = Query(None),
    approval_status: Optional[str] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ResultService(session)
    results = await service.list_exam_results(tenant_id, exam_id, class_id, section_id, approval_status)
    return {"success": True, "data": [r.model_dump() for r in results], "count": len(results)}


@router.get("/exams/{exam_id}/students/{student_id}", response_model=Dict[str, Any])
async def get_student_report_card(
    exam_id: uuid.UUID,
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(get_current_user_claims),
) -> Dict[str, Any]:
    service = ResultService(session)
    report = await service.get_student_report_card(tenant_id, exam_id, student_id, current_user, claims.get("role", ""))
    return {"success": True, "data": report.model_dump()}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Result Approval Workflow
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/approval-workflow", response_model=Dict[str, Any])
async def process_approval_workflow(
    data: ResultApprovalWorkflowRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(get_current_user_claims),
) -> Dict[str, Any]:
    if claims.get("role") == "TEACHER" and not current_user.is_superadmin and data.action != "SUBMIT_FOR_REVIEW":
        raise AuthorizationException("An institution administrator must approve, publish, or return results.")
    service = ResultService(session)
    result = await service.process_approval_workflow(tenant_id, data, current_user)
    return {"success": True, "data": result}


# ─────────────────────────────────────────────────────────────────────────────
# 5. Result Revisions & Audit History
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/revisions", response_model=Dict[str, Any])
async def revise_subject_marks(
    data: ResultRevisionRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ResultService(session)
    updated = await service.revise_subject_marks(tenant_id, data, current_user)
    return {"success": True, "data": updated.model_dump()}


@router.get("/revisions/{subject_result_id}", response_model=Dict[str, Any])
async def get_revision_history(
    subject_result_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ResultService(session)
    history = await service.get_revision_history(tenant_id, subject_result_id)
    return {"success": True, "data": [h.model_dump() for h in history]}


# ─────────────────────────────────────────────────────────────────────────────
# 6. Re-Evaluation Appeals
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/re-evaluations", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def submit_reevaluation_request(
    data: ReEvaluationRequestCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["STUDENT", "PARENT", "INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(get_current_user_claims),
) -> Dict[str, Any]:
    service = ResultService(session)
    req = await service.submit_reevaluation_request(tenant_id, data, current_user, claims.get("role", ""))
    return {"success": True, "data": req.model_dump()}


@router.get("/re-evaluations", response_model=Dict[str, Any])
async def list_reevaluation_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ResultService(session)
    reqs = await service.list_reevaluation_requests(tenant_id, status_filter)
    return {"success": True, "data": [r.model_dump() for r in reqs]}


@router.post("/re-evaluations/{request_id}/resolve", response_model=Dict[str, Any])
async def resolve_reevaluation_request(
    request_id: uuid.UUID,
    data: ReEvaluationActionRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ResultService(session)
    resolved = await service.resolve_reevaluation_request(tenant_id, request_id, data, current_user)
    return {"success": True, "data": resolved.model_dump()}


# ─────────────────────────────────────────────────────────────────────────────
# 7. Performance Analytics & PDF Report Card
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/exams/{exam_id}/analytics", response_model=Dict[str, Any])
async def get_class_performance_analytics(
    exam_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ResultService(session)
    analytics = await service.get_class_performance_analytics(tenant_id, exam_id)
    return {"success": True, "data": analytics.model_dump()}


@router.get("/exams/{exam_id}/students/{student_id}/pdf")
async def download_report_card_pdf(
    exam_id: uuid.UUID,
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(get_current_user_claims),
) -> RawResponse:
    service = ResultService(session)
    pdf_bytes = await service.generate_pdf_report_card(tenant_id, exam_id, student_id, current_user, claims.get("role", ""))
    return RawResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report_card_{student_id}_{exam_id}.pdf"'},
    )
