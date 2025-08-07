#!/bin/bash

# Generate SSL certificates for development
# For production, replace with real certificates from a CA

DOMAIN="odoo.greenfund.rw"
SSL_DIR="$(dirname "$0")/../nginx/ssl"

echo "Generating SSL certificates for $DOMAIN..."

# Create SSL directory if it doesn't exist
mkdir -p "$SSL_DIR"

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_DIR/odoo.key" \
    -out "$SSL_DIR/odoo.crt" \
    -subj "/C=RW/ST=Kigali/L=Kigali/O=Green Fund/CN=$DOMAIN" \
    -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost,DNS:*.greenfund.rw,IP:127.0.0.1"

# Set proper permissions
chmod 600 "$SSL_DIR/odoo.key"
chmod 644 "$SSL_DIR/odoo.crt"

echo "SSL certificates generated successfully!"
echo "Certificate: $SSL_DIR/odoo.crt"
echo "Private key: $SSL_DIR/odoo.key"
echo ""
echo "For local testing, add this line to your /etc/hosts file:"
echo "127.0.0.1 odoo.greenfund.rw"