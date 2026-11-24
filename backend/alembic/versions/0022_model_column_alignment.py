"""Align module tables with the timestamps and soft deletes used by their models."""

from alembic import op

revision = "0022_model_column_alignment"
down_revision = "0021_academic_soft_delete"

SOFT_DELETE_TABLES = (
    "examination_questions",
    "grading_scales",
    "question_bank",
    "re_evaluation_requests",
    "report_card_templates",
    "student_exam_answers",
    "student_exam_attempts",
    "student_subject_results",
    "student_term_results",
)

DELETION_TIMESTAMP_TABLES = (
    "hostel_buildings",
    "hostel_maintenance_requests",
    "hostel_room_allocations",
    "hostel_rooms",
    "library_book_copies",
    "library_books",
    "library_borrow_records",
    "library_categories",
    "notification_templates",
    "parent_teacher_messages",
    "scheduled_reports",
    "student_link_verification_codes",
    "student_transport_allocations",
    "study_material_versions",
    "study_materials",
    "tenant_integrations",
    "timetable_schedules",
    "transport_drivers",
    "transport_maintenance_logs",
    "transport_routes",
    "transport_stops",
    "transport_vehicles",
)


def upgrade() -> None:
    for table in SOFT_DELETE_TABLES:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS is_deleted boolean NOT NULL DEFAULT false")
    for table in (*SOFT_DELETE_TABLES, *DELETION_TIMESTAMP_TABLES):
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS deleted_at timestamptz")
    for table in ("examination_questions", "fee_payment_webhook_events", "transport_gps_logs"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()")


def downgrade() -> None:
    # Existing deployments may already have these columns and recorded deletions.
    pass
