# PDF Form Field Tools

Werkzeuge zum Arbeiten mit PDF-Formularfeldern für das AbsenzFlow-System.

## Übersicht

Wenn neue PDF-Formulare vom Kultusministerium herausgegeben werden, müssen die Formularfelder identifiziert und gemappt werden. Diese Scripts helfen dabei.

## Scripts

### 1. `extract_pdf_fields.py` - Formularfelder auslesen

**Zweck:** Zeigt alle Formularfelder eines PDFs mit Name, Typ, aktuellem Wert und Flags an.

**Usage:**
```bash
# Im Backend-Container
docker-compose exec backend python scripts/extract_pdf_fields.py /app/assets/1211.pdf

# Von außerhalb des Containers
docker-compose exec backend python scripts/extract_pdf_fields.py /pfad/zur/datei.pdf
```

**Output:**
```
📄 Field: Nachname
   Type:     Text
   Value:    (empty)
   Flags:    0 (binary: 0b0)

📄 Field: Vorname_2
   Type:     Text
   Value:    (empty)
   Flags:    0 (binary: 0b0)
```

**Wann verwenden:**
- Neues PDF-Formular erhalten
- Feldnamen für Mapping-Config benötigt
- Prüfen, welche Felder im PDF vorhanden sind

---

### 2. `fill_pdf_with_field_names.py` - PDF mit Feldnamen befüllen

**Zweck:** Befüllt jedes Formularfeld mit seinem eigenen Namen. Dadurch kann man im PDF sehen, wo welcher Feldname steht.

**Usage:**
```bash
# Im Backend-Container
docker-compose exec backend python scripts/fill_pdf_with_field_names.py \
    /app/assets/1211.pdf \
    /app/scripts/1211_labeled.pdf

# Mehrere PDFs gleichzeitig
docker-compose exec backend python scripts/fill_pdf_with_field_names.py \
    /app/assets/1211.pdf /app/scripts/1211_labeled.pdf && \
docker-compose exec backend python scripts/fill_pdf_with_field_names.py \
    /app/assets/1201.pdf /app/scripts/1201_labeled.pdf

# PDFs ins Projekt-Root kopieren
cp backend/scripts/*_labeled.pdf .
```

**Output:**
```
📄 Reading PDF: /app/assets/1211.pdf
✅ Found 49 form fields
📝 Filling 49 fields with their names...
   ✓ Updated fields on page 1
   ✓ Updated fields on page 2
💾 Writing output to: /app/scripts/1211_labeled.pdf
✅ Done! Generated /app/scripts/1211_labeled.pdf (50471 bytes)
```

**Wann verwenden:**
- Neues PDF-Formular mappen
- Herausfinden, welcher Feldname zu welcher Position gehört
- Debugging von fehlerhaften Mappings

---

### 3. `sanitize_pdf_fields.py` - Doppelte Feldnamen bereinigen 🛠️

**Zweck:** Behebt das häufige Problem von PDF-Formularen mit doppelten Feldnamen, indem alle Felder eindeutig umbenannt werden.

**Problem:** Viele offiziell erstellte PDF-Formulare (ja, auch vom Kultusministerium) haben das gleiche Feld mehrfach mit identischem Namen. Beim Ausfüllen bekommen dann alle Felder mit demselben Namen den gleichen Wert - nicht das, was man will!

**Beispiel des Problems:**
```
"0" erscheint auf Seite 2 (3x) und Seite 3 (2x)
→ Beim Ausfüllen bekommen ALLE 5 Felder den gleichen Wert!
```

**Lösung:** Das Script benennt doppelte Felder um und fügt die Seitennummer hinzu:
```
"0" (Seite 2, erstes Vorkommen) → "0_p2"
"0" (Seite 3, erstes Vorkommen) → "0_p3"
```

