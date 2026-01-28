# AbsenzFlow - Handover für Claude Code

## 🎯 Projekt-Übersicht

**AbsenzFlow** ist ein Open-Source Tool für Schulen zur Verwaltung von Lehrkraft-Abwesenheiten und Vertretungsplanung.

- **Backend:** FastAPI (Python) mit PostgreSQL
- **Frontend:** WordPress-Plugin (React) + geplante Standalone-Version
- **Integrationen:** LDAP/AD, WebUntis, SMTP
- **Deployment:** Docker & Docker Compose

## 📁 Projektstruktur

```
absenzflow/
├── README.md                  # Haupt-README mit Überblick
├── docker-compose.yml         # Docker-Orchestrierung
├── .env.example              # Umgebungsvariablen-Template
├── .gitignore                # Git-Ignore-Regeln
│
├── backend/                  # FastAPI Backend
│   ├── app/
│   │   ├── api/             # API Endpoints (auth, absences, users)
│   │   ├── core/            # Config, DB, Security
│   │   ├── models/          # SQLAlchemy Models
│   │   ├── schemas/         # Pydantic Schemas
│   │   ├── services/        # Business Logic (LDAP, WebUntis, Email)
│   │   └── main.py          # FastAPI App
│   ├── scripts/             # Utility Scripts (init_db.py)
│   ├── Dockerfile
│   └── requirements.txt
│
├── wordpress-plugin/         # WordPress Plugin (React)
│   ├── src/
│   │   ├── components/      # React Components
│   │   ├── pages/           # Page Components
│   │   ├── api/             # API Client
│   │   └── index.jsx        # Entry Point
│   ├── plugin/              # PHP Plugin Files
│   ├── package.json
│   └── webpack.config.js
│
└── docs/                    # Dokumentation
    ├── SETUP.md            # Setup-Guide
    ├── API.md              # API-Dokumentation
    └── WEBUNTIS.md         # WebUntis-Integration
```

## 🚀 Quick Start für Claude Code

### 1. Projekt-Setup

```bash
# In Claude Code Terminal:
cd /pfad/zum/projekt/absenzflow

# Environment konfigurieren
cp .env.example .env
# .env editieren und alle Credentials eintragen

# Docker Container starten
docker-compose up -d

# Datenbank initialisieren
docker-compose exec backend python scripts/init_db.py
```

### 2. Was bereits implementiert ist ✅

**Backend (vollständig scaffolded):**
- ✅ FastAPI App-Struktur
- ✅ PostgreSQL mit SQLAlchemy
- ✅ LDAP/AD-Authentifizierung (Service)
- ✅ JWT-Token-basierte API-Auth
- ✅ User-Models mit Rollen (Teacher, DepartmentHead, Planner, Admin)
- ✅ Absence-Models mit Lessons
- ✅ API Endpoints (auth, absences, users)
- ✅ WebUntis-Service (Stundenplan-Abfrage)
- ✅ Email-Service (Benachrichtigungen)
- ✅ Docker-Setup
- ✅ Database-Init-Script

**Frontend (Basis vorhanden):**
- ✅ WordPress-Plugin-Struktur (PHP + React)
- ✅ Webpack-Build-Setup
- ✅ API-Client (axios)
- ✅ Basis-Komponenten (Navigation, LoginForm)
- ✅ App-Struktur mit Routing
- ✅ Basis-Styling (CSS)

**Dokumentation:**
- ✅ README mit Projektübersicht
- ✅ Detaillierter SETUP.md Guide
- ✅ API.md mit allen Endpoints
- ✅ WEBUNTIS.md für Integration

### 3. Was noch zu implementieren ist 🔨

**Backend:**
- ⏳ Alembic Migrations einrichten
- ⏳ Unit Tests schreiben
- ⏳ WebUntis Stundennummern-Mapping anpassen (schulspezifisch)
- ⏳ Error Handling verfeinern
- ⏳ Logging konfigurieren

**Frontend - WordPress Plugin:**
- ⏳ Dashboard-Komponente (Übersicht)
- ⏳ CreateAbsence-Seite (Formular + WebUntis-Integration)
- ⏳ AbsenceList-Seite (Tabelle mit Filtern)
- ⏳ AbsenceDetail-Seite (Details + Stunden + Hinweise)
- ⏳ PlannerView-Seite (Sortierte Liste für Planer)
- ⏳ Role-Management UI (Admin-Bereich)
- ⏳ Responsive Design
- ⏳ Loading States & Error Handling
- ⏳ Form Validation

**Frontend - Standalone (Phase 2):**
- ⏳ Neues Frontend-Projekt aufsetzen (Next.js/Vite)
- ⏳ Komponenten wiederverwenden
- ⏳ Eigene Auth-UI
- ⏳ Deployment-Setup

**Integration & Testing:**
- ⏳ End-to-End Tests
- ⏳ LDAP mit echtem AD testen
- ⏳ WebUntis API mit echten Daten testen
- ⏳ Email-Versand testen

