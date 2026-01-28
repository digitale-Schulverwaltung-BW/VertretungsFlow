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
- 🎨 Zwei Frontend-Varianten:
  - WordPress-Plugin (Shortcode-Integration)
  - Standalone Web-App

## 🏗️ Architektur

```
absenzflow/
├── backend/              # FastAPI Backend (Python)
├── frontend-wp/          # WordPress Plugin (React)
├── frontend-standalone/  # Standalone Frontend (React)
├── docs/                 # Dokumentation
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

- [Backend Setup](./backend/README.md)
- [WordPress Plugin Installation](./frontend-wp/README.md)
- [Standalone Frontend](./frontend-standalone/README.md)
- [API Dokumentation](./docs/API.md)
- [Entwickler Guide](./docs/DEVELOPMENT.md)

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
