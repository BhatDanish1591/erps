from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TenantStatus
from app.models.super_admin import GlobalAnnouncement, PlatformIntegration, PlatformSetting
from app.models.tenant import Tenant
from app.repositories.super_admin import SuperAdminRepository
from app.schemas.super_admin import (
    GlobalAnnouncementCreate,
    PlatformIntegrationUpdate,
    PlatformSettingUpdate,
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    SupportTicketCreate,
    SupportTicketReplyCreate,
)


class SuperAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SuperAdminRepository(session)

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        return await self.repo.get_dashboard_metrics()

    async def list_institutions(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        institution_type: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[Tenant], int]:
        return await self.repo.list_institutions(search, status, institution_type, page, size)

    async def get_institution_detail(self, tenant_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        return await self.repo.get_institution_detail(tenant_id)

    async def update_institution_status(
        self,
        tenant_id: uuid.UUID,
        new_status_str: str,
        actor_user_id: uuid.UUID,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tenant:
        try:
            target_status = TenantStatus(new_status_str)
        except ValueError:
            raise ValueError(f"Invalid tenant status: {new_status_str}")

        tenant = await self.repo.update_tenant_status(tenant_id, target_status)
        if not tenant:
            raise ValueError("Institution not found")

        # Record privileged action audit log
        await self.repo.record_audit_log(
            action=f"INSTITUTION_{new_status_str}",
            entity_type="TENANT",
            entity_id=str(tenant.id),
            user_id=actor_user_id,
            tenant_id=tenant.id,
            changes={"previous_status": tenant.status.value, "new_status": new_status_str, "reason": reason},
            ip_address=ip_address,
        )
        return tenant

    async def list_institution_users(
        self, tenant_id: uuid.UUID, page: int = 1, size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        return await self.repo.list_institution_users(tenant_id, page, size)

    # ── Plans ─────────────────────────────────────────────────────────────────
    async def list_plans(self) -> List[Any]:
        return await self.repo.list_plans()

    async def create_plan(
        self, payload: SubscriptionPlanCreate, actor_user_id: uuid.UUID, ip_address: Optional[str] = None
    ) -> Any:
        data = payload.model_dump(exclude={"features"})
        features = [f.model_dump() for f in payload.features]
        plan = await self.repo.create_plan(data, features)

        await self.repo.record_audit_log(
            action="CREATE_PLAN",
            entity_type="SUBSCRIPTION_PLAN",
            entity_id=str(plan.id),
            user_id=actor_user_id,
            changes={"code": plan.code, "name": plan.name, "price": float(plan.price)},
            ip_address=ip_address,
        )
        return plan

    async def update_plan(
        self,
        plan_id: uuid.UUID,
        payload: SubscriptionPlanUpdate,
        actor_user_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> Any:
        data = payload.model_dump(exclude={"features"}, exclude_unset=True)
        features = [f.model_dump() for f in payload.features] if payload.features is not None else None
        plan = await self.repo.update_plan(plan_id, data, features)
        if not plan:
            raise ValueError("Plan not found")

        await self.repo.record_audit_log(
            action="UPDATE_PLAN",
            entity_type="SUBSCRIPTION_PLAN",
            entity_id=str(plan.id),
            user_id=actor_user_id,
            changes=data,
            ip_address=ip_address,
        )
        return plan

    # ── Announcements ─────────────────────────────────────────────────────────
    async def list_announcements(self) -> List[GlobalAnnouncement]:
        return await self.repo.list_announcements()

    async def create_announcement(
        self, payload: GlobalAnnouncementCreate, actor_user_id: uuid.UUID
    ) -> GlobalAnnouncement:
        data = payload.model_dump()
        data["created_by_user_id"] = actor_user_id
        ann = await self.repo.create_announcement(data)

        await self.repo.record_audit_log(
            action="CREATE_ANNOUNCEMENT",
            entity_type="GLOBAL_ANNOUNCEMENT",
            entity_id=str(ann.id),
            user_id=actor_user_id,
            changes={"title": ann.title, "priority": ann.priority, "target_role": ann.target_role},
        )
        return ann

    async def delete_announcement(self, announcement_id: uuid.UUID, actor_user_id: uuid.UUID) -> bool:
        ok = await self.repo.delete_announcement(announcement_id)
        if ok:
            await self.repo.record_audit_log(
                action="DELETE_ANNOUNCEMENT",
                entity_type="GLOBAL_ANNOUNCEMENT",
                entity_id=str(announcement_id),
                user_id=actor_user_id,
                changes={},
            )
        return ok

    # ── Support Tickets ───────────────────────────────────────────────────────
    async def list_tickets(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        return await self.repo.list_tickets(status)

    async def create_ticket(self, payload: SupportTicketCreate, user_id: uuid.UUID) -> Any:
        import random
        num = f"TICK-{random.randint(10000, 99999)}"
        ticket_data = payload.model_dump()
        ticket_data["ticket_number"] = num
        ticket_data["user_id"] = user_id
        from app.models.super_admin import SupportTicket
        ticket = SupportTicket(**ticket_data)
        self.session.add(ticket)
        await self.session.flush()
        return ticket

    async def update_ticket_status(
        self, ticket_id: uuid.UUID, status: str, actor_user_id: uuid.UUID, assigned_to: Optional[uuid.UUID] = None
    ) -> bool:
        ok = await self.repo.update_ticket_status(ticket_id, status, assigned_to)
        if ok:
            await self.repo.record_audit_log(
                action="UPDATE_TICKET_STATUS",
                entity_type="SUPPORT_TICKET",
                entity_id=str(ticket_id),
                user_id=actor_user_id,
                changes={"status": status, "assigned_to_user_id": str(assigned_to) if assigned_to else None},
            )
        return ok

    async def reply_ticket(
        self, ticket_id: uuid.UUID, payload: SupportTicketReplyCreate, actor_user_id: uuid.UUID
    ) -> Any:
        return await self.repo.add_ticket_reply(
            ticket_id=ticket_id,
            user_id=actor_user_id,
            message=payload.message,
            is_internal=payload.is_internal,
        )

    # ── Platform Settings & Integrations ──────────────────────────────────────
    async def get_settings(self) -> List[PlatformSetting]:
        return await self.repo.get_all_settings()

    async def update_setting(
        self, payload: PlatformSettingUpdate, actor_user_id: uuid.UUID, ip_address: Optional[str] = None
    ) -> PlatformSetting:
        setting = await self.repo.upsert_setting(
            key=payload.key,
            value=payload.value,
            category=payload.category,
            description=payload.description,
        )
        await self.repo.record_audit_log(
            action="UPDATE_PLATFORM_SETTING",
            entity_type="PLATFORM_SETTING",
            entity_id=setting.key,
            user_id=actor_user_id,
            changes={"key": setting.key, "category": setting.category},
            ip_address=ip_address,
        )
        return setting

    async def list_integrations(self) -> List[PlatformIntegration]:
        return await self.repo.list_integrations()

    async def update_integration(
        self, provider: str, payload: PlatformIntegrationUpdate, actor_user_id: uuid.UUID
    ) -> Optional[PlatformIntegration]:
        item = await self.repo.update_integration(provider, payload.is_enabled, payload.config, payload.status)
        if item:
            await self.repo.record_audit_log(
                action="UPDATE_INTEGRATION",
                entity_type="PLATFORM_INTEGRATION",
                entity_id=provider,
                user_id=actor_user_id,
                changes={"is_enabled": payload.is_enabled, "status": payload.status},
            )
        return item

    # ── Audit Logs ────────────────────────────────────────────────────────────
    async def list_audit_logs(
        self, action: Optional[str] = None, entity_type: Optional[str] = None, page: int = 1, size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        return await self.repo.list_audit_logs(action, entity_type, page, size)
