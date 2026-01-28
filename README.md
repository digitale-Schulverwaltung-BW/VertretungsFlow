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
│   ├── src/
│   │   ├── pages/        # React Pages (CreateAbsence)
│   │   ├── components/   # UI Components
│   │   ├── api/          # API Client
│   │   └── types/        # TypeScript Types
│   ├── includes/         # PHP Classes
│   └── absenzflow.php    # Plugin Main File
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

3. Docker Container starten:
```bash
docker-compose up -d
```

4. Backend ist erreichbar unter: `http://localhost:8000`
5. API-Dokumentation: `http://localhost:8000/docs`

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
