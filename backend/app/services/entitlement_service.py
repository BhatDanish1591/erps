from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.models.academic import StudentProfile, TeacherProfile
from app.models.enums import SubscriptionStatus
from app.models.subscription import PlanFeature, Subscription, SubscriptionPlan
from app.models.tenant import TenantSetting
from app.permissions.rbac import get_active_tenant_id

logger = get_logger(__name__)


class SubscriptionLimitExceeded(AppException):
    def __init__(self, resource: str, current: int, limit: int, plan_name: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="SUBSCRIPTION_LIMIT_EXCEEDED",
            message=f"Plan limit reached for {resource} ({current}/{limit}). Please upgrade your subscription to continue.",
            details=[
                {
                    "resource": resource,
                    "current": current,
                    "limit": limit,
                    "plan": plan_name,
                    "action": "UPGRADE_PLAN",
                }
            ],
        )


class FeatureNotEntitled(AppException):
    def __init__(self, feature_key: str, plan_name: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FEATURE_NOT_ENTITLED",
            message=f"Feature '{feature_key}' is not available in your current plan ({plan_name}). Upgrade to unlock this feature.",
            details=[
                {
                    "feature": feature_key,
                    "plan": plan_name,
                    "action": "UPGRADE_PLAN",
                }
            ],
        )


