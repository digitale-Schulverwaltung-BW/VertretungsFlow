# CLAUDE.md - VertretungsFlow Development Guide

Dieses Dokument hilft Claude (und anderen Entwicklern) beim Arbeiten mit dem VertretungsFlow-Projekt.

## Projektübersicht

**VertretungsFlow** ist ein Absenzverwaltungssystem für Schulen mit:
- **FastAPI Backend** (Python) für Geschäftslogik und Datenhaltung
- **React Frontend** (TypeScript) als WordPress-Plugin
- **PostgreSQL** Datenbank
- **Docker-Compose** für Deployment

### Hauptfunktionen
- Lehrkräfte melden Absenzen (Krankheit, Fortbildung, Exkursion, etc.)
- Automatischer Import von Stunden aus WebUntis
- Workflow: Eingereicht → Genehmigt (Abteilungsleitung) → Erledigt (Vertretungsplaner)
- File-Uploads für Nachweise (Arztbescheinigungen, Einladungen, etc.)
- Conditional Inputs basierend auf Abwesenheitsgrund

## Architektur

### Authentifizierung: WordPress Proxy Mode (Production)

Das System nutzt **WordPress-Cookie-Authentication** über einen Proxy:

1. User ist in WordPress eingeloggt (Session-Cookie)
2. Frontend ruft WordPress REST API Proxy auf (`/wp-json/vertretungsflow/v1/proxy`)
3. WordPress-Proxy leitet Request an FastAPI Backend weiter mit Custom Headers:
   - `X-WordPress-Secret`: Shared Secret zur Authentifizierung
   - `X-WordPress-User`: Username
   - `X-WordPress-Email`: E-Mail
   - `X-WordPress-Role`: VertretungsFlow-Rolle (admin/teacher/dept_head/planner)
   - `X-WordPress-WebUntis-Code`: WebUntis-Kürzel des Users
4. Backend validiert Secret und erstellt/aktualisiert User automatisch

**Wichtig:** Alle Frontend-API-Requests müssen:
- `withCredentials: true` setzen (für WordPress-Cookies)
- `X-WP-Nonce` Header mitschicken (für CSRF-Schutz)

**🔒 Sicherheit:**
- ✅ **HTTP-only cookies** - Nicht über JavaScript zugreifbar (XSS-geschützt)
- ✅ **Keine localStorage-Tokens** - Keine client-seitigen Token-Speicherung
- ✅ **Server-to-server secret** - Proxy-Validierung mit HMAC constant-time comparison
- ✅ **CSRF-Protection** - WordPress-Nonce-Validierung

**Alternative:** Standalone/LDAP Mode verfügbar (siehe [AUTHENTICATION.md](AUTHENTICATION.md))
- ⚠️ Nutzt JWT tokens in localStorage (XSS-vulnerabel)
- ⚠️ Nur für Development/Testing oder spezielle LDAP-Integration
- ⚠️ Nicht empfohlen für Production

Siehe: `backend/app/api/auth.py:get_wordpress_proxy_user()` und [AUTHENTICATION.md](AUTHENTICATION.md)

### File Uploads

**Separate Proxy-Endpoints** für Uploads/Downloads wegen multipart/form-data:
- Upload: `POST /wp-json/vertretungsflow/v1/proxy/upload/{absence_id}`
- Download: `GET /wp-json/vertretungsflow/v1/proxy/download/{absence_id}/{attachment_id}`

**Storage:**
- Container: `/app/uploads/absence_{id}/` (gemountet auf `./backend/uploads`)
- Sicherheit: UUID-basierte Dateinamen, auth-geschützter Download
- Auto-Deletion: Dateien werden gelöscht wenn Absenz auf "erledigt" gesetzt wird

Siehe: `backend/app/api/attachments.py` und `backend/app/services/attachment_service.py`

## Verzeichnisstruktur

