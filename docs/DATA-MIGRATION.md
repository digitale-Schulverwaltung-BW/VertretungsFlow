# DATA-MIGRATION.md — VertretungsFlow Backend-Umzug

Dieses Dokument beschreibt den vollständigen Umzug einer laufenden VertretungsFlow-Instanz
auf eine neue Maschine, inklusive Wechsel von Development- auf Production-Modus.

**Was migriert wird:**
- PostgreSQL-Datenbank (alle Abwesenheiten, User, Lektionen, Anhänge-Metadaten)
- `backend/uploads/` — hochgeladene Dateien (Arztbescheinigungen etc.)
- `.env` — Konfiguration und Secrets

---

## Vorbereitung

### Auf der Quellmaschine

Sicherstellen, dass keine Aktionen laufen (kein Upload, kein laufendes Approval):

```bash
# Laufende Container prüfen
docker-compose ps

# Letzte Backend-Aktivität im Log prüfen (optional)
docker-compose logs --tail=20 backend
```

---

## Schritt 1 — Datenbank-Dump erstellen (Quellmaschine)

```bash
# Dump in das Backend-Verzeichnis schreiben (ist bereits im Mount)
docker-compose exec -T postgres pg_dump \
  -U absenzflow \
  -d absenzflow \
  --no-owner \
  --no-acl \
  -F c \
  -f /tmp/absenzflow_dump.dump

# Dump aus dem Container auf den Host kopieren
docker cp absenzflow-db:/tmp/absenzflow_dump.dump ./absenzflow_dump.dump
```

> **`-F c`** erzeugt ein binäres Custom-Format — kompakter als SQL-Text und von
> `pg_restore` direkt importierbar. Mit `--no-owner`/`--no-acl` spielen User-Namen
> auf der Zielmaschine keine Rolle.

---

## Schritt 2 — Uploads-Verzeichnis packen (Quellmaschine)

```bash
# Alle hochgeladenen Anhänge sichern
tar -czf absenzflow_uploads.tar.gz -C backend uploads/
```

---

## Schritt 3 — Dateien zur Zielmaschine übertragen

```bash
# Auf der Quellmaschine — Zieladresse anpassen:
scp absenzflow_dump.dump absenzflow_uploads.tar.gz user@ZIELMASCHINE:/tmp/
```

Alternativ via `rsync`, USB, SFTP — Hauptsache die drei Dateien kommen an:
- `absenzflow_dump.dump`
- `absenzflow_uploads.tar.gz`

---

## Schritt 4 — Zielmaschine vorbereiten

### 4a — Code auschecken

```bash
git clone <repo-url> VertretungsFlow
cd VertretungsFlow
```

Oder falls bereits ausgecheckt:

```bash
git pull origin main
```

### 4b — `.env` anlegen

```bash
cp .env.example .env
# Jetzt .env bearbeiten — ALLE Secrets MÜSSEN gesetzt werden:
```

Pflichtfelder für Production:

| Variable | Beschreibung | Generieren mit |
|---|---|---|
| `POSTGRES_PASSWORD` | DB-Passwort | `openssl rand -base64 32` |
| `SECRET_KEY` | JWT-Secret | `openssl rand -hex 32` |
| `WORDPRESS_PROXY_SECRET` | Proxy-Auth-Secret | `openssl rand -hex 32` |
| `CORS_ORIGINS` | Nur Production-Domain, kein localhost | — |
| `FRONTEND_URL` | WordPress-Seite mit `[vertretungsflow]` | — |

> ⚠️ `WORDPRESS_PROXY_SECRET` muss identisch mit dem Wert in den WordPress Admin-Einstellungen sein.
> Wenn du es änderst, musst du es auch dort aktualisieren.

### 4c — Docker-Netzwerk anlegen

Das externe Netzwerk `absenzflow-shared` ist in `docker-compose.prod.yml` als `external: true`
deklariert — Docker Compose verweigert den Start wenn es nicht existiert, auch wenn es nicht
genutzt wird. Daher immer anlegen:

```bash
docker network create absenzflow-shared
```

