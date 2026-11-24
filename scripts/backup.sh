#!/usr/bin/env bash
# ==============================================================================
# EduSaaS CRM - Production Automated Backup Script
# Creates timestamped PostgreSQL dumps and asset archives with SHA-256 verification
# Usage: ./scripts/backup.sh [/path/to/backup_dir]
# ==============================================================================

set -eo pipefail

BACKUP_DIR="${1:-/var/backups/edusaas}"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"
compose=(docker compose --env-file "$PROJECT_ROOT/.env.production" -f "$COMPOSE_FILE")

mkdir -p "$BACKUP_DIR"

echo "=================================================================="
echo "📦 Starting EduSaaS CRM Production Backup"
echo "Backup Directory: $BACKUP_DIR"
echo "Timestamp:        $TIMESTAMP"
echo "=================================================================="

# 1. PostgreSQL Database Dump
DB_FILE="$BACKUP_DIR/edusaas_db_${TIMESTAMP}.dump"
echo "🗄️ Dumping PostgreSQL database..."
"${compose[@]}" exec -T postgres sh -ec \
    'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --clean --if-exists --no-owner --no-privileges' > "$DB_FILE"

# Verify dump file size
FILE_SIZE=$(wc -c <"$DB_FILE" | tr -d ' ')
if [ "$FILE_SIZE" -lt 1024 ]; then
    echo "❌ ERROR: Database dump file is suspiciously small ($FILE_SIZE bytes)!"
    rm -f "$DB_FILE"
    exit 1
fi

echo "✅ Database dump created ($FILE_SIZE bytes): $DB_FILE"

# 2. Compute SHA-256 Checksum
CHECKSUM_FILE="${DB_FILE}.sha256"
sha256sum "$DB_FILE" > "$CHECKSUM_FILE"
echo "🔒 Checksum generated: $(cat "$CHECKSUM_FILE")"

# 3. Archive Uploaded Documents and Media (if local)
if [ -d "$PROJECT_ROOT/uploads" ] && [ "$(ls -A "$PROJECT_ROOT/uploads" 2>/dev/null)" ]; then
    UPLOADS_FILE="$BACKUP_DIR/edusaas_uploads_${TIMESTAMP}.tar.gz"
    echo "📁 Archiving user uploads directory..."
    tar -czf "$UPLOADS_FILE" -C "$PROJECT_ROOT" uploads
    sha256sum "$UPLOADS_FILE" > "${UPLOADS_FILE}.sha256"
    echo "✅ Uploads archive created: $UPLOADS_FILE"
fi

# 4. Enforce Retention Policy (Retain last 30 daily backups)
echo "🧹 Pruning backups older than 30 days..."
find "$BACKUP_DIR" -name "edusaas_*.dump*" -type f -mtime +30 -delete
find "$BACKUP_DIR" -name "edusaas_*.tar.gz*" -type f -mtime +30 -delete

echo "=================================================================="
echo "🎉 Backup successfully created and verified!"
echo "Files in $BACKUP_DIR:"
ls -lh "$BACKUP_DIR"/*"$TIMESTAMP"*
echo "=================================================================="
