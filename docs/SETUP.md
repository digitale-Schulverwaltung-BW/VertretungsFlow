# AbsenzFlow Setup Guide

Vollständige Anleitung zur Installation und Konfiguration von AbsenzFlow.

## Voraussetzungen

### Server-Anforderungen
- Docker & Docker Compose (für Backend)
- PostgreSQL 15+ (oder via Docker)
- Python 3.11+ (für lokale Entwicklung)
- **Node.js 18+ & npm** (für WordPress-Plugin Build)

#### Node.js Installation

**Ubuntu/Debian:**
```bash
# Node.js 20 LTS (empfohlen)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Version prüfen
node --version  # sollte v20.x.x zeigen
npm --version
```

**macOS:**
```bash
# Mit Homebrew
brew install node@20

# Oder mit nvm (Node Version Manager)
brew install nvm
nvm install 20
nvm use 20
```

**Windows:**
- Download von https://nodejs.org/ (LTS Version 20.x)
- Oder mit Chocolatey: `choco install nodejs-lts`

### Externe Dienste
- **LDAP/Active Directory Server**
  - Zugriff auf LDAP-Server
  - Service Account mit Leseberechtigung
  - Base DN für User-Suche

- **WebUntis Zugang**
  - WebUntis Server URL
  - Schulname
  - API-Benutzer mit Leserechten
  - API-Passwort

- **SMTP Server**
  - SMTP Host und Port
  - SMTP Credentials (falls erforderlich)

### WordPress (für Plugin)
- WordPress 6.0 oder höher
- PHP 7.4 oder höher
- LDAP-Authentifizierung für WordPress (empfohlen)

## Installation Schritt für Schritt

### 1. Repository klonen

```bash
git clone https://github.com/your-org/absenzflow.git
cd absenzflow
```

### 2. Environment-Konfiguration

Kopieren Sie die Beispiel-Konfiguration:

```bash
cp .env.example .env
```

Bearbeiten Sie `.env` und füllen Sie alle erforderlichen Werte aus:

#### Datenbank
```env
DB_USER=absenzflow
DB_PASSWORD=ihr_sicheres_passwort
DB_NAME=absenzflow
```

#### LDAP/AD
```env
LDAP_SERVER=ldap://dc.school.local:389
LDAP_BASE_DN=DC=school,DC=local
LDAP_BIND_DN=CN=AbsenzFlow Service,OU=Service Accounts,DC=school,DC=local
LDAP_BIND_PASSWORD=ihr_bind_passwort
```

**LDAP Attribute Mapping:**
Falls Ihr AD andere Attribute verwendet, passen Sie diese an:
```env
LDAP_USERNAME_ATTR=sAMAccountName
LDAP_EMAIL_ATTR=mail
LDAP_FIRSTNAME_ATTR=givenName
LDAP_LASTNAME_ATTR=sn
LDAP_DISPLAYNAME_ATTR=displayName
```

#### WebUntis
```env
WEBUNTIS_SERVER=ihre-schule.webuntis.com
WEBUNTIS_SCHOOL=ihre-schule
WEBUNTIS_USERNAME=api-benutzer
WEBUNTIS_PASSWORD=api-passwort
```

**WebUntis API User erstellen:**
1. In WebUntis als Admin einloggen
2. Verwaltung → Stammdaten → Lehrer
3. Neuen Lehrer mit Kürzel "API" anlegen
4. Benutzername und Passwort notieren
5. Dem User Leserechte auf Stundenpläne geben

#### E-Mail
```env
SMTP_HOST=smtp.school.local
SMTP_PORT=587
SMTP_USER=absenzflow@school.local
SMTP_PASSWORD=smtp_passwort
SMTP_FROM=absenzflow@school.local
```

#### Security
Generieren Sie einen sicheren Secret Key:
```bash
openssl rand -hex 32
```

Tragen Sie diesen ein:
```env
SECRET_KEY=ihr_generierter_key
```

#### Application URLs
```env
ALLOWED_ORIGINS=https://intranet.school.local,http://localhost:3000
FRONTEND_URL=https://intranet.school.local/absenzflow
```

### 3. Backend starten (Docker)

#### Mit Standard-Konfiguration
```bash
docker-compose up -d
```

#### Nur Backend und DB (ohne Mock-LDAP)
```bash
docker-compose up -d db backend
```

#### Mit Development-Tools (inkl. Mock-LDAP)
```bash
docker-compose --profile development up -d
```

Überprüfen Sie, ob die Container laufen:
```bash
docker-compose ps
```

### 4. Datenbank initialisieren

```bash
docker-compose exec backend python scripts/init_db.py
```

### 5. Backend testen