### 4. Wichtige Dateien für die Weiterentwicklung

**Backend:**
- `backend/app/main.py` - Haupt-Einstiegspunkt
- `backend/app/api/endpoints/absences.py` - Absences-Logik
- `backend/app/services/webuntis.py` - WebUntis-Integration (Stundennummern anpassen!)
- `backend/app/core/config.py` - Konfiguration

**Frontend:**
- `wordpress-plugin/src/App.jsx` - Haupt-App
- `wordpress-plugin/src/api/client.js` - API-Client
- `wordpress-plugin/src/pages/` - Seiten-Komponenten (implementieren!)
- `wordpress-plugin/plugin/absenzflow.php` - WordPress-Plugin

**Docker:**
- `docker-compose.yml` - Service-Orchestrierung
- `.env` - Umgebungsvariablen (nicht committen!)

### 5. Typische Workflows für die Entwicklung

**Backend testen:**
```bash
# Logs anschauen
docker-compose logs -f backend

# Shell im Container
docker-compose exec backend bash

# Tests ausführen (wenn geschrieben)
docker-compose exec backend pytest

# API-Docs öffnen
# Browser: http://localhost:8000/docs
```

**Frontend entwickeln:**
```bash
cd wordpress-plugin
npm install
npm run dev  # Watch mode
```

**Datenbank-Zugriff:**
```bash
# PostgreSQL Shell
docker-compose exec db psql -U absenzflow absenzflow

# SQL ausführen
\dt  # Tabellen anzeigen
SELECT * FROM users;
```

### 6. Wichtige Anpassungen für eure Schule

**WebUntis Stundennummern:**
Die Datei `backend/app/services/webuntis.py` Zeile ~150 enthält:
```python
def _calculate_lesson_number(self, start_time: int) -> int:
```
Diese Funktion MUSS an euren Stundenplan angepasst werden!

**LDAP-Attribute:**
Falls euer AD andere Attribute verwendet, in `.env` anpassen:
```env
LDAP_USERNAME_ATTR=sAMAccountName
LDAP_EMAIL_ATTR=mail
# etc.
```

### 7. Nächste Schritte (Priorität)

1. **Backend testen:**
   - `.env` mit echten Credentials füllen
   - Docker starten
   - LDAP-Login testen
   - WebUntis-Verbindung testen

2. **Frontend-Seiten implementieren:**
   - `CreateAbsence` (wichtigste Seite!)
   - `AbsenceList`
   - `AbsenceDetail`
   - `PlannerView`

3. **Integration testen:**
   - Kompletter Workflow durchspielen
   - Email-Versand prüfen

4. **WordPress-Integration:**
   - Plugin in WordPress installieren
   - Shortcode testen
   - Rollenverwaltung implementieren

### 8. Hilfreiche Kommandos

```bash
# Container neu bauen
docker-compose build

# Nur bestimmten Service starten
docker-compose up -d backend

# Container stoppen
docker-compose down

# DB zurücksetzen
docker-compose down -v  # ACHTUNG: Löscht Daten!
docker-compose up -d
docker-compose exec backend python scripts/init_db.py

# Ersten Admin-User erstellen
docker-compose exec backend python -c "
from app.core.database import SessionLocal
from app.models.user import User, UserRole
db = SessionLocal()
user = db.query(User).filter(User.username == 'IHR_USERNAME').first()
if user:
    user.role = UserRole.ADMIN
    db.commit()
    print('Admin created')
"
```

### 9. Troubleshooting-Checkliste

- [ ] Alle Umgebungsvariablen in `.env` gesetzt?
- [ ] LDAP-Server erreichbar? (ping/ldapsearch testen)
- [ ] WebUntis-Credentials korrekt?
- [ ] Docker-Container laufen? (`docker-compose ps`)
- [ ] Datenbank initialisiert? (`docker-compose exec backend python scripts/init_db.py`)
- [ ] Logs gecheckt? (`docker-compose logs backend`)
- [ ] Browser-Konsole für Frontend-Fehler gecheckt?

### 10. Support & Ressourcen

**Dokumentation:**
- `docs/SETUP.md` - Detaillierte Installation
- `docs/API.md` - API-Referenz
- `docs/WEBUNTIS.md` - WebUntis-Integration

**FastAPI:**
- https://fastapi.tiangolo.com/
- Swagger UI: http://localhost:8000/docs

**WebUntis API:**
- https://help.untis.at/hc/de/articles/4403351094034

**SQLAlchemy:**
- https://docs.sqlalchemy.org/

**React:**
- https://react.dev/

## 🎉 Viel Erfolg!

Das Projekt ist gut strukturiert und ready für die Weiterentwicklung. Die Architektur ist sauber getrennt und gut erweiterbar. Viel Erfolg bei der Implementierung! 🚀
