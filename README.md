# AbsenzFlow

**Modernes Abwesenheitsmanagement für Schulen mit WebUntis-Integration**

AbsenzFlow ist ein Open-Source-Tool, das Lehrkräften ermöglicht, ihre Abwesenheiten einfach zu melden und Vertretungsplanern eine übersichtliche Verwaltung bietet.

## 🎯 Features

- 📝 Einfache Abwesenheitsmeldung durch Lehrkräfte
- 📅 Automatische Stundenplan-Abfrage über WebUntis API
- ✅ Genehmigungsworkflow für Abteilungsleiter
- 📊 Übersichtliches Dashboard für Vertretungsplaner
- 🔐 LDAP/AD-Authentifizierung
- 📧 E-Mail-Benachrichtigungen
- 🎨 WordPress-Plugin mit React-Frontend
  - Shortcode-Integration: `[absenzflow]`
  - 2-Schritt-Workflow für Abwesenheitsmeldungen

## 🏗️ Architektur

**Deployment-Modell:**
```
┌─────────────────────────────────────┐
│  WordPress + AbsenzFlow Plugin      │  ← Frontend (React-App)
│  - PHP Plugin lädt React-Bundle     │
│  - Shortcode: [absenzflow]          │
└──────────────┬──────────────────────┘
               │ REST API (HTTPS)
┌──────────────▼──────────────────────┐
│  FastAPI Backend (Docker)           │  ← Business Logic
│  - LDAP/AD Auth                     │
│  - WebUntis Integration             │
│  - Email Service                    │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  PostgreSQL (Docker)                │  ← Datenbank
└─────────────────────────────────────┘
```

**Projektstruktur:**
```
absenzflow/
├── backend/              # FastAPI Backend (Python)
│   └── app/
│       ├── api/          # API Routes
│       ├── core/         # Config, Database
│       ├── models/       # SQLAlchemy Models
│       ├── schemas/      # Pydantic Schemas
│       └── services/     # LDAP, WebUntis, Email
├── wordpress-plugin/     # WordPress Plugin (React + TypeScript)
│   ├── src/              # React-Frontend-Code
│   │   ├── pages/        # React Pages (CreateAbsence)
│   │   ├── components/   # UI Components
│   │   ├── api/          # API Client
│   │   └── types/        # TypeScript Types
│   ├── assets/           # Statische Assets (Logo, etc.)
│   ├── includes/         # PHP Classes
│   ├── absenzflow.php    # Plugin Main File
│   ├── package.json      # Node.js Dependencies
│   └── vite.config.ts    # Vite Build Config
├── docs/                 # Dokumentation
│   ├── SETUP.md          # Installationsanleitung
│   ├── API.md            # API Dokumentation
│   └── WEBUNTIS.md       # WebUntis Integration
├── .env.example          # Beispiel-Konfiguration
└── docker-compose.yml    # Docker Setup
```

## 🚀 Quick Start

### Voraussetzungen

- Docker & Docker Compose
- WebUntis Account mit API-Zugang
- LDAP/AD Server

### Installation

1. Repository klonen:
```bash
git clone https://github.com/your-org/absenzflow.git
cd absenzflow
```

2. Umgebungsvariablen konfigurieren:
```bash
cp .env.example .env
# .env bearbeiten mit deinen Credentials
```

**Wichtig:** Setze `WORDPRESS_PROXY_SECRET` auf einen zufälligen, sicheren Wert:
```bash
# Beispiel für sicheres Secret generieren
openssl rand -hex 32
```

Dieser Secret muss identisch im Backend (.env) und im WordPress Plugin (Einstellungen) konfiguriert werden.

3. Docker Container starten:
```bash
docker-compose up -d
```

4. Backend ist erreichbar unter: `http://localhost:8000`
5. API-Dokumentation: `http://localhost:8000/docs`

### WordPress Plugin

1. WordPress Plugin bauen:
```bash
cd wordpress-plugin
npm install
npm run build
```

2. Plugin nach WordPress kopieren:
```bash
# Methode 1: Kopieren (für einfache Installation)
cp -r wordpress-plugin/ /path/to/wordpress/wp-content/plugins/absenzflow/

# Methode 2: Softlink (empfohlen für Entwicklung/Updates)
ln -s /absolute/path/to/absenzflow/wordpress-plugin /path/to/wordpress/wp-content/plugins/absenzflow
```

**Wichtig:** Das `assets/` Verzeichnis muss ebenfalls ins WordPress-Plugin kopiert/verlinkt werden:
```bash
# Falls nicht automatisch mitkopiert:
cp -r wordpress-plugin/assets/ /path/to/wordpress/wp-content/plugins/absenzflow/assets/

# Oder bei Softlink-Verwendung bereits enthalten
```

**Vorteil Softlink:** Updates werden direkt synchronisiert - einfach `npm run build` ausführen, ohne erneut zu kopieren.

3. In WordPress aktivieren: **Plugins → AbsenzFlow → Aktivieren**

4. Einstellungen konfigurieren (**AbsenzFlow → Einstellungen**):
   - **Backend API URL**: `http://your-backend-server:8000/api`
   - **Backend API Secret**: Identischer Wert wie `WORDPRESS_PROXY_SECRET` aus Backend .env

5. Shortcode `[absenzflow]` auf eine Seite einfügen

## 📚 Dokumentation

- [Vollständiger Setup Guide](./docs/SETUP.md) - Installation Schritt für Schritt
- [API Dokumentation](./docs/API.md) - Alle API-Endpoints
- [WebUntis Integration](./docs/WEBUNTIS.md) - WebUntis-Setup
- [Entwickler Guide](./docs/DEVELOPMENT.md) - Entwicklung und Testing
- [Projekt-Zusammenfassung](./docs/PROJECT_SUMMARY.md) - Überblick und Status

## 🔧 Technologien

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: React, TypeScript, TailwindCSS
- **Auth**: LDAP/AD Integration
- **Integration**: WebUntis API
- **Deployment**: Docker, docker-compose

## 📝 Lizenz

MIT License - siehe [LICENSE](LICENSE)

## 🤝 Contributing

Contributions sind willkommen! Bitte lies [CONTRIBUTING.md](CONTRIBUTING.md) für Details.

## 📧 Support

Bei Fragen oder Problemen erstelle bitte ein Issue auf GitHub.

---

**Entwickelt für Schulen, von Schulen** 🎓