```
AbsenzFlow/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/               # REST API Endpoints (dünn, delegieren an Services)
│   │   │   ├── absences.py    # CRUD Endpoints für Absenzen (317 LOC)
│   │   │   ├── attachments.py # File Upload/Download/Delete (183 LOC)
│   │   │   ├── webuntis.py    # WebUntis Timetable Integration (72 LOC)
│   │   │   ├── auth.py        # WordPress Proxy Auth
│   │   │   └── admin.py       # Admin Endpoints
│   │   ├── services/          # Business Logic (neu seit 2026-02-03)
│   │   │   ├── absence_service.py               # Absence CRUD Logic (323 LOC)
│   │   │   ├── absence_notification_service.py  # Absence Notifications (117 LOC)
│   │   │   ├── attachment_service.py            # File Management Logic (235 LOC)
│   │   │   ├── permission_service.py            # Centralized Authorization (134 LOC)
│   │   │   ├── pdf_service.py                   # PDF Form Generation (364 LOC)
│   │   │   ├── template_service.py              # Template Processing (138 LOC)
│   │   │   ├── email_service.py                 # Email Notifications
│   │   │   ├── webuntis_service.py              # WebUntis API Integration
│   │   │   └── ldap_service.py                  # LDAP Authentication (optional)
│   │   ├── utils/             # Helper Functions (neu seit 2026-02-03)
│   │   │   ├── email_utils.py       # get_recipients_by_roles, REASON_LABELS
│   │   │   ├── time_format_utils.py # WebUntis time formatting (126 LOC)
│   │   │   ├── absence_utils.py     # Absence validation/filtering (99 LOC)
│   │   │   └── __init__.py
│   │   ├── core/
│   │   │   ├── config.py      # Settings (Pydantic BaseSettings)
│   │   │   ├── database.py    # Database Connection
│   │   │   └── audit.py       # Audit Logging
│   │   ├── models/
│   │   │   └── models.py      # SQLAlchemy ORM Models
│   │   └── schemas/
│   │       └── schemas.py     # Pydantic Request/Response Schemas
│   ├── migrations/            # SQL Migrations (manuell)
│   ├── uploads/               # File Uploads (gemountet, in .gitignore)
│   └── requirements-base.txt  # Python Dependencies
│
├── wordpress-plugin/           # React Frontend (WordPress Plugin)
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts      # API Client (Axios, Proxy-Support)
│   │   ├── pages/
│   │   │   ├── Dashboard/     # Übersicht (Lehrer/Planer-Views)
│   │   │   ├── CreateAbsence/ # Wizard (StepOne, StepTwo)
│   │   │   └── AbsenceDetail/ # Detailansicht mit Downloads
│   │   └── types/
│   │       └── index.ts       # TypeScript Type Definitions
│   ├── includes/              # PHP Backend
│   │   ├── class-api-proxy.php    # WordPress REST API Proxy
│   │   ├── class-shortcode.php    # [vertretungsflow] Shortcode
│   │   └── class-admin.php        # Admin-Einstellungen
│   ├── build/                 # Vite Build Output (zu WordPress kopieren)
│   └── package.json
│
├── docker-compose.yml         # Docker Services (Postgres, Backend)
├── .env                       # Environment Variables (NICHT committen!)
└── .env.example               # Template für .env
```

## Wichtige Dateien

### Backend

**API Routes (dünn, delegieren an Services):**

| Datei | Beschreibung | Endpoints |
|-------|--------------|-----------|
| `backend/app/api/absences.py` | Absence CRUD Endpoints (317 LOC) | `POST /`, `GET /`, `GET /{id}`, `PATCH /{id}/lessons/{lesson_id}`, `POST /{id}/approve`, `POST /{id}/complete`, `DELETE /{id}` |
| `backend/app/api/attachments.py` | File Upload/Download/Delete (183 LOC) | `POST /{id}/attachments`, `GET /{id}/attachments/{att_id}`, `DELETE /{id}/attachments/{att_id}` |
| `backend/app/api/webuntis.py` | WebUntis Integration (72 LOC) | `POST /absences/fetch-lessons` |
| `backend/app/api/auth.py` | WordPress Proxy Auth | `get_wordpress_proxy_user()` - validiert Secret |

**Services (Business Logic):**

| Datei | Beschreibung | Wichtige Funktionen |
|-------|--------------|---------------------|
| `backend/app/services/absence_service.py` | Absence CRUD Logic (323 LOC) | `create_absence()`, `approve_absence()`, `complete_absence()`, `delete_absence()` |
| `backend/app/services/absence_notification_service.py` | Absence Notifications (117 LOC) | `send_submitted_notification()`, `send_approved_notification()`, `send_completed_notification()` |
| `backend/app/services/attachment_service.py` | File Management (235 LOC) | `validate_file()`, `save_file()`, `delete_file()`, `get_file_path()` |
| `backend/app/services/permission_service.py` | Authorization (134 LOC) | `can_view_absence()`, `can_edit_absence()`, `can_approve_absence()`, `can_complete_absence()` |
| `backend/app/services/pdf_service.py` | PDF Form Generation (364 LOC) | `get_available_forms()`, `generate_filled_pdf()` |
| `backend/app/services/template_service.py` | Template Processing (138 LOC) | `process_template_variable()`, `get_nested_value()`, `apply_filter()`, `process_field_mappings()` |
| `backend/app/services/email_service.py` | Email Notifications | `send_absence_submitted_notification()`, etc. |
| `backend/app/services/webuntis_service.py` | WebUntis API | `get_timetable_for_teacher()` |

