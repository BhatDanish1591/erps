"""onboarding_and_academic_structure

Revision ID: 0003_onboarding_and_academic
Revises: 0002_super_admin_entities
Create Date: 2026-11-19 12:45:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_onboarding_and_academic"
down_revision: Union[str, None] = "0002_super_admin_entities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create Invitations ─────────────────────────────────────────────────
    op.create_table(
        "invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("token_hash", sa.String(255), unique=True, nullable=False),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_invitations_tenant_id", "invitations", ["tenant_id"])
    op.create_index("ix_invitations_email", "invitations", ["email"])
    op.create_index("ix_invitations_token_hash", "invitations", ["token_hash"])
    op.create_index("ix_invitations_status_expires", "invitations", ["status", "expires_at"])
    op.execute("ALTER TABLE invitations ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY invitations_tenant_isolation ON invitations
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
            WITH CHECK (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 2. Create School Classes ──────────────────────────────────────────────
    op.create_table(
        "school_classes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_school_classes_tenant_code"),
    )
    op.create_index("ix_school_classes_tenant_order", "school_classes", ["tenant_id", "order_index"])
    op.execute("ALTER TABLE school_classes ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY school_classes_tenant_isolation ON school_classes
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 3. Create Sections ────────────────────────────────────────────────────
    op.create_table(
        "sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("capacity", sa.Integer(), server_default="40", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "class_id", "name", name="uq_sections_tenant_class_name"),
    )
    op.create_index("ix_sections_tenant_id", "sections", ["tenant_id"])
    op.create_index("ix_sections_class_id", "sections", ["class_id"])
    op.execute("ALTER TABLE sections ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY sections_tenant_isolation ON sections
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 4. Create Departments ─────────────────────────────────────────────────
    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_departments_tenant_code"),
    )
    op.create_index("ix_departments_tenant_id", "departments", ["tenant_id"])
    op.execute("ALTER TABLE departments ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY departments_tenant_isolation ON departments
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 5. Create Courses ─────────────────────────────────────────────────────
    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("duration_semesters", sa.Integer(), server_default="8", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_courses_tenant_code"),
    )
    op.create_index("ix_courses_tenant_id", "courses", ["tenant_id"])
    op.create_index("ix_courses_department_id", "courses", ["department_id"])
    op.execute("ALTER TABLE courses ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY courses_tenant_isolation ON courses
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 6. Create Subjects ────────────────────────────────────────────────────
    op.create_table(
        "subjects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("subject_type", sa.String(30), server_default="THEORY", nullable=False),
        sa.Column("credits", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "code", name="uq_subjects_tenant_code"),
    )
    op.create_index("ix_subjects_tenant_id", "subjects", ["tenant_id"])
    op.execute("ALTER TABLE subjects ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY subjects_tenant_isolation ON subjects
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 7. Create Student Profiles ────────────────────────────────────────────
    op.create_table(
        "student_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("admission_number", sa.String(100), nullable=False),
        sa.Column("roll_number", sa.String(50), nullable=True),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("school_classes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("parent_name", sa.String(150), nullable=True),
        sa.Column("parent_phone", sa.String(50), nullable=True),
        sa.Column("parent_email", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "admission_number", name="uq_student_profiles_tenant_admission"),
    )
    op.create_index("ix_student_profiles_tenant_id", "student_profiles", ["tenant_id"])
    op.create_index("ix_student_profiles_user_id", "student_profiles", ["user_id"])
    op.execute("ALTER TABLE student_profiles ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY student_profiles_tenant_isolation ON student_profiles
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)

    # ── 8. Create Teacher Profiles ────────────────────────────────────────────
    op.create_table(
        "teacher_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.String(100), nullable=False),
        sa.Column("designation", sa.String(100), nullable=True),
        sa.Column("qualification", sa.String(255), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("joining_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "employee_id", name="uq_teacher_profiles_tenant_emp"),
    )
    op.create_index("ix_teacher_profiles_tenant_id", "teacher_profiles", ["tenant_id"])
    op.create_index("ix_teacher_profiles_user_id", "teacher_profiles", ["user_id"])
    op.execute("ALTER TABLE teacher_profiles ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY teacher_profiles_tenant_isolation ON teacher_profiles
            FOR ALL
            USING (
                current_setting('app.is_superadmin', true) = 'true'
                OR tenant_id::text = current_setting('app.current_tenant_id', true)
            )
    """)


def downgrade() -> None:
    op.drop_table("teacher_profiles")
    op.drop_table("student_profiles")
    op.drop_table("subjects")
    op.drop_table("courses")
    op.drop_table("departments")
    op.drop_table("sections")
    op.drop_table("school_classes")
    op.drop_table("invitations")
