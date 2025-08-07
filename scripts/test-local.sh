#!/bin/bash

echo "🚀 Starting Fonerwa Odoo with domain configuration..."
echo "Domain: odoo.greenfund.rw"
echo "Local access: https://odoo.greenfund.rw"
echo ""

# Start the services
docker-compose up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

echo ""
echo "🔍 Checking service status..."
docker-compose ps

echo ""
echo "📋 Service logs (last 10 lines):"
echo "--- Nginx logs ---"
docker-compose logs --tail=10 nginx

echo ""
echo "--- Odoo logs ---"
docker-compose logs --tail=10 web

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Access your Odoo instance at:"
echo "   - https://odoo.greenfund.rw (recommended)"
echo "   - https://localhost"
echo "   - http://odoo.greenfund.rw (redirects to HTTPS)"
echo ""
echo "💡 To check if domain is working:"
echo "   curl -I https://odoo.greenfund.rw"
echo ""
echo "🛑 To stop services:"
echo "   docker-compose down"