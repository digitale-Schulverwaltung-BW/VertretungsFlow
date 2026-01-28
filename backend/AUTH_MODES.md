# AbsenzFlow Authentifizierungs-Modi

AbsenzFlow unterstützt zwei Authentifizierungs-Modi:

## WordPress-Modus (Standard)

Benutzer werden über WordPress authentifiziert. Das Backend vertraut auf die WordPress-Authentifizierung und erhält Benutzerdaten über das WordPress-Plugin.

### Installation

```bash
# Dependencies installieren
pip install -r requirements-wordpress.txt
# oder
pip install -r requirements.txt  # Identisch mit requirements-wordpress.txt
```

### Konfiguration

```env
# .env Datei
AUTH_MODE=wordpress
WORDPRESS_PROXY_SECRET=ihr-shared-secret-hier

# LDAP-Konfiguration ist NICHT erforderlich
```

### Funktionsweise

1. Benutzer meldet sich in WordPress an
2. WordPress-Plugin sendet Requests mit folgenden Headern:
   - `X-WordPress-Secret`: Shared Secret zur Authentifizierung
   - `X-WordPress-User`: WordPress Username
   - `X-WordPress-Email`: User Email
   - `X-WordPress-Name`: Display Name
   - `X-WordPress-Role`: Rolle (admin/teacher/student)
3. Backend erstellt/aktualisiert User automatisch
4. Login-Endpoint `/api/auth/login` ist **nicht verfügbar** (404)

## Standalone-Modus

Direkter LDAP-Zugriff für Schulen ohne WordPress. Benutzer authentifizieren sich direkt gegen Active Directory/LDAP.

### Installation

```bash
# Dependencies installieren (inkl. python-ldap)
pip install -r requirements-standalone.txt
```

### Konfiguration

```env
# .env Datei
AUTH_MODE=standalone

# LDAP-Konfiguration
LDAP_SERVER=ldap.schule.local
LDAP_PORT=389
LDAP_BASE_DN=dc=schule,dc=local
LDAP_BIND_DN=cn=absenzflow,ou=services,dc=schule,dc=local
LDAP_BIND_PASSWORD=ihr-ldap-password
LDAP_USE_SSL=false

# WordPress-Konfiguration ist optional
```

### Funktionsweise

1. Benutzer sendet Login-Request an `/api/auth/login`
2. Backend authentifiziert gegen LDAP
3. Bei erfolgreicher Authentifizierung:
   - Benutzerdaten werden aus LDAP geladen
   - User wird in DB angelegt (falls neu)
   - JWT Token wird zurückgegeben
4. Weitere API-Requests nutzen JWT Token im Authorization-Header

## Unterschiede im Überblick

| Feature | WordPress-Modus | Standalone-Modus |
|---------|----------------|------------------|
| Authentifizierung | WordPress | LDAP/Active Directory |
| Benutzerdaten | WordPress-Plugin Headers | LDAP-Abfrage |
| Login-Endpoint | ❌ Nicht verfügbar | ✅ `/api/auth/login` |
| JWT Tokens | Optional | Erforderlich |
| LDAP-Dependencies | ❌ Nicht erforderlich | ✅ python-ldap |
| WordPress-Plugin | ✅ Erforderlich | ❌ Optional |

## Migration zwischen Modi

### Von Standalone zu WordPress

1. WordPress installieren und AbsenzFlow-Plugin aktivieren
2. `.env` anpassen: `AUTH_MODE=wordpress`
3. Shared Secret konfigurieren
4. Backend neu starten
5. Bestehende User bleiben erhalten, werden bei nächstem Login aktualisiert

### Von WordPress zu Standalone

1. LDAP-Konfiguration in `.env` hinzufügen
2. `.env` anpassen: `AUTH_MODE=standalone`
3. `pip install -r requirements-standalone.txt`
4. Backend neu starten
5. Bestehende User bleiben erhalten, Authentifizierung erfolgt gegen LDAP

## Troubleshooting

### WordPress-Modus

**Problem**: User wird nicht angelegt
- Prüfen: Sind alle Header vorhanden? (X-WordPress-User, Email, Name, Role)
- Prüfen: Ist das Shared Secret korrekt?
- Logs checken: Backend-Logs auf Authentifizierungsfehler prüfen

**Problem**: User-Daten werden nicht aktualisiert
- Smart Update ist aktiv: Nur bei Änderungen wird aktualisiert
- Prüfen: Haben sich die Daten in WordPress geändert?

### Standalone-Modus

**Problem**: `ImportError: python-ldap`
- Lösung: `pip install -r requirements-standalone.txt`

**Problem**: LDAP-Verbindungsfehler
- Prüfen: LDAP_SERVER und LDAP_PORT korrekt?
- Prüfen: Firewall erlaubt Verbindung?
- Prüfen: LDAP_BIND_DN und LDAP_BIND_PASSWORD korrekt?

**Problem**: User nicht in LDAP gefunden
- Prüfen: LDAP_BASE_DN korrekt?
- Prüfen: Suchfilter in `ldap_service.py` passt zu LDAP-Schema?
- Für AD: Filter auf `sAMAccountName` statt `uid` ändern

## Best Practices

1. **WordPress-Modus**: Default für neue Installationen
2. **Standalone-Modus**: Nur wenn WordPress nicht verfügbar
3. **Shared Secret**: Starkes, zufälliges Secret verwenden
4. **LDAP SSL**: In Produktion immer `LDAP_USE_SSL=true`
5. **Rollenmapping**: WordPress-Rollen an Schul-Kontext anpassen
