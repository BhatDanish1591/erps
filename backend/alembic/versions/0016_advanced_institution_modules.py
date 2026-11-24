"""Create Advanced Institution Modules (Library, Transport, Hostel)

Revision ID: 0016_advanced_modules
Revises: 0015_notification_system
Create Date: 2026-11-19 21:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0016_advanced_modules"
down_revision: Union[str, None] = "0015_notification_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ═════════════════════════════════════════════════════════════════════════
    # A. LIBRARY MANAGEMENT TABLES
    # ═════════════════════════════════════════════════════════════════════════

    # 1. library_categories
    op.create_table(
        "library_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_library_categories_tenant_code"),
    )
    op.create_index("ix_library_categories_tenant_code", "library_categories", ["tenant_id", "code"])
    op.execute("ALTER TABLE library_categories ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY library_categories_isolation ON library_categories "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # 2. library_books
    op.create_table(
        "library_books",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("library_categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("isbn", sa.String(50), nullable=True),
        sa.Column("publisher", sa.String(255), nullable=True),
        sa.Column("edition", sa.String(50), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("total_copies", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("available_copies", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("shelf_location", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_image_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_library_books_tenant_title", "library_books", ["tenant_id", "title"])
    op.create_index("ix_library_books_tenant_author", "library_books", ["tenant_id", "author"])
    op.create_index("ix_library_books_tenant_isbn", "library_books", ["tenant_id", "isbn"])
    op.execute("ALTER TABLE library_books ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY library_books_isolation ON library_books "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # 3. library_book_copies
    op.create_table(
        "library_book_copies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("book_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("library_books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("accession_number", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="AVAILABLE"),  # AVAILABLE, ISSUED, LOST, DAMAGED, RESERVED
        sa.Column("condition_notes", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.UniqueConstraint("tenant_id", "accession_number", name="uq_library_copies_tenant_acc"),
    )
    op.create_index("ix_library_copies_tenant_book", "library_book_copies", ["tenant_id", "book_id"])
    op.create_index("ix_library_copies_tenant_status", "library_book_copies", ["tenant_id", "status"])
    op.execute("ALTER TABLE library_book_copies ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY library_copies_isolation ON library_book_copies "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # 4. library_borrow_records
    op.create_table(
        "library_borrow_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("copy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("library_book_copies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("book_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("library_books.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("borrower_type", sa.String(20), nullable=False, server_default="STUDENT"),  # STUDENT, TEACHER, STAFF
        sa.Column("borrower_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teacher_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("return_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="ISSUED"),  # ISSUED, RETURNED, OVERDUE, LOST
        sa.Column("fine_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("fine_paid", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("issued_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("received_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_library_borrows_tenant_user", "library_borrow_records", ["tenant_id", "borrower_user_id"])
    op.create_index("ix_library_borrows_tenant_status", "library_borrow_records", ["tenant_id", "status"])
    op.create_index("ix_library_borrows_tenant_student", "library_borrow_records", ["tenant_id", "student_id"])
    op.execute("ALTER TABLE library_borrow_records ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY library_borrows_isolation ON library_borrow_records "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # B. TRANSPORT MANAGEMENT TABLES
    # ═════════════════════════════════════════════════════════════════════════

    # 1. transport_vehicles
    op.create_table(
        "transport_vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("registration_number", sa.String(50), nullable=False),
        sa.Column("vehicle_model", sa.String(100), nullable=False),
        sa.Column("seating_capacity", sa.Integer(), nullable=False),
        sa.Column("fuel_type", sa.String(30), nullable=False, server_default="DIESEL"),
        sa.Column("insurance_number", sa.String(100), nullable=True),
        sa.Column("insurance_expiry", sa.Date(), nullable=True),
        sa.Column("fitness_certificate_expiry", sa.Date(), nullable=True),
        sa.Column("gps_device_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),  # ACTIVE, IN_SERVICE, MAINTENANCE, RETIRED
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.UniqueConstraint("tenant_id", "registration_number", name="uq_transport_vehicles_tenant_reg"),
    )
    op.create_index("ix_transport_vehicles_tenant_reg", "transport_vehicles", ["tenant_id", "registration_number"])
    op.execute("ALTER TABLE transport_vehicles ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY transport_vehicles_isolation ON transport_vehicles "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # 2. transport_drivers
    op.create_table(
        "transport_drivers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("license_number", sa.String(100), nullable=False),
        sa.Column("license_expiry", sa.Date(), nullable=True),
        sa.Column("emergency_contact", sa.String(50), nullable=True),
        sa.Column("experience_years", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_transport_drivers_tenant_phone", "transport_drivers", ["tenant_id", "phone"])
    op.execute("ALTER TABLE transport_drivers ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY transport_drivers_isolation ON transport_drivers "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # 3. transport_routes
    op.create_table(
        "transport_routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("start_location", sa.String(150), nullable=False),
        sa.Column("end_location", sa.String(150), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transport_vehicles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transport_drivers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("total_distance_km", sa.Numeric(6, 2), nullable=True),
        sa.Column("monthly_fare", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_transport_routes_tenant_code"),
    )
    op.create_index("ix_transport_routes_tenant_code", "transport_routes", ["tenant_id", "code"])
    op.execute("ALTER TABLE transport_routes ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY transport_routes_isolation ON transport_routes "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # 4. transport_stops
    op.create_table(
        "transport_stops",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transport_routes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("stop_order", sa.Integer(), nullable=False),
        sa.Column("pickup_time", sa.Time(), nullable=False),
        sa.Column("drop_time", sa.Time(), nullable=False),
        sa.Column("stop_fee", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_transport_stops_route_order", "transport_stops", ["tenant_id", "route_id", "stop_order"])
    op.execute("ALTER TABLE transport_stops ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY transport_stops_isolation ON transport_stops "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # 5. student_transport_allocations
    op.create_table(
        "student_transport_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transport_routes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("stop_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transport_stops.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("pickup_drop_type", sa.String(20), nullable=False, server_default="BOTH"),  # PICKUP_ONLY, DROP_ONLY, BOTH
        sa.Column("monthly_fee", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),  # ACTIVE, SUSPENDED, CANCELLED
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_transport_alloc_tenant_student", "student_transport_allocations", ["tenant_id", "student_id"])
    op.create_index("ix_transport_alloc_tenant_route", "student_transport_allocations", ["tenant_id", "route_id"])
    op.execute("ALTER TABLE student_transport_allocations ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY transport_alloc_isolation ON student_transport_allocations "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # 6. transport_maintenance_logs
    op.create_table(
        "transport_maintenance_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transport_vehicles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("maintenance_date", sa.Date(), nullable=False),
        sa.Column("maintenance_type", sa.String(50), nullable=False),
        sa.Column("cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("odometer_reading", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("service_center", sa.String(150), nullable=True),
        sa.Column("next_service_due", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_transport_maint_tenant_veh", "transport_maintenance_logs", ["tenant_id", "vehicle_id"])
    op.execute("ALTER TABLE transport_maintenance_logs ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY transport_maint_isolation ON transport_maintenance_logs "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # 7. transport_gps_logs
    op.create_table(
        "transport_gps_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transport_vehicles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("speed_kmh", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_transport_gps_veh_time", "transport_gps_logs", ["tenant_id", "vehicle_id", "recorded_at"])
    op.execute("ALTER TABLE transport_gps_logs ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY transport_gps_isolation ON transport_gps_logs "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # ═════════════════════════════════════════════════════════════════════════
    # C. HOSTEL MANAGEMENT TABLES
    # ═════════════════════════════════════════════════════════════════════════

    # 1. hostel_buildings
    op.create_table(
        "hostel_buildings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("hostel_type", sa.String(30), nullable=False, server_default="BOYS"),  # BOYS, GIRLS, CO_ED
        sa.Column("total_floors", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("warden_name", sa.String(150), nullable=False),
        sa.Column("warden_phone", sa.String(50), nullable=False),
        sa.Column("warden_email", sa.String(150), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_hostel_buildings_tenant_code"),
    )
    op.create_index("ix_hostel_buildings_tenant_code", "hostel_buildings", ["tenant_id", "code"])
    op.execute("ALTER TABLE hostel_buildings ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY hostel_buildings_isolation ON hostel_buildings "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # 2. hostel_rooms
    op.create_table(
        "hostel_rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hostel_buildings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("room_number", sa.String(50), nullable=False),
        sa.Column("floor", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("room_type", sa.String(50), nullable=False, server_default="DOUBLE"),  # SINGLE, DOUBLE, TRIPLE, FOUR_SHARING, DORMITORY
        sa.Column("is_ac", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("occupied_beds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rent_per_term", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(30), nullable=False, server_default="AVAILABLE"),  # AVAILABLE, FULL, MAINTENANCE
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.UniqueConstraint("tenant_id", "building_id", "room_number", name="uq_hostel_rooms_building_num"),
    )
    op.create_index("ix_hostel_rooms_tenant_bld_status", "hostel_rooms", ["tenant_id", "building_id", "status"])
    op.execute("ALTER TABLE hostel_rooms ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY hostel_rooms_isolation ON hostel_rooms "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # 3. hostel_room_allocations
    op.create_table(
        "hostel_room_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hostel_buildings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hostel_rooms.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bed_number", sa.String(20), nullable=False, server_default="Bed-1"),
        sa.Column("check_in_date", sa.Date(), nullable=False),
        sa.Column("check_out_date", sa.Date(), nullable=True),
        sa.Column("rent_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),  # ACTIVE, VACATED, TRANSFERRED
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_hostel_alloc_tenant_student", "hostel_room_allocations", ["tenant_id", "student_id"])
    op.create_index("ix_hostel_alloc_tenant_room", "hostel_room_allocations", ["tenant_id", "room_id"])
    op.execute("ALTER TABLE hostel_room_allocations ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY hostel_alloc_isolation ON hostel_room_allocations "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # 4. hostel_attendance
    op.create_table(
        "hostel_attendance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hostel_buildings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PRESENT"),  # PRESENT, ABSENT, NIGHT_OUT, LEAVE
        sa.Column("in_time", sa.Time(), nullable=True),
        sa.Column("out_time", sa.Time(), nullable=True),
        sa.Column("remarks", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "building_id", "student_id", "attendance_date", name="uq_hostel_att_tenant_bld_st_date"),
    )
    op.create_index("ix_hostel_att_tenant_date", "hostel_attendance", ["tenant_id", "attendance_date"])
    op.execute("ALTER TABLE hostel_attendance ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY hostel_attendance_isolation ON hostel_attendance "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # 5. hostel_visitors
    op.create_table(
        "hostel_visitors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hostel_buildings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("visitor_name", sa.String(150), nullable=False),
        sa.Column("relation", sa.String(50), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("in_time", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("out_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purpose", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_hostel_visitors_tenant_date", "hostel_visitors", ["tenant_id", "visit_date"])
    op.execute("ALTER TABLE hostel_visitors ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY hostel_visitors_isolation ON hostel_visitors "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )

    # 6. hostel_maintenance_requests
    op.create_table(
        "hostel_maintenance_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hostel_buildings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hostel_rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reported_by_student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("student_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("issue_type", sa.String(50), nullable=False),  # ELECTRICAL, PLUMBING, CARPENTRY, CLEANING, OTHER
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),  # PENDING, IN_PROGRESS, RESOLVED, CANCELLED
        sa.Column("priority", sa.String(20), nullable=False, server_default="MEDIUM"),  # LOW, MEDIUM, HIGH, EMERGENCY
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_hostel_maint_tenant_status", "hostel_maintenance_requests", ["tenant_id", "status"])
    op.execute("ALTER TABLE hostel_maintenance_requests ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY hostel_maint_isolation ON hostel_maintenance_requests "
        "FOR ALL USING (current_setting('app.is_superadmin', true) = 'true' OR tenant_id::text = current_setting('app.current_tenant_id', true));"
    )


def downgrade() -> None:
    # Drop Hostel
    op.drop_table("hostel_maintenance_requests")
    op.drop_table("hostel_visitors")
    op.drop_table("hostel_attendance")
    op.drop_table("hostel_room_allocations")
    op.drop_table("hostel_rooms")
    op.drop_table("hostel_buildings")
    # Drop Transport
    op.drop_table("transport_gps_logs")
    op.drop_table("transport_maintenance_logs")
    op.drop_table("student_transport_allocations")
    op.drop_table("transport_stops")
    op.drop_table("transport_routes")
    op.drop_table("transport_drivers")
    op.drop_table("transport_vehicles")
    # Drop Library
    op.drop_table("library_borrow_records")
    op.drop_table("library_book_copies")
    op.drop_table("library_books")
    op.drop_table("library_categories")