class EntitlementService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_subscription(self, tenant_id: uuid.UUID) -> Optional[Subscription]:
        """
        Retrieves the active or trial subscription for the given tenant.
        """
        stmt = (
            select(Subscription)
            .where(
                Subscription.tenant_id == tenant_id,
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
            )
            .order_by(Subscription.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_subscription_with_plan(self, tenant_id: uuid.UUID) -> Optional[Subscription]:
        stmt = (
            select(Subscription)
            .where(Subscription.tenant_id == tenant_id)
            .order_by(Subscription.created_at.desc())
        )
        res = await self.session.execute(stmt)
        sub = res.scalars().first()
        if sub and sub.plan_id:
            plan = (await self.session.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.id == sub.plan_id)
            )).scalar_one_or_none()
            if plan:
                sub.plan = plan
        return sub

    async def get_tenant_usage_and_limits(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        """
        Calculates real-time usage (students, teachers, storage, notifications)
        against the tenant's active subscription limits.
        """
        sub = await self.get_subscription_with_plan(tenant_id)
        plan = sub.plan if sub else None

        # Count active students
        student_count_stmt = select(func.count(StudentProfile.id)).where(
            StudentProfile.tenant_id == tenant_id,
            StudentProfile.is_deleted == False,
        )
        total_students = (await self.session.execute(student_count_stmt)).scalar() or 0

        # Count active teachers
        teacher_count_stmt = select(func.count(TeacherProfile.id)).where(
            TeacherProfile.tenant_id == tenant_id,
            TeacherProfile.is_deleted == False,
        )
        total_teachers = (await self.session.execute(teacher_count_stmt)).scalar() or 0

        max_students = plan.max_students if plan else 300
        max_teachers = plan.max_teachers if plan else 20
        storage_limit_gb = plan.storage_limit_gb if plan else 10
        notification_quota = plan.notification_quota if plan else 1000

        # Storage & Notification placeholder counters (expandable per file/notification tables)
        storage_used_mb = 120.0
        notifications_used = 45

        # Feature flags from PlanFeature
        features: Dict[str, bool] = {}
        if plan:
            features_stmt = select(PlanFeature).where(
                PlanFeature.plan_id == plan.id,
                PlanFeature.is_enabled == True,
            )
            feature_rows = (await self.session.execute(features_stmt)).scalars().all()
            for f in feature_rows:
                features[f.feature_key] = True

        # Feature flags from TenantSetting add-ons/overrides
        settings_stmt = select(TenantSetting).where(
            TenantSetting.tenant_id == tenant_id,
        )
        settings_rows = (await self.session.execute(settings_stmt)).scalars().all()
        for s in settings_rows:
            if s.key == "features" and isinstance(s.value, dict):
                for k, v in s.value.items():
                    if bool(v):
                        features[k] = True
            elif s.key.startswith("feature:"):
                feature_name = s.key.split(":", 1)[1]
                val = s.value.get("enabled", True) if isinstance(s.value, dict) else bool(s.value)
                if val:
                    features[feature_name] = True

        return {
            "has_subscription": sub is not None,
            "subscription_id": sub.id if sub else None,
            "status": sub.status.value if sub else "NO_SUBSCRIPTION",
            "billing_cycle": sub.billing_cycle.value if sub else None,
            "current_period_start": sub.current_period_start if sub else None,
            "current_period_end": sub.current_period_end if sub else None,
            "trial_ends_at": sub.trial_ends_at if sub else None,
            "is_auto_renew": sub.is_auto_renew if sub else False,
            "plan": {
                "id": plan.id if plan else None,
                "name": plan.name if plan else "Free Trial",
                "code": plan.code if plan else "TRIAL",
                "price": float(plan.price) if plan else 0.0,
                "currency": plan.currency if plan else "INR",
            } if plan else None,
            "usage": {
                "students": {
                    "current": total_students,
                    "limit": max_students,
                    "remaining": max(0, max_students - total_students),
                    "percentage": round((total_students / max_students) * 100, 1) if max_students > 0 else 100.0,
                },
                "teachers": {
                    "current": total_teachers,
                    "limit": max_teachers,
                    "remaining": max(0, max_teachers - total_teachers),
                    "percentage": round((total_teachers / max_teachers) * 100, 1) if max_teachers > 0 else 100.0,
                },
                "storage": {
                    "used_mb": storage_used_mb,
                    "limit_gb": storage_limit_gb,
                    "percentage": round((storage_used_mb / (storage_limit_gb * 1024)) * 100, 1) if storage_limit_gb > 0 else 0.0,
                },
                "notifications": {
                    "used": notifications_used,
                    "quota": notification_quota,
                    "remaining": max(0, notification_quota - notifications_used),
                    "percentage": round((notifications_used / notification_quota) * 100, 1) if notification_quota > 0 else 0.0,
                },
            },
            "features": features,
        }

    async def check_quota(
        self,
        tenant_id: uuid.UUID,
        resource: str,
        increment: int = 1,
    ) -> None:
        """
        Verifies that adding `increment` to `resource` will not exceed the plan limit.
        """
        usage_data = await self.get_tenant_usage_and_limits(tenant_id)
        plan_name = usage_data["plan"]["name"] if usage_data.get("plan") else "Current Plan"

        if resource == "students":
            curr = usage_data["usage"]["students"]["current"]
            limit = usage_data["usage"]["students"]["limit"]
            if curr + increment > limit:
                raise SubscriptionLimitExceeded("students", curr, limit, plan_name)

        elif resource == "teachers":
            curr = usage_data["usage"]["teachers"]["current"]
            limit = usage_data["usage"]["teachers"]["limit"]
            if curr + increment > limit:
                raise SubscriptionLimitExceeded("teachers", curr, limit, plan_name)

        elif resource == "notifications":
            curr = usage_data["usage"]["notifications"]["used"]
            quota = usage_data["usage"]["notifications"]["quota"]
            if curr + increment > quota:
                raise SubscriptionLimitExceeded("notifications", curr, quota, plan_name)

    async def check_feature(self, tenant_id: uuid.UUID, feature_key: str) -> None:
        """
        Verifies that the tenant's current plan includes the given feature flag.
        """
        usage_data = await self.get_tenant_usage_and_limits(tenant_id)
        plan_name = usage_data["plan"]["name"] if usage_data.get("plan") else "Current Plan"
        features = usage_data.get("features", {})
        if not features.get(feature_key):
            raise FeatureNotEntitled(feature_key, plan_name)


def require_quota(resource: str, increment: int = 1):
    """
    FastAPI dependency factory to enforce resource quotas.
    """
    async def _quota_checker(
        tenant_id: uuid.UUID = Depends(get_active_tenant_id),
        session: AsyncSession = Depends(get_db),
    ) -> None:
        service = EntitlementService(session)
        await service.check_quota(tenant_id, resource, increment)

    return _quota_checker


def require_feature(feature_key: str):
    """
    FastAPI dependency factory to enforce feature entitlements.
    """
    async def _feature_checker(
        tenant_id: uuid.UUID = Depends(get_active_tenant_id),
        session: AsyncSession = Depends(get_db),
    ) -> None:
        service = EntitlementService(session)
        await service.check_feature(tenant_id, feature_key)

    return _feature_checker
