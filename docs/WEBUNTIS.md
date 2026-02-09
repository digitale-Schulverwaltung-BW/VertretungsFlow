# WebUntis Integration

Dokumentation zur Integration von AbsenzFlow mit WebUntis.

## Überblick

AbsenzFlow nutzt die WebUntis JSON-RPC API, um:
- Stundenpläne von Lehrkräften abzurufen
- Betroffene Stunden bei Abwesenheiten zu identifizieren
- Klassen-, Fach- und Rauminformationen zu erhalten

## API-Zugang einrichten

### 1. API-Benutzer in WebUntis erstellen

1. In WebUntis als Administrator einloggen
2. **Verwaltung → Stammdaten → Lehrer**
3. Neuen Lehrer anlegen:
   - Name: "API"
   - Vorname: "AbsenzFlow"
   - Kürzel: "API" oder ähnlich
   - E-Mail: optional
4. Unter **Rechte** dem User folgende Berechtigungen geben:
   - Stundenpläne lesen
   - Lehrerdaten lesen
   - Klassendaten lesen
   - Fachdaten lesen

### 2. Credentials notieren

- **Server:** z.B. `neilo.webuntis.com` (ohne `https://`)
- **Schulname:** Ihr Schulname in WebUntis
- **Username:** Benutzername des API-Users
- **Password:** Passwort des API-Users

### 3. In AbsenzFlow konfigurieren

In der `.env` Datei:

```env
WEBUNTIS_SERVER=neilo.webuntis.com
WEBUNTIS_USERNAME=api
WEBUNTIS_PASSWORD=ihr_passwort
```

## API-Nutzung

### Authentifizierung

```python
from app.services.webuntis import webuntis_service

# Authentifizieren
await webuntis_service.authenticate()

# Nach Nutzung ausloggen
await webuntis_service.logout()
```

### Stundenplan abrufen

```python
from datetime import date

# Stundenplan für eine Lehrkraft abrufen
lessons = await webuntis_service.get_teacher_timetable(
    teacher_username="max.mustermann",
    start_date=date(2024, 2, 15),
    end_date=date(2024, 2, 15)
)

# Gibt Liste von WebUntisLesson-Objekten zurück
for lesson in lessons:
    print(f"{lesson.class_name} - {lesson.subject} in {lesson.room}")
```

### Betroffene Stunden bei Abwesenheit

```python
# Stunden für eine Abwesenheit abrufen
affected_lessons = await webuntis_service.get_lessons_for_absence(
    teacher_username="max.mustermann",
    start_date=date(2024, 2, 15),
    end_date=date(2024, 2, 16),
    start_lesson=1,
    end_lesson=6
)
```

## Stundennummern-Mapping

Die WebUntis API gibt Zeiten zurück, keine Stundennummern. AbsenzFlow berechnet die Stundennummer basierend auf der Startzeit:

```python
def _calculate_lesson_number(self, start_time: int) -> int:
    """
    Beispiel: 800 (08:00 Uhr) → Stunde 1
    """
    hour = start_time // 100
    minute = start_time % 100
    
    # Annahme: 1. Stunde beginnt um 8:00
    minutes_since_start = (hour - 8) * 60 + minute
    lesson_number = (minutes_since_start // 50) + 1
    
    return max(1, min(12, lesson_number))
```

**⚠️ Wichtig:** Passen Sie diese Funktion an Ihren Stundenplan an!

Beispiel für angepasstes Mapping:

```python
# Für Schule mit anderen Zeiten
LESSON_TIMES = {
    1: (750, 835),   # 07:50 - 08:35
    2: (840, 925),   # 08:40 - 09:25
    3: (945, 1030),  # 09:45 - 10:30
    # ...
}

def _calculate_lesson_number(self, start_time: int) -> int:
    for lesson_num, (start, end) in LESSON_TIMES.items():
        if start <= start_time < end:
            return lesson_num
    return 1  # Fallback
```

## Häufige Probleme

### Authentifizierung schlägt fehl

**Fehler:** "WebUntis authentication error"

**Lösungen:**
- Server-URL ohne `https://` oder `http://` angeben
- Schulname exakt wie in WebUntis eingeben (Groß-/Kleinschreibung beachten)
- API-User-Credentials überprüfen
- Firewall-Regeln prüfen (Port 443 ausgehend)

### Keine Stunden werden gefunden

**Mögliche Ursachen:**
- Teacher-Username stimmt nicht mit WebUntis-Kürzel überein
- Zeitraum liegt außerhalb des Schuljahres
- Lehrkraft hat keine Stunden in diesem Zeitraum
- Stunden wurden als "irregulär" oder "entfallen" markiert

**Debug:**
```python
# Alle Lehrer abrufen
teachers = await webuntis_service._request("getTeachers")
print(teachers)

# Richtiges Kürzel finden
for teacher in teachers:
    print(f"{teacher['name']}: {teacher['id']}")
```

### Stundennummern stimmen nicht

Die Berechnung der Stundennummern aus Uhrzeiten muss an Ihren Stundenplan angepasst werden. Siehe "Stundennummern-Mapping" oben.

## API-Rate-Limits

WebUntis hat keine offiziellen Rate-Limits dokumentiert, aber:
- Vermeiden Sie zu viele Requests in kurzer Zeit
- Cachen Sie Stundenplan-Daten wenn möglich
- Nutzen Sie Batch-Requests für mehrere Tage

## API-Referenz

Offizielle WebUntis API-Dokumentation:
https://help.untis.at/hc/de/articles/4403351094034-General-documentation-for-integration-partners

### Wichtige Endpoints

#### authenticate
```json
{
  "id": "AbsenzFlow",
  "method": "authenticate",
  "params": {
    "user": "api-user",
    "password": "password",
    "client": "AbsenzFlow"
  }
}
```

#### getTimetable
```json
{
  "id": "AbsenzFlow",
  "method": "getTimetable",
  "params": {
    "id": 123,
    "type": 2,
    "startDate": "20240215",
    "endDate": "20240215"
  }
}
```

**Type-Werte:**
- 1: Klasse
- 2: Lehrer
- 3: Fach
- 4: Raum
- 5: Schüler

#### getTeachers
```json
{
  "id": "AbsenzFlow",
  "method": "getTeachers"
}
```

## Erweiterte Features (Phase 2)

Geplant für zukünftige Versionen:
- Automatisches Eintragen von Vertretungen in WebUntis
- Sync von Raumbuchungen
- Benachrichtigungen bei Stundenplanänderungen
- Import von Ferien-/Feiertagskalendern

## Testing

Für lokale Entwicklung ohne WebUntis-Zugang können Mock-Daten verwendet werden:

```python
# In .env
USE_MOCK_WEBUNTIS=true
```

Dann werden statische Testdaten zurückgegeben statt echte API-Calls.