**Utilities:**

| Datei | Beschreibung | Funktionen |
|-------|--------------|-----------|
| `backend/app/utils/email_utils.py` | Email Helpers | `get_recipients_by_roles()`, `REASON_LABELS` |
| `backend/app/utils/time_format_utils.py` | Time Formatting (126 LOC) | `format_webuntis_time()`, `get_time_from_period()`, `get_time_for_period()` |
| `backend/app/utils/absence_utils.py` | Absence Validation (99 LOC) | `validate_date_range()`, `is_lesson_in_period()` |

**Core:**

| Datei | Beschreibung | Wichtige Elemente |
|-------|--------------|-------------------|
| `backend/app/models/models.py` | Datenbank-Modelle | `Absence`, `AffectedLesson`, `AbsenceAttachment`, `User` |
| `backend/app/schemas/schemas.py` | Pydantic Schemas | Validierung mit `@field_validator` für Conditional Fields |
| `backend/app/core/config.py` | Konfiguration | `WORDPRESS_PROXY_SECRET`, `UPLOAD_DIR` |

### Frontend

| Datei | Beschreibung | Wichtige Features |
|-------|--------------|-------------------|
| `wordpress-plugin/src/api/client.ts` | API Client | Proxy-Support, Nonce-Header, Upload/Download |
| `wordpress-plugin/src/pages/CreateAbsence/StepOne.tsx` | Absenz-Wizard Schritt 1 | Conditional Inputs (Exkursion, Privat) |
| `wordpress-plugin/src/pages/CreateAbsence/StepTwo.tsx` | Absenz-Wizard Schritt 2 | Stunden-Tabelle, File-Upload, Bemerkungen |
| `wordpress-plugin/src/pages/AbsenceDetail/index.tsx` | Detailansicht | Download-Links, conditional "Kann entfallen" |
| `wordpress-plugin/includes/class-api-proxy.php` | WordPress Proxy | Leitet Requests an Backend weiter mit Auth-Headers |

## Development Workflow

### 1. Environment Setup

```bash
# .env aus Template erstellen
cp .env.example .env

# Wichtige Variablen konfigurieren:
# - WORDPRESS_PROXY_SECRET (gleicher Wert wie in WordPress Admin!)
# - LDAP_* (Active Directory)
# - WEBUNTIS_* (für Stundenimport)
# - UPLOAD_DIR=/app/uploads (für Docker)

# Dependencies installieren (Frontend)
cd wordpress-plugin
npm install

# Backend starten (Docker)
cd ..
docker-compose up -d
```

### 2. Datenbank-Migrationen

Manuelle SQL-Migrationen in `backend/migrations/`:

```bash
# Auf Deployment-Server:
docker-compose exec -T postgres psql -U absenzflow -d absenzflow < backend/migrations/001_initial.sql
```

**Konvention:** Dateien nummerieren (`001_`, `002_`, etc.), aussagekräftige Namen.

### 3. Backend-Änderungen

**Models ändern:**
1. SQLAlchemy Model in `models/models.py` anpassen
2. Migration schreiben (SQL-Datei in `migrations/`)
3. Schema in `schemas/schemas.py` aktualisieren
4. Optional: Validatoren mit `@field_validator` hinzufügen

**API-Endpoints ändern:**
1. Route in `api/absences.py` oder `api/auth.py` bearbeiten
2. Dependency Injection nutzen: `current_user: User = Depends(get_wordpress_proxy_user)`
3. Eager Loading für Performance: `.options(selectinload(...), joinedload(...))`

**Backend neu starten:**
```bash
docker-compose restart backend
# Oder für kompletten Rebuild:
docker-compose up -d --build backend
```

### 4. Frontend-Änderungen

