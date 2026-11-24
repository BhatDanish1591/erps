"""Add institution membership roles for Principal and Head of Department."""

from alembic import op
import sqlalchemy as sa

revision = "0019_college_staff_roles"
down_revision = "0018_runtime_tenant_context"

STAFF_ROLES = (
    ("b40ad817-bd41-44c8-aba5-f8de7bc362ee", "PRINCIPAL", "Principal", "Institution academic and staff oversight"),
    ("88c9c0fc-c27b-42b7-9454-e906c481f4a2", "HOD", "Head of Department", "Oversight of assigned departments"),
)


def upgrade() -> None:
    connection = op.get_bind()
    for role_id, code, name, description in STAFF_ROLES:
        connection.execute(
            sa.text("""
                INSERT INTO roles (id, code, name, description, scope, is_system_role)
                SELECT CAST(:id AS uuid), CAST(:code AS varchar), :name, :description, 'TENANT'::role_scope_enum, TRUE
                WHERE NOT EXISTS (
                    SELECT 1 FROM roles WHERE code = CAST(:code AS varchar) AND tenant_id IS NULL AND is_system_role
                )
            """),
            {"id": role_id, "code": code, "name": name, "description": description},
        )


def downgrade() -> None:
    connection = op.get_bind()
    for role_id, _, _, _ in STAFF_ROLES:
        connection.execute(sa.text("DELETE FROM roles WHERE id = CAST(:id AS uuid)"), {"id": role_id})
