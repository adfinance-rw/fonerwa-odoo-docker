#!/bin/sh
# Custom entrypoint for certbot container
# Installs docker CLI if needed and runs certbot renewal loop

# Install docker CLI if not available (certbot image is Debian-based)
if ! command -v docker >/dev/null 2>&1; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Installing docker CLI..."
    # Try to install docker CLI (requires root, which certbot container should have)
    if [ "$(id -u)" = "0" ]; then
        apt-get update -qq >/dev/null 2>&1 && \
        (apt-get install -y -qq docker.io >/dev/null 2>&1 || \
         apt-get install -y -qq docker-ce-cli >/dev/null 2>&1 || \
         echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  Warning: Could not install docker CLI. Will use fallback method for nginx reload.") || true
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  Warning: Not running as root. Cannot install docker CLI. Will use fallback method."
    fi
fi

# Verify docker socket is accessible
if [ -S /var/run/docker.sock ] && command -v docker >/dev/null 2>&1; then
    if docker ps >/dev/null 2>&1; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ Docker CLI is available and socket is accessible"
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  Warning: Docker CLI available but socket not accessible. Will use fallback method."
    fi
else
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  Warning: Docker CLI or socket not available. Will use fallback method for nginx reload."
fi

# Verify renewal hook exists and is executable
if [ -f /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh ]; then
    if [ -x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh ]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ Renewal hook script is ready"
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  Warning: Renewal hook script is not executable"
    fi
else
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  Warning: Renewal hook script not found"
fi

# Renewal loop
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting certbot renewal loop (checks every 12 hours)..."
trap 'echo "Received TERM signal, exiting..."; exit 0' TERM

while :; do
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Checking for certificate renewal..."
    certbot renew \
        --webroot \
        -w /var/www/certbot \
        --deploy-hook '/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh' \
        --quiet
    
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Renewal check completed. Next check in 12 hours..."
    sleep 12h
done

