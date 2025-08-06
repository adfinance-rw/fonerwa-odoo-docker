#!/bin/bash

# Production deployment script for Fonerwa Odoo
# Usage: ./scripts/deploy.sh [environment]

set -e

ENVIRONMENT=${1:-production}
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

# Check SSL certificates
echo "🔒 Checking SSL certificates..."
if [[ ! -f "$PROJECT_DIR/nginx/ssl/odoo.crt" ]] || [[ ! -f "$PROJECT_DIR/nginx/ssl/odoo.key" ]]; then
    echo "⚠️  SSL certificates not found. Generating self-signed certificates..."
    mkdir -p "$PROJECT_DIR/nginx/ssl"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$PROJECT_DIR/nginx/ssl/odoo.key" \
        -out "$PROJECT_DIR/nginx/ssl/odoo.crt" \
        -subj "/C=US/ST=State/L=City/O=Fonerwa/CN=localhost" \
        2>/dev/null
    
    # Set proper permissions
    chmod 600 "$PROJECT_DIR/nginx/ssl/odoo.key"
    chmod 644 "$PROJECT_DIR/nginx/ssl/odoo.crt"
    echo "✅ Self-signed certificates generated"
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

# Show service status
echo "📊 Service status:"
docker-compose ps

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📝 Next steps:"
echo "  1. Access your Odoo instance at: https://localhost"
echo "  2. Configure your domain name in the Nginx configuration"
echo "  3. Replace self-signed certificates with proper SSL certificates"
echo "  4. Update passwords and security settings"
echo "  5. Configure monitoring and backup solutions"
echo ""
echo "📚 Documentation: See README.md for more information"