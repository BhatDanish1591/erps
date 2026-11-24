# Architecture Overview

## Multi-Tenant Strategy

### Data Isolation
- Shared PostgreSQL database
- Every tenant-scoped table has a `tenant_id` UUID column (indexed)
- The API connects as a limited PostgreSQL role subject to row-level security on tables with policies.
- Authenticated tenant requests use the tenant identifier in the signed access token.
- Database sessions reapply their tenant scope when a service starts a new transaction after a commit.

### Tenant Resolution Flow
```
Request -> Nginx -> FastAPI authorization dependencies
         |
  Validate access token and load active user
         |
  Set tenant context from the signed token
         |
  Repositories use the active tenant scope
         |
  PostgreSQL applies row-level policies using transaction-local context
```

## Module Layer Responsibilities

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Router | `app/api/v1/` | HTTP interface, request parsing, response formatting |
| Service | `app/services/` | Business logic, orchestration, validation |
| Repository | `app/repositories/` | Database access, query building |
| Model | `app/models/` | SQLAlchemy ORM definitions |
| Schema | `app/schemas/` | Pydantic request/response contracts |
| Permission | `app/permissions/` | RBAC guards, role checks |
| Middleware | `app/middleware/` | Cross-cutting concerns (tenant, logging) |
| Worker | `app/workers/` | Async Celery tasks |
