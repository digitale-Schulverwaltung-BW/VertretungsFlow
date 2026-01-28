# 🚀 AbsenzFlow - Setup für Claude Code

Willkommen! Hier ist dein komplettes AbsenzFlow-Projekt bereit für die Entwicklung mit Claude Code.

## 📦 Was ist enthalten?

Das Projekt ist vollständig strukturiert und bereit für die Entwicklung:

```
absenzflow/
├── backend/                    ✅ FastAPI Backend (Python)
│   ├── app/
│   │   ├── api/               # API Routes (auth, absences, admin)
│   │   ├── core/              # Config, Database
│   │   ├── models/            # SQLAlchemy Models
│   │   ├── schemas/           # Pydantic Schemas
│   │   ├── services/          # LDAP, WebUntis, Email
│   │   └── main.py            # FastAPI App
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
│
├── frontend-wp/                ✅ WordPress Plugin
│   ├── absenzflow.php         # Plugin Hauptdatei
│   ├── includes/              # PHP Classes
│   ├── src/                   # React App (TypeScript)
│   ├── package.json
│   └── README.md
│
├── frontend-standalone/        📝 TODO: Standalone Frontend
│
├── docs/                       ✅ Dokumentation
│   ├── API.md                 # API Dokumentation
│   └── DEVELOPMENT.md         # Entwickler Guide
│
├── docker-compose.yml          ✅ Docker Setup
├── .env.example                ✅ Environment Template
├── .gitignore                  ✅ Git Ignore
└── README.md                   ✅ Haupt-README
```

## 🎯 Was zu Claude Code kopieren?

Kopiere den **kompletten `absenzflow/` Ordner** zu Claude Code:

1. **Öffne Claude Code** in deinem Terminal
2. **Navigiere** zu deinem Arbeitsverzeichnis
3. **Kopiere** den absenzflow-Ordner dorthin

```bash
# Beispiel:
cp -r /pfad/zu/absenzflow ~/projekte/absenzflow
cd ~/projekte/absenzflow
```

## ✅ Was ist bereits implementiert?

### Backend (Python/FastAPI)
- ✅ Komplette API-Struktur
- ✅ Authentication (LDAP + JWT)
- ✅ Datenbank-Models (User, Absence, AffectedLesson, Notification)
- ✅ CRUD Endpoints für Abwesenheiten
- ✅ Rollen-basierte Zugriffskontrolle
- ✅ WebUntis Service (API Integration)
- ✅ E-Mail Service (SMTP)
- ✅ Admin Dashboard Endpoints
- ✅ Docker Setup

### WordPress Plugin (PHP + React)
- ✅ Plugin-Struktur
- ✅ Admin-Bereich (Einstellungen, Rollenverwaltung)
- ✅ Shortcode-Handler
- ✅ API Proxy (sichere Backend-Kommunikation)
- ✅ React-App Grundgerüst
- ✅ Vite Build Setup
- ✅ TailwindCSS Integration

### Dokumentation
- ✅ Haupt-README
- ✅ Backend README
- ✅ WordPress Plugin README
- ✅ Vollständige API Dokumentation
- ✅ Entwickler Guide
- ✅ Docker Setup

## 📝 Was fehlt noch? (TODOs für morgen)

### 1. Backend
- [ ] Alembic Migrations einrichten
- [ ] Unit Tests schreiben
- [ ] WebUntis API Authentifizierung testen
- [ ] E-Mail Templates erstellen
- [ ] Error Handling verfeinern

### 2. Frontend (WordPress Plugin)
- [ ] Abwesenheitsformular Component
- [ ] Stundenplan-Anzeige Component
- [ ] Dashboard für verschiedene Rollen
- [ ] API Service Layer
- [ ] State Management (Context/Redux)
- [ ] Responsive Design finalisieren

### 3. Frontend (Standalone)
- [ ] Komplett neu erstellen
- [ ] Gleiche Components wie WP-Plugin
- [ ] Eigene Authentifizierung (kein WordPress)

### 4. Testing & Deployment
- [ ] Backend Tests
- [ ] Frontend Tests
- [ ] CI/CD Pipeline
- [ ] Production Deployment Guide

