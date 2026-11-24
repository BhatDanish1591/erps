"""super_admin_entities

Revision ID: 0002_super_admin_entities
Revises: 0001_initial_schema
Create Date: 2026-11-19 12:20:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_super_admin_entities"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Update TenantStatus Enum with PENDING and REJECTED ────────────────
    # In PostgreSQL, we can use ALTER TYPE ... ADD VALUE IF NOT EXISTS
    op.execute("ALTER TYPE tenant_status_enum ADD VALUE IF NOT EXISTS 'PENDING'")
    op.execute("ALTER TYPE tenant_status_enum ADD VALUE IF NOT EXISTS 'REJECTED'")

    # ── 2. Create Global Announcements ───────────────────────────────────────
    op.create_table(
        "global_announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("target_role", sa.String(50), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False, server_default="NORMAL"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_global_announcements_is_active", "global_announcements", ["is_active"])

    # ── 3. Create Support Tickets ─────────────────────────────────────────────
    op.create_table(
        "support_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_number", sa.String(32), unique=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="GENERAL"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])
    op.create_index("ix_support_tickets_tenant_id", "support_tickets", ["tenant_id"])
    op.create_index("ix_support_tickets_user_id", "support_tickets", ["user_id"])
    op.create_index("ix_support_tickets_ticket_number", "support_tickets", ["ticket_number"])

    # ── 4. Create Support Ticket Replies ──────────────────────────────────────
    op.create_table(
        "support_ticket_replies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_support_ticket_replies_ticket_id", "support_ticket_replies", ["ticket_id"])

    # ── 5. Create Platform Settings ───────────────────────────────────────────
    op.create_table(
        "platform_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("category", sa.String(50), nullable=False, server_default="GENERAL"),
        sa.Column("key", sa.String(100), unique=True, nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_platform_settings_key", "platform_settings", ["key"])
    op.create_index("ix_platform_settings_category", "platform_settings", ["category"])

    # ── 6. Create Platform Integrations ───────────────────────────────────────
    op.create_table(
        "platform_integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(30), nullable=False, server_default="NOT_CONFIGURED"),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_platform_integrations_provider", "platform_integrations", ["provider"])

    # ── 7. Seed Initial Integrations ──────────────────────────────────────────
    integrations_table = sa.table(
        "platform_integrations",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("provider", sa.String),
        sa.column("name", sa.String),
        sa.column("is_enabled", sa.Boolean),
        sa.column("config", postgresql.JSONB),
        sa.column("status", sa.String),
    )
    op.bulk_insert(
        integrations_table,
        [
            {
                "id": uuid.uuid4(),
                "provider": "RAZORPAY",
                "name": "Razorpay Payment Gateway",
                "is_enabled": True,
                "config": {"key_id": "rzp_test_placeholder", "currency": "INR", "webhook_enabled": True},
                "status": "CONFIGURED",
            },
            {
                "id": uuid.uuid4(),
                "provider": "AWS_S3",
                "name": "Amazon S3 / Cloudflare R2 Storage",
                "is_enabled": True,
                "config": {"bucket": "edusaas-documents", "region": "ap-south-1"},
                "status": "CONFIGURED",
            },
            {
                "id": uuid.uuid4(),
                "provider": "RESEND",
                "name": "Resend / Amazon SES Email",
                "is_enabled": True,
                "config": {"from_email": "notifications@edusaas.com"},
                "status": "CONFIGURED",
            },
            {
                "id": uuid.uuid4(),
                "provider": "META_WHATSAPP",
                "name": "Meta WhatsApp Cloud API",
                "is_enabled": False,
                "config": {"phone_number_id": "", "business_account_id": ""},
                "status": "NOT_CONFIGURED",
            },
            {
                "id": uuid.uuid4(),
                "provider": "MSG91",
                "name": "MSG91 SMS Gateway",
                "is_enabled": False,
                "config": {"sender_id": "EDUSAS"},
                "status": "NOT_CONFIGURED",
            },
            {
                "id": uuid.uuid4(),
                "provider": "FIREBASE_FCM",
                "name": "Firebase Cloud Messaging",
                "is_enabled": False,
                "config": {"project_id": "edusaas-mobile"},
                "status": "NOT_CONFIGURED",
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("platform_integrations")
    op.drop_table("platform_settings")
    op.drop_table("support_ticket_replies")
    op.drop_table("support_tickets")
    op.drop_table("global_announcements")