**TypeScript entwickeln:**
```bash
cd wordpress-plugin
npm run dev  # Vite Dev Server (Hot Reload)
```

**Production Build:**
```bash
npm run build  # Erstellt build/
```

**Deployment:**
```bash
# build/* zu WordPress kopieren:
cp -r build/* /pfad/zu/wordpress/wp-content/plugins/absenzflow/build/
```

**Wichtig beim API-Client (`client.ts`):**
- `useProxy: true` für WordPress-Integration
- `withCredentials: true` für Cookies
- `X-WP-Nonce` Header für CSRF-Schutz

### 5. WordPress-Plugin-PHP ändern

**PHP-Dateien editieren:**
```bash
wordpress-plugin/includes/*.php
```

**Deployment:**
```bash
cp -r includes/* /pfad/zu/wordpress/wp-content/plugins/absenzflow/includes/
```

**Wichtig:**
- WordPress-Nonce generieren: `wp_create_nonce('wp_rest')`
- Config an Frontend übergeben: `wp_localize_script('absenzflow-app', 'vertretungsflowConfig', $config)`

## Deployment

### Deployment-Server vorbereiten

```bash
git pull origin main  # oder feature-branch

# .env prüfen:
# - WORDPRESS_PROXY_SECRET muss mit WordPress Admin übereinstimmen!
# - UPLOAD_DIR=/app/uploads (für persistente Uploads)

# Backend neu starten
docker-compose up -d --build backend

# Migrationen ausführen (falls nötig)
docker-compose exec -T postgres psql -U absenzflow -d absenzflow < backend/migrations/XXX_new.sql

# WordPress-Plugin aktualisieren
# PHP-Dateien + build/ kopieren
```

### Wichtige Environment-Variablen

| Variable | Beschreibung | Beispiel |
|----------|--------------|----------|
| `WORDPRESS_PROXY_SECRET` | **KRITISCH!** Shared Secret für Auth | `openssl rand -hex 32` |
| `UPLOAD_DIR` | Upload-Verzeichnis | `/app/uploads` (Docker) |
| `DATABASE_URL` | PostgreSQL Connection | `postgresql://user:pass@postgres:5432/db` |
| `LDAP_SERVER` | Active Directory Server | `ldap.schule.local` |
| `WEBUNTIS_*` | WebUntis API Credentials | Siehe .env.example |

**Prüfen ob Secret geladen wurde:**
```bash
docker-compose exec backend env | grep WORDPRESS_PROXY_SECRET
```

## Häufige Aufgaben

### Neues Feld zu Absences hinzufügen

1. **Backend Model** (`backend/app/models/models.py`):
   ```python
   class Absence(Base):
       new_field = Column(String, nullable=True)
   ```

2. **Migration** (`backend/migrations/00X_add_new_field.sql`):
   ```sql
   ALTER TABLE absences ADD COLUMN new_field VARCHAR(255);
   ```

3. **Schema** (`backend/app/schemas/schemas.py`):
   ```python
   class AbsenceBase(BaseModel):
       new_field: Optional[str] = None
   ```

4. **Frontend Type** (`wordpress-plugin/src/types/index.ts`):
   ```typescript
   export interface Absence {
       new_field?: string;
   }
   ```

5. **UI anpassen** (z.B. StepOne.tsx, AbsenceDetail/index.tsx)

### Conditional Field mit Validierung

**Backend Schema:**
```python
@field_validator('excursion_classes')
@classmethod
def validate_excursion_classes(cls, v, info):
    reason = info.data.get('reason')
    if reason == 'excursion' and (not v or not v.strip()):
        raise ValueError('Klasse(n) sind bei Exkursionen Pflichtfeld')
    return v
```

**Frontend:**
```tsx
{reason === 'excursion' && (
  <input
    type="text"
    value={excursionClasses}
    onChange={(e) => setExcursionClasses(e.target.value)}
    required
  />
)}
```

### Neuen API-Endpoint hinzufügen

**Backend (`backend/app/api/absences.py`):**
```python
@router.get("/custom-endpoint")
async def my_endpoint(
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db)
):
    # Berechtigungsprüfung
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Logik hier
    return {"result": "data"}
```

**Frontend (`wordpress-plugin/src/api/client.ts`):**
```typescript
async myEndpoint(): Promise<MyResponse> {
  return this.request<MyResponse>({
    method: 'GET',
    url: '/custom-endpoint',
  });
}
```

