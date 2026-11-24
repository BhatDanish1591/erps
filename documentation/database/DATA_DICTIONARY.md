# EduSaaS CRM — Database Data Dictionary

This document provides a comprehensive data dictionary for all tables, columns, constraints, data types, and row-level security (RLS) policies implemented in the Multi-Tenant School & College SaaS CRM.

---

## Table of Contents

1. [tenants](#1-tenants)
2. [tenant_domains](#2-tenant_domains)
3. [tenant_settings](#3-tenant_settings)
4. [users](#4-users)
5. [refresh_tokens](#5-refresh_tokens)
6. [login_history](#6-login_history)
7. [roles](#7-roles)
8. [permissions](#8-permissions)
9. [role_permissions](#9-role_permissions)
10. [memberships](#10-memberships)
11. [academic_sessions](#11-academic_sessions)
12. [subscription_plans](#12-subscription_plans)
13. [plan_features](#13-plan_features)
14. [subscriptions](#14-subscriptions)
15. [subscription_invoices](#15-subscription_invoices)
16. [subscription_payments](#16-subscription_payments)
17. [audit_logs](#17-audit_logs)

---

### 1. tenants
The core institution entity representing a distinct school or college tenant on the platform.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key (UUIDv4) |
| `name` | `VARCHAR(255)` | No | - | Official institution name |
| `slug` | `VARCHAR(100)` | No | - | Unique URL slug for subdomain routing (e.g. `oakridge`) |
| `institution_type` | `ENUM` | No | `'SCHOOL'` | Educational tier: `SCHOOL` or `COLLEGE` |
| `status` | `ENUM` | No | `'TRIAL'` | State: `TRIAL`, `ACTIVE`, `SUSPENDED`, `INACTIVE` |
| `email` | `VARCHAR(255)` | Yes | `NULL` | Primary administrative contact email |
| `phone` | `VARCHAR(50)` | Yes | `NULL` | Primary contact phone number |
| `address` | `VARCHAR(500)` | Yes | `NULL` | Physical campus address |
| `city` | `VARCHAR(100)` | Yes | `NULL` | City |
| `state` | `VARCHAR(100)` | Yes | `NULL` | State / Province |
| `country` | `VARCHAR(100)` | No | `'India'` | Country |
| `postal_code` | `VARCHAR(20)` | Yes | `NULL` | PIN / Postal code |
| `logo_url` | `VARCHAR(1024)`| Yes | `NULL` | S3 / R2 storage URL for institution crest / logo |
| `timezone` | `VARCHAR(50)` | No | `'Asia/Kolkata'`| Default timezone for academic scheduling and attendance |
| `currency` | `VARCHAR(10)` | No | `'INR'` | Billing currency code |
| `is_deleted` | `BOOLEAN` | No | `false` | Soft-deletion flag |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last modification timestamp |

- **Indexes:** `ix_tenants_slug` (UNIQUE), `ix_tenants_status`, `ix_tenants_type_status` (`institution_type`, `status`), `ix_tenants_is_deleted`.

---

### 2. tenant_domains
Maps hostnames, subdomains, and custom domains to specific institutions.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `tenant_id` | `UUID` | No | - | Foreign Key -> `tenants.id` (CASCADE) |
| `domain` | `VARCHAR(255)` | No | - | Full domain (e.g. `oakridge.edusaas.com`) |
| `is_primary` | `BOOLEAN` | No | `false` | Indicates the institution's canonical web domain |
| `is_verified` | `BOOLEAN` | No | `false` | Whether DNS ownership has been validated |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last modification timestamp |

- **Constraints & Indexes:** `uq_tenant_domains_domain` (UNIQUE), `ix_tenant_domains_tenant_primary` (`tenant_id`, `is_primary`).

---

### 3. tenant_settings
Tenant-specific configuration key-value pairs (branding, notification switches, academic rules).

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `tenant_id` | `UUID` | No | - | Foreign Key -> `tenants.id` (CASCADE) |
| `key` | `VARCHAR(100)` | No | - | Setting identifier (e.g. `branding_theme`, `grading_scale`) |
| `value` | `JSONB` | No | `'{}'` | Configuration payload |
| `is_public` | `BOOLEAN` | No | `false` | If true, exposed to unauthenticated landing pages |
| `is_deleted` | `BOOLEAN` | No | `false` | Soft-deletion flag |
| `deleted_at` | `TIMESTAMPTZ` | Yes | `NULL` | Soft-deletion timestamp |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last modification timestamp |

- **RLS Enabled:** Yes (`tenant_isolation_policy`, `tenant_isolation_insert_policy`).
- **Constraints & Indexes:** `uq_tenant_settings_tenant_key` (`tenant_id`, `key`), `ix_tenant_settings_tenant_public` (`tenant_id`, `is_public`).

---

### 4. users
Global user identity. Users authenticate centrally at the platform level and access institutions via memberships.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `email` | `VARCHAR(255)` | No | - | Unique login email address |
| `password_hash` | `VARCHAR(255)` | No | - | Argon2id secure password hash |
| `full_name` | `VARCHAR(255)` | No | - | User's full display name |
| `phone` | `VARCHAR(50)` | Yes | `NULL` | Contact mobile number |
| `avatar_url` | `VARCHAR(1024)`| Yes | `NULL` | Profile photo URL |
| `is_active` | `BOOLEAN` | No | `true` | Account active flag |
| `is_superadmin`| `BOOLEAN` | No | `false` | Platform-level super administrator flag |
| `email_verified_at` | `TIMESTAMPTZ` | Yes | `NULL` | Verification timestamp |
| `phone_verified_at` | `TIMESTAMPTZ` | Yes | `NULL` | Phone verification timestamp |
| `mfa_enabled` | `BOOLEAN` | No | `false` | Multi-Factor Authentication enabled |
| `mfa_secret` | `VARCHAR(255)` | Yes | `NULL` | TOTP secret (encrypted) |
| `last_login_at`| `TIMESTAMPTZ` | Yes | `NULL` | Timestamp of most recent successful login |
| `is_deleted` | `BOOLEAN` | No | `false` | Soft-deletion flag |
| `deleted_at` | `TIMESTAMPTZ` | Yes | `NULL` | Soft-deletion timestamp |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last modification timestamp |

- **Indexes:** `ix_users_email` (UNIQUE), `ix_users_phone`, `ix_users_is_superadmin`, `ix_users_email_active` (`email`, `is_active`).

---

### 5. refresh_tokens
Hashed JWT refresh tokens with device fingerprinting and automatic rotation.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `user_id` | `UUID` | No | - | Foreign Key -> `users.id` (CASCADE) |
| `token_hash` | `VARCHAR(255)` | No | - | SHA-256 hash of the rotating refresh token |
| `expires_at` | `TIMESTAMPTZ` | No | - | Absolute token expiration date |
| `is_revoked` | `BOOLEAN` | No | `false` | Revocation status flag |
| `revoked_at` | `TIMESTAMPTZ` | Yes | `NULL` | Timestamp of revocation |
| `replaced_by_token_hash` | `VARCHAR(255)` | Yes | `NULL` | Successor token hash (detects replay attacks) |
| `user_agent` | `VARCHAR(500)` | Yes | `NULL` | Device / browser User-Agent string |
| `ip_address` | `VARCHAR(45)` | Yes | `NULL` | Client IP address |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last modification timestamp |

- **Indexes:** `ix_refresh_tokens_token_hash` (UNIQUE), `ix_refresh_tokens_user_valid` (`user_id`, `is_revoked`, `expires_at`).

---

### 6. login_history
Security audit trail recording every authentication attempt.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `user_id` | `UUID` | Yes | `NULL` | Foreign Key -> `users.id` (SET NULL) |
| `tenant_id` | `UUID` | Yes | `NULL` | Foreign Key -> `tenants.id` (SET NULL) |
| `email` | `VARCHAR(255)` | No | - | Email submitted during login attempt |
| `status` | `ENUM` | No | `'SUCCESS'` | State: `SUCCESS`, `FAILED` |
| `ip_address` | `VARCHAR(45)` | Yes | `NULL` | Client IPv4 / IPv6 address |
| `user_agent` | `VARCHAR(500)` | Yes | `NULL` | Client User-Agent string |
| `failure_reason` | `VARCHAR(255)` | Yes | `NULL` | Error details (e.g. `INVALID_CREDENTIALS`, `LOCKED`) |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Attempt timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Timestamp |

- **Indexes:** `ix_login_history_user_created` (`user_id`, `created_at`), `ix_login_history_tenant_created` (`tenant_id`, `created_at`).

---

### 7. roles
Role definitions separating platform-level roles from tenant-level institutional roles.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `tenant_id` | `UUID` | Yes | `NULL` | Foreign Key -> `tenants.id` (NULL for platform template roles) |
| `name` | `VARCHAR(100)` | No | - | Human-readable name (e.g. `Teacher`, `Principal`) |
| `code` | `VARCHAR(100)` | No | - | Machine code (e.g. `INSTITUTION_ADMIN`, `TEACHER`) |
| `scope` | `ENUM` | No | `'TENANT'` | Access scope: `PLATFORM`, `TENANT` |
| `description` | `VARCHAR(255)` | Yes | `NULL` | Role purpose summary |
| `is_system_role`| `BOOLEAN` | No | `false` | System protected role (cannot be deleted) |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last modification timestamp |

- **Constraints & Indexes:** `uq_roles_tenant_code` (`tenant_id`, `code`), `ix_roles_scope_tenant` (`scope`, `tenant_id`).

---

### 8. permissions
Granular permission actions defined at the platform level.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `code` | `VARCHAR(100)` | No | - | Unique permission code (e.g. `attendance:mark`) |
| `module` | `VARCHAR(50)` | No | - | Functional module (e.g. `academic`, `finance`) |
| `description` | `VARCHAR(255)` | No | - | Plain language description of capability |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last modification timestamp |

- **Indexes:** `ix_permissions_code` (UNIQUE), `ix_permissions_module`.

---

### 9. role_permissions
Junction mapping permissions to roles.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `role_id` | `UUID` | No | - | Foreign Key -> `roles.id` (CASCADE) |
| `permission_id`| `UUID` | No | - | Foreign Key -> `permissions.id` (CASCADE) |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last modification timestamp |

- **Constraints & Indexes:** `uq_role_permissions_role_perm` (`role_id`, `permission_id`).

---

### 10. memberships
Links a User to an Institution Tenant with an assigned Role. Enforces strict tenant membership.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `tenant_id` | `UUID` | No | - | Foreign Key -> `tenants.id` (CASCADE) |
| `user_id` | `UUID` | No | - | Foreign Key -> `users.id` (CASCADE) |
| `role_id` | `UUID` | No | - | Foreign Key -> `roles.id` (RESTRICT) |
| `status` | `ENUM` | No | `'ACTIVE'` | State: `ACTIVE`, `INVITED`, `SUSPENDED` |
| `is_deleted` | `BOOLEAN` | No | `false` | Soft-deletion flag |
| `deleted_at` | `TIMESTAMPTZ` | Yes | `NULL` | Soft-deletion timestamp |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last modification timestamp |

- **RLS Enabled:** Yes (`tenant_isolation_policy`, `tenant_isolation_insert_policy`).
- **Constraints & Indexes:** `uq_memberships_tenant_user` (`tenant_id`, `user_id`), `ix_memberships_tenant_status` (`tenant_id`, `status`), `ix_memberships_user_tenant` (`user_id`, `tenant_id`).

---

### 11. academic_sessions
Academic years, cycles, or college semesters isolated per tenant.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `tenant_id` | `UUID` | No | - | Foreign Key -> `tenants.id` (CASCADE) |
| `name` | `VARCHAR(100)` | No | - | Display name (e.g. `Academic Year 2026-27`) |
| `code` | `VARCHAR(50)` | No | - | Machine code (e.g. `AY-2026-27`, `SEM-FALL-26`) |
| `start_date` | `DATE` | No | - | Cycle starting date |
| `end_date` | `DATE` | No | - | Cycle ending date |
| `is_current` | `BOOLEAN` | No | `false` | Whether this is the active operational session |
| `status` | `ENUM` | No | `'ACTIVE'` | State: `UPCOMING`, `ACTIVE`, `COMPLETED`, `ARCHIVED` |
| `description` | `VARCHAR(255)` | Yes | `NULL` | Optional details |
| `is_deleted` | `BOOLEAN` | No | `false` | Soft-deletion flag |
| `deleted_at` | `TIMESTAMPTZ` | Yes | `NULL` | Soft-deletion timestamp |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last modification timestamp |

- **RLS Enabled:** Yes (`tenant_isolation_policy`, `tenant_isolation_insert_policy`).
- **Constraints & Indexes:** `uq_academic_sessions_tenant_code` (`tenant_id`, `code`), `ix_academic_sessions_tenant_current` (`tenant_id`, `is_current`), `ix_academic_sessions_tenant_dates` (`tenant_id`, `start_date`, `end_date`).

---

### 12. subscription_plans
Platform-level SaaS tiers (e.g. Starter, Growth, Enterprise).

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `name` | `VARCHAR(100)` | No | - | Tier display name |
| `code` | `VARCHAR(50)` | No | - | Unique tier code (e.g. `GROWTH_SCHOOL`) |
| `description` | `VARCHAR(500)` | Yes | `NULL` | Plan summary |
| `institution_type`| `ENUM` | Yes | `NULL` | Targeted institution tier (or null for all) |
| `billing_cycle`| `ENUM` | No | `'YEARLY'` | Frequency: `MONTHLY`, `QUARTERLY`, `YEARLY` |
| `price` | `NUMERIC(12,2)`| No | `0.0` | Plan price |
| `currency` | `VARCHAR(10)` | No | `'INR'` | ISO currency code |
| `is_active` | `BOOLEAN` | No | `true` | Public availability flag |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last modification timestamp |

- **Indexes:** `ix_subscription_plans_code` (UNIQUE), `ix_subscription_plans_is_active`.

---

### 13. plan_features
Feature flags, quotas, and entitlement limits bundled with a plan.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `plan_id` | `UUID` | No | - | Foreign Key -> `subscription_plans.id` (CASCADE) |
| `feature_key` | `VARCHAR(100)` | No | - | Entitlement key (e.g. `max_students`, `sms_gateway`) |
| `feature_value`| `JSONB` | No | `'{}'` | Limits and parameters (e.g. `{"limit": 1000}`) |
| `is_enabled` | `BOOLEAN` | No | `true` | Feature switch |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last modification timestamp |

- **Constraints & Indexes:** `uq_plan_features_plan_key` (`plan_id`, `feature_key`).

---

### 14. subscriptions
Binds an institution tenant to an active commercial plan.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `tenant_id` | `UUID` | No | - | Foreign Key -> `tenants.id` (CASCADE) |
| `plan_id` | `UUID` | No | - | Foreign Key -> `subscription_plans.id` (RESTRICT) |
| `status` | `ENUM` | No | `'TRIAL'` | State: `TRIAL`, `ACTIVE`, `PAST_DUE`, `CANCELED`, `EXPIRED`, `SUSPENDED` |
| `billing_cycle`| `ENUM` | No | `'YEARLY'` | Frequency: `MONTHLY`, `QUARTERLY`, `YEARLY` |
| `current_period_start`| `TIMESTAMPTZ`| No | - | Start of current billing window |
| `current_period_end` | `TIMESTAMPTZ`| No | - | End of current billing window |
| `trial_ends_at`| `TIMESTAMPTZ` | Yes | `NULL` | Trial expiry timestamp |
| `canceled_at` | `TIMESTAMPTZ` | Yes | `NULL` | Cancellation timestamp |
| `is_auto_renew`| `BOOLEAN` | No | `true` | Automatic recurring renewal flag |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last modification timestamp |

- **Indexes:** `ix_subscriptions_tenant_status` (`tenant_id`, `status`), `ix_subscriptions_current_period_end`.

---

### 15. subscription_invoices
Invoices generated for subscription fees and renewals.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `tenant_id` | `UUID` | No | - | Foreign Key -> `tenants.id` (CASCADE) |
| `subscription_id`| `UUID` | No | - | Foreign Key -> `subscriptions.id` (CASCADE) |
| `invoice_number` | `VARCHAR(50)` | No | - | Unique serial number (e.g. `INV-2026-0001`) |
| `subtotal` | `NUMERIC(12,2)`| No | - | Subtotal before taxes |
| `tax_amount` | `NUMERIC(12,2)`| No | `0.0` | Tax component (GST) |
| `total_amount` | `NUMERIC(12,2)`| No | - | Net payable amount |
| `currency` | `VARCHAR(10)` | No | `'INR'` | Currency code |
| `status` | `ENUM` | No | `'ISSUED'`| State: `DRAFT`, `ISSUED`, `PAID`, `VOID`, `UNCOLLECTIBLE` |
| `due_date` | `DATE` | No | - | Payment due date |
| `paid_at` | `TIMESTAMPTZ` | Yes | `NULL` | Settlement timestamp |
| `invoice_url` | `VARCHAR(1024)`| Yes | `NULL` | S3 / R2 hosted PDF receipt URL |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last modification timestamp |

- **RLS Enabled:** Yes (`tenant_isolation_policy`, `tenant_isolation_insert_policy`).
- **Indexes:** `ix_subscription_invoices_invoice_number` (UNIQUE), `ix_subscription_invoices_tenant_status` (`tenant_id`, `status`).

---

### 16. subscription_payments
Receipt transactions executed via payment gateways (Razorpay, Stripe, Netbanking).

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `tenant_id` | `UUID` | No | - | Foreign Key -> `tenants.id` (CASCADE) |
| `invoice_id` | `UUID` | No | - | Foreign Key -> `subscription_invoices.id` (CASCADE) |
| `amount` | `NUMERIC(12,2)`| No | - | Amount captured |
| `currency` | `VARCHAR(10)` | No | `'INR'` | Currency code |
| `payment_method`| `VARCHAR(50)` | No | `'RAZORPAY'`| Gateway method (e.g. UPI, Card, Netbanking) |
| `gateway` | `VARCHAR(50)` | No | `'razorpay'`| Payment gateway name |
| `transaction_reference` | `VARCHAR(255)`| Yes | `NULL`| Gateway transaction ID (e.g. `pay_29OzAKH34df`) |
| `status` | `ENUM` | No | `'PENDING'` | State: `PENDING`, `SUCCESS`, `FAILED`, `REFUNDED` |
| `paid_at` | `TIMESTAMPTZ` | Yes | `NULL` | Settlement timestamp |
| `failure_reason`| `VARCHAR(500)`| Yes | `NULL` | Reason code if payment declined |
| `payload` | `JSONB` | No | `'{}'` | Webhook transaction response payload |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Row creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last modification timestamp |

- **RLS Enabled:** Yes (`tenant_isolation_policy`, `tenant_isolation_insert_policy`).
- **Indexes:** `ix_subscription_payments_transaction_ref` (UNIQUE), `ix_subscription_payments_tenant_status` (`tenant_id`, `status`).

---

### 17. audit_logs
Immutable record of all mutations and sensitive actions across tenants and platform operations.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary Key |
| `tenant_id` | `UUID` | Yes | `NULL` | Foreign Key -> `tenants.id` (SET NULL) |
| `user_id` | `UUID` | Yes | `NULL` | Foreign Key -> `users.id` (SET NULL) |
| `action` | `VARCHAR(50)` | No | - | Action tag (e.g. `CREATE`, `UPDATE`, `DELETE`, `LOGIN`) |
| `entity_type` | `VARCHAR(100)` | No | - | Target entity name (e.g. `AcademicSession`, `User`) |
| `entity_id` | `VARCHAR(100)` | Yes | `NULL` | Primary key of the affected entity |
| `ip_address` | `VARCHAR(45)` | Yes | `NULL` | Origin client IP address |
| `user_agent` | `VARCHAR(500)` | Yes | `NULL` | Origin client User-Agent |
| `changes` | `JSONB` | No | `'{}'` | JSON delta of modified columns `{"old": {...}, "new": {...}}` |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Operation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Modification timestamp |

- **Indexes:** `ix_audit_logs_tenant_created` (`tenant_id`, `created_at`), `ix_audit_logs_entity_lookup` (`entity_type`, `entity_id`), `ix_audit_logs_action`.
