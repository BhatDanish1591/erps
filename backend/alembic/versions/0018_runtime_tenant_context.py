"""Support authorized operations with a row-level-security runtime role."""

from alembic import op

revision = "0018_runtime_tenant_context"
down_revision = "0017_analytics_reporting"

CORE_TENANT_TABLES = (
    "tenant_settings",
    "memberships",
    "academic_sessions",
    "subscription_invoices",
    "subscription_payments",
)


def upgrade() -> None:
    for table in CORE_TENANT_TABLES:
        op.execute(
            f"CREATE POLICY platform_operations ON {table} "
            "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true')"
        )
    op.execute(
        "CREATE POLICY own_memberships ON memberships FOR SELECT "
        "USING (user_id::text = current_setting('app.membership_user_id', true))"
    )
    op.execute(
        "CREATE POLICY invitation_by_token ON invitations FOR SELECT "
        "USING (token_hash = current_setting('app.invitation_token_hash', true) "
        "AND status = 'PENDING' AND expires_at > now())"
    )


def downgrade() -> None:
    op.execute("DROP POLICY invitation_by_token ON invitations")
    op.execute("DROP POLICY own_memberships ON memberships")
    for table in CORE_TENANT_TABLES:
        op.execute(f"DROP POLICY platform_operations ON {table}")
