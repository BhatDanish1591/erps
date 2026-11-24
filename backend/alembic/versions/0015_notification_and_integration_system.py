"""Create Notification and Integration System tables

Revision ID: 0015_notification_and_integration
Revises: 0014_parent_guardian_portal
Create Date: 2026-11-19 20:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0015_notification_system"
down_revision: Union[str, None] = "0014_parent_guardian_portal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create tenant_integrations ──────────────────────────────────────────
    op.create_table(
        "tenant_integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_type", sa.String(50), nullable=False),  # EMAIL_SES, EMAIL_RESEND, WHATSAPP_META, SMS_MSG91, PUSH_FIREBASE, PUSH_APNS, PAYMENT_RAZORPAY, STORAGE_S3, STORAGE_R2
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("credentials_encrypted", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("webhook_secret", sa.String(255), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="UNTESTED"),  # ACTIVE, INACTIVE, ERROR, UNTESTED
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.UniqueConstraint("tenant_id", "provider_type", name="uq_tenant_integrations_provider"),
    )
    op.create_index("ix_tenant_integrations_tenant_provider", "tenant_integrations", ["tenant_id", "provider_type"])
    op.create_index("ix_tenant_integrations_status", "tenant_integrations", ["tenant_id", "status"])

    op.execute("ALTER TABLE tenant_integrations ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY tenant_integrations_isolation ON tenant_integrations "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # ── 2. Create notification_templates ──────────────────────────────────────
    op.create_table(
        "notification_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),  # EMAIL, WHATSAPP, SMS, PUSH, IN_APP
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("subject_template", sa.String(255), nullable=True),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("whatsapp_template_name", sa.String(100), nullable=True),
        sa.Column("whatsapp_template_namespace", sa.String(100), nullable=True),
        sa.Column("whatsapp_language", sa.String(20), nullable=False, server_default="en_US"),
        sa.Column("msg91_template_id", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_notif_templates_event_channel", "notification_templates", ["event_type", "channel"])
    op.create_index("ix_notif_templates_tenant_event", "notification_templates", ["tenant_id", "event_type"])

    op.execute("ALTER TABLE notification_templates ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY notif_templates_isolation ON notification_templates "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id IS NULL OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # ── 3. Create user_notification_preferences ───────────────────────────────
    op.create_table(
        "user_notification_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_email", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("channel_whatsapp", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("channel_sms", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("channel_push", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("channel_in_app", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("category_attendance", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("category_academic", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("category_examinations", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("category_finance", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("category_announcements", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("quiet_hours_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("quiet_hours_start", sa.String(10), nullable=True),
        sa.Column("quiet_hours_end", sa.String(10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_user_notif_prefs_tenant_user"),
    )
    op.create_index("ix_user_notif_prefs_tenant_user", "user_notification_preferences", ["tenant_id", "user_id"])

    op.execute("ALTER TABLE user_notification_preferences ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY user_notif_prefs_isolation ON user_notification_preferences "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # ── 4. Create notification_outbox ─────────────────────────────────────────
    op.create_table(
        "notification_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("event_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),  # PENDING, PROCESSING, PROCESSED, FAILED, CANCELLED
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_notif_outbox_tenant_idempotency"),
    )
    op.create_index("ix_notif_outbox_tenant_status", "notification_outbox", ["tenant_id", "status"])
    op.create_index("ix_notif_outbox_status_sched", "notification_outbox", ["status", "scheduled_for"])

    op.execute("ALTER TABLE notification_outbox ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY notif_outbox_isolation ON notification_outbox "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # ── 5. Create notification_logs ───────────────────────────────────────────
    op.create_table(
        "notification_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("outbox_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notification_outbox.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),  # EMAIL, WHATSAPP, SMS, PUSH, IN_APP
        sa.Column("provider", sa.String(50), nullable=False),  # SES, RESEND, META_WHATSAPP, MSG91, FIREBASE, APNS, IN_APP
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="QUEUED"),  # QUEUED, DISPATCHED, DELIVERED, FAILED, BOUNCED, READ
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_notif_logs_tenant_channel_status", "notification_logs", ["tenant_id", "channel", "status"])
    op.create_index("ix_notif_logs_tenant_event", "notification_logs", ["tenant_id", "event_type"])
    op.create_index("ix_notif_logs_provider_msg_id", "notification_logs", ["provider_message_id"])

    op.execute("ALTER TABLE notification_logs ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY notif_logs_isolation ON notification_logs "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # ── 6. Create user_notifications ──────────────────────────────────────────
    op.create_table(
        "user_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("action_url", sa.String(500), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_user_notifs_tenant_user_read", "user_notifications", ["tenant_id", "user_id", "is_read"])
    op.create_index("ix_user_notifs_user_created", "user_notifications", ["user_id", "created_at"])

    op.execute("ALTER TABLE user_notifications ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY user_notifs_isolation ON user_notifications "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )


def downgrade() -> None:
    op.drop_table("user_notifications")
    op.drop_table("notification_logs")
    op.drop_table("notification_outbox")
    op.drop_table("user_notification_preferences")
    op.drop_table("notification_templates")
    op.drop_table("tenant_integrations")