**Usage:**
```bash
# Im Backend-Container
docker-compose exec backend python scripts/sanitize_pdf_fields.py \
    /app/assets/1201.pdf \
    /app/assets/1201-sanitized.pdf

# Ohne Output-Pfad (Standard: <name>-sanitized.pdf)
docker-compose exec backend python scripts/sanitize_pdf_fields.py /app/assets/1201.pdf
```

**Output:**
```
======================================================================
Sanitizing PDF: 1201.pdf
======================================================================

🔍 Analyzing PDF fields...
⚠️  Found 9 duplicate field names:

   '0' appears on pages: 2, 2, 2, 3, 3
   '1' appears on pages: 2, 3, 3, 3
   '2' appears on pages: 2, 2, 2, 3

📝 Renaming 9 fields to make them unique...
   Renamed: '0' → '0_p2' (page 2)
   Renamed: '0' → '0_p3' (page 3)
   ...

💾 Writing sanitized PDF to: /app/assets/1201-sanitized.pdf

======================================================================
✅ Sanitization Complete!
======================================================================

Summary:
  - Original fields: 89
  - Duplicate field names: 9
  - Fields renamed: 25
  - Output: /app/assets/1201-sanitized.pdf
```

**Wann verwenden:**
- **IMMER** wenn `extract_pdf_fields.py` zeigt, dass ein Feldname mehrfach vorkommt
- Bei offiziellen PDF-Formularen (die sind oft schlecht gemacht)
- Wenn beim Ausfüllen alle Felder mit gleichem Namen den gleichen Wert bekommen

**Wichtig:**
- Nach dem Sanitizing IMMER `extract_pdf_fields.py` auf das **sanitized** PDF anwenden
- Die sanitized Version als Template verwenden
- Die Feldnamen mit `_p2`, `_p3` Suffix in der Config nutzen

---

## Workflow: Neues PDF-Formular integrieren

### Schritt 1: PDF-Felder extrahieren (Quick Check)

```bash
# Felder auflisten
docker-compose exec backend python scripts/extract_pdf_fields.py /app/assets/neues_formular.pdf

# Output in Datei speichern
docker-compose exec backend python scripts/extract_pdf_fields.py /app/assets/neues_formular.pdf \
    > backend/docs/neues_formular_fields.txt
```

**⚠️ Wichtig:** Prüfe, ob Feldnamen mehrfach vorkommen! Wenn ja, weiter zu Schritt 2.

### Schritt 2: Doppelte Feldnamen bereinigen (falls nötig)

```bash
# Sanitize das PDF (falls Duplikate gefunden)
docker-compose exec backend python scripts/sanitize_pdf_fields.py \
    /app/assets/neues_formular.pdf \
    /app/assets/neues_formular-sanitized.pdf

# Felder vom sanitized PDF neu auflisten
docker-compose exec backend python scripts/extract_pdf_fields.py \
    /app/assets/neues_formular-sanitized.pdf \
    > backend/docs/neues_formular_sanitized_fields.txt
```

**Ab jetzt:** Nutze `neues_formular-sanitized.pdf` als Template!

### Schritt 3: PDF mit Feldnamen labeln

```bash
# Labeled PDF erstellen (vom sanitized PDF, falls vorhanden!)
docker-compose exec backend python scripts/fill_pdf_with_field_names.py \
    /app/assets/neues_formular-sanitized.pdf \
    /app/scripts/neues_formular_labeled.pdf

# Ins Projekt-Root kopieren für einfachen Zugriff
cp backend/scripts/neues_formular_labeled.pdf .
```

### Schritt 4: Labeled PDF öffnen

Öffne `neues_formular_labeled.pdf` mit einem PDF-Viewer und schaue dir an, wo welcher Feldname steht.

### Schritt 5: Mapping-Config erstellen

Bearbeite `backend/config/pdf_form_mappings.json` und füge das neue Formular hinzu:

