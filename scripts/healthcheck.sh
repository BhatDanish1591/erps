#!/usr/bin/env bash
# ==============================================================================
# EduSaaS CRM - Production Cluster Health & Diagnostics Monitor
# Usage: ./scripts/healthcheck.sh
# ==============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"
compose=(docker compose --env-file "$PROJECT_ROOT/.env.production" -f "$COMPOSE_FILE")

echo "=================================================================="
echo "🩺 EduSaaS CRM - Production Cluster Health Monitor"
echo "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%SZ")"
echo "=================================================================="

EXIT_CODE=0

# 1. Check Container States
echo "🐳 Checking Container States:"
"${compose[@]}" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" || EXIT_CODE=1
echo ""

# 2. Check Backend API Endpoint
echo "🌐 Checking API readiness (/api/v1/health/ready):"
if "${compose[@]}" exec -T backend curl --fail-with-body -sS --max-time 4 -H 'Host: backend' http://127.0.0.1:8000/api/v1/health/ready; then
    echo
    echo "✅ API Status: HEALTHY"
else
    echo
    echo "❌ API Status: DEGRADED"
    EXIT_CODE=1
fi
echo ""

# 3. Check PostgreSQL Latency
echo "🗄️ Checking PostgreSQL Connection & Query Latency:"
if "${compose[@]}" exec -T postgres sh -ec 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\timing on" -c "SELECT count(*) FROM tenants;"'; then
    echo "✅ Database: CONNECTED"
else
    echo "❌ Database: CONNECTION FAILED"
    EXIT_CODE=1
fi
echo ""

# 4. Check Redis Memory & PING
echo "⚡ Checking Redis Cache & Queue Broker:"
REDIS_PING=$("${compose[@]}" exec -T redis redis-cli ping 2>/dev/null || echo "FAILED")
if [ "$REDIS_PING" = "PONG" ]; then
    REDIS_MEM=$("${compose[@]}" exec -T redis redis-cli info memory 2>/dev/null | grep "used_memory_human:" | tr -d '\r')
    echo "✅ Redis Status: PONG ($REDIS_MEM)"
else
    echo "❌ Redis Status: UNREACHABLE"
    EXIT_CODE=1
fi
echo ""

# 5. Check Disk Space
echo "💾 Host Disk Space:"
df -h / | awk 'NR==1 || NR==2'
echo ""

# 6. Overall Summary
if [ "$EXIT_CODE" -eq 0 ]; then
    echo "=================================================================="
    echo "🟢 API, PostgreSQL, and Redis checks passed."
    echo "=================================================================="
else
    echo "=================================================================="
    echo "🔴 SYSTEM ALERT: One or more services are degraded or failing!"
    echo "=================================================================="
fi

exit $EXIT_CODE