### Uploads debuggen

**Prüfen ob Dateien ankommen:**
```bash
# Im Container
docker-compose exec backend ls -la /app/uploads/absence_*/

# Auf Host
ls -la backend/uploads/absence_*/

# Backend-Logs
docker-compose logs backend | grep -i upload
```

**WordPress-Logs:**
```bash
tail -f /pfad/zu/wordpress/wp-content/debug.log | grep VertretungsFlow
```

## Debugging

### 401 "Invalid proxy secret"

**Checkliste:**
1. Ist `WORDPRESS_PROXY_SECRET` in Backend `.env` gesetzt?
2. Ist derselbe Wert in WordPress Admin (Einstellungen → VertretungsFlow) eingetragen?
3. Wurde Backend nach `.env`-Änderung neu gestartet?
4. Ist Secret in `docker-compose.yml` unter `backend.environment` gelistet?

**Debug-Commands:**
```bash
# Backend Secret prüfen
docker-compose exec backend env | grep WORDPRESS_PROXY_SECRET

# WordPress Secret prüfen (MySQL)
wp option get vertretungsflow_options --format=json
```

### 401 "Not authenticated" (ohne "Invalid proxy secret")

**Checkliste:**
1. Ist User in WordPress eingeloggt?
2. Wird `X-WP-Nonce` Header mitgeschickt?
3. Ist `withCredentials: true` bei axios-Request?
4. Ist WordPress-Nonce in `window.vertretungsflowConfig.nonce` verfügbar?

**Fix:**
- PHP: `wp_create_nonce('wp_rest')` generieren und in `wp_localize_script()` übergeben
- TypeScript: `'X-WP-Nonce': window.vertretungsflowConfig?.nonce` in Request-Header

### N+1 Query Problem

**Symptom:** Viele wiederholte DB-Queries im Backend-Log.

**Lösung:** Eager Loading mit SQLAlchemy:
```python
absences = db.query(Absence).options(
    selectinload(Absence.affected_lessons),
    selectinload(Absence.attachments),
    joinedload(Absence.teacher)
).all()
```

### Uploads verschwinden nach Container-Restart

**Ursache:** `UPLOAD_DIR` zeigt auf Pfad der nicht gemountet ist.

**Lösung:**
```bash
# .env
UPLOAD_DIR=/app/uploads

# docker-compose.yml prüfen:
# volumes:
#   - ./backend:/app
```

### Frontend Build schlägt fehl

**Häufige Ursachen:**
1. TypeScript-Fehler → `npm run build` zeigt Fehler
2. Missing dependencies → `npm install`
3. Node-Version inkompatibel → Node 18+ erforderlich

**Debug:**
```bash
cd wordpress-plugin
npm run build  # Zeigt detaillierte Fehler
```

## Coding Conventions

### Backend (Python)

- **Docstrings:** Alle public Functions mit Args/Returns dokumentieren
- **Type Hints:** Überall verwenden (`def foo(x: int) -> str:`)
- **Pydantic:** Validierung mit `@field_validator` für komplexe Regeln
- **Logging:** `logger.info()` für wichtige Events, `logger.error()` für Fehler
- **Imports:** Absolute Imports (`from app.models.models import User`)

#### Code Formatierung mit Black

**Black** ist der obligatorische Code-Formatter (line-length = 88). Konfiguration in `backend/pyproject.toml`.

```bash
# Vor jedem Commit: Backend-Code formatieren
cd backend
black .

# Nur prüfen (kein Ändern):
black . --check

# Im Docker-Container:
docker-compose exec backend black .
```

**Wichtige Black-Regeln (für AI-generierte Code-Blöcke):**

```python
# ✅ Kurze UUID-Strings: eine Zeile
mock_uuid.return_value = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

# ✅ Lange Funktionsaufrufe: umbrechen wenn > 88 Zeichen
with patch(
    "uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")
):

# ✅ Kurze Funktionssignaturen: eine Zeile
def test_get_file_path(self, attachment_service, temp_upload_dir):

# ✅ Leerzeile vor Klassen-Body und nach letzter Methode vor Kommentar-Block
```

**CI prüft automatisch:**
```bash
# In .gitlab-ci.yml (lint_backend stage):
black . --check
```

> **Hinweis für Claude:** Generierten Python-Code immer so schreiben, dass er Black-konform ist (88 Zeichen Zeilenlänge). Im Zweifelsfall `black .` im Container ausführen lassen.