```json
{
  "forms": {
    "neues_formular": {
      "pdf_filename": "neues_formular-sanitized.pdf",
      "display_name": "Neues Formular Beschreibung",
      "applicable_reasons": ["training", "exam"],
      "field_mappings": {
        "_comment": "=== Lehrkraft-Daten ===",
        "Nachname": "{{ absence.teacher.last_name }}",
        "Vorname": "{{ absence.teacher.first_name }}",

        "_comment2": "=== Datum ===",
        "Datum": "{{ absence.start_date | format_date('%d.%m.%Y') }}",

        "_comment3": "=== Weitere Felder ===",
        "Feldname_aus_PDF": "{{ template_variable }}"
      }
    }
  }
}
```

### Schritt 6: Frontend-Constants aktualisieren

Füge das neue Formular in `wordpress-plugin/src/constants.ts` hinzu:

```typescript
export const PDF_FORMS: Record<AbsenceReason, PDFFormInfo[]> = {
  training: [
    { type: 'neues_formular', label: 'Neues Formular' }
  ],
  // ...
};
```

### Schritt 7: Testen

1. Backend neu starten: `docker-compose restart backend`
2. Frontend neu bauen: `cd wordpress-plugin && npm run build`
3. Absenz erstellen und PDF herunterladen
4. Prüfen, ob Felder korrekt ausgefüllt sind

---

## Template-Variablen

Verfügbare Variablen für `field_mappings`:

### Absence-Daten
```
{{ absence.teacher.full_name }}      - Vollständiger Name
{{ absence.teacher.first_name }}     - Vorname
{{ absence.teacher.last_name }}      - Nachname
{{ absence.teacher.email }}          - E-Mail

{{ absence.start_date | format_date('%d.%m.%Y') }}  - Startdatum
{{ absence.end_date | format_date('%d.%m.%Y') }}    - Enddatum

{{ absence.excursion_classes }}      - Klassen (nur bei Exkursion)
{{ absence.admin_notes }}            - Bemerkungen
```

### Lessons-Daten (aus WebUntis)
```
{{ lessons_time_start }}             - Start-Uhrzeit (z.B. "07:45")
{{ lessons_time_end }}               - End-Uhrzeit (z.B. "15:00")
{{ lessons_subjects_combined }}      - Fächer (z.B. "Mathe, Deutsch")
{{ lessons_rooms_combined }}         - Räume (z.B. "A101, A102")
```

### Config-Defaults (schulweit)
```
{{ config.school_name }}             - Schulname
{{ config.school_address }}          - Schuladresse
{{ config.school_city }}             - Schulort
{{ config.school_phone }}            - Schultelefon
```

---

## Troubleshooting

### Problem: "PDF file not found"
**Lösung:** Stelle sicher, dass das PDF im Container verfügbar ist:
```bash
docker-compose exec backend ls -la /app/assets/
```

### Problem: "No form fields found"
**Lösung:** Das PDF ist kein Formular oder die Felder sind "flattened" (mit Content verschmolzen).

### Problem: Felder werden nicht ausgefüllt
**Debug-Schritte:**
1. Backend-Logs prüfen: `docker-compose logs backend | grep -i "field"`
2. Prüfen ob Feldname korrekt: Vergleiche mit `extract_pdf_fields.py` Output
3. Prüfen ob Template-Variable Wert hat: Backend-Log zeigt "Processed X fields"

### Problem: Warnings "Incorrect first char in NameObject"
**Lösung:** Ignorieren - das sind PyPDF2-Warnings wegen Sonderzeichen in Feldnamen. Die PDFs funktionieren trotzdem.

---

## Beispiele

### Beispiel: 1211.pdf (Exkursionsantrag)

```bash
# 1. Felder auflisten
docker-compose exec backend python scripts/extract_pdf_fields.py /app/assets/1211.pdf

# 2. Labeled PDF erstellen
docker-compose exec backend python scripts/fill_pdf_with_field_names.py \
    /app/assets/1211.pdf backend/scripts/1211_labeled.pdf

# 3. Ins Projekt kopieren
cp backend/scripts/1211_labeled.pdf .

# 4. PDF öffnen und Mapping in pdf_form_mappings.json anpassen
```

