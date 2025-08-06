#!/bin/bash

# Backup script for Fonerwa Odoo production environment
# Usage: ./scripts/backup.sh [database_name]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
DATE=$(date +"%Y%m%d_%H%M%S")
DB_NAME=${1:-""}

echo "💾 Starting Fonerwa Odoo backup process..."

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Source database configuration
source "$PROJECT_DIR/.env" 2>/dev/null || true

# Use environment variables or defaults
DB_HOST=${DB_HOST:-"10.10.77.148"}
DB_PORT=${DB_PORT:-"5432"}
DB_USER=${DB_USER:-"postgres"}

if [[ -z "$DB_NAME" ]]; then
    echo "📋 Available databases:"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -l
    echo ""
    read -p "Enter database name to backup: " DB_NAME
fi

if [[ -z "$DB_NAME" ]]; then
    echo "❌ Database name is required"
    exit 1
fi

BACKUP_FILE="$BACKUP_DIR/odoo_backup_${DB_NAME}_$DATE.sql"
FILESTORE_BACKUP="$BACKUP_DIR/odoo_filestore_${DB_NAME}_$DATE.tar.gz"

echo "🗄️  Backing up database: $DB_NAME"
echo "📂 Backup location: $BACKUP_FILE"

# Database backup
echo "💾 Creating database backup..."
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-privileges \
    --format=plain \
    --file="$BACKUP_FILE"

if [[ $? -eq 0 ]]; then
    echo "✅ Database backup completed: $BACKUP_FILE"
    
    # Compress the backup
    gzip "$BACKUP_FILE"
    echo "🗜️  Backup compressed: ${BACKUP_FILE}.gz"
else
    echo "❌ Database backup failed"
    exit 1
fi

# Filestore backup
echo "📁 Creating filestore backup..."
if docker-compose ps web | grep -q "Up"; then
    docker-compose exec web tar -czf "/tmp/filestore_backup.tar.gz" -C /var/lib/odoo/filestore . 2>/dev/null || true
    docker cp "$(docker-compose ps -q web):/tmp/filestore_backup.tar.gz" "$FILESTORE_BACKUP" 2>/dev/null || true
    docker-compose exec web rm -f "/tmp/filestore_backup.tar.gz" 2>/dev/null || true
    
    if [[ -f "$FILESTORE_BACKUP" ]]; then
        echo "✅ Filestore backup completed: $FILESTORE_BACKUP"
    else
        echo "⚠️  Filestore backup skipped (no filestore found or service not running)"
    fi
else
    echo "⚠️  Filestore backup skipped (Odoo service not running)"
fi

# Cleanup old backups (keep last 7 days)
echo "🧹 Cleaning up old backups..."
find "$BACKUP_DIR" -name "odoo_backup_*.sql.gz" -mtime +7 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "odoo_filestore_*.tar.gz" -mtime +7 -delete 2>/dev/null || true

echo ""
echo "🎉 Backup process completed successfully!"
echo "📊 Backup summary:"
echo "  - Database: ${BACKUP_FILE}.gz"
[[ -f "$FILESTORE_BACKUP" ]] && echo "  - Filestore: $FILESTORE_BACKUP"
echo "  - Date: $(date)"
echo ""