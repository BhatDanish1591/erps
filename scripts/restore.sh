#!/usr/bin/env bash
# ==============================================================================
# EduSaaS CRM - Production Disaster Recovery & Restoration Script
# Usage: ./scripts/restore.sh /path/to/edusaas_db_YYYYMMDD_HHMMSS.dump
# ==============================================================================

set -eo pipefail

DUMP_FILE="$1"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"
compose=(docker compose --env-file "$PROJECT_ROOT/.env.production" -f "$COMPOSE_FILE")

if [ -z "$DUMP_FILE" ] || [ ! -f "$DUMP_FILE" ]; then
    echo "❌ Usage: $0 <path_to_database_dump_file>"
    exit 1
fi

echo "=================================================================="
echo "⚠️  CRITICAL: EDUSAAS CRM PRODUCTION RESTORATION"
echo "Target Dump File: $DUMP_FILE"
TARGET_DB=$("${compose[@]}" exec -T postgres printenv POSTGRES_DB)
echo "Target Database:  $TARGET_DB"
echo "=================================================================="

# 1. Verify SHA-256 Checksum if present
if [ -f "${DUMP_FILE}.sha256" ]; then
    echo "🔒 Verifying SHA-256 checksum..."
    sha256sum --check "${DUMP_FILE}.sha256"
    echo "✅ Checksum verified successfully."
fi

# 2. Strict Confirmation Prompt
read -r -p "🚨 WARNING: This will completely overwrite existing production data! Type 'CONFIRM_RESTORE' to continue: " CONFIRM
if [ "$CONFIRM" != "CONFIRM_RESTORE" ]; then
    echo "❌ Restoration aborted by user."
    exit 1
fi

# 3. Terminate Active Connections
echo "🔌 Terminating active database connections..."
"${compose[@]}" exec -T postgres sh -ec \
    'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid();"'

# 4. Perform PostgreSQL Restore
echo "🗄️ Restoring database from custom dump..."
"${compose[@]}" exec -T postgres sh -ec \
    'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges --single-transaction' < "$DUMP_FILE"

# 5. Ensure Schema is Synchronized
echo "📦 Running Alembic schema verification..."
"${compose[@]}" run --rm --no-deps migrate
"${compose[@]}" exec -T postgres sh -ec 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /opt/edusaas/provision-app-role.sql'

# 6. Restart Application Workers and Backend
echo "🔄 Restarting backend cluster to reload active caches..."
"${compose[@]}" restart backend celery_worker celery_beat

# 7. Verification Health Check
echo "🩺 Running health check..."
sleep 5
"${compose[@]}" exec -T backend curl -fsS --max-time 4 -H 'Host: backend' http://127.0.0.1:8000/api/v1/health/ready || {
    echo "❌ ERROR: Health check failed after restore!"
    exit 1
}

echo "=================================================================="
echo "🎉 Restoration completed successfully! System is healthy and online."
echo "=================================================================="
