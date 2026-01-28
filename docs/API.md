# AbsenzFlow API Dokumentation

REST API für AbsenzFlow Backend

## Base URL

```
http://localhost:8000/api
```

## Authentifizierung

Alle API-Requests (außer `/auth/login`) benötigen einen JWT Token im Authorization Header:

```
Authorization: Bearer <token>
```

---

## Authentication Endpoints

### POST /auth/login

Authentifizierung gegen LDAP und JWT Token Generierung.

**Request Body**:
```json
{
  "username": "max.mustermann",
  "password": "passwort123"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors**:
- `401 Unauthorized`: Falsche Credentials

---

### GET /auth/me

Gibt Informationen über aktuellen User zurück.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "id": 1,
  "username": "max.mustermann",
  "email": "max.mustermann@schule.de",
  "full_name": "Max Mustermann",
  "role": "teacher",
  "is_active": true,
  "created_at": "2024-01-15T10:00:00"
}
```

---

## Absence Endpoints

### POST /absences/

Erstellt neue Abwesenheitsmeldung.

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "reason": "Fortbildung",
  "start_date": "2024-02-01T08:00:00",
  "end_date": "2024-02-01T13:00:00",
  "start_period": 1,
  "end_period": 6
}
```

**Response** (201 Created):
```json
{
  "id": 42,
  "teacher_id": 1,
  "reason": "Fortbildung",
  "start_date": "2024-02-01T08:00:00",
  "end_date": "2024-02-01T13:00:00",
  "start_period": 1,
  "end_period": 6,
  "status": "submitted",
  "created_at": "2024-01-20T14:30:00",
  "teacher": {
    "id": 1,
    "username": "max.mustermann",
    "full_name": "Max Mustermann"
  },
  "affected_lessons": [
    {
      "id": 100,
      "absence_id": 42,
      "date": "2024-02-01T08:00:00",
      "period": 1,
      "subject": "Mathematik",
      "class_name": "10a",
      "room": "A201",
      "notes": null
    }
  ]
}
```

---

### GET /absences/

Listet Abwesenheiten auf.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `skip` (optional): Anzahl zu überspringen (default: 0)
- `limit` (optional): Maximale Anzahl (default: 100)
- `status` (optional): Filter nach Status (`submitted`, `approved`, `completed`, `rejected`)

**Response** (200 OK):
```json
[
  {
    "id": 42,
    "teacher_id": 1,
    "reason": "Fortbildung",
    "status": "submitted",
    "teacher": {...},
    "affected_lessons": [...]
  }
]
```

**Zugriff**:
- Lehrkräfte: Nur eigene Abwesenheiten
- Abteilungsleiter & Vertretungsplaner: Alle Abwesenheiten

---

### GET /absences/{absence_id}

Holt einzelne Abwesenheit.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "id": 42,
  "teacher_id": 1,
  "reason": "Fortbildung",
  "affected_lessons": [...]
}
```

**Errors**:
- `404 Not Found`: Abwesenheit nicht gefunden
- `403 Forbidden`: Keine Berechtigung

---

### PATCH /absences/{absence_id}/lessons/{lesson_id}

Aktualisiert Hinweise für betroffene Stunde.

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "notes": "Klasse bearbeitet Projekt selbstständig"
}
```

**Response** (200 OK):
```json
{
  "id": 100,
  "absence_id": 42,
  "date": "2024-02-01T08:00:00",
  "period": 1,
  "subject": "Mathematik",
  "class_name": "10a",
  "room": "A201",
  "notes": "Klasse bearbeitet Projekt selbstständig"
}
```

**Errors**:
- `400 Bad Request`: Abwesenheit bereits erledigt
- `403 Forbidden`: Keine Berechtigung

---

### POST /absences/{absence_id}/approve

Genehmigt oder lehnt Abwesenheit ab.

**Headers**: `Authorization: Bearer <token>`

**Rolle**: Nur Abteilungsleiter

**Request Body**:
```json
{
  "approved": true,
  "notes": "Genehmigt"
}
```

**Response** (200 OK):
```json
{
  "message": "Absence approved"
}
```

**Errors**:
- `403 Forbidden`: Keine Berechtigung (nicht Abteilungsleiter)
- `400 Bad Request`: Status nicht "submitted"

---

### POST /absences/{absence_id}/complete

Markiert Abwesenheit als erledigt/eingetragen.

**Headers**: `Authorization: Bearer <token>`

**Rolle**: Nur Vertretungsplaner

**Response** (200 OK):
```json
{
  "message": "Absence marked as completed"
}
```

**Errors**:
- `403 Forbidden`: Keine Berechtigung
- `400 Bad Request`: Status nicht "approved"

---

### DELETE /absences/{absence_id}

Löscht Abwesenheit.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "message": "Absence deleted"
}
```

**Regeln**:
- Nur eigene Abwesenheiten
- Nur Status "draft" oder "submitted"

---

## Admin Endpoints

### GET /admin/users

Listet alle Benutzer auf.

**Headers**: `Authorization: Bearer <token>`

**Rolle**: Admin oder Abteilungsleiter

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "username": "max.mustermann",
    "email": "max.mustermann@schule.de",
    "full_name": "Max Mustermann",
    "role": "teacher",
    "is_active": true
  }
]
```

---

### POST /admin/users/{user_id}/role

Weist Rolle zu.

**Headers**: `Authorization: Bearer <token>`

**Rolle**: Nur Admin

**Request Body**:
```json
{
  "user_id": 1,
  "role": "dept_head"
}
```

**Response** (200 OK):
```json
{
  "id": 1,
  "username": "max.mustermann",
  "role": "dept_head"
}
```

---

### GET /admin/dashboard

Dashboard Statistiken.

**Headers**: `Authorization: Bearer <token>`

**Rolle**: Vertretungsplaner, Abteilungsleiter, Admin

**Response** (200 OK):
```json
{
  "pending_absences": 5,
  "approved_absences": 12,
  "completed_absences": 48,
  "total_affected_lessons": 156
}
```

---

### GET /admin/absences/pending

Ausstehende Abwesenheiten sortiert nach Datum.

**Headers**: `Authorization: Bearer <token>`

**Rolle**: Vertretungsplaner, Abteilungsleiter, Admin

**Response** (200 OK):
```json
[
  {
    "id": 42,
    "teacher_id": 1,
    "reason": "Fortbildung",
    "start_date": "2024-02-01T08:00:00",
    "status": "submitted"
  }
]
```

---

## Status Codes

- `200 OK`: Erfolgreiche GET/PATCH/DELETE Anfrage
- `201 Created`: Ressource erstellt (POST)
- `400 Bad Request`: Ungültige Eingabe
- `401 Unauthorized`: Nicht authentifiziert
- `403 Forbidden`: Keine Berechtigung
- `404 Not Found`: Ressource nicht gefunden
- `500 Internal Server Error`: Server-Fehler

---

## Fehler-Format

```json
{
  "detail": "Error message"
}
```

---

## Rollen

- `teacher`: Lehrkraft
- `dept_head`: Abteilungsleiter
- `planner`: Vertretungsplaner
- `admin`: Administrator

---

## Status Werte

- `draft`: Entwurf
- `submitted`: Eingereicht
- `approved`: Genehmigt
- `completed`: Eingetragen/Erledigt
- `rejected`: Abgelehnt