### Beispiel: 1201.pdf (Dienstreiseantrag)

```bash
# Felder + Labeled PDF in einem Schritt
docker-compose exec backend python scripts/extract_pdf_fields.py /app/assets/1201.pdf \
    > backend/docs/1201_fields.txt && \
docker-compose exec backend python scripts/fill_pdf_with_field_names.py \
    /app/assets/1201.pdf backend/scripts/1201_labeled.pdf && \
cp backend/scripts/1201_labeled.pdf .
```

---

## Hinweise

- **Feldnamen mit Sonderzeichen:** PDF-Feldnamen können Umlaute, Leerzeichen oder Sonderzeichen enthalten. Das ist in Ordnung.
- **Leere Felder:** Wenn eine Template-Variable keinen Wert hat (z.B. `admin_notes` ist leer), bleibt das Feld im PDF leer.
- **Numerische Feldnamen:** Manche PDFs haben Felder mit Namen wie "0", "1", "2". Diese müssen in der Config als Strings angegeben werden: `"0": "wert"`.
- **Checkboxen:** Checkboxen funktionieren möglicherweise nicht mit diesem Ansatz - hier müsste man spezielle Werte setzen.

---

## Warum sanitize_pdf_fields.py überhaupt nötig ist 🤦

### Die Geschichte eines kaputten PDF-Formats

PDF-Formulare sollten eigentlich einfach sein: Jedes Feld hat einen eindeutigen Namen, und man befüllt es mit Daten. **Sollte.**

Aber dann kommen PDF-Ersteller (ja, auch offizielle Stellen) und produzieren Formulare, bei denen **dasselbe Feld mehrfach mit identischem Namen** vorkommt. Warum? Weil sie Copy-Paste verwenden und vergessen, die Feldnamen zu ändern.

### Das konkrete Problem

Bei **1201.pdf (offizieller Dienstreiseantrag)** hatten wir:
- Feld `"0"` erscheint **5 Mal** (3x auf Seite 2, 2x auf Seite 3)
- Feld `"1"` erscheint **4 Mal**
- Insgesamt **9 doppelte Feldnamen** mit **25 Feldinstanzen**

**Folge:** Beim Ausfüllen bekommen ALLE Felder mit demselben Namen den gleichen Wert. Will man den Nachnamen auf Seite 2 und die Unterschrift auf Seite 3 in unterschiedliche Felder `"0"` schreiben? **Unmöglich.**

### Die Lösung

`sanitize_pdf_fields.py` durchläuft das PDF, findet alle doppelten Feldnamen und benennt sie um:
- `"0"` (Seite 2) → `"0_p2"`
- `"0"` (Seite 3) → `"0_p3"`

Jetzt sind die Felder eindeutig, und man kann sie individuell befüllen. **Problem gelöst.**

### Lehren daraus

1. **Traue niemals einem offiziellen PDF-Formular.** Prüfe IMMER mit `extract_pdf_fields.py`, ob Duplikate existieren.
2. **Sanitize first, ask questions later.** Es dauert 5 Sekunden und erspart Stunden Debugging.
3. **PDF-Ersteller sollten sich schämen.** Aber wir haben die Lösung, also whatever. 🤷

### Real-World-Stats

- **1201.pdf (Original):** 89 Feldnamen, davon 9 mehrfach vergeben (25 Duplikate)
- **1201-sanitized.pdf:** 117 eindeutige Feldnamen, 0 Probleme

**Fazit:** Wer PDF-Formulare mit doppelten Feldnamen erstellt, hat die Kontrolle über sein Leben verloren. Aber wir haben `sanitize_pdf_fields.py`, also alles gut. ✨

---

## Autor

Erstellt von: Claude Sonnet 4.5 & Seyfried
Datum: 2026-02-05
Version: 1.1 (mit Anti-Dummheits-Patch)
