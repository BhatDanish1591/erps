from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.permissions.rbac import get_active_tenant_id, get_current_user, require_any_role
from app.schemas.notification import (
    TenantIntegrationCreate,
    TenantIntegrationResponse,
    TenantIntegrationUpdate,
    TestIntegrationRequest,
    TestIntegrationResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/integrations", tags=["Tenant Integrations"])


def get_notification_service(session: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(session)


def _mask_credentials(creds: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not creds:
        return {}
    masked = {}
    for k, v in creds.items():
        s = str(v)
        if len(s) > 8:
            masked[k] = f"{s[:4]}...{s[-4:]}"
        else:
            masked[k] = "******"
    return masked


@router.get(
    "",
    response_model=List[TenantIntegrationResponse],
    summary="List all third-party integrations configured for current institution",
    dependencies=[Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"]))],
)
async def list_tenant_integrations(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: NotificationService = Depends(get_notification_service),
):
    items = await service.repo.list_integrations(tenant_id=tenant_id)
    response = []
    for item in items:
        resp_item = TenantIntegrationResponse.model_validate(item)
        resp_item.masked_credentials = _mask_credentials(item.credentials_encrypted)
        response.append(resp_item)
    return response


@router.post(
    "",
    response_model=TenantIntegrationResponse,
    summary="Configure or update third-party integration (SES, Resend, WhatsApp, MSG91, FCM, APNs, Razorpay, S3/R2)",
    dependencies=[Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"]))],
)
async def configure_integration(
    data: TenantIntegrationCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: NotificationService = Depends(get_notification_service),
):
    integration = await service.repo.upsert_integration(
        tenant_id=tenant_id,
        provider_type=data.provider_type,
        is_enabled=data.is_enabled,
        credentials=data.credentials,
        settings=data.settings,
        webhook_secret=data.webhook_secret,
        status="UNTESTED",
    )
    await service.session.commit()
    resp = TenantIntegrationResponse.model_validate(integration)
    resp.masked_credentials = _mask_credentials(integration.credentials_encrypted)
    return resp


@router.get(
    "/{provider_type}",
    response_model=TenantIntegrationResponse,
    summary="Get integration configuration by provider type",
    dependencies=[Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"]))],
)
async def get_integration(
    provider_type: str,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: NotificationService = Depends(get_notification_service),
):
    integration = await service.repo.get_integration(tenant_id=tenant_id, provider_type=provider_type)
    if not integration:
        raise HTTPException(status_code=404, detail=f"Integration {provider_type} not found")
    resp = TenantIntegrationResponse.model_validate(integration)
    resp.masked_credentials = _mask_credentials(integration.credentials_encrypted)
    return resp


@router.post(
    "/{provider_type}/test",
    response_model=TestIntegrationResponse,
    summary="Test connectivity and credentials for an integration provider",
    dependencies=[Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"]))],
)
async def test_integration(
    provider_type: str,
    data: Optional[TestIntegrationRequest] = None,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: NotificationService = Depends(get_notification_service),
):
    recipient = data.recipient if data else None
    result = await service.test_integration(
        tenant_id=tenant_id,
        provider_type=provider_type,
        recipient=recipient,
    )
    return TestIntegrationResponse(
        success=result["success"],
        provider_type=provider_type,
        message=result["message"],
        details=result.get("details"),
    )
