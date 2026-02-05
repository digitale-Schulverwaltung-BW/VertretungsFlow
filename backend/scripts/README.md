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

## Workflow: Neues PDF-Formular integrieren

### Schritt 1: PDF-Felder extrahieren

```bash
# Felder auflisten
docker-compose exec backend python scripts/extract_pdf_fields.py /app/assets/neues_formular.pdf

# Output in Datei speichern
docker-compose exec backend python scripts/extract_pdf_fields.py /app/assets/neues_formular.pdf \
    > backend/docs/neues_formular_fields.txt
```

### Schritt 2: PDF mit Feldnamen labeln

```bash
# Labeled PDF erstellen
docker-compose exec backend python scripts/fill_pdf_with_field_names.py \
    /app/assets/neues_formular.pdf \
    /app/scripts/neues_formular_labeled.pdf

# Ins Projekt-Root kopieren für einfachen Zugriff
cp backend/scripts/neues_formular_labeled.pdf .
```

### Schritt 3: Labeled PDF öffnen

Öffne `neues_formular_labeled.pdf` mit einem PDF-Viewer und schaue dir an, wo welcher Feldname steht.

### Schritt 4: Mapping-Config erstellen

Bearbeite `backend/config/pdf_form_mappings.json` und füge das neue Formular hinzu:

```json
{
  "forms": {
    "neues_formular": {
      "pdf_filename": "neues_formular.pdf",
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

### Schritt 5: Frontend-Constants aktualisieren

Füge das neue Formular in `wordpress-plugin/src/constants.ts` hinzu:

```typescript
export const PDF_FORMS: Record<AbsenceReason, PDFFormInfo[]> = {
  training: [
    { type: 'neues_formular', label: 'Neues Formular' }
  ],
  // ...
};
```

### Schritt 6: Testen

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

## Autor

Erstellt von: Claude Sonnet 4.5 & Seyfried
Datum: 2026-02-05
Version: 1.0
