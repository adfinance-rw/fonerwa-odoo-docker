#!/bin/bash

# Production deployment script for Fonerwa Odoo
# Usage: ./scripts/deploy.sh [environment]

set -e

ENVIRONMENT=${1:-production}
# Domain and email for Let's Encrypt
DOMAIN=${DOMAIN:-odoo.greenfund.rw}
CERTBOT_EMAIL=${CERTBOT_EMAIL:-}
# If set to 1, use Let's Encrypt staging to avoid rate limits
CERTBOT_STAGING=${CERTBOT_STAGING:-0}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting Fonerwa Odoo deployment for $ENVIRONMENT environment..."

# Check if running as root (not recommended for production)
if [[ $EUID -eq 0 ]]; then
   echo "⚠️  Warning: Running as root is not recommended for production deployments"
   read -p "Continue anyway? (y/N): " -n 1 -r
   echo
   if [[ ! $REPLY =~ ^[Yy]$ ]]; then
       exit 1
   fi
fi

# Check required files
echo "📋 Checking required files..."
required_files=(
    "docker-compose.yml"
    "config/odoo.conf"
    "nginx/conf.d/odoo.conf"
    "requirements.txt"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$PROJECT_DIR/$file" ]]; then
        echo "❌ Required file missing: $file"
        exit 1
    fi
done

# Prepare Let's Encrypt directories and dummy cert so Nginx can start
echo "🔒 Preparing Let's Encrypt directories and bootstrap cert..."
mkdir -p "$PROJECT_DIR/certbot/www" "$PROJECT_DIR/certbot/conf/live/$DOMAIN"
if [[ ! -f "$PROJECT_DIR/certbot/conf/live/$DOMAIN/fullchain.pem" ]] || [[ ! -f "$PROJECT_DIR/certbot/conf/live/$DOMAIN/privkey.pem" ]]; then
    echo "⚠️  No existing certs for $DOMAIN. Creating temporary self-signed cert..."
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
        -keyout "$PROJECT_DIR/certbot/conf/live/$DOMAIN/privkey.pem" \
        -out "$PROJECT_DIR/certbot/conf/live/$DOMAIN/fullchain.pem" \
        -subj "/CN=$DOMAIN" \
        2>/dev/null
    chmod 600 "$PROJECT_DIR/certbot/conf/live/$DOMAIN/privkey.pem" || true
    chmod 644 "$PROJECT_DIR/certbot/conf/live/$DOMAIN/fullchain.pem" || true
    echo "✅ Temporary cert created"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p "$PROJECT_DIR/logs/nginx"
mkdir -p "$PROJECT_DIR/logs/odoo"
mkdir -p "$PROJECT_DIR/backups"

# Set proper permissions
echo "🔐 Setting file permissions..."
chmod +x "$PROJECT_DIR/scripts/"*.sh 2>/dev/null || true

# Pull latest images
echo "📥 Pulling latest Docker images..."
cd "$PROJECT_DIR"
docker-compose pull

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down --remove-orphans

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Health check
echo "🏥 Performing health checks..."
max_attempts=30
attempt=1

while [[ $attempt -le $max_attempts ]]; do
    echo "Attempt $attempt/$max_attempts..."
    
    # Check Nginx
    if curl -f -s http://localhost/nginx-health > /dev/null; then
        echo "✅ Nginx is healthy"
        nginx_healthy=true
        break
    else
        echo "❌ Nginx health check failed"
        nginx_healthy=false
    fi
    
    sleep 10
    ((attempt++))
done

if [[ "$nginx_healthy" != true ]]; then
    echo "❌ Nginx failed to start properly"
    docker-compose logs nginx
    exit 1
fi

# Obtain/renew real Let's Encrypt certificate if needed
echo "🔐 Ensuring real Let's Encrypt certificate for $DOMAIN..."
LE_LIVE_DIR="$PROJECT_DIR/certbot/conf/live/$DOMAIN"
if [[ ! -f "$LE_LIVE_DIR/cert.pem" ]] || [[ ! -f "$LE_LIVE_DIR/chain.pem" ]]; then
    echo "📥 Requesting certificate from Let's Encrypt..."
    if [[ -n "$CERTBOT_EMAIL" ]]; then
        EMAIL_ARGS="--email $CERTBOT_EMAIL --agree-tos"
    else
        EMAIL_ARGS="--register-unsafely-without-email --agree-tos"
        echo "⚠️  CERTBOT_EMAIL not set. Proceeding without email registration."
    fi
    if [[ "$CERTBOT_STAGING" == "1" ]]; then
        STAGING_FLAG="--staging"
        echo "ℹ️  Using Let's Encrypt staging environment"
    else
        STAGING_FLAG=""
    fi
    docker-compose run --rm --entrypoint "" certbot certbot certonly --webroot -w /var/www/certbot -d "$DOMAIN" $EMAIL_ARGS --no-eff-email $STAGING_FLAG || true
    echo "🔁 Reloading Nginx to pick up certificates..."
    docker-compose exec -T nginx nginx -s reload || true
fi

# Show service status
echo "📊 Service status:"
docker-compose ps

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📝 Next steps:"
echo "  1. Access your Odoo instance at: https://$DOMAIN"
echo "  2. If you need a different domain, set DOMAIN env var and re-run"
echo "  3. Set CERTBOT_EMAIL env var for certificate registration"
echo "  4. Update passwords and security settings"
echo "  5. Configure monitoring and backup solutions"
echo ""
echo "📚 Documentation: See README.md for more information"