"""Create Student Fees and Finance Management tables

Revision ID: 0013_student_fees_and_finance
Revises: 0012_timetable_management
Create Date: 2026-11-19 17:15:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0013_student_fees_and_finance"
down_revision: Union[str, None] = "0012_timetable_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create fee_categories ─────────────────────────────────────────────
    op.create_table(
        "fee_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("fee_type", sa.String(30), nullable=False, server_default="ACADEMIC"),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_refundable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "code", name="uq_fee_categories_tenant_code"),
    )
    op.create_index("ix_fee_categories_tenant_id", "fee_categories", ["tenant_id"])
    op.execute("ALTER TABLE fee_categories ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY fee_categories_tenant_isolation ON fee_categories
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 2. Create fee_structures ─────────────────────────────────────────────
    op.create_table(
        "fee_structures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("institution_type", sa.String(20), nullable=False, server_default="SCHOOL"),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("semester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_semesters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("college_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("frequency", sa.String(30), nullable=False, server_default="ANNUAL"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_fee_structures_tenant_session", "fee_structures", ["tenant_id", "academic_session_id"])
    op.execute("ALTER TABLE fee_structures ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY fee_structures_tenant_isolation ON fee_structures
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 3. Create fee_structure_components ───────────────────────────────────
    op.create_table(
        "fee_structure_components",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("fee_structure_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fee_structures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fee_category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fee_categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("is_optional", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_fee_structure_components_structure", "fee_structure_components", ["fee_structure_id"])

    # ── 4. Create fee_structure_installments ─────────────────────────────────
    op.create_table(
        "fee_structure_installments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("fee_structure_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fee_structures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("installment_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("late_fine_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("late_fine_type", sa.String(30), nullable=False, server_default="NONE"),
        sa.Column("grace_period_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_fee_structure_installments_structure", "fee_structure_installments", ["fee_structure_id", "installment_number"])

    # ── 5. Create fee_discounts_scholarships ─────────────────────────────────
    op.create_table(
        "fee_discounts_scholarships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("discount_type", sa.String(30), nullable=False, server_default="DISCOUNT"),
        sa.Column("calculation_type", sa.String(30), nullable=False, server_default="PERCENTAGE"),
        sa.Column("value", sa.Numeric(12, 2), nullable=False),
        sa.Column("applicable_categories", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='["ALL"]'),
        sa.Column("criteria", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_fee_discounts_tenant_session", "fee_discounts_scholarships", ["tenant_id", "academic_session_id"])
    op.execute("ALTER TABLE fee_discounts_scholarships ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY fee_discounts_scholarships_tenant_isolation ON fee_discounts_scholarships
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 6. Create student_fee_allocations ────────────────────────────────────
    op.create_table(
        "student_fee_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fee_structure_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fee_structures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("discount_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fee_discounts_scholarships.id", ondelete="SET NULL"), nullable=True),
        sa.Column("custom_discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("discount_reason", sa.String(255), nullable=True),
        sa.Column("net_fee_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_student_fee_allocations_tenant_student", "student_fee_allocations", ["tenant_id", "student_id", "academic_session_id"])
    op.execute("ALTER TABLE student_fee_allocations ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY student_fee_allocations_tenant_isolation ON student_fee_allocations
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 7. Create fee_invoices ───────────────────────────────────────────────
    op.create_table(
        "fee_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fee_structure_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fee_structures.id", ondelete="SET NULL"), nullable=True),
        sa.Column("allocation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_fee_allocations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_number", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("scholarship_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("late_fine_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("balance_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="ISSUED"),
        sa.Column("line_items", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "invoice_number", name="uq_fee_invoices_tenant_number"),
    )
    op.create_index("ix_fee_invoices_tenant_student", "fee_invoices", ["tenant_id", "student_id"])
    op.create_index("ix_fee_invoices_tenant_status", "fee_invoices", ["tenant_id", "status"])
    op.create_index("ix_fee_invoices_due_date", "fee_invoices", ["tenant_id", "due_date"])
    op.execute("ALTER TABLE fee_invoices ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY fee_invoices_tenant_isolation ON fee_invoices
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 8. Create fee_payments ───────────────────────────────────────────────
    op.create_table(
        "fee_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fee_invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("receipt_number", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("payment_mode", sa.String(30), nullable=False, server_default="CASH"),
        sa.Column("status", sa.String(30), nullable=False, server_default="SUCCESS"),
        sa.Column("cash_drawer_reference", sa.String(100), nullable=True),
        sa.Column("cheque_number", sa.String(50), nullable=True),
        sa.Column("bank_name", sa.String(100), nullable=True),
        sa.Column("cheque_date", sa.Date(), nullable=True),
        sa.Column("clearance_date", sa.Date(), nullable=True),
        sa.Column("transaction_reference", sa.String(150), nullable=True),
        sa.Column("razorpay_order_id", sa.String(100), nullable=True),
        sa.Column("razorpay_payment_id", sa.String(100), nullable=True),
        sa.Column("razorpay_signature", sa.String(255), nullable=True),
        sa.Column("received_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reconciliation_status", sa.String(30), nullable=False, server_default="RECONCILED"),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remarks", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "receipt_number", name="uq_fee_payments_tenant_receipt"),
    )
    op.create_index("ix_fee_payments_tenant_invoice", "fee_payments", ["tenant_id", "invoice_id"])
    op.create_index("ix_fee_payments_tenant_student", "fee_payments", ["tenant_id", "student_id"])
    op.create_index("ix_fee_payments_payment_date", "fee_payments", ["tenant_id", "payment_date"])
    op.create_index("ix_fee_payments_rzp_order", "fee_payments", ["razorpay_order_id"])
    op.execute("ALTER TABLE fee_payments ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY fee_payments_tenant_isolation ON fee_payments
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 9. Create fee_payment_webhook_events ─────────────────────────────────
    op.create_table(
        "fee_payment_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, server_default="RAZORPAY"),
        sa.Column("event_id", sa.String(150), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PROCESSED"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "provider", "event_id", name="uq_fee_webhook_event"),
    )
    op.create_index("ix_fee_webhook_events_tenant", "fee_payment_webhook_events", ["tenant_id", "event_id"])
    op.execute("ALTER TABLE fee_payment_webhook_events ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY fee_payment_webhook_events_tenant_isolation ON fee_payment_webhook_events
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)


def downgrade() -> None:
    op.drop_table("fee_payment_webhook_events")
    op.drop_table("fee_payments")
    op.drop_table("fee_invoices")
    op.drop_table("student_fee_allocations")
    op.drop_table("fee_discounts_scholarships")
    op.drop_table("fee_structure_installments")
    op.drop_table("fee_structure_components")
    op.drop_table("fee_structures")
    op.drop_table("fee_categories")
