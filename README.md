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
- In Planung: Frontend ohne Wordpress.

## 🏗️ Architektur

**Deployment-Modell:**
```
┌─────────────────────────────────────┐
│  WordPress + AbsenzFlow Plugin      │  ← Frontend (React-App)
│  - PHP Plugin lädt React-Bundle     │    als Wordpress-Plugin
│  - Shortcode: [absenzflow]          │    Benutzerdaten aus WP
└──────────────┬──────────────────────┘
               │ REST API (HTTPS)
┌──────────────▼──────────────────────┐
│  FastAPI Backend (Docker)           │  ← Business Logic
│  - Wordpress Auth                   │    auf Backend-Server
│  - WebUntis Integration             │    (durch Firewall vom Internet getrennt)
│  - Email Service                    │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  PostgreSQL (Docker)                │  ← Datenbank-Server, kann auf Backend laufen
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
│       └── utils/        # Werkzeuge
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

Für eine ausführliche Anleitung siehe unseren [vollständigen Setup Guide](./docs/SETUP.md) - Installation Schritt für Schritt

### Voraussetzungen

- Docker & Docker Compose auf dem Backend-Server
- WebUntis Account mit API-Zugang
- Bestehende Wordpress-Installation mit Benutzern für alle Lehrkräfte auf Frontend-Server. 
  **Tipp**: Es gibt Wordpress-Plugins, welche eine AD-Integration anbieten. Dabei kann die Default-Rolle
  so eingestellt sein, dass die Lehrkräfte keine Berechtigung haben, im Wordpress Beiträge oder Seiten
  zu ändern, aber einen Account haben.
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
nano .env # .env bearbeiten mit deinen Credentials
```

**Wichtig:** Setze `WORDPRESS_PROXY_SECRET` auf einen zufälligen, sicheren Wert:
```bash
# Beispiel für sicheres Secret generieren und in .env eintragen
SECRET=$(openssl rand -hex 32); sed -i.bak "s/change-this-shared-secret-in-production/$SECRET/" .env; echo "Secret in Wordpress-Plugin-Einstellungen eintragen: $SECRET"
```

Dieser Secret muss identisch im Backend (.env) und im WordPress Plugin (Einstellungen) konfiguriert werden.

3. Docker Container starten:
```bash
docker-compose up -d
```

4. Backend ist erreichbar unter: `http://localhost:8000`
5. API-Dokumentation: `http://localhost:8000/docs`

### WordPress Plugin

1. WordPress Plugin bauen auf Frontend-Server:
```bash
cd wordpress-plugin
npm install
npm run build
```

2. Plugin nach WordPress kopieren:
Hier zunächst WP_ROOT anpassen!
```bash
WP_ROOT=/var/www/html
for file in absenzflow.php  assets  build  includes; do
  ln -s $(pwd)/wordpress-plugin/$file $WP_ROOT/wp-content/plugins/absenzflow/$file
done
```
**Hinweis:** der Vorteil der Softlinks ist, dass Updates im AbsenzFlow-Verzeichnis bereits im WebRoot liegen und nur noch
ein ```npm run build``` erfolgen muss.

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

Bei Fragen oder Problemen erstelle bitte ein Issue auf [GitHub](https://github.com/digitale-Schulverwaltung-BW/absenzflow) - Schülerinnen, Schüler und Lehrkräfte der HHS Karlsruhe natürlich auch gerne über das [HHS Gitlab](https://gitlab.hhs.karlsruhe.de/digitale-schulverwaltung/absenzflow).

---

**Entwickelt für Schulen, von Schulen** 🎓
