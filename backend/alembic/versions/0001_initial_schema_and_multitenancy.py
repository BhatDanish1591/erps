"""initial_schema_and_multitenancy

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-11-18 22:30:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create Extensions ──────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ── 2. Create Enums ───────────────────────────────────────────────────────
    institution_type_enum = postgresql.ENUM(
        'SCHOOL', 'COLLEGE', name='institution_type_enum', create_type=False
    )
    institution_type_enum.create(op.get_bind(), checkfirst=True)

    tenant_status_enum = postgresql.ENUM(
        'TRIAL', 'ACTIVE', 'SUSPENDED', 'INACTIVE', name='tenant_status_enum', create_type=False
    )
    tenant_status_enum.create(op.get_bind(), checkfirst=True)

    role_scope_enum = postgresql.ENUM(
        'PLATFORM', 'TENANT', name='role_scope_enum', create_type=False
    )
    role_scope_enum.create(op.get_bind(), checkfirst=True)

    membership_status_enum = postgresql.ENUM(
        'ACTIVE', 'INVITED', 'SUSPENDED', name='membership_status_enum', create_type=False
    )
    membership_status_enum.create(op.get_bind(), checkfirst=True)

    session_status_enum = postgresql.ENUM(
        'UPCOMING', 'ACTIVE', 'COMPLETED', 'ARCHIVED', name='session_status_enum', create_type=False
    )
    session_status_enum.create(op.get_bind(), checkfirst=True)

    billing_cycle_enum = postgresql.ENUM(
        'MONTHLY', 'QUARTERLY', 'YEARLY', name='billing_cycle_enum', create_type=False
    )
    billing_cycle_enum.create(op.get_bind(), checkfirst=True)

    subscription_status_enum = postgresql.ENUM(
        'TRIAL', 'ACTIVE', 'PAST_DUE', 'CANCELED', 'EXPIRED', 'SUSPENDED',
        name='subscription_status_enum', create_type=False
    )
    subscription_status_enum.create(op.get_bind(), checkfirst=True)

    invoice_status_enum = postgresql.ENUM(
        'DRAFT', 'ISSUED', 'PAID', 'VOID', 'UNCOLLECTIBLE',
        name='invoice_status_enum', create_type=False
    )
    invoice_status_enum.create(op.get_bind(), checkfirst=True)

    payment_status_enum = postgresql.ENUM(
        'PENDING', 'SUCCESS', 'FAILED', 'REFUNDED',
        name='payment_status_enum', create_type=False
    )
    payment_status_enum.create(op.get_bind(), checkfirst=True)

    login_status_enum = postgresql.ENUM(
        'SUCCESS', 'FAILED', name='login_status_enum', create_type=False
    )
    login_status_enum.create(op.get_bind(), checkfirst=True)

    # ── 3. Table: tenants ─────────────────────────────────────────────────────
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('institution_type', institution_type_enum, nullable=False, server_default='SCHOOL'),
        sa.Column('status', tenant_status_enum, nullable=False, server_default='TRIAL'),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('country', sa.String(100), nullable=False, server_default='India'),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('logo_url', sa.String(1024), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='Asia/Kolkata'),
        sa.Column('currency', sa.String(10), nullable=False, server_default='INR'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_tenants_slug', 'tenants', ['slug'])
    op.create_index('ix_tenants_status', 'tenants', ['status'])
    op.create_index('ix_tenants_is_deleted', 'tenants', ['is_deleted'])
    op.create_index('ix_tenants_type_status', 'tenants', ['institution_type', 'status'])

    # ── 4. Table: tenant_domains ──────────────────────────────────────────────
    op.create_table(
        'tenant_domains',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('domain', sa.String(255), nullable=False, unique=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_tenant_domains_tenant_id', 'tenant_domains', ['tenant_id'])
    op.create_index('ix_tenant_domains_domain', 'tenant_domains', ['domain'])
    op.create_index('ix_tenant_domains_tenant_primary', 'tenant_domains', ['tenant_id', 'is_primary'])

    # ── 5. Table: tenant_settings ─────────────────────────────────────────────
    op.create_table(
        'tenant_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('tenant_id', 'key', name='uq_tenant_settings_tenant_key'),
    )
    op.create_index('ix_tenant_settings_tenant_id', 'tenant_settings', ['tenant_id'])
    op.create_index('ix_tenant_settings_key', 'tenant_settings', ['key'])
    op.create_index('ix_tenant_settings_is_deleted', 'tenant_settings', ['is_deleted'])
    op.create_index('ix_tenant_settings_tenant_public', 'tenant_settings', ['tenant_id', 'is_public'])

    # ── 6. Table: users ───────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('avatar_url', sa.String(1024), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superadmin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('phone_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('mfa_secret', sa.String(255), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_phone', 'users', ['phone'])
    op.create_index('ix_users_is_superadmin', 'users', ['is_superadmin'])
    op.create_index('ix_users_is_deleted', 'users', ['is_deleted'])
    op.create_index('ix_users_email_active', 'users', ['email', 'is_active'])

    # ── 7. Table: refresh_tokens ──────────────────────────────────────────────
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('replaced_by_token_hash', sa.String(255), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'])
    op.create_index('ix_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'])
    op.create_index('ix_refresh_tokens_is_revoked', 'refresh_tokens', ['is_revoked'])
    op.create_index('ix_refresh_tokens_user_valid', 'refresh_tokens', ['user_id', 'is_revoked', 'expires_at'])

    # ── 8. Table: login_history ───────────────────────────────────────────────
    op.create_table(
        'login_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='SET NULL'), nullable=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('status', login_status_enum, nullable=False, server_default='SUCCESS'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('failure_reason', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_login_history_user_id', 'login_history', ['user_id'])
    op.create_index('ix_login_history_tenant_id', 'login_history', ['tenant_id'])
    op.create_index('ix_login_history_status', 'login_history', ['status'])
    op.create_index('ix_login_history_user_created', 'login_history', ['user_id', 'created_at'])
    op.create_index('ix_login_history_tenant_created', 'login_history', ['tenant_id', 'created_at'])

    # ── 9. Table: roles ───────────────────────────────────────────────────────
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(100), nullable=False),
        sa.Column('scope', role_scope_enum, nullable=False, server_default='TENANT'),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('is_system_role', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_roles_tenant_code'),
    )
    op.create_index('ix_roles_tenant_id', 'roles', ['tenant_id'])
    op.create_index('ix_roles_code', 'roles', ['code'])
    op.create_index('ix_roles_scope', 'roles', ['scope'])
    op.create_index('ix_roles_scope_tenant', 'roles', ['scope', 'tenant_id'])

    # ── 10. Table: permissions ────────────────────────────────────────────────
    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(100), nullable=False, unique=True),
        sa.Column('module', sa.String(50), nullable=False),
        sa.Column('description', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_permissions_code', 'permissions', ['code'])
    op.create_index('ix_permissions_module', 'permissions', ['module'])

    # ── 11. Table: role_permissions ───────────────────────────────────────────
    op.create_table(
        'role_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permissions_role_perm'),
    )
    op.create_index('ix_role_permissions_role_id', 'role_permissions', ['role_id'])
    op.create_index('ix_role_permissions_permission_id', 'role_permissions', ['permission_id'])

    # ── 12. Table: memberships ────────────────────────────────────────────────
    op.create_table(
        'memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('status', membership_status_enum, nullable=False, server_default='ACTIVE'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('tenant_id', 'user_id', name='uq_memberships_tenant_user'),
    )
    op.create_index('ix_memberships_tenant_id', 'memberships', ['tenant_id'])
    op.create_index('ix_memberships_user_id', 'memberships', ['user_id'])
    op.create_index('ix_memberships_role_id', 'memberships', ['role_id'])
    op.create_index('ix_memberships_status', 'memberships', ['status'])
    op.create_index('ix_memberships_is_deleted', 'memberships', ['is_deleted'])
    op.create_index('ix_memberships_tenant_status', 'memberships', ['tenant_id', 'status'])
    op.create_index('ix_memberships_user_tenant', 'memberships', ['user_id', 'tenant_id'])

    # ── 13. Table: academic_sessions ──────────────────────────────────────────
    op.create_table(
        'academic_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('status', session_status_enum, nullable=False, server_default='ACTIVE'),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_academic_sessions_tenant_code'),
    )
    op.create_index('ix_academic_sessions_tenant_id', 'academic_sessions', ['tenant_id'])
    op.create_index('ix_academic_sessions_code', 'academic_sessions', ['code'])
    op.create_index('ix_academic_sessions_status', 'academic_sessions', ['status'])
    op.create_index('ix_academic_sessions_is_deleted', 'academic_sessions', ['is_deleted'])
    op.create_index('ix_academic_sessions_tenant_current', 'academic_sessions', ['tenant_id', 'is_current'])
    op.create_index('ix_academic_sessions_tenant_dates', 'academic_sessions', ['tenant_id', 'start_date', 'end_date'])

    # ── 14. Table: subscription_plans ─────────────────────────────────────────
    op.create_table(
        'subscription_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('institution_type', institution_type_enum, nullable=True),
        sa.Column('billing_cycle', billing_cycle_enum, nullable=False, server_default='YEARLY'),
        sa.Column('price', sa.Numeric(12, 2), nullable=False, server_default='0.0'),
        sa.Column('currency', sa.String(10), nullable=False, server_default='INR'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_subscription_plans_code', 'subscription_plans', ['code'])
    op.create_index('ix_subscription_plans_is_active', 'subscription_plans', ['is_active'])

    # ── 15. Table: plan_features ──────────────────────────────────────────────
    op.create_table(
        'plan_features',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subscription_plans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('feature_key', sa.String(100), nullable=False),
        sa.Column('feature_value', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('plan_id', 'feature_key', name='uq_plan_features_plan_key'),
    )
    op.create_index('ix_plan_features_plan_id', 'plan_features', ['plan_id'])
    op.create_index('ix_plan_features_feature_key', 'plan_features', ['feature_key'])

    # ── 16. Table: subscriptions ──────────────────────────────────────────────
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subscription_plans.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('status', subscription_status_enum, nullable=False, server_default='TRIAL'),
        sa.Column('billing_cycle', billing_cycle_enum, nullable=False, server_default='YEARLY'),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_auto_renew', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_subscriptions_tenant_id', 'subscriptions', ['tenant_id'])
    op.create_index('ix_subscriptions_plan_id', 'subscriptions', ['plan_id'])
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'])
    op.create_index('ix_subscriptions_current_period_end', 'subscriptions', ['current_period_end'])
    op.create_index('ix_subscriptions_tenant_status', 'subscriptions', ['tenant_id', 'status'])

    # ── 17. Table: subscription_invoices ──────────────────────────────────────
    op.create_table(
        'subscription_invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('invoice_number', sa.String(50), nullable=False, unique=True),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(12, 2), nullable=False, server_default='0.0'),
        sa.Column('total_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='INR'),
        sa.Column('status', invoice_status_enum, nullable=False, server_default='ISSUED'),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('invoice_url', sa.String(1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_subscription_invoices_tenant_id', 'subscription_invoices', ['tenant_id'])
    op.create_index('ix_subscription_invoices_subscription_id', 'subscription_invoices', ['subscription_id'])
    op.create_index('ix_subscription_invoices_invoice_number', 'subscription_invoices', ['invoice_number'])
    op.create_index('ix_subscription_invoices_status', 'subscription_invoices', ['status'])
    op.create_index('ix_subscription_invoices_tenant_status', 'subscription_invoices', ['tenant_id', 'status'])

    # ── 18. Table: subscription_payments ──────────────────────────────────────
    op.create_table(
        'subscription_payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subscription_invoices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='INR'),
        sa.Column('payment_method', sa.String(50), nullable=False, server_default='RAZORPAY'),
        sa.Column('gateway', sa.String(50), nullable=False, server_default='razorpay'),
        sa.Column('transaction_reference', sa.String(255), nullable=True, unique=True),
        sa.Column('status', payment_status_enum, nullable=False, server_default='PENDING'),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.String(500), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_subscription_payments_tenant_id', 'subscription_payments', ['tenant_id'])
    op.create_index('ix_subscription_payments_invoice_id', 'subscription_payments', ['invoice_id'])
    op.create_index('ix_subscription_payments_transaction_ref', 'subscription_payments', ['transaction_reference'])
    op.create_index('ix_subscription_payments_status', 'subscription_payments', ['status'])
    op.create_index('ix_subscription_payments_tenant_status', 'subscription_payments', ['tenant_id', 'status'])

    # ── 19. Table: audit_logs ─────────────────────────────────────────────────
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', sa.String(100), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('changes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_audit_logs_tenant_id', 'audit_logs', ['tenant_id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_entity_type', 'audit_logs', ['entity_type'])
    op.create_index('ix_audit_logs_entity_id', 'audit_logs', ['entity_id'])
    op.create_index('ix_audit_logs_tenant_created', 'audit_logs', ['tenant_id', 'created_at'])
    op.create_index('ix_audit_logs_entity_lookup', 'audit_logs', ['entity_type', 'entity_id'])

    # ── 20. PostgreSQL Row-Level Security (RLS) ──────────────────────────────
    # Enable RLS on all tenant-isolated tables
    rls_tables = [
        'tenant_settings',
        'memberships',
        'academic_sessions',
        'subscription_invoices',
        'subscription_payments',
    ]
    for tbl in rls_tables:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        # Read & update policy: current_tenant must match or tenant_id is explicitly set
        op.execute(f"""
            CREATE POLICY tenant_isolation_policy ON {tbl}
            USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
        """)
        # Insert policy: tenant_id must match session context
        op.execute(f"""
            CREATE POLICY tenant_isolation_insert_policy ON {tbl}
            WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
        """)

    # ── 21. Seed Initial Permissions & Roles ──────────────────────────────────
    # Default Permissions
    permissions_data = [
        # Academic sessions
        ("academic:session:read", "academic", "View academic sessions and semesters"),
        ("academic:session:create", "academic", "Create new academic sessions"),
        ("academic:session:update", "academic", "Edit academic sessions"),
        ("academic:session:delete", "academic", "Delete academic sessions"),
        # User & Membership management
        ("users:read", "users", "View institutional users and staff"),
        ("users:invite", "users", "Invite new users to the institution"),
        ("users:manage_roles", "users", "Assign and modify user roles"),
        # Attendance
        ("attendance:read", "attendance", "View attendance records"),
        ("attendance:mark", "attendance", "Mark and update attendance"),
        # Fees & Finance
        ("fees:read", "finance", "View fee schedules and dues"),
        ("fees:collect", "finance", "Collect fees and issue receipts"),
        ("fees:manage", "finance", "Configure fee structures and discounts"),
        # Examinations
        ("exams:read", "examinations", "View examinations and schedules"),
        ("exams:manage", "examinations", "Create and manage examinations"),
        ("exams:grades:enter", "examinations", "Enter and submit student grades"),
        # Settings & Reports
        ("settings:read", "settings", "View institutional settings"),
        ("settings:update", "settings", "Update institutional configuration"),
        ("reports:view", "reports", "View institutional analytics and reports"),
        ("audit:read", "audit", "View institutional audit logs"),
    ]

    permission_table = sa.table(
        'permissions',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('code', sa.String),
        sa.column('module', sa.String),
        sa.column('description', sa.String),
    )
    perm_records = []
    for code, mod, desc in permissions_data:
        perm_records.append({
            'id': uuid.uuid4(),
            'code': code,
            'module': mod,
            'description': desc,
        })
    op.bulk_insert(permission_table, perm_records)

    # System Template Roles
    role_table = sa.table(
        'roles',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('name', sa.String),
        sa.column('code', sa.String),
        sa.column('scope', role_scope_enum),
        sa.column('description', sa.String),
        sa.column('is_system_role', sa.Boolean),
    )
    role_admin_id = uuid.uuid4()
    role_teacher_id = uuid.uuid4()
    role_student_id = uuid.uuid4()
    role_parent_id = uuid.uuid4()
    role_superadmin_id = uuid.uuid4()

    roles_data = [
        {
            'id': role_superadmin_id,
            'name': 'Super Admin',
            'code': 'SUPER_ADMIN',
            'scope': 'PLATFORM',
            'description': 'Platform-wide administrator with full system access',
            'is_system_role': True,
        },
        {
            'id': role_admin_id,
            'name': 'Institution Admin',
            'code': 'INSTITUTION_ADMIN',
            'scope': 'TENANT',
            'description': 'Head of institution / Principal with complete tenant administrative control',
            'is_system_role': True,
        },
        {
            'id': role_teacher_id,
            'name': 'Teacher',
            'code': 'TEACHER',
            'scope': 'TENANT',
            'description': 'Academic teacher or college professor',
            'is_system_role': True,
        },
        {
            'id': role_student_id,
            'name': 'Student',
            'code': 'STUDENT',
            'scope': 'TENANT',
            'description': 'Enrolled school student or college undergraduate',
            'is_system_role': True,
        },
        {
            'id': role_parent_id,
            'name': 'Parent / Guardian',
            'code': 'PARENT',
            'scope': 'TENANT',
            'description': 'Parent or legal guardian of an enrolled student',
            'is_system_role': True,
        },
    ]
    op.bulk_insert(role_table, roles_data)

    # Map all permissions to INSTITUTION_ADMIN
    role_perm_table = sa.table(
        'role_permissions',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('role_id', postgresql.UUID(as_uuid=True)),
        sa.column('permission_id', postgresql.UUID(as_uuid=True)),
    )
    admin_perms = [
        {'id': uuid.uuid4(), 'role_id': role_admin_id, 'permission_id': p['id']}
        for p in perm_records
    ]
    op.bulk_insert(role_perm_table, admin_perms)

    # Map Teacher permissions
    teacher_codes = {"academic:session:read", "attendance:read", "attendance:mark", "exams:read", "exams:grades:enter", "reports:view"}
    teacher_perms = [
        {'id': uuid.uuid4(), 'role_id': role_teacher_id, 'permission_id': p['id']}
        for p in perm_records if p['code'] in teacher_codes
    ]
    op.bulk_insert(role_perm_table, teacher_perms)

    # Map Student permissions
    student_codes = {"academic:session:read", "attendance:read", "fees:read", "exams:read", "reports:view"}
    student_perms = [
        {'id': uuid.uuid4(), 'role_id': role_student_id, 'permission_id': p['id']}
        for p in perm_records if p['code'] in student_codes
    ]
    op.bulk_insert(role_perm_table, student_perms)

    # Map Parent permissions
    parent_codes = {"academic:session:read", "attendance:read", "fees:read", "reports:view"}
    parent_perms = [
        {'id': uuid.uuid4(), 'role_id': role_parent_id, 'permission_id': p['id']}
        for p in perm_records if p['code'] in parent_codes
    ]
    op.bulk_insert(role_perm_table, parent_perms)


def downgrade() -> None:
    # Disable RLS and drop policies
    rls_tables = [
        'tenant_settings',
        'memberships',
        'academic_sessions',
        'subscription_invoices',
        'subscription_payments',
    ]
    for tbl in rls_tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_insert_policy ON {tbl}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")

    # Drop tables in reverse dependency order
    op.drop_table('audit_logs')
    op.drop_table('subscription_payments')
    op.drop_table('subscription_invoices')
    op.drop_table('subscriptions')
    op.drop_table('plan_features')
    op.drop_table('subscription_plans')
    op.drop_table('academic_sessions')
    op.drop_table('memberships')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('login_history')
    op.drop_table('refresh_tokens')
    op.drop_table('users')
    op.drop_table('tenant_settings')
    op.drop_table('tenant_domains')
    op.drop_table('tenants')

    # Drop enums
    enums = [
        'login_status_enum',
        'payment_status_enum',
        'invoice_status_enum',
        'subscription_status_enum',
        'billing_cycle_enum',
        'session_status_enum',
        'membership_status_enum',
        'role_scope_enum',
        'tenant_status_enum',
        'institution_type_enum',
    ]
    for e in enums:
        op.execute(f"DROP TYPE IF EXISTS {e} CASCADE")
