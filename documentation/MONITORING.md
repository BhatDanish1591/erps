# Production Monitoring, Logging & Alerting

This document outlines the observability, error tracking, structured logging, and alerting architecture for the **EduSaaS CRM** multi-tenant platform.

---

## 1. Error Tracking (Sentry Integration)

The backend and frontend are instrumented with **Sentry** for real-time exception tracking, breadcrumbs, user session telemetry, and distributed tracing.

### Backend Setup
In `backend/.env.production`:
```env
SENTRY_DSN=https://<public_key>@o<org_id>.ingest.sentry.io/<project_id>
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.2
```
FastAPI automatically tags every Sentry event with:
- `tenant_id`: Current institution UUID.
- `user_id`: Authenticated user UUID.
- `role`: Authenticated role (Super Admin, Institution Admin, Teacher, Student, Parent).
- `route`: HTTP method and path template.

Sensitive fields (`password`, `credit_card`, `token`, `secret`) are automatically redacted before transmission via Sentry's `before_send` scrubber hook.

### Frontend Setup
In `web/.env.production`:
```env
VITE_SENTRY_DSN=https://<public_key>@o<org_id>.ingest.sentry.io/<project_id>
```

---

## 2. Structured JSON Access Logging

Production Nginx generates structured JSON logs adhering to the schema below, located at `/var/log/nginx/access.log`:

```json
{
  "time_local": "20/Nov/2026:01:45:00 +0000",
  "remote_addr": "203.0.113.195",
  "request": "POST /api/v1/auth/login HTTP/1.1",
  "status": "200",
  "body_bytes_sent": "648",
  "request_time": "0.045",
  "http_referrer": "https://oakridge.edusaas.com/login",
  "http_user_agent": "Mozilla/5.0 ...",
  "host": "oakridge.edusaas.com"
}
```

These logs can be ingested directly into Logstash, Vector, FluentBit, Datadog, or AWS CloudWatch without custom regex parsers.

---

## 3. Recommended Production Alerting Rules

| Alert Metric | Warning Threshold | Critical Threshold | Action Plan |
|---|---|---|---|
| **API Error Rate (5xx)** | > 1% over 5m | > 5% over 2m | Inspect backend logs (`docker compose logs --tail=100 backend`), review Sentry issues |
| **API P95 Latency** | > 800ms over 5m | > 2000ms over 2m | Check PostgreSQL slow queries and Redis connection pool saturation |
| **PostgreSQL Connection Pool** | > 75% pool used | > 90% pool used | Scale `DATABASE_POOL_SIZE` or investigate idle in transaction leaks |
| **Redis Memory Utilization** | > 70% of 512MB | > 85% of 512MB | Evict expired keys or scale memory in `docker-compose.prod.yml` |
| **Celery Queue Backlog** | > 500 tasks | > 2,000 tasks | Scale `celery_worker` concurrency or add additional worker instances |
| **Disk Space Available** | < 20% remaining | < 10% remaining | Prune old Docker images (`docker image prune -a`) and old backups |
| **Failed Rate Limit Hits (429)** | > 50/min | > 200/min | Review potential brute-force or DDoS attack patterns; block offending IPs via `ufw` |

---

## 4. Operational Health Check Command

To inspect all services, database response times, and Redis status in a single call:
```bash
./scripts/healthcheck.sh
```
Outputs exit code `0` when all checks pass, and `1` when any service is unreachable or degraded.
