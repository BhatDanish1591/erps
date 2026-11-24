from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.permissions.rbac import get_active_tenant_id, get_current_user, get_current_user_claims, require_any_role
from app.schemas.parent import (
    AdminApproveLinkRequest,
    AdminGenerateVerificationCodeRequest,
    AdminInviteParentRequest,
    ChildAssignmentItem,
    ChildAttendanceResponse,
    ChildDetailedProfileResponse,
    ChildExaminationsResponse,
    ChildStudyMaterialItem,
    ChildTeacherContact,
    ChildTermResultResponse,
    ChildTimetableResponse,
    LinkedChildSummary,
    ParentLinkChildRequest,
    ParentLinkRequestItem,
    ParentTeacherMessageResponse,
    SendMessageRequest,
    VerificationCodeResponse,
)
from app.services.parent_service import ParentService

router = APIRouter(prefix="/parents", tags=["Parent & Guardian Portal"])


def get_parent_service(session: AsyncSession = Depends(get_db)) -> ParentService:
    return ParentService(session)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Multi-Child Parent Portal (Accessible to Parents)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/children",
    response_model=List[LinkedChildSummary],
    summary="List all linked children for the current parent across all institutions",
)
async def list_linked_children(
    current_user: User = Depends(get_current_user),
    service: ParentService = Depends(get_parent_service),
) -> List[LinkedChildSummary]:
    return await service.get_parent_children(current_user.id)


@router.post(
    "/link-requests",
    status_code=status.HTTP_201_CREATED,
    summary="Submit child linking request (auto-verified if valid security code provided, else queued for admin approval)",
)
async def request_link_child(
    data: ParentLinkChildRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    service: ParentService = Depends(get_parent_service),
) -> Dict[str, Any]:
    return await service.link_child_request(tenant_id, current_user.id, data)


@router.get(
    "/children/{student_id}/profile",
    response_model=ChildDetailedProfileResponse,
    summary="Get detailed demographic and academic profile of a verified linked child",
)
async def get_child_profile(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    service: ParentService = Depends(get_parent_service),
) -> ChildDetailedProfileResponse:
    return await service.get_child_profile(tenant_id, current_user.id, student_id)


@router.get(
    "/children/{student_id}/attendance",
    response_model=ChildAttendanceResponse,
    summary="Get attendance summary, history, and low-attendance alert for a verified linked child",
)
async def get_child_attendance(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    service: ParentService = Depends(get_parent_service),
) -> ChildAttendanceResponse:
    return await service.get_child_attendance(tenant_id, current_user.id, student_id)


@router.get(
    "/children/{student_id}/timetable",
    response_model=ChildTimetableResponse,
    summary="Get weekly timetable schedule for a verified linked child",
)
async def get_child_timetable(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    service: ParentService = Depends(get_parent_service),
) -> ChildTimetableResponse:
    return await service.get_child_timetable(tenant_id, current_user.id, student_id)


@router.get(
    "/children/{student_id}/examinations",
    response_model=ChildExaminationsResponse,
    summary="Get upcoming exam dates and past examinations for a verified linked child",
)
async def get_child_examinations(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    service: ParentService = Depends(get_parent_service),
) -> ChildExaminationsResponse:
    return await service.get_child_examinations(tenant_id, current_user.id, student_id)


@router.get(
    "/children/{student_id}/results",
    response_model=List[ChildTermResultResponse],
    summary="Get published exam results and term report card grades for a verified linked child",
)
async def get_child_results(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    service: ParentService = Depends(get_parent_service),
) -> List[ChildTermResultResponse]:
    return await service.get_child_results(tenant_id, current_user.id, student_id)


@router.get(
    "/children/{student_id}/assignments",
    response_model=List[ChildAssignmentItem],
    summary="Get homework and assignments status, deadlines, and teacher feedback for a verified linked child",
)
async def get_child_assignments(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    service: ParentService = Depends(get_parent_service),
) -> List[ChildAssignmentItem]:
    return await service.get_child_assignments(tenant_id, current_user.id, student_id)


@router.get(
    "/children/{student_id}/materials",
    response_model=List[ChildStudyMaterialItem],
    summary="Get class LMS study materials and recorded lecture references for a verified linked child",
)
async def get_child_materials(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    service: ParentService = Depends(get_parent_service),
) -> List[ChildStudyMaterialItem]:
    return await service.get_child_study_materials(tenant_id, current_user.id, student_id)


@router.get(
    "/children/{student_id}/fees",
    summary="Get fee invoices, pending dues balance, and verified payment history for a child",
)
async def get_child_fees(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    service: ParentService = Depends(get_parent_service),
) -> Dict[str, Any]:
    return await service.get_child_fees(tenant_id, current_user.id, student_id)


@router.get(
    "/children/{student_id}/teachers",
    response_model=List[ChildTeacherContact],
    summary="Get assigned subject and class teachers for a verified linked child",
)
async def get_child_teachers(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    service: ParentService = Depends(get_parent_service),
) -> List[ChildTeacherContact]:
    return await service.get_child_teachers(tenant_id, current_user.id, student_id)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Parent-Teacher Messaging & Communications
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/communications",
    status_code=status.HTTP_201_CREATED,
    summary="Send a communication inquiry or reply between parent and assigned teacher",
)
async def send_parent_teacher_message(
    data: SendMessageRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    service: ParentService = Depends(get_parent_service),
) -> Dict[str, Any]:
    role = claims.get("role", "PARENT")
    return await service.send_message(tenant_id, current_user.id, role, data)


@router.get(
    "/communications",
    response_model=List[ParentTeacherMessageResponse],
    summary="List communication message threads for the current parent or teacher",
)
async def list_parent_teacher_messages(
    student_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    service: ParentService = Depends(get_parent_service),
) -> List[ParentTeacherMessageResponse]:
    role = claims.get("role", "PARENT")
    return await service.list_messages(current_user.id, role, student_id)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Administrator Governance & Verification Controls
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/admin/linking-requests",
    response_model=List[ParentLinkRequestItem],
    dependencies=[Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"]))],
    summary="List pending parent-student linking requests awaiting administrative verification",
)
async def list_pending_linking_requests(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: ParentService = Depends(get_parent_service),
) -> List[ParentLinkRequestItem]:
    return await service.list_pending_requests(tenant_id)


@router.post(
    "/admin/linking-requests/{link_id}/process",
    dependencies=[Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"]))],
    summary="Approve or reject a parent-student linking request",
)
async def process_linking_request(
    link_id: uuid.UUID,
    data: AdminApproveLinkRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    service: ParentService = Depends(get_parent_service),
) -> Dict[str, Any]:
    return await service.process_link_request(tenant_id, link_id, current_user.id, data)


@router.post(
    "/admin/invite",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"]))],
    summary="Directly invite a parent with pre-verified student linkage",
)
async def admin_invite_parent(
    data: AdminInviteParentRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    service: ParentService = Depends(get_parent_service),
) -> Dict[str, Any]:
    return await service.admin_invite_parent(tenant_id, current_user.id, data)


@router.post(
    "/admin/verification-codes",
    response_model=VerificationCodeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"]))],
    summary="Generate a secure one-time linking verification code for a student",
)
async def generate_student_verification_code(
    data: AdminGenerateVerificationCodeRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    service: ParentService = Depends(get_parent_service),
) -> VerificationCodeResponse:
    return await service.generate_verification_code(tenant_id, current_user.id, data)
