# VertretungsFlow Deployment-Anleitung

Diese Anleitung erklärt, wie man VertretungsFlow sicher in verschiedenen Umgebungen bereitstellt.

## 📋 Inhaltsverzeichnis

- [Umgebungsübersicht](#umgebungsübersicht)
- [Production-Deployment](#production-deployment)
- [Sicherheits-Checkliste](#sicherheits-checkliste)
- [Development-Setup](#development-setup)
- [Datenbankzugriff](#datenbankzugriff)
- [Troubleshooting](#troubleshooting)

---

## Umgebungsübersicht

VertretungsFlow bietet zwei Docker-Compose-Konfigurationen:

| Datei | Zweck | Sicherheit | Use Case |
|------|---------|----------------|----------|
| `docker-compose.yml` | Development | ⚠️ Niedrig | Lokale Entwicklung mit Hot-Reload |
| `docker-compose.prod.yml` | Production | ✅ Hoch | Produktives Deployment |

### Wichtigste Unterschiede

| Feature | Development | Production |
|---------|-------------|------------|
| **Datenbank-Port** | ⚠️ Exposed (5432) | ✅ Nicht exposed |
| **Quellcode** | ✅ Mounted (Hot-Reload) | ❌ In Image eingebunden |
| **DEBUG Mode** | ✅ Standardmäßig aktiviert | ❌ Standardmäßig deaktiviert |
| **Secrets** | ⚠️ Hat Defaults | ✅ Müssen gesetzt werden |
| **Uvicorn Worker** | 1 (--reload) | 4 (production) |
| **Restart Policy** | ❌ Keine | ✅ unless-stopped |
| **pgAdmin** | ✅ Immer verfügbar | ❌ Nur mit Profil |

---

## Production-Deployment

### Voraussetzungen

Vor dem Deployment in Production sicherstellen:

1. ✅ Gültige `.env` Datei mit sicheren Secrets vorhanden
2. ✅ WordPress installiert und VertretungsFlow-Plugin konfiguriert
3. ✅ WordPress Proxy Secret stimmt zwischen WordPress Admin und `.env` überein
4. ✅ Datenbank-Backups konfiguriert
5. ✅ SSL/TLS-Zertifikate vorhanden (falls HTTPS verwendet)

Wir nehmen an, das Frontend, auf dem Wordpress läuft, ist erreichbar unter https://your-production-domain.com und das Backend ist vom Frontend-Server aus erreichbar über https://backend.local.

### Schritt-für-Schritt Production-Deployment

#### 1. Repository klonen:
```bash
git clone https://github.com/your-org/absenzflow.git
cd absenzflow
```

#### 2. Umgebungsvariablen-Datei aus Vorlage erstellen:
```bash
cp .env.example .env
```

#### 3. Sichere Secrets generieren

```bash
# SECRET_KEY generieren
openssl rand -hex 32

# WORDPRESS_PROXY_SECRET generieren
openssl rand -hex 32

# Sicheres Datenbankpasswort generieren
openssl rand -base64 32
```

#### 4. Production .env konfigurieren

`.env` Datei mit Production-Werten erstellen oder aktualisieren:

```bash
nano .env
# .env (PRODUCTION)

# === KRITISCH: Diese ändern! ===
SECRET_KEY=<SECRET_KEY aus Schritt 1>
WORDPRESS_PROXY_SECRET=<WORDPRESS_PROXY_SECRET aus Schritt 1>
POSTGRES_PASSWORD=<Datenbankpasswort aus Schritt 1>

# === Anwendungseinstellungen ===
DEBUG=false
ENVIRONMENT=production
CORS_ORIGINS=https://your-production-domain.com
FRONTEND_URL=https://your-production-domain.com/absenzflow
# FRONTEND_URL zeigt auf die Seite, wo der [vertretungsflow]-Shortcode platziert wurde.
# In den E-Mails des Systems werden hier noch Parameter angehängt, um direkt zu einer
# Abwesenheit zu springen.

# === Datenbank ===
POSTGRES_DB=absenzflow
POSTGRES_USER=absenzflow
# POSTGRES_PASSWORD bereits gesetzt

# === WordPress-Integration ===
# WORDPRESS_PROXY_SECRET bereits gesetzt

# === LDAP (bei Standalone-Auth, kann bei Wordpress-Setup leer bleiben) ===
LDAP_SERVER=ldap.schule.local
LDAP_PORT=389
LDAP_BASE_DN=dc=schule,dc=local
LDAP_BIND_DN=cn=absenzflow,ou=services,dc=schule,dc=local
LDAP_BIND_PASSWORD=<ldap-password>

# === WebUntis API ===
WEBUNTIS_USERNAME=<webuntis-api-user>
WEBUNTIS_PASSWORD=<webuntis-api-password>
WEBUNTIS_SERVER=schoolname.webuntis.com

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

#### 3. WordPress-Plugin-Einstellungen aktualisieren

In WordPress Admin → Einstellungen → VertretungsFlow:

1. **Proxy Secret** auf `WORDPRESS_PROXY_SECRET` aus `.env` setzen
2. **Backend URL** auf die Backend-API-URL setzen
3. Verbindung testen

#### 4. Mit Production-Konfiguration deployen

```bash
# 1. Zum Projektverzeichnis navigieren
cd VertretungsFlow

# 2. Images bauen (nur beim ersten Mal)
docker-compose -f docker-compose.prod.yml build

# 3. Services starten
docker-compose -f docker-compose.prod.yml up -d

# 4. Logs prüfen
docker-compose -f docker-compose.prod.yml logs -f backend

# 5. Startup verifizieren
# Nach "✅ Security validation passed" suchen
```

#### 5. Production-Deployment verifizieren

```bash
# Health Check testen
curl http://localhost:8000/health

# Erwartete Antwort: {"status":"ok"}

# Backend-Logs auf Sicherheitsvalidierung prüfen
docker-compose -f docker-compose.prod.yml logs backend | grep "Security validation"

# Erwartet: "✅ Security validation passed - no default secrets detected"
```

---

## Sicherheits-Checkliste

Vor dem Go-Live überprüfen:

### ✅ Kritische Sicherheitselemente

- [ ] `SECRET_KEY` von Default geändert (min 32 Zeichen)
- [ ] `WORDPRESS_PROXY_SECRET` von Default geändert
- [ ] `POSTGRES_PASSWORD` von Default geändert
- [ ] WordPress Admin Secret stimmt mit `.env` Secret überein
- [ ] `DEBUG=false` in `.env`
- [ ] `CORS_ORIGINS` nur auf Production-Domain gesetzt
- [ ] Datenbank-Port NICHT exposed (mit `docker-compose.prod.yml`)
- [ ] SSL/TLS aktiviert (Reverse Proxy)
- [ ] Upload-Verzeichnis hat korrekte Berechtigungen

### ✅ Operationelle Elemente

- [ ] Datenbank-Backups konfiguriert
- [ ] Log-Rotation konfiguriert
- [ ] Monitoring/Alerting eingerichtet
- [ ] Firewall-Regeln konfiguriert
- [ ] Container-Restart-Policies aktiviert
- [ ] Health Checks konfiguriert

### ✅ WordPress-Integration

- [ ] VertretungsFlow-Plugin aktiviert
- [ ] Proxy Secret in WordPress Admin konfiguriert
- [ ] Backend URL korrekt konfiguriert
- [ ] Benutzerrollen korrekt gemappt
- [ ] Test-Absenz-Erstellung funktioniert

---

## Development-Setup

### Quick Start

```bash
# 1. Repository klonen
git clone https://gitlab.hhs.karlsruhe.de/digitale-schulverwaltung/absenzflow.git
cd absenzflow

# 2. Environment-Template kopieren
cp .env.example .env

# 3. .env bearbeiten (optional für Development)
nano .env

# 4. Development-Umgebung starten
docker-compose up -d

# 5. Logs anschauen
docker-compose logs -f backend

# 6. Services aufrufen
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - PostgreSQL: localhost:5432
# - pgAdmin: http://localhost:5050 (mit docker-compose --profile dev up)
```

### Development-Features

✅ **Hot-Reload**: Codeänderungen starten Backend automatisch neu
✅ **Direkter DB-Zugriff**: Verbindung zu PostgreSQL auf `localhost:5432`
✅ **Debug-Logging**: Detaillierte Logs zur Fehlersuche
✅ **pgAdmin**: Datenbank-Management-UI verfügbar

### ⚠️ Development-Sicherheitswarnungen

Die Development-Umgebung hat absichtlich mehrere Sicherheitsschwächen für Bequemlichkeit:

- **Datenbank-Port exposed** - Jeder im Netzwerk kann auf die Datenbank zugreifen
- **Default Secrets erlaubt** - Triggert Validierungsfehler bei Defaults
- **Debug Mode** - Zeigt detaillierte Fehlermeldungen
- **CORS permissiv** - Erlaubt localhost Origins

**Stellen Sie die Development-Konfiguration niemals in Production bereit!**

---

## Datenbankzugriff

### Development (Direkter Zugriff)

```bash
# Mit psql verbinden
psql -h localhost -U absenzflow -d absenzflow

# Oder pgAdmin verwenden
docker-compose --profile dev up -d pgadmin
# Öffne http://localhost:5050
```

### Production (Sicherer Zugriff)

**Option 1: Docker Exec (Empfohlen)**

```bash
# Auf Datenbank über Container zugreifen
docker-compose -f docker-compose.prod.yml exec postgres psql -U absenzflow -d absenzflow

# Beispiel: Query ausführen
docker-compose -f docker-compose.prod.yml exec postgres psql -U absenzflow -d absenzflow -c "SELECT COUNT(*) FROM absences;"
```

**Option 2: Notfall pgAdmin-Zugriff**

```bash
# pgAdmin mit Admin-Profil starten (nur im Notfall!)
docker-compose -f docker-compose.prod.yml --profile admin up -d pgadmin

# Zugriff unter http://localhost:5050 (nur localhost!)

# Nach Verwendung pgAdmin stoppen
docker-compose -f docker-compose.prod.yml stop pgadmin
```

**Option 3: SSH-Portweiterleitung**

```bash
# Von deinem lokalen Rechner Port durch SSH weiterleiten
ssh -L 5432:localhost:5432 user@production-server

# Jetzt verbinde dich mit localhost:5432
psql -h localhost -U absenzflow -d absenzflow
```

---

## Troubleshooting

### Backend startet nicht - Sicherheitsvalidierungsfehler

**Problem:**
```
🚨 SECURITY CONFIGURATION ERROR - STARTUP ABORTED 🚨
❌ SECRET_KEY is still set to default value!
```

**Lösung:**
1. Neue Secrets generieren: `openssl rand -hex 32`
2. `.env` mit generierten Secrets aktualisieren
3. Neu starten: `docker-compose -f docker-compose.prod.yml restart backend`

---

### Datenbankverbindung fehlgeschlagen

**Problem:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Lösungen:**

```bash
# 1. Prüfe ob postgres gesund ist
docker-compose -f docker-compose.prod.yml ps postgres

# 2. Postgres-Logs prüfen
docker-compose -f docker-compose.prod.yml logs postgres

# 3. Verifiziere DATABASE_URL im Backend
docker-compose -f docker-compose.prod.yml exec backend env | grep DATABASE_URL

# 4. Verbindung manuell testen
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U absenzflow
```

---

### WordPress kann sich nicht mit Backend verbinden

**Problem:** WordPress zeigt "Invalid proxy secret" oder Verbindungsfehler.

**Lösungen:**

```bash
# 1. Verifiziere Backend läuft
curl http://localhost:8000/health

# 2. Prüfe WORDPRESS_PROXY_SECRET stimmt überein
# Im Backend:
docker-compose -f docker-compose.prod.yml exec backend env | grep WORDPRESS_PROXY_SECRET

# In WordPress:
# Admin → Einstellungen → VertretungsFlow → Proxy Secret

# 3. Backend-Logs auf Auth-Fehler prüfen
docker-compose -f docker-compose.prod.yml logs backend | grep -i "proxy\|auth"
```

---

### Hohe Speichernutzung

**Problem:** Container nutzen zu viel Speicher.

**Lösungen:**

```bash
# 1. Ressourcennutzung prüfen
docker stats

# 2. Backend neu starten (löscht Caches)
docker-compose -f docker-compose.prod.yml restart backend

# 3. Worker-Anzahl anpassen (in docker-compose.prod.yml)
# Ändere: --workers 4 zu --workers 2

# 4. Ressourcen-Limits setzen (in docker-compose.prod.yml)
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 512M
```

---

## Nützliche Commands

### Development

```bash
# Development-Umgebung starten
docker-compose up -d

# Logs anschauen (alle Services)
docker-compose logs -f

# Logs anschauen (nur Backend)
docker-compose logs -f backend

# Neu starten nach Code-Änderungen (falls Hot-Reload fehlschlägt)
docker-compose restart backend

# Alle Services stoppen
docker-compose down

# Datenbank zurücksetzen (⚠️ DATENVERLUST!)
docker-compose down -v
docker-compose up -d
```

### Production

```bash
# Production-Umgebung starten
docker-compose -f docker-compose.prod.yml up -d

# Nach Code-Änderungen aktualisieren
docker-compose -f docker-compose.prod.yml build backend
docker-compose -f docker-compose.prod.yml up -d backend

# Logs anschauen
docker-compose -f docker-compose.prod.yml logs -f backend

# Services neu starten
docker-compose -f docker-compose.prod.yml restart

# Alle Services stoppen
docker-compose -f docker-compose.prod.yml down

# Datenbank-Backup erstellen
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U absenzflow absenzflow > backup_$(date +%Y%m%d).sql

# Datenbank wiederherstellen
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U absenzflow absenzflow < backup.sql
```

---

## Nächste Schritte

Nach erfolgreichem Deployment:

1. ✅ Regelmäßige Datenbank-Backups konfigurieren
2. ✅ Log-Monitoring und Alerting einrichten
3. ✅ Reverse Proxy (Nginx/Caddy) mit SSL konfigurieren
4. ✅ Firewall-Regeln einrichten
5. ✅ Production-Umgebung dokumentieren
6. ✅ Benutzer im System einweisen

---

**Zuletzt aktualisiert:** 2026-02-06
**Betreuer:** VertretungsFlow Team
**Fragen?** Siehe [CLAUDE.md](CLAUDE.md) für Entwickler-Dokumentation
