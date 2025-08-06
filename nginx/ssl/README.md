# SSL Certificates

Place your SSL certificates in this directory:

- `odoo.crt` - SSL certificate file
- `odoo.key` - SSL private key file

## Self-signed certificate for development

To generate a self-signed certificate for testing purposes:

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout odoo.key \
    -out odoo.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

## Production certificates

For production, use certificates from a trusted Certificate Authority (CA) like:
- Let's Encrypt (free)
- DigiCert
- GlobalSign
- Comodo

Make sure to set proper file permissions:
```bash
chmod 600 odoo.key
chmod 644 odoo.crt
```