**Wofür wird es gebraucht?**
- **WordPress auf derselben Maschine (Docker):** Ermöglicht dem WordPress-Container das Backend
  per Container-Name zu erreichen (`http://absenzflow-backend:8000`). WordPress-Container muss
  ebenfalls in dieses Netzwerk eingebunden werden.
- **WordPress auf einer anderen Maschine:** Das Netzwerk ist funktional nutzlos — WordPress
  spricht das Backend per IP/Hostname an. Der Befehl ist trotzdem nötig, damit docker-compose
  nicht abbricht. Optional kann das Netzwerk als separater Cleanup-Commit aus
  `docker-compose.prod.yml` entfernt werden (Backend-Service und `networks:`-Block).

### 4d — Uploads-Verzeichnis wiederherstellen

```bash
# Uploads in das richtige Verzeichnis entpacken
tar -xzf /tmp/absenzflow_uploads.tar.gz -C backend/

# Ergebnis prüfen
ls backend/uploads/
```

---

## Schritt 5 — Container starten (ohne Backend, nur Postgres)

```bash
docker-compose -f docker-compose.prod.yml up -d postgres

# Warten bis Postgres bereit ist
docker-compose -f docker-compose.prod.yml ps
# → postgres sollte "healthy" zeigen
```

---

## Schritt 6 — Datenbank-Dump importieren

```bash
# Dump in den Container kopieren
docker cp /tmp/absenzflow_dump.dump absenzflow-db:/tmp/absenzflow_dump.dump

# Dump einspielen
docker-compose -f docker-compose.prod.yml exec -T postgres pg_restore \
  -U absenzflow \
  -d absenzflow \
  --no-owner \
  --no-acl \
  -F c \
  /tmp/absenzflow_dump.dump
```

> Falls die Datenbank noch Daten aus einem früheren Test enthält, vorher leeren:
> ```bash
> docker-compose -f docker-compose.prod.yml exec -T postgres \
>   psql -U absenzflow -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
> ```

---

## Schritt 7 — Alle Container starten

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

Logs prüfen:

```bash
docker-compose -f docker-compose.prod.yml logs -f backend
```

Erwartete Ausgabe (keine Fehler, kein "Invalid proxy secret"):

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Schritt 8 — Verifikation

### Datenbank-Inhalt prüfen

```bash
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U absenzflow -d absenzflow -c "SELECT COUNT(*) FROM absences;"
```

→ Zahl muss mit der Quellmaschine übereinstimmen.

### Uploads prüfen

```bash
ls backend/uploads/absence_*/
```

→ Dateien müssen vorhanden sein.

### API Health Check

```bash
curl http://localhost:8000/api/health
# oder
curl http://localhost:8000/docs
```

---

## Schritt 9 — WordPress-Plugin umschalten

Im WordPress-Admin unter **Einstellungen → VertretungsFlow**:

1. **Backend API URL** auf die neue Maschine setzen (z.B. `http://neue-maschine:8000/api`)
2. **Backend API Secret** — muss identisch mit `WORDPRESS_PROXY_SECRET` in der neuen `.env` sein

Ersten Request im Backend-Log beobachten:

```bash
docker-compose -f docker-compose.prod.yml logs -f backend | grep -E "POST|GET|401"
```

---

## Rollback

Falls etwas schiefläuft, ist die alte Instanz noch intakt (sie wurde nur gestoppt, nicht gelöscht). Einfach auf der Quellmaschine wieder starten:

```bash
docker-compose up -d
```

Und im WordPress-Admin die API URL zurücksetzen.

---

## Aufräumen (nach erfolgreicher Migration)

Erst aufräumen, wenn die neue Instanz mindestens einen vollen Tag stabil läuft:

```bash
# Auf der Quellmaschine — Container und Volume entfernen
docker-compose down -v  # -v löscht das postgres_data Volume!

# Temporäre Dump-Dateien löschen
rm absenzflow_dump.dump absenzflow_uploads.tar.gz
# Auf der Zielmaschine:
rm /tmp/absenzflow_dump.dump /tmp/absenzflow_uploads.tar.gz
```

> ⚠️ `docker-compose down -v` löscht das Datenbank-Volume unwiderruflich.
> Erst ausführen wenn du sicher bist, dass die Migration erfolgreich war.
