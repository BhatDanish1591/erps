from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.models.user import User
from app.permissions.rbac import get_active_tenant_id, get_current_user, require_any_role
from app.schemas.institution import (
    AcademicSessionSetupRequest,
    AcceptInvitationRequest,
    BulkTeacherInviteRequest,
    CustomDomainCreate,
    InstitutionProfileUpdate,
    InstitutionRegistrationRequest,
    OnboardingNotificationSetupRequest,
    OnboardingStructureSetupRequest,
    OnboardingSubjectsSetupRequest,
)
from app.services.institution_service import InstitutionService

router = APIRouter(prefix="/institutions", tags=["Institutions"])


# ── Public Registration & Domain Check ────────────────────────────────────────
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_institution(
    payload: InstitutionRegistrationRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = InstitutionService(session)
    result = await service.register_institution(
        payload=payload,
        ip_address=request.client.host if request.client else None,
    )
    return {"success": True, "data": result}


@router.get("/check-subdomain")
async def check_subdomain(
    slug: str = Query(..., min_length=2, max_length=100),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = InstitutionService(session)
    result = await service.check_subdomain(slug)
    return {"success": True, "data": result.model_dump()}


# ── Administrator & Staff Invitation Handling ─────────────────────────────────
@router.get("/invitations/verify")
async def verify_invitation(
    token: str = Query(...),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = InstitutionService(session)
    result = await service.verify_invitation(token)
    if not result.get("valid"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message"))
    return {"success": True, "data": result}


@router.post("/invitations/accept")
async def accept_invitation(
    payload: AcceptInvitationRequest,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = InstitutionService(session)
    result = await service.accept_invitation(
        token=payload.token,
        password=payload.password,
        full_name=payload.full_name,
        phone=payload.phone,
    )
    return {"success": True, "data": result}


# ── Institution Profile & Configuration ───────────────────────────────────────
@router.get("/profile")
async def get_institution_profile(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = InstitutionService(session)
    profile = await service.get_profile(tenant_id)
    return {"success": True, "data": profile}


@router.put("/profile")
async def update_institution_profile(
    payload: InstitutionProfileUpdate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = InstitutionService(session)
    res = await service.update_profile(tenant_id, payload)
    return {"success": True, "data": res}


# ── Onboarding Wizard APIs ────────────────────────────────────────────────────
@router.get("/onboarding/status")
async def get_onboarding_status(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = InstitutionService(session)
    data = await service.get_onboarding_status(tenant_id)
    return {"success": True, "data": data}


@router.post("/onboarding/academic-session")
async def onboarding_setup_academic_session(
    payload: AcademicSessionSetupRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = InstitutionService(session)
    acad_session = await service.setup_academic_session(tenant_id, payload)
    return {
        "success": True,
        "data": {"id": str(acad_session.id), "name": acad_session.name, "code": acad_session.code},
        "message": "Academic session configured successfully.",
    }


@router.post("/onboarding/structure")
async def onboarding_setup_structure(
    payload: OnboardingStructureSetupRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = InstitutionService(session)
    res = await service.setup_structure(tenant_id, payload)
    return {"success": True, "data": res}


@router.post("/onboarding/subjects")
async def onboarding_setup_subjects(
    payload: OnboardingSubjectsSetupRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = InstitutionService(session)
    res = await service.setup_subjects(tenant_id, payload)
    return {"success": True, "data": res}


@router.post("/onboarding/teachers")
async def onboarding_invite_teachers(
    payload: BulkTeacherInviteRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = InstitutionService(session)
    res = await service.invite_teachers(tenant_id, payload, current_user.id)
    return {"success": True, "data": res}


@router.post("/onboarding/notifications")
async def onboarding_setup_notifications(
    payload: OnboardingNotificationSetupRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = InstitutionService(session)
    res = await service.setup_notifications(tenant_id, payload)
    return {"success": True, "data": res}


@router.post("/onboarding/complete")
async def onboarding_complete(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = InstitutionService(session)
    res = await service.complete_onboarding(tenant_id)
    return {"success": True, "data": res}


# ── CSV / Excel Templates & Bulk Import ───────────────────────────────────────
@router.get("/templates/{import_type}")
async def download_import_template(import_type: str) -> Response:
    if import_type.lower() not in ["students", "teachers"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid types: students, teachers")

    service = InstitutionService(None)  # No DB needed for static template generation
    csv_text = service.get_template_csv(import_type)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={import_type}_template.csv"},
    )


@router.post("/import/students")
async def import_students_csv(
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    content = await file.read()
    try:
        csv_str = content.decode("utf-8")
    except UnicodeDecodeError:
        csv_str = content.decode("latin-1")

    service = InstitutionService(session)
    res = await service.parse_and_import_students(tenant_id, csv_str)
    return {"success": True, "data": res.model_dump()}


# ── Custom Domains ────────────────────────────────────────────────────────────
@router.get("/domains")
async def list_institution_domains(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = InstitutionService(session)
    domains = await service.repo.list_custom_domains(tenant_id)
    return {
        "success": True,
        "data": [
            {
                "id": str(d.id),
                "domain": d.domain,
                "is_primary": d.is_primary,
                "is_verified": d.is_verified,
            }
            for d in domains
        ],
    }


@router.post("/domains")
async def add_custom_domain(
    payload: CustomDomainCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = InstitutionService(session)
    domain = await service.repo.add_custom_domain(tenant_id, payload.domain)
    return {
        "success": True,
        "data": {"id": str(domain.id), "domain": domain.domain, "is_verified": domain.is_verified},
        "message": "Custom domain registered. DNS verification pending.",
    }
