# 🎯 AbsenzFlow - Projekt-Zusammenfassung

## Was ist AbsenzFlow?

Ein **Open-Source Tool** für Schulen zur Verwaltung von Lehrkraft-Abwesenheiten und Vertretungsplanung mit:
- ✅ Einfacher Abwesenheitsmeldung
- ✅ Automatischer Stundenabfrage via WebUntis
- ✅ Genehmigungs-Workflow
- ✅ Vertretungsplanungs-Unterstützung
- ✅ E-Mail-Benachrichtigungen

## 🏗️ Architektur

```
┌─────────────────────────────────────┐
│  Frontend (WordPress + React)       │  ← User Interface
│  Port: WordPress-URL                │
└──────────────┬──────────────────────┘
               │ REST API (HTTPS)
┌──────────────▼──────────────────────┐
│  Backend (FastAPI)                  │  ← Business Logic
│  Port: 8000                         │
│  • LDAP Auth                        │
│  • WebUntis Integration             │
│  • Email Service                    │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  PostgreSQL Database                │  ← Data Storage
│  Port: 5432                         │
└─────────────────────────────────────┘
```

## 📊 Funktionsweise

### 1️⃣ Lehrkraft meldet Abwesenheit
- Wählt Grund (Fortbildung, Prüfung, etc.)
- Gibt Zeitraum und Stunden an
- System fragt WebUntis nach betroffenen Stunden
- Lehrkraft gibt Hinweise für jede Stunde

### 2️⃣ Abteilungsleiter genehmigt
- Erhält E-Mail-Benachrichtigung
- Prüft Abwesenheit
- Genehmigt oder lehnt ab mit Kommentar

### 3️⃣ Vertretungsplaner organisiert
- Sieht sortierte Liste aller genehmigten Abwesenheiten
- Plant Vertretungen (außerhalb des Systems)
- Markiert Abwesenheit als "eingetragen"

### 4️⃣ Alle werden informiert
- Automatische E-Mails bei jedem Statuswechsel
- Transparenter Workflow für alle Beteiligten

## 🔑 Benutzerrollen

| Rolle | Rechte |
|-------|--------|
| **Teacher** (Lehrkraft) | Eigene Abwesenheiten melden und einsehen |
| **Department Head** (Abteilungsleiter) | Abwesenheiten genehmigen/ablehnen |
| **Substitution Planner** (Vertretungsplaner) | Alle Abwesenheiten einsehen, als erledigt markieren |
| **Admin** | Vollzugriff + Benutzerverwaltung |

## 📦 Was wurde erstellt?

### ✅ Vollständig implementiert

**Backend:**
- FastAPI-Anwendung mit allen Endpoints
- Datenbank-Models (Users, Absences, Lessons)
- LDAP/AD-Authentifizierung
- JWT-Token-basierte API-Security
- WebUntis-Integration (Stundenplan-Abfrage)
- E-Mail-Service (alle Benachrichtigungen)
- Docker-Setup mit docker-compose
- Datenbank-Initialisierung

**WordPress-Plugin (Grundgerüst):**
- PHP-Plugin-Datei mit Shortcode
- React-App-Struktur
- API-Client (axios)
- Routing-Setup
- Basis-Komponenten
- CSS-Styling
- Webpack-Build

**Dokumentation:**
- README mit Projektübersicht
- Detaillierter Setup-Guide
- API-Dokumentation
- WebUntis-Integrations-Guide
- Handover-Dokument für Claude Code

### ⏳ Noch zu implementieren

**Frontend-Komponenten:**
- Standalone-Version des Frontends ohne Wordpress-Installation

**Testing & Refinement:**
- Unit Tests (Backend)
- E2E Tests
- Echte LDAP/WebUntis-Integration testen
- Responsive Design verfeinern

## 🚀 Was muss in Claude Code rüberkopiert werden?

### Gesamtes Projekt:
```
absenzflow/
├── backend/              # ← Komplettes Backend
├── wordpress-plugin/     # ← WordPress-Plugin
├── docs/                # ← Dokumentation
├── docker-compose.yml   # ← Docker-Orchestrierung
├── .env.example         # ← Config-Template
├── .gitignore          # ← Git-Regeln
└── README.md           # ← Haupt-README
```

**Alle Dateien im `/mnt/user-data/outputs/absenzflow/` Ordner sind fertig zum Transfer!**

## 🎯 Nächste Schritte in Claude Code

1. **Projekt-Setup (30 Min)**
   - Ordner nach Claude Code kopieren
   - `.env` konfigurieren mit echten Credentials
   - `docker-compose up -d` ausführen
   - Datenbank initialisieren

2. **Backend testen (1h)**
   - LDAP-Verbindung testen
   - WebUntis-Verbindung testen
   - Erste User über Login anlegen
   - Admin-Rolle zuweisen
   - API mit Swagger UI testen

3. **Frontend implementieren (10-15h)**
   - CreateAbsence-Seite (wichtigste!)
   - AbsenceList-Seite
   - AbsenceDetail-Seite
   - PlannerView-Seite
   - Dashboard-Seite
   - Admin-Bereich für Rollen

4. **Integration & Testing (5h)**
   - Kompletten Workflow durchspielen
   - Email-Versand prüfen
   - Edge Cases testen
   - Responsive Design prüfen

5. **WordPress-Integration (2h)**
   - Plugin in WordPress installieren
   - Shortcode auf Seite einfügen
   - Rollenverwaltung konfigurieren
   - Mit echten Usern testen

6. **Deployment (3h)**
   - Produktiv-Server vorbereiten
   - SSL/HTTPS einrichten
   - Backups konfigurieren
   - Monitoring einrichten

**Geschätzte Gesamtzeit bis MVP: 22-28 Stunden**

## 💡 Wichtige Hinweise

### ⚠️ Anpassungen erforderlich

**WebUntis Stundennummern:**
Die Datei `backend/app/services/webuntis.py` berechnet Stundennummern aus Uhrzeiten. Diese Logik **MUSS** an euren Stundenplan angepasst werden!

**Beispiel-Anpassung:**
```python
# In webuntis.py, Zeile ~150
LESSON_TIMES = {
    1: (750, 835),   # 07:50 - 08:35
    2: (840, 925),   # 08:40 - 09:25
    # ... eure Zeiten
}
```

### 🔐 Security-Checkliste

- [ ] `.env` nicht ins Git committen!
- [ ] Starke Passwörter verwenden
- [ ] SECRET_KEY zufällig generieren: `openssl rand -hex 32`
- [ ] In Produktion: HTTPS nutzen
- [ ] In Produktion: DEBUG=false setzen
- [ ] Firewall-Regeln prüfen

### 📚 Hilfreiche Ressourcen

**Während der Entwicklung:**
- FastAPI Swagger UI: http://localhost:8000/docs
- Backend Logs: `docker-compose logs -f backend`
- DB-Zugriff: `docker-compose exec db psql -U absenzflow absenzflow`

**Dokumentation:**
- `docs/SETUP.md` - Installation Step-by-Step
- `docs/API.md` - Alle API-Endpoints
- `docs/WEBUNTIS.md` - WebUntis-Integration
- `HANDOVER.md` - Detaillierte Entwickler-Infos
