from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BadRequestException, NotFoundException, AuthorizationException
from app.models.user import User
from app.permissions.rbac import get_active_tenant_id, get_current_user, get_current_user_claims, require_any_role
from app.schemas.lms import (
    StudyMaterialCreate,
    StudyMaterialResponse,
    StudyMaterialUpdate,
    StudyMaterialVersionResponse,
)
from app.services.lms_service import LMSService
from app.utils.storage import storage_service

router = APIRouter(prefix="/materials", tags=["Study Material & LMS Module"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. Local File Streaming Fallback (HMAC Secured)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/files/stream")
async def stream_local_file(
    key: str = Query(..., description="Storage key"),
    exp: int = Query(..., description="Timestamp expiry"),
    sig: str = Query(..., description="HMAC signature"),
    mode: str = Query("download", description="download or preview"),
):
    """
    Direct file streaming for local storage fallback, validated via HMAC signature and expiry.
    """
    if not storage_service.verify_signed_local_token(key, exp, sig):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The download/preview token is invalid or has expired.",
        )

    file_bytes, mime_type = storage_service.read_local_file(key)
    filename = key.split("/")[-1].split("_", 1)[-1] if "_" in key else "file"

    disposition = "attachment" if mode == "download" else "inline"
    headers = {
        "Content-Disposition": f'{disposition}; filename="{filename}"',
        "Content-Type": mime_type,
    }

    return Response(content=file_bytes, media_type=mime_type, headers=headers)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Upload / Create Study Material
# ─────────────────────────────────────────────────────────────────────────────

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_study_material_json(
    data: StudyMaterialCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Create study material record without initial file upload (e.g. video link, reference URL).
    """
    service = LMSService(session)
    result = await service.create_study_material(
        tenant_id=tenant_id,
        data=data.model_dump(),
        uploaded_by=current_user.id,
    )
    return {"success": True, "data": result.model_dump()}


@router.post("/upload", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def upload_study_material_with_file(
    file: UploadFile = File(...),
    title: str = Form(...),
    academic_session_id: uuid.UUID = Form(...),
    description: Optional[str] = Form(None),
    chapter: Optional[str] = Form(None),
    material_type: str = Form("PDF"),
    category: str = Form("GENERAL"),
    subject_id: Optional[uuid.UUID] = Form(None),
    class_id: Optional[uuid.UUID] = Form(None),
    section_id: Optional[uuid.UUID] = Form(None),
    department_id: Optional[uuid.UUID] = Form(None),
    course_id: Optional[uuid.UUID] = Form(None),
    semester_id: Optional[uuid.UUID] = Form(None),
    batch_id: Optional[uuid.UUID] = Form(None),
    external_url: Optional[str] = Form(None),
    tags_json: Optional[str] = Form(None),
    is_published: bool = Form(True),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Upload a study material file (PDF, Doc, PPT, Images, Video, etc.) with metadata.
    """
    tags = []
    if tags_json:
        try:
            tags = json.loads(tags_json)
        except Exception:
            tags = [t.strip() for t in tags_json.split(",") if t.strip()]

    file_bytes = await file.read()
    data = {
        "title": title,
        "academic_session_id": academic_session_id,
        "description": description,
        "chapter": chapter,
        "material_type": material_type,
        "category": category,
        "subject_id": subject_id,
        "class_id": class_id,
        "section_id": section_id,
        "department_id": department_id,
        "course_id": course_id,
        "semester_id": semester_id,
        "batch_id": batch_id,
        "external_url": external_url,
        "tags": tags,
        "is_published": is_published,
    }

    service = LMSService(session)
    result = await service.create_study_material(
        tenant_id=tenant_id,
        data=data,
        uploaded_by=current_user.id,
        file_bytes=file_bytes,
        file_name=file.filename,
        content_type=file.content_type,
    )
    return {"success": True, "data": result.model_dump()}


# ─────────────────────────────────────────────────────────────────────────────
# 3. List & Filter Study Materials
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=Dict[str, Any])
async def list_study_materials(
    academic_session_id: Optional[uuid.UUID] = Query(None),
    subject_id: Optional[uuid.UUID] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    section_id: Optional[uuid.UUID] = Query(None),
    category: Optional[str] = Query(None),
    material_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    is_published: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    List, filter, and search study materials.
    Students and parents only see published materials by default.
    """
    effective_published = is_published
    user_role = claims.get("role")
    if user_role in ("STUDENT", "PARENT"):
        effective_published = True

    service = LMSService(session)
    offset = (page - 1) * size
    items, total = await service.list_study_materials(
        tenant_id=tenant_id,
        academic_session_id=academic_session_id,
        subject_id=subject_id,
        class_id=class_id,
        section_id=section_id,
        category=category,
        material_type=material_type,
        search=search,
        is_published=effective_published,
        limit=size,
        offset=offset,
    )
    return {
        "success": True,
        "data": [item.model_dump() for item in items],
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "total_pages": (total + size - 1) // size if total > 0 else 1,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Get, Download, Update & Delete Material
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{material_id}", response_model=Dict[str, Any])
async def get_study_material_details(
    material_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = LMSService(session)
    material = await service.get_study_material(tenant_id, material_id, track_view=True)
    return {"success": True, "data": material.model_dump()}


@router.get("/{material_id}/download")
async def download_study_material(
    material_id: uuid.UUID,
    redirect: bool = Query(True, description="Whether to redirect immediately or return URL in JSON"),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
):
    service = LMSService(session)
    url_info = await service.get_download_url(tenant_id, material_id)
    if redirect:
        return RedirectResponse(url=url_info["url"], status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    return {"success": True, "data": url_info}


@router.put("/{material_id}", response_model=Dict[str, Any])
async def update_study_material_metadata(
    material_id: uuid.UUID,
    data: StudyMaterialUpdate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = LMSService(session)
    updated = await service.update_study_material(
        tenant_id=tenant_id,
        material_id=material_id,
        data=data.model_dump(exclude_unset=True),
    )
    return {"success": True, "data": updated.model_dump()}


@router.post("/{material_id}/versions", response_model=Dict[str, Any])
async def upload_new_material_version(
    material_id: uuid.UUID,
    file: UploadFile = File(...),
    change_summary: str = Form("Updated study material version"),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Upload a new version of an existing study material with change log audit.
    """
    service = LMSService(session)
    file_bytes = await file.read()
    updated = await service.upload_material_version(
        tenant_id=tenant_id,
        material_id=material_id,
        change_summary=change_summary,
        uploaded_by=current_user.id,
        file_bytes=file_bytes,
        file_name=file.filename,
        content_type=file.content_type,
    )
    return {"success": True, "data": updated.model_dump()}


@router.delete("/{material_id}", response_model=Dict[str, Any])
async def delete_study_material(
    material_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = LMSService(session)
    success = await service.delete_study_material(tenant_id, material_id)
    return {"success": success, "message": "Study material deleted successfully."}
