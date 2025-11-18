#!/bin/sh
# Certbot renewal hook to reload nginx after successful certificate renewal
# This script is executed by certbot after a successful renewal

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Certificate renewed successfully. Reloading nginx..."

# Method 1: Try using docker exec (requires docker socket mount)
if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q 'fonerwa-odoo-nginx'; then
    if docker exec fonerwa-odoo-nginx nginx -s reload 2>/dev/null; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ Nginx reloaded successfully via docker exec"
        exit 0
    fi
fi

# Method 2: Try using docker-compose (if available in container)
if command -v docker-compose >/dev/null 2>&1; then
    if docker-compose exec -T nginx nginx -s reload 2>/dev/null; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ Nginx reloaded successfully via docker-compose"
        exit 0
    fi
fi

# Method 3: Create a reload trigger file (nginx can watch this via a sidecar or cron)
# This is a fallback if docker commands aren't available
RELOAD_TRIGGER="/etc/letsencrypt/reload-nginx.trigger"
if touch "$RELOAD_TRIGGER" 2>/dev/null; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  Created reload trigger file. Nginx should be reloaded by monitoring script."
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  If no monitoring script exists, reload nginx manually: docker exec fonerwa-odoo-nginx nginx -s reload"
    exit 0
fi

# If all methods fail
echo "[$(date +'%Y-%m-%d %H:%M:%S')] ❌ ERROR: Could not reload nginx automatically."
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Please reload nginx manually: docker exec fonerwa-odoo-nginx nginx -s reload"
exit 1

