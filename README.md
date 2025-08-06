# Fonerwa Odoo Production Environment

A production-ready Docker setup for Fonerwa Odoo 18.0 with Nginx reverse proxy, SSL termination, and comprehensive security configurations.

## 🏗️ Architecture

- **Odoo 18.0**: Main application server with optimized production settings
- **Nginx**: Reverse proxy with SSL termination, compression, and security headers
- **External PostgreSQL**: Uses existing database configuration from `config/odoo.conf`
- **Production optimizations**: Multi-worker setup, caching, logging, and monitoring

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- External PostgreSQL database (configured in `config/odoo.conf`)
- Domain name (for production SSL certificates)

## 🚀 Quick Start

1. **Clone and prepare the environment:**
   ```bash
   git clone <repository-url>
   cd fonerwa-odoo-docker
   ```

2. **Configure your database settings:**
   Edit `config/odoo.conf` with your database credentials:
   ```ini
   db_host = your-db-host
   db_user = your-db-user
   db_password = your-db-password
   ```

3. **Set up SSL certificates:**
   ```bash
   # For development (self-signed)
   ./scripts/deploy.sh
   
   # For production, place your certificates:
   cp your-certificate.crt nginx/ssl/odoo.crt
   cp your-private-key.key nginx/ssl/odoo.key
   ```

4. **Deploy the application:**
   ```bash
   ./scripts/deploy.sh production
   ```

5. **Access your Odoo instance:**
   - HTTP: `http://localhost` (redirects to HTTPS)
   - HTTPS: `https://localhost`

## 📁 Project Structure

```
fonerwa-odoo-docker/
├── config/
│   └── odoo.conf              # Odoo configuration with production settings
├── nginx/
│   ├── conf.d/
│   │   └── odoo.conf          # Nginx reverse proxy configuration
│   └── ssl/                   # SSL certificates directory
├── scripts/
│   ├── deploy.sh              # Production deployment script
│   └── backup.sh              # Database and filestore backup script
├── logs/                      # Application and web server logs
├── addons/                    # Third-party Odoo addons
├── custom_addons/             # Custom Odoo addons
├── requirements.txt           # Python dependencies
├── docker-compose.yml         # Docker services configuration
└── .dockerignore             # Docker build exclusions
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Key configurations:
- `DB_HOST`: PostgreSQL server hostname
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password
- `ODOO_ADMIN_PASSWORD`: Odoo master password
- `WORKERS`: Number of Odoo worker processes

### Odoo Configuration

The `config/odoo.conf` file includes production-optimized settings:

- **Multi-worker configuration**: 4 workers for better performance
- **Memory limits**: Optimized for production workloads
- **Security settings**: Database listing disabled, proxy mode enabled
- **Logging**: Structured logging with rotation
- **Session management**: Optimized for production

### Nginx Configuration

The Nginx setup provides:

- **SSL/TLS termination** with modern cipher suites
- **HTTP/2 support** for improved performance
- **Security headers** (HSTS, CSP, X-Frame-Options, etc.)
- **Gzip compression** for static assets
- **Load balancing** and health checks
- **WebSocket support** for Odoo's longpolling

## 🛠️ Management Commands

### Deployment
```bash
# Deploy to production
./scripts/deploy.sh production

# Deploy to staging
./scripts/deploy.sh staging
```

### Backup
```bash
# Backup specific database
./scripts/backup.sh your-database-name

# Interactive backup (prompts for database)
./scripts/backup.sh
```

### Service Management
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f web
docker-compose logs -f nginx

# Restart Odoo only
docker-compose restart web

# Update images and restart
docker-compose pull && docker-compose up -d
```

## 🔒 Security Considerations

### SSL/TLS
- Use proper SSL certificates from a trusted CA for production
- Configure your domain name in the Nginx configuration
- Consider using Let's Encrypt for free SSL certificates

### Database Security
- Use a dedicated database user with minimal privileges
- Ensure database server is properly secured and patched
- Use strong passwords and consider certificate-based authentication

### Application Security
- Change default admin password in `odoo.conf`
- Disable database listing (`list_db = False`)
- Enable proxy mode for proper IP forwarding
- Regular security updates for Docker images

### Network Security
- Use Docker networks for service isolation
- Configure firewall rules appropriately
- Consider using a VPN for database access

## 📊 Monitoring and Logging

### Logs Location
- **Odoo logs**: `logs/odoo/odoo.log`
- **Nginx access logs**: `logs/nginx/odoo_access.log`
- **Nginx error logs**: `logs/nginx/odoo_error.log`

### Health Checks
- **Odoo health**: `https://your-domain/web/health`
- **Nginx health**: `https://your-domain/nginx-health`

### Performance Monitoring
Consider integrating with monitoring solutions:
- Prometheus + Grafana
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Sentry for error tracking

## 🔄 Backup and Recovery

### Automated Backups
```bash
# Setup daily backups with cron
0 2 * * * /path/to/fonerwa-odoo-docker/scripts/backup.sh your-database-name
```

### Restore Procedure
```bash
# Restore database
PGPASSWORD="password" psql -h db-host -U db-user -d database-name < backup.sql

# Restore filestore
tar -xzf filestore_backup.tar.gz -C /var/lib/odoo/filestore/
```

## 🚀 Production Deployment Checklist

- [ ] Configure proper SSL certificates
- [ ] Update domain name in Nginx configuration
- [ ] Change default passwords
- [ ] Configure database backups
- [ ] Set up monitoring and alerting
- [ ] Configure log rotation
- [ ] Review and update security settings
- [ ] Test disaster recovery procedures
- [ ] Document operational procedures

## 🐛 Troubleshooting

### Common Issues

1. **SSL Certificate Errors**
   ```bash
   # Check certificate validity
   openssl x509 -in nginx/ssl/odoo.crt -text -noout
   ```

2. **Database Connection Issues**
   ```bash
   # Test database connectivity
   docker-compose exec web python3 -c "import psycopg2; print('DB connection OK')"
   ```

3. **Service Health Checks**
   ```bash
   # Check all services
   docker-compose ps
   
   # View specific service logs
   docker-compose logs -f web
   ```

## 📞 Support

For issues specific to this deployment setup, please check:
1. Docker and Docker Compose logs
2. Odoo application logs in `logs/odoo/`
3. Nginx logs in `logs/nginx/`

For Odoo-specific issues, consult the [official Odoo documentation](https://www.odoo.com/documentation/).
Green Fund Odoo docker repository
