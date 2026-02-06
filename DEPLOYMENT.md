# AbsenzFlow Deployment Guide

This guide explains how to deploy AbsenzFlow securely in different environments.

## 📋 Table of Contents

- [Environment Overview](#environment-overview)
- [Development Setup](#development-setup)
- [Production Deployment](#production-deployment)
- [Security Checklist](#security-checklist)
- [Database Access](#database-access)
- [Troubleshooting](#troubleshooting)

---

## Environment Overview

AbsenzFlow provides two Docker Compose configurations:

| File | Purpose | Security Level | Use Case |
|------|---------|----------------|----------|
| `docker-compose.yml` | Development | ⚠️ Low | Local development with hot-reload |
| `docker-compose.prod.yml` | Production | ✅ High | Production deployment |

### Key Differences

| Feature | Development | Production |
|---------|-------------|------------|
| **Database Port** | ⚠️ Exposed (5432) | ✅ Not exposed |
| **Source Code** | ✅ Mounted (hot-reload) | ❌ Baked into image |
| **DEBUG Mode** | ✅ Enabled by default | ❌ Disabled by default |
| **Secrets** | ⚠️ Has defaults | ✅ Must be provided |
| **Uvicorn Workers** | 1 (--reload) | 4 (production) |
| **Restart Policy** | ❌ None | ✅ unless-stopped |
| **pgAdmin** | ✅ Always available | ❌ Profile-only |

---

## Development Setup

### Quick Start

```bash
# 1. Clone repository
git clone <repository-url>
cd AbsenzFlow

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env with your settings (optional for dev)
nano .env

# 4. Start development environment
docker-compose up -d

# 5. View logs
docker-compose logs -f backend

# 6. Access services
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - PostgreSQL: localhost:5432
# - pgAdmin: http://localhost:5050 (use docker-compose --profile dev up)
```

### Development Features

✅ **Hot-Reload**: Code changes automatically restart the backend
✅ **Direct DB Access**: Connect to PostgreSQL on `localhost:5432`
✅ **Debug Logging**: Detailed logs for troubleshooting
✅ **pgAdmin**: Database management UI available

### ⚠️ Development Security Warnings

The development environment has several intentional security weaknesses for convenience:

- **Database port exposed** - Anyone on your network can access the database
- **Default secrets allowed** - Will trigger validation error if you have the defaults
- **Debug mode** - Exposes detailed error messages
- **CORS permissive** - Allows localhost origins

**Never deploy the development configuration to production!**

---

## Production Deployment

### Prerequisites

Before deploying to production, ensure:

1. ✅ You have a valid `.env` file with secure secrets
2. ✅ WordPress is installed and AbsenzFlow plugin configured
3. ✅ WordPress Proxy Secret matches between WordPress Admin and `.env`
4. ✅ Database backups are configured
5. ✅ SSL/TLS certificates are ready (if using HTTPS)

### Step-by-Step Production Deployment

#### 1. Generate Secure Secrets

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate WORDPRESS_PROXY_SECRET
openssl rand -hex 32

# Generate secure database password
openssl rand -base64 32
```

#### 2. Configure Production .env

Create or update your `.env` file with production values:

```bash
# .env (PRODUCTION)

# === CRITICAL: Change These! ===
SECRET_KEY=<generated-secret-from-step-1>
WORDPRESS_PROXY_SECRET=<generated-secret-from-step-1>
POSTGRES_PASSWORD=<generated-password-from-step-1>

# === Application Settings ===
DEBUG=false
ENVIRONMENT=production
CORS_ORIGINS=https://your-production-domain.com
FRONTEND_URL=https://your-production-domain.com
API_URL=https://your-production-domain.com/api

# === Database ===
POSTGRES_DB=absenzflow
POSTGRES_USER=absenzflow
# POSTGRES_PASSWORD already set above

# === WordPress Integration ===
# WORDPRESS_PROXY_SECRET already set above

# === LDAP (if using standalone auth) ===
LDAP_SERVER=ldap.schule.local
LDAP_PORT=389
LDAP_BASE_DN=dc=schule,dc=local
LDAP_BIND_DN=cn=absenzflow,ou=services,dc=schule,dc=local
LDAP_BIND_PASSWORD=<ldap-password>

# === WebUntis API ===
WEBUNTIS_SCHOOL=<your-school-name>
WEBUNTIS_USERNAME=<webuntis-api-user>
WEBUNTIS_PASSWORD=<webuntis-api-password>
WEBUNTIS_SERVER=neilo.webuntis.com

# === SMTP ===
SMTP_HOST=smtp.schule.local
SMTP_PORT=587
SMTP_USERNAME=<smtp-user>
SMTP_PASSWORD=<smtp-password>
SMTP_FROM=absenzflow@schule.de
SMTP_USE_TLS=true

# === File Uploads ===
UPLOAD_DIR=/app/uploads
```

#### 3. Update WordPress Plugin Settings

In WordPress Admin → Settings → AbsenzFlow:

1. Set **Proxy Secret** to match `WORDPRESS_PROXY_SECRET` from `.env`
2. Set **Backend URL** to your backend API URL
3. Test the connection

#### 4. Deploy with Production Configuration

```bash
# 1. Navigate to project directory
cd AbsenzFlow

# 2. Build images (first time only)
docker-compose -f docker-compose.prod.yml build

# 3. Start services
docker-compose -f docker-compose.prod.yml up -d

# 4. Check logs
docker-compose -f docker-compose.prod.yml logs -f backend

# 5. Verify startup
# Look for: "✅ Security validation passed"
```

#### 5. Verify Production Deployment

```bash
# Test health check
curl http://localhost:8000/health

# Expected response: {"status":"ok"}

# Check backend logs for security validation
docker-compose -f docker-compose.prod.yml logs backend | grep "Security validation"

# Expected: "✅ Security validation passed - no default secrets detected"
```

---

## Security Checklist

Before going live, verify:

### ✅ Critical Security Items

- [ ] `SECRET_KEY` changed from default (min 32 chars)
- [ ] `WORDPRESS_PROXY_SECRET` changed from default
- [ ] `POSTGRES_PASSWORD` changed from default
- [ ] WordPress Admin secret matches `.env` secret
- [ ] `DEBUG=false` in `.env`
- [ ] `CORS_ORIGINS` set to production domain only
- [ ] Database port NOT exposed (using `docker-compose.prod.yml`)
- [ ] SSL/TLS enabled (reverse proxy)
- [ ] File upload directory has proper permissions

### ✅ Operational Items

- [ ] Database backups configured
- [ ] Log rotation configured
- [ ] Monitoring/alerting set up
- [ ] Firewall rules configured
- [ ] Container restart policies enabled
- [ ] Health checks configured

### ✅ WordPress Integration

- [ ] AbsenzFlow plugin activated
- [ ] Proxy secret configured in WordPress Admin
- [ ] Backend URL configured correctly
- [ ] User roles mapped correctly
- [ ] Test absence creation works

---

## Database Access

### Development (Direct Access)

```bash
# Connect via psql
psql -h localhost -U absenzflow -d absenzflow

# Or use pgAdmin
docker-compose --profile dev up -d pgadmin
# Visit http://localhost:5050
```

### Production (Secure Access)

**Option 1: Docker Exec (Recommended)**

```bash
# Access database via container
docker-compose -f docker-compose.prod.yml exec postgres psql -U absenzflow -d absenzflow

# Example: Run a query
docker-compose -f docker-compose.prod.yml exec postgres psql -U absenzflow -d absenzflow -c "SELECT COUNT(*) FROM absences;"
```

**Option 2: Emergency pgAdmin Access**

```bash
# Start pgAdmin with admin profile (emergency only)
docker-compose -f docker-compose.prod.yml --profile admin up -d pgadmin

# Access at http://localhost:5050 (localhost only!)

# When done, stop pgAdmin
docker-compose -f docker-compose.prod.yml stop pgadmin
```

**Option 3: SSH Port Forwarding**

```bash
# From your local machine, forward port through SSH
ssh -L 5432:localhost:5432 user@production-server

# Now connect to localhost:5432 from your machine
psql -h localhost -U absenzflow -d absenzflow
```

---

## Troubleshooting

### Backend Won't Start - Security Validation Error

**Problem:**
```
🚨 SECURITY CONFIGURATION ERROR - STARTUP ABORTED 🚨
❌ SECRET_KEY is still set to default value!
```

**Solution:**
1. Generate new secrets: `openssl rand -hex 32`
2. Update `.env` with generated secrets
3. Restart: `docker-compose -f docker-compose.prod.yml restart backend`

---

### Database Connection Failed

**Problem:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solutions:**

```bash
# 1. Check if postgres is healthy
docker-compose -f docker-compose.prod.yml ps postgres

# 2. Check postgres logs
docker-compose -f docker-compose.prod.yml logs postgres

# 3. Verify DATABASE_URL in backend
docker-compose -f docker-compose.prod.yml exec backend env | grep DATABASE_URL

# 4. Test connection manually
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U absenzflow
```

---

### WordPress Can't Connect to Backend

**Problem:** WordPress shows "Invalid proxy secret" or connection errors.

**Solutions:**

```bash
# 1. Verify backend is running
curl http://localhost:8000/health

# 2. Check WORDPRESS_PROXY_SECRET matches
# In backend:
docker-compose -f docker-compose.prod.yml exec backend env | grep WORDPRESS_PROXY_SECRET

# In WordPress:
# Admin → Settings → AbsenzFlow → Proxy Secret

# 3. Check backend logs for auth errors
docker-compose -f docker-compose.prod.yml logs backend | grep -i "proxy\|auth"
```

---

### High Memory Usage

**Problem:** Containers using excessive memory.

**Solutions:**

```bash
# 1. Check resource usage
docker stats

# 2. Restart backend (clears caches)
docker-compose -f docker-compose.prod.yml restart backend

# 3. Adjust worker count (in docker-compose.prod.yml)
# Change: --workers 4 to --workers 2

# 4. Add resource limits (in docker-compose.prod.yml)
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 512M
```

---

## Useful Commands

### Development

```bash
# Start development environment
docker-compose up -d

# View logs (all services)
docker-compose logs -f

# View logs (backend only)
docker-compose logs -f backend

# Restart after code changes (if hot-reload fails)
docker-compose restart backend

# Stop all services
docker-compose down

# Reset database (⚠️ DATA LOSS!)
docker-compose down -v
docker-compose up -d
```

### Production

```bash
# Start production environment
docker-compose -f docker-compose.prod.yml up -d

# Update after code changes
docker-compose -f docker-compose.prod.yml build backend
docker-compose -f docker-compose.prod.yml up -d backend

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Stop all services
docker-compose -f docker-compose.prod.yml down

# Backup database
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U absenzflow absenzflow > backup_$(date +%Y%m%d).sql

# Restore database
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U absenzflow absenzflow < backup.sql
```

---

## Next Steps

After successful deployment:

1. ✅ Configure regular database backups
2. ✅ Set up log monitoring and alerting
3. ✅ Configure reverse proxy (Nginx/Caddy) with SSL
4. ✅ Set up firewall rules
5. ✅ Document your production environment
6. ✅ Train users on the system

---

**Last Updated:** 2026-02-06
**Maintainer:** AbsenzFlow Team
**Questions?** See [CLAUDE.md](CLAUDE.md) for development documentation
