from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin


class ScheduledReport(BaseModel, SoftDeleteMixin):
    """
    Automated recurring report schedule for Super Admin or Institution staff.
    """
    __tablename__ = "scheduled_reports"

    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), default="WEEKLY", nullable=False)  # DAILY, WEEKLY, MONTHLY
    format: Mapped[str] = mapped_column(String(20), default="PDF", nullable=False)  # PDF, EXCEL
    recipients: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    filters: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_scheduled_reports_tenant_type", "tenant_id", "report_type"),
        Index("ix_scheduled_reports_is_active", "is_active"),
    )
