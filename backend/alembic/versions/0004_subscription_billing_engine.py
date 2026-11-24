"""subscription_billing_engine

Revision ID: 0004_subscription_billing
Revises: 0003_onboarding_and_academic
Create Date: 2026-11-19 13:05:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_subscription_billing"
down_revision: Union[str, None] = "0003_onboarding_and_academic"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create discount_type_enum ─────────────────────────────────────────
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE discount_type_enum AS ENUM ('PERCENTAGE', 'FIXED_AMOUNT'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    # ── 2. Add columns to subscription_plans ──────────────────────────────────
    op.add_column("subscription_plans", sa.Column("monthly_price", sa.Numeric(12, 2), nullable=False, server_default="0.0"))
    op.add_column("subscription_plans", sa.Column("annual_price", sa.Numeric(12, 2), nullable=False, server_default="0.0"))
    op.add_column("subscription_plans", sa.Column("max_students", sa.Integer(), nullable=False, server_default="300"))
    op.add_column("subscription_plans", sa.Column("max_teachers", sa.Integer(), nullable=False, server_default="20"))
    op.add_column("subscription_plans", sa.Column("storage_limit_gb", sa.Integer(), nullable=False, server_default="10"))
    op.add_column("subscription_plans", sa.Column("notification_quota", sa.Integer(), nullable=False, server_default="1000"))
    op.add_column("subscription_plans", sa.Column("trial_days", sa.Integer(), nullable=False, server_default="30"))

    # ── 3. Add columns to subscriptions ───────────────────────────────────────
    op.add_column("subscriptions", sa.Column("grace_period_ends_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("subscriptions", sa.Column("payment_method", sa.String(50), nullable=True))

    # ── 4. Add columns to subscription_invoices ───────────────────────────────
    op.add_column("subscription_invoices", sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0.0"))
    op.add_column("subscription_invoices", sa.Column("coupon_code", sa.String(50), nullable=True))
    op.add_column("subscription_invoices", sa.Column("billing_name", sa.String(255), nullable=True))
    op.add_column("subscription_invoices", sa.Column("billing_address", sa.String(500), nullable=True))
    op.add_column("subscription_invoices", sa.Column("line_items", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column(
        "subscription_invoices",
        sa.Column(
            "billing_cycle",
            postgresql.ENUM("MONTHLY", "QUARTERLY", "YEARLY", name="billing_cycle_enum", create_type=False),
            nullable=False,
            server_default="YEARLY",
        ),
    )

    # ── 5. Add columns to subscription_payments ───────────────────────────────
    op.add_column("subscription_payments", sa.Column("gateway_order_id", sa.String(100), nullable=True))
    op.add_column("subscription_payments", sa.Column("gateway_payment_id", sa.String(100), nullable=True))
    op.add_column("subscription_payments", sa.Column("gateway_signature", sa.String(255), nullable=True))
    op.add_column("subscription_payments", sa.Column("idempotency_key", sa.String(100), nullable=True))

    op.create_index("ix_subscription_payments_gateway_order_id", "subscription_payments", ["gateway_order_id"])
    op.create_index("ix_subscription_payments_gateway_payment_id", "subscription_payments", ["gateway_payment_id"])
    op.create_index("ix_subscription_payments_idempotency_key", "subscription_payments", ["idempotency_key"], unique=True)

    # ── 6. Create coupons table ───────────────────────────────────────────────
    op.create_table(
        "coupons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column(
            "discount_type",
            postgresql.ENUM("PERCENTAGE", "FIXED_AMOUNT", name="discount_type_enum", create_type=False),
            nullable=False,
            server_default="PERCENTAGE",
        ),
        sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("max_redemptions", sa.Integer(), nullable=True),
        sa.Column("times_redeemed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "applicable_institution_type",
            postgresql.ENUM("SCHOOL", "COLLEGE", name="institution_type_enum", create_type=False),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_coupons_code", "coupons", ["code"])
    op.create_index("ix_coupons_is_active", "coupons", ["is_active"])

    # ── 7. Create webhook_events table ────────────────────────────────────────
    op.create_table(
        "webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", sa.String(100), unique=True, nullable=False),
        sa.Column("gateway", sa.String(50), nullable=False, server_default="razorpay"),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_processed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_webhook_events_event_id", "webhook_events", ["event_id"])
    op.create_index("ix_webhook_events_event_type", "webhook_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.drop_table("coupons")
    op.drop_index("ix_subscription_payments_idempotency_key", table_name="subscription_payments")
    op.drop_index("ix_subscription_payments_gateway_payment_id", table_name="subscription_payments")
    op.drop_index("ix_subscription_payments_gateway_order_id", table_name="subscription_payments")
    op.drop_column("subscription_payments", "idempotency_key")
    op.drop_column("subscription_payments", "gateway_signature")
    op.drop_column("subscription_payments", "gateway_payment_id")
    op.drop_column("subscription_payments", "gateway_order_id")
    op.drop_column("subscription_invoices", "billing_cycle")
    op.drop_column("subscription_invoices", "line_items")
    op.drop_column("subscription_invoices", "billing_address")
    op.drop_column("subscription_invoices", "billing_name")
    op.drop_column("subscription_invoices", "coupon_code")
    op.drop_column("subscription_invoices", "discount_amount")
    op.drop_column("subscriptions", "payment_method")
    op.drop_column("subscriptions", "grace_period_ends_at")
    op.drop_column("subscription_plans", "trial_days")
    op.drop_column("subscription_plans", "notification_quota")
    op.drop_column("subscription_plans", "storage_limit_gb")
    op.drop_column("subscription_plans", "max_teachers")
    op.drop_column("subscription_plans", "max_students")
    op.drop_column("subscription_plans", "annual_price")
    op.drop_column("subscription_plans", "monthly_price")
    op.execute("DROP TYPE IF EXISTS discount_type_enum;")
