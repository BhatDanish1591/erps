#!/usr/bin/env bash
# ==============================================================================
# EduSaaS CRM - Production Automated Deployment Script (Ubuntu / Linux)
# Usage: ./scripts/deploy.sh [BRANCH_NAME]
# ==============================================================================

set -eo pipefail

BRANCH="${1:-main}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"
compose=(docker compose --env-file "$PROJECT_ROOT/.env.production" -f "$COMPOSE_FILE")

echo "=================================================================="
echo "🚀 Starting EduSaaS CRM Production Deployment"
echo "Target Branch: $BRANCH"
echo "Timestamp:     $(date -u +"%Y-%m-%d %H:%M:%SZ")"
echo "=================================================================="

cd "$PROJECT_ROOT"

# 1. Pre-flight Checks
if [ ! -f "$PROJECT_ROOT/.env.production" ]; then
    echo "❌ ERROR: Root production environment file .env.production not found!"
    exit 1
fi

if [ ! -f "$PROJECT_ROOT/backend/.env.production" ]; then
    echo "❌ ERROR: Backend production environment file backend/.env.production not found!"
    exit 1
fi

# 2. Pull Latest Git Commits
echo "📥 Pulling latest code changes from origin/$BRANCH..."
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull origin "$BRANCH"

# 3. Pull Base Images and Build Containers
echo "🔨 Building production Docker images..."
"${compose[@]}" build --pull backend celery_worker celery_beat web

# 4. Start Core Database and Cache Services
echo "🗄️ Ensuring PostgreSQL and Redis are healthy..."
"${compose[@]}" up -d --wait --wait-timeout 120 postgres redis

# 5. Run Database Migrations
echo "📦 Running database migrations via Alembic..."
"${compose[@]}" exec -T postgres sh -ec 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /opt/edusaas/provision-app-role.sql'
"${compose[@]}" run --rm --no-deps migrate

# 6. Deploy / Restart Application Cluster with Minimal Downtime
echo "🔄 Rolling out backend, workers, and frontend..."
"${compose[@]}" up -d --remove-orphans backend celery_worker celery_beat web nginx backup certbot

# 7. Post-Deployment Verification Health Check
echo "🩺 Verifying application cluster health..."
RETRIES=12
WAIT_SECONDS=5
HEALTHY=false

for i in $(seq 1 $RETRIES); do
    if "${compose[@]}" exec -T backend curl -fsS --max-time 4 -o /dev/null -H 'Host: backend' http://127.0.0.1:8000/api/v1/health/ready; then
        echo "✅ Readiness check passed on attempt $i/$RETRIES."
        HEALTHY=true
        break
    else
        echo "⏳ Attempt $i/$RETRIES: Backend is unavailable or not ready. Retrying in ${WAIT_SECONDS}s..."
        sleep $WAIT_SECONDS
    fi
done

if [ "$HEALTHY" = false ]; then
    echo "❌ CRITICAL: Deployment health check FAILED after $RETRIES attempts!"
    echo "Printing last 50 lines of backend logs:"
    "${compose[@]}" logs --tail=50 backend
    exit 1
fi

# 8. Clean up unused images
echo "🧹 Pruning old Docker images..."
docker image prune -f

echo "=================================================================="
echo "🎉 EduSaaS CRM Production Deployment Successfully Completed!"
echo "Cluster Status:"
"${compose[@]}" ps
echo "=================================================================="