API-Dokumentation aufrufen:
```
http://localhost:8000/docs
```

Health-Check:
```bash
curl http://localhost:8000/health
```

### 6. WordPress-Plugin installieren

#### Build des Plugins
```bash
cd wordpress-plugin
npm install
npm run build
```

#### Plugin nach WordPress kopieren
```bash
# Gesamten plugin/ Ordner kopieren
cp -r plugin/ /pfad/zu/wordpress/wp-content/plugins/absenzflow/
```

#### In WordPress aktivieren
1. WordPress Admin-Bereich öffnen
2. Plugins → Installierte Plugins
3. "AbsenzFlow" aktivieren

#### Plugin konfigurieren
1. AbsenzFlow → Einstellungen
2. Backend API URL eintragen: `https://api.school.de/absenzflow/api/v1`
3. Einstellungen speichern

#### Shortcode auf Seite einfügen
1. Neue Seite erstellen (z.B. "Abwesenheiten")
2. Shortcode einfügen: `[absenzflow]`
3. Seite veröffentlichen

### 7. Rollenverwaltung einrichten

#### Initial Admin-User erstellen
Über die Datenbank einen ersten Admin-User anlegen:

```sql
-- Nach dem ersten Login des Users via LDAP
UPDATE users 
SET role = 'admin' 
WHERE username = 'ihr_username';
```

#### Oder via Python-Script:
```bash
docker-compose exec backend python -c "
from app.core.database import SessionLocal
from app.models.user import User, UserRole

db = SessionLocal()
user = db.query(User).filter(User.username == 'ihr_username').first()
if user:
    user.role = UserRole.ADMIN
    db.commit()
    print(f'User {user.username} is now admin')
else:
    print('User not found')
"
```

#### Rollen in WordPress zuweisen
1. AbsenzFlow → Rollenverwaltung
2. Benutzer suchen
3. Rolle zuweisen:
   - `teacher`: Normale Lehrkraft
   - `department_head`: Abteilungsleiter (kann genehmigen)
   - `substitution_planner`: Vertretungsplaner
   - `admin`: Administrator

## Entwicklung

### Backend lokal entwickeln

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt

# Development Server
uvicorn app.main:app --reload
```

### Frontend lokal entwickeln

```bash
cd wordpress-plugin
npm install
npm run dev  # Watch mode
```

### Tests ausführen

```bash
# Backend Tests
cd backend
pytest

# Mit Coverage
pytest --cov=app tests/
```

## Produktiv-Deployment

### Backend

#### Option 1: Docker auf eigenem Server
```bash
# Production docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

#### Option 2: Kubernetes
Siehe `docs/DEPLOYMENT.md` für Kubernetes-Manifests.

### WordPress-Plugin

1. Plugin builden: `npm run build`
2. `plugin/` Ordner auf Produktiv-WordPress kopieren
3. In WordPress aktivieren und konfigurieren

## Troubleshooting

### Backend startet nicht
- Logs prüfen: `docker-compose logs backend`
- Umgebungsvariablen in `.env` überprüfen
- Datenbank-Verbindung testen

### LDAP-Authentifizierung funktioniert nicht
- LDAP-Server erreichbar? `ldapsearch -x -H ldap://server -b "dc=school,dc=local"`
- Bind-Credentials korrekt?
- Base DN korrekt?
- Firewall-Regeln prüfen

### WebUntis-Integration funktioniert nicht
- API-Credentials korrekt?
- Server-URL korrekt? (ohne `https://`)
- Hat der API-User die nötigen Rechte?
- WebUntis-Logs in Backend prüfen

### E-Mail werden nicht versendet
- SMTP-Server erreichbar?
- Port korrekt? (587 für TLS, 465 für SSL)
- Credentials korrekt?
- Firewall erlaubt ausgehende Verbindungen?

### WordPress-Plugin lädt nicht
- JavaScript-Fehler in Browser-Konsole prüfen
- Plugin neu builden und erneut hochladen
- WordPress-Cache leeren
- Browser-Cache leeren

## Wartung

### Datenbank-Backup
```bash
docker-compose exec db pg_dump -U absenzflow absenzflow > backup.sql
```

### Datenbank-Restore
```bash
docker-compose exec -T db psql -U absenzflow absenzflow < backup.sql
```

### Logs ansehen
```bash
# Alle Services
docker-compose logs -f

# Nur Backend
docker-compose logs -f backend

# Letzte 100 Zeilen
docker-compose logs --tail=100 backend
```

### Updates einspielen
```bash
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

## Support

Bei Problemen:
1. Logs prüfen
2. Dokumentation durchlesen
3. Issues auf GitHub erstellen: https://github.com/your-org/absenzflow/issues