## 🚀 Schnellstart für morgen

### Option 1: Komplett mit Docker

```bash
cd absenzflow

# .env erstellen
cp .env.example .env
# .env mit deinen Credentials bearbeiten

# Alles starten
docker-compose up -d

# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
# PostgreSQL: localhost:5432
```

### Option 2: Lokale Entwicklung

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# PostgreSQL muss laufen
docker-compose up -d postgres

uvicorn app.main:app --reload
```

**WordPress Plugin:**
```bash
cd frontend-wp
npm install
npm run dev  # oder: npm run build
```

## 🔧 Konfiguration

Bearbeite `.env` mit deinen Daten:

```env
# Database
POSTGRES_DB=absenzflow
POSTGRES_USER=absenzflow
POSTGRES_PASSWORD=dein-password

# LDAP (deine IT-Schule)
LDAP_SERVER=ldap.schule.local
LDAP_BASE_DN=dc=schule,dc=local
# ...

# WebUntis
WEBUNTIS_SCHOOL=deine-schule
WEBUNTIS_USERNAME=api-user
WEBUNTIS_PASSWORD=api-password

# SMTP
SMTP_HOST=smtp.schule.local
```

## 📚 Wichtige Dateien zum Starten

1. **Backend verstehen**:
   - `backend/app/main.py` - FastAPI App Entry Point
   - `backend/app/models/models.py` - Datenbank-Schema
   - `backend/app/api/absences.py` - Hauptlogik für Abwesenheiten

2. **WordPress Plugin verstehen**:
   - `frontend-wp/absenzflow.php` - Plugin Entry Point
   - `frontend-wp/src/App.tsx` - React App

3. **API verstehen**:
   - `docs/API.md` - Komplette API Dokumentation

## 🎯 Empfohlene Reihenfolge

1. **Backend testen** (mit Docker)
   - `docker-compose up -d`
   - API Docs öffnen: http://localhost:8000/docs
   - Login testen (mit Mock oder echtem LDAP)

2. **Datenbank Migrations erstellen**
   - Alembic einrichten
   - Initial Migration

3. **WebUntis Integration testen**
   - Mit echten Credentials
   - Stundenplan abrufen

4. **WordPress Plugin entwickeln**
   - React Components bauen
   - API Integration
   - UI/UX optimieren

5. **Standalone Frontend**
   - Neue React App
   - Gleiche Components wiederverwenden

## 💡 Tipps

- **API Docs**: http://localhost:8000/docs ist interaktiv - du kannst alle Endpoints direkt testen!
- **pgAdmin**: Mit `docker-compose --profile dev up -d` bekommst du auch pgAdmin auf Port 5050
- **Hot Reload**: Backend und Frontend haben beide Hot Reload aktiviert
- **TypeScript**: Frontend nutzt TypeScript - hilft bei der Entwicklung

## 🐛 Wenn etwas nicht funktioniert

1. **Backend startet nicht**:
   - PostgreSQL läuft? `docker-compose ps`
   - .env korrekt? Alle Variablen gesetzt?
   - Requirements installiert? `pip list`

2. **Frontend baut nicht**:
   - node_modules installiert? `npm install`
   - Richtige Node Version? (14+)

3. **LDAP Connection Failed**:
   - Für Development: Mock aktivieren in ldap_service.py
   - Oder echten LDAP Server nutzen

## 📞 Nächste Schritte mit Claude Code

Morgen kannst du mit Claude Code direkt loslegen:

1. **Projekt öffnen**: `code ~/projekte/absenzflow`
2. **Claude Code starten**: Im Terminal Claude Code aufrufen
3. **Fragen**: "Hilf mir, Alembic Migrations einzurichten"
4. **Entwickeln**: "Erstelle das Abwesenheitsformular Component"

## 🎉 Ready to go!

Alles ist vorbereitet. Die Architektur steht, die Struktur ist da, die Dokumentation ist vollständig.

Morgen kannst du direkt mit der Entwicklung der Features starten! 🚀

**Viel Erfolg! Falls Fragen auftauchen, siehe die Dokumentation in `docs/` oder frage Claude Code!**