### Frontend (TypeScript)

- **Types:** Nie `any` verwenden, alle Props typisieren
- **Interfaces:** In `src/types/index.ts` zentral definieren
- **API-Client:** Alle Backend-Calls über `api` Singleton
- **Components:** Functional Components mit TypeScript (`React.FC`)
- **State:** `useState` für lokalen State, Props für Parent-Child-Kommunikation

### Git

- **Branch-Namen:** `feature/beschreibung`, `fix/bug-name`
- **Commits:** Aussagekräftige Messages, deutsch oder englisch konsistent
- **Co-Authoring:** Claude als Co-Author taggen:
  ```
  Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
  ```

## Testing

### Manueller E2E-Test

1. **Login** als Lehrkraft in WordPress
2. **Absenz erstellen:**
   - Grund wählen (z.B. "Exkursion")
   - Conditional Input erscheint (Klassen-Feld)
   - Datum wählen, Weiter
   - Stunden aus WebUntis importiert ✓
   - Bemerkungen eingeben
   - Datei hochladen (PDF/JPG)
   - Absenden
3. **Prüfen:**
   - Dashboard zeigt Absenz
   - Detailansicht: Alle Felder korrekt, Download-Link funktioniert
   - Backend: `ls backend/uploads/absence_X/` zeigt Datei
4. **Als Planner einloggen:**
   - Absenz genehmigen
   - Absenz auf "Erledigt" setzen
   - Prüfen: Datei wurde gelöscht (`ls backend/uploads/absence_X/` leer)

### Backend Unit Tests (TODO)

Aktuell keine automatisierten Tests. Zukünftig mit `pytest`:

```bash
cd backend
pytest tests/
```

## Troubleshooting

### Docker-Container startet nicht

```bash
# Logs anschauen
docker-compose logs backend

# Häufige Fehler:
# - DATABASE_URL falsch → .env prüfen
# - Port bereits belegt → docker-compose.yml Ports ändern
# - .env nicht geladen → docker-compose down && up -d
```

### WordPress zeigt weißen Bildschirm

```bash
# PHP-Fehler aktivieren (wp-config.php):
define('WP_DEBUG', true);
define('WP_DEBUG_LOG', true);

# Logs checken:
tail -f wp-content/debug.log
```

### Build funktioniert lokal aber nicht auf Server

**Checkliste:**
1. Node-Version gleich? (`node --version`)
2. Dependencies installiert? (`npm install`)
3. Dateiberechtigungen? (`chmod -R 755 build/`)

## Nützliche Commands

```bash
# Backend neu starten (schnell)
docker-compose restart backend

# Backend neu bauen (nach requirements.txt Änderung)
docker-compose up -d --build backend

# Backend Logs live anschauen
docker-compose logs -f backend

# Postgres-Shell öffnen
docker-compose exec postgres psql -U absenzflow -d absenzflow

# WordPress-Plugin Build
cd wordpress-plugin && npm run build

# Git: Alle Änderungen committen mit Claude Co-Author
git add . && git commit -m "Your message

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

## Weiterführende Dokumentation

- **Authentication:** [AUTHENTICATION.md](AUTHENTICATION.md) - WordPress Proxy vs LDAP/Standalone modes, security comparison
- **Deployment:** [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment guide, security checklist
- **Security Audit:** [SEC-AUDIT.md](SEC-AUDIT.md) - Security assessment and recommendations
- **API Endpoints:** FastAPI Docs: `http://localhost:8000/docs`
- **WordPress Plugin:** Inline-Kommentare in PHP-Dateien
- **Environment Vars:** [.env.example](.env.example) mit allen Optionen und Sicherheitshinweisen

## Refactoring-Historie

### 2026-02-06: PDF Service Refactoring - Separation of Concerns

**Problem:** `backend/app/services/pdf_service.py` war mit 564 LOC zu groß und hatte drei gemischte Verantwortlichkeiten (Template Processing, Time Calculations, PDF Generation).

**Lösung:** Aufspaltung in fokussierte Module
1. **Template Service extrahiert** (Template Variable Processing)
   - `template_service.py` (138 LOC) - Template Processing Service
   - Methoden: `process_template_variable()`, `get_nested_value()`, `apply_filter()`, `process_field_mappings()`
