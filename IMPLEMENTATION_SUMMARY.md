# WebUntis Teacher Code Implementation - Summary

## Overview
Successfully implemented the WebUntis teacher code (Lehrerkürzel) feature to map WordPress usernames to WebUntis teacher abbreviations.

## What Was Changed

### 1. Backend - Database Model
**File**: `backend/app/models/models.py`
- Added `webuntis_teacher_code` field to User model (String(20), nullable, indexed)

**File**: `backend/app/schemas/schemas.py`
- Added `webuntis_teacher_code: Optional[str]` to UserBase schema

### 2. Database Migration
**File**: `backend/migrations/001_add_webuntis_teacher_code.sql`
- SQL migration to add the new column and index
- **Action Required**: Run this migration on your database

### 3. WordPress Plugin - Admin UI
**File**: `wordpress-plugin/includes/class-admin.php`
- Added "WebUntis-Kürzel" column to role management table
- Added input field for entering teacher codes (max 20 characters)
- Updated save handler to store/delete the code in WordPress user meta

### 4. WordPress Plugin - API Proxy
**File**: `wordpress-plugin/includes/class-api-proxy.php`
- Added `X-WordPress-WebUntis-Code` header to backend requests
- Retrieves code from user meta (`absenzflow_webuntis_code`)

### 5. Backend - Authentication
**File**: `backend/app/api/auth.py`
- Added `x_wordpress_webuntis_code` header parameter
- Updated user creation/update logic to sync WebUntis code
- Smart update: only commits when data actually changes

### 6. Backend - WebUntis Service
**File**: `backend/app/services/webuntis_service.py`
- Added `webuntis_code` parameter to `get_timetable_for_teacher()`
- Implemented fallback logic: uses code if available, otherwise uses username
- Enhanced logging to show which lookup value is being used

### 7. Backend - Absences API
**File**: `backend/app/api/absences.py`
- Updated `create_absence()` to pass `current_user.webuntis_teacher_code`
- Updated `fetch_lessons_from_webuntis()` to pass `current_user.webuntis_teacher_code`

## Fallback Logic

```
User creates absence
    ↓
Check: current_user.webuntis_teacher_code
    ↓
If set → Use code (e.g., "SEY")
If empty → Use username (e.g., "max.mustermann")
    ↓
WebUntis Teacher Lookup
    ↓
Find Teacher ID
    ↓
Fetch Timetable
```

## Testing Instructions

### 1. Database Migration
```bash
cd backend

# Option A: Using psql
psql -U your_user -d absenzflow -f migrations/001_add_webuntis_teacher_code.sql

# Option B: Using docker
docker exec -i postgres_container psql -U your_user -d absenzflow < migrations/001_add_webuntis_teacher_code.sql
```

### 2. Restart Backend
```bash
cd backend
# Stop and restart your backend service
uvicorn app.main:app --reload
```

### 3. Configure WebUntis Codes in WordPress
1. Log into WordPress Admin: `http://localhost/wp-admin`
2. Navigate to: **AbsenzFlow → Rollenverwaltung**
3. For each teacher:
   - Set their AbsenzFlow role (e.g., "Lehrkraft")
   - Enter their WebUntis code in the "WebUntis-Kürzel" field (e.g., "SEY")
   - Click "Speichern"

### 4. Verify Storage
Check that the code is stored in WordPress:
```sql
SELECT * FROM wp_usermeta WHERE meta_key = 'absenzflow_webuntis_code';
```

### 5. Test API Proxy
Create a test absence and check backend logs:
```bash
# Backend logs should show:
📅 Stundenplan abrufen für max.mustermann (WebUntis-Lookup: SEY)
🔍 Suche Teacher ID für Username: SEY
✅ Teacher ID gefunden: 12345 für SEY
```

### 6. Test Fallback
Test with a user that does NOT have a WebUntis code set:
```bash
# Backend logs should show:
📅 Stundenplan abrufen für max.mustermann (WebUntis-Lookup: max.mustermann)
🔍 Suche Teacher ID für Username: max.mustermann
```

## Key Features

✅ **Backward Compatible**: Users without codes still work (fallback to username)
✅ **Smart Updates**: Only commits database changes when data actually changes
✅ **Indexed**: WebUntis code field is indexed for performance
✅ **Validation**: 20 character limit on codes
✅ **Clean Storage**: Empty codes are deleted from user meta (not stored as empty strings)

## Log Messages to Watch For

**Success Case (with code):**
```
📅 Stundenplan abrufen für max.mustermann (WebUntis-Lookup: SEY) (2026-02-01 - 2026-02-05)
🔍 Suche Teacher ID für Username: SEY
✅ Teacher ID gefunden: 12345 für SEY
📚 15 Stundeneinträge von WebUntis erhalten
✅ 15 Stunden erfolgreich geparst
```

**Fallback Case (without code):**
```
📅 Stundenplan abrufen für max.mustermann (WebUntis-Lookup: max.mustermann) (2026-02-01 - 2026-02-05)
🔍 Suche Teacher ID für Username: max.mustermann
```

**Error Case (code not found in WebUntis):**
```
📅 Stundenplan abrufen für max.mustermann (WebUntis-Lookup: WRONG) (2026-02-01 - 2026-02-05)
🔍 Suche Teacher ID für Username: WRONG
⚠️ Kein Lehrer mit Username 'WRONG' gefunden
Verfügbare Namen: SEY, MUE, BER, ...
⚠️ Keine Teacher ID gefunden für WRONG, gebe leere Liste zurück
```

## Files Modified

### Backend (7 files)
1. `backend/app/models/models.py` - User model
2. `backend/app/schemas/schemas.py` - User schema
3. `backend/migrations/001_add_webuntis_teacher_code.sql` - Database migration (new)
4. `backend/app/api/auth.py` - WordPress proxy authentication
5. `backend/app/services/webuntis_service.py` - WebUntis integration
6. `backend/app/api/absences.py` - Absences endpoints

### WordPress Plugin (2 files)
7. `wordpress-plugin/includes/class-admin.php` - Admin UI
8. `wordpress-plugin/includes/class-api-proxy.php` - API proxy

## Total Changes
- **8 files modified/created**
- **~180 lines of code added**
- **0 breaking changes** (fully backward compatible)

## Next Steps (Optional Improvements)

1. **Bulk Import**: CSV upload for WebUntis code assignments
2. **Auto-Sync**: Fetch teacher list from WebUntis and offer dropdown
3. **Validation**: Check if code exists in WebUntis when saving
4. **Standalone Admin**: Backend endpoint for code management without WordPress

## Troubleshooting

### Code not being sent to backend
- Check WordPress user meta: `SELECT * FROM wp_usermeta WHERE meta_key = 'absenzflow_webuntis_code';`
- Check API proxy headers in browser network tab
- Verify backend receives header: check logs for "X-WordPress-WebUntis-Code"

### Teacher still not found
- Verify the code matches exactly what's in WebUntis (case-sensitive)
- Check backend logs for available teacher names
- Test with a known working code first

### Database migration fails
- Check if column already exists: `\d users` in psql
- Ensure you have ALTER TABLE permissions
- Try manual execution instead of script

## Implementation Date
2026-01-29

## Status
✅ Implementation Complete
⏳ Database Migration Required
⏳ User Configuration Required