2. **Time Utils extrahiert** (Pure Functions für Zeit-Formatierung)
   - `time_format_utils.py` (126 LOC) - WebUntis Time Formatting Utils
   - Funktionen: `format_webuntis_time()`, `get_time_from_period()`, `get_time_for_period()`
3. **PDF Service geschrumpft** (Fokus auf PDF Generation)
   - `pdf_service.py` von 564 LOC → 364 LOC (35% Reduktion)
   - Behält: Config Loading, Form Selection, PDF Merging mit pypdf

**Ergebnis:**
- ✅ `pdf_service.py` von 564 LOC → 364 LOC (35% Reduktion)
- ✅ Separation of Concerns (Template, Time, PDF getrennt)
- ✅ Wiederverwendbarkeit (Template Service für andere Features nutzbar)
- ✅ Testbarkeit (Pure Functions in utils leichter testbar)
- ✅ Folgt Codebase-Patterns (Service + Utils wie email_service/email_utils)

**Von:** Claude Sonnet 4.5 (mit User Seyfried)

### 2026-02-06: Absence Service Refactoring - Notification & Validation Extraction

**Problem:** `backend/app/services/absence_service.py` war mit 479 LOC zu groß und hatte gemischte Verantwortlichkeiten (CRUD Logic, Email Notifications, Validation).

**Lösung:** Extraktion in spezialisierte Module
1. **Notification Service extrahiert** (Email-Benachrichtigungen)
   - `absence_notification_service.py` (117 LOC) - Absence Notification Service
   - Methoden: `send_submitted_notification()`, `send_approved_notification()`, `send_completed_notification()`
2. **Validation Utils extrahiert** (Pure Functions für Validierung)
   - `absence_utils.py` (99 LOC) - Absence Validation & Filtering Utils
   - Funktionen: `validate_date_range()`, `is_lesson_in_period()`
3. **Absence Service geschrumpft** (Fokus auf CRUD Logic)
   - `absence_service.py` von 479 LOC → 323 LOC (33% Reduktion)
   - Behält: `create_absence()`, `approve_absence()`, `complete_absence()`, `delete_absence()`

**Ergebnis:**
- ✅ `absence_service.py` von 479 LOC → 323 LOC (33% Reduktion)
- ✅ Separation of Concerns (CRUD, Notifications, Validation getrennt)
- ✅ Wiederverwendbarkeit (Notification Service für andere Absence-Events nutzbar)
- ✅ Testbarkeit (Pure Validation-Functions leichter testbar)
- ✅ Folgt etablierte Patterns (Service + Utils Struktur konsistent)

**Von:** Claude Sonnet 4.5 (mit User Seyfried)

### 2026-02-03: Backend-Refactoring - Services & Routes-Aufteilung

**Problem:** `backend/app/api/absences.py` war mit 993 LOC zu groß und schwer wartbar.

**Lösung:** 3-Layer-Refactoring
1. **Services extrahiert** (Business Logic aus Routes)
   - `absence_service.py` (417 LOC) - Absence CRUD Logic
   - `attachment_service.py` (235 LOC) - File Management
   - `permission_service.py` (134 LOC) - Authorization
2. **Routes aufgeteilt** (nach Feature)
   - `absences.py` (317 LOC) - Absence CRUD Endpoints
   - `attachments.py` (183 LOC) - File Upload/Download/Delete
   - `webuntis.py` (72 LOC) - WebUntis Integration
3. **Utils erstellt** (Wiederverwendbare Helpers)
   - `email_utils.py` - `get_recipients_by_roles()`, `REASON_LABELS`

**Ergebnis:**
- ✅ `absences.py` von 993 LOC → 317 LOC (68% Reduktion)
- ✅ Bessere Testbarkeit (Services unabhängig testbar)
- ✅ Wiederverwendbarkeit (Services können von mehreren Routes genutzt werden)
- ✅ DRY (keine Code-Duplikation mehr bei Permission-Checks, Validierung, Email-Logik)
- ✅ Klare Verantwortlichkeiten (Single Responsibility Principle)

**Von:** Claude Sonnet 4.5 (mit User Seyfried)

## Letzte Aktualisierung

- Datum: 2026-02-06
- Version: Nach Service Refactorings (PDF Service + Absence Service)
- Von: Claude Sonnet 4.5 (mit User Seyfried)

---

**Hinweis für Claude:** Bei Unklarheiten immer fragen, nicht raten! Der User kennt das System gut und kann kontextuelle Informationen liefern.
