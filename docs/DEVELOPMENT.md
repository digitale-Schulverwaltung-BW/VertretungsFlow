# VertretungsFlow Entwickler Guide

Anleitung für Entwickler die an VertretungsFlow arbeiten möchten.

## 🏗️ Projekt-Setup

### 1. Repository klonen

```bash
git clone https://github.com/your-org/absenzflow.git
cd absenzflow
```

### 2. Backend Setup

```bash
cd backend

# Virtual Environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate (Windows)

# Dependencies
pip install -r requirements.txt

# Environment
cp ../.env.example ../.env
# .env bearbeiten
```

### 3. Datenbank Setup

```bash
# PostgreSQL starten (Docker)
docker-compose up -d postgres

# Migrations (TODO: Alembic einrichten)
alembic upgrade head
```

### 4. Backend starten

```bash
uvicorn app.main:app --reload
```

Backend läuft auf: http://localhost:8000
API Docs: http://localhost:8000/docs

### 5. Frontend (WordPress) Setup

```bash
cd ../frontend-wp

# Dependencies
npm install

# Development Build
npm run dev
```

## 🐳 Docker Development

Komplettes Setup mit Docker:

```bash
docker-compose up -d
```

Services:
- Backend: http://localhost:8000
- PostgreSQL: localhost:5432
- pgAdmin: http://localhost:5050 (mit `--profile dev`)

## 📝 Code-Style

### Python (Backend)

```bash
# Formatting
black app/

# Linting
flake8 app/

# Type Checking
mypy app/
```

### TypeScript (Frontend)

```bash
# Linting
npm run lint

# Type Checking
npm run type-check
```

## 🧪 Testing

### Backend Tests

```bash
pytest tests/
pytest --cov=app tests/  # Mit Coverage
```

### Frontend Tests

```bash
npm run test
```

## 🗄️ Datenbank Migrations

### Neue Migration erstellen

```bash
cd backend
alembic revision --autogenerate -m "Add new table"
```

### Migrations anwenden

```bash
alembic upgrade head
```

### Migration rückgängig

```bash
alembic downgrade -1
```

## 🔌 API Development

### Neuen Endpoint hinzufügen

1. **Schema definieren** (`app/schemas/schemas.py`):
```python
class NewFeatureCreate(BaseModel):
    name: str
    description: Optional[str] = None
```

2. **Model erstellen** (`app/models/models.py`):
```python
class NewFeature(Base):
    __tablename__ = "new_features"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
```

3. **Route hinzufügen** (`app/api/new_feature.py`):
```python
@router.post("/", response_model=NewFeatureResponse)
async def create_feature(
    feature: NewFeatureCreate,
    db: Session = Depends(get_db)
):
    # Implementation
```

4. **In main.py registrieren**:
```python
from app.api import new_feature
app.include_router(new_feature.router, prefix="/api/features")
```

## 🎨 Frontend Development

### Neue React Component

```tsx
// src/components/NewComponent.tsx
import React from 'react'

interface NewComponentProps {
  title: string
}

export const NewComponent: React.FC<NewComponentProps> = ({ title }) => {
  return (
    <div className="p-4">
      <h2 className="text-xl font-bold">{title}</h2>
    </div>
  )
}
```

### API Service

```typescript
// src/services/api.ts
import axios from 'axios'

const api = axios.create({
  baseURL: window.vertretungsflowConfig.apiUrl
})

export const getAbsences = async () => {
  const response = await api.get('/api/absences/')
  return response.data
}
```

## 🔐 LDAP Testing

Für lokales Development ohne echten LDAP:

```python
# app/services/ldap_service.py
class LDAPService:
    def authenticate(self, username: str, password: str) -> bool:
        # Development Mock
        if os.getenv('DEBUG') == 'true':
            return username == 'test' and password == 'test'
        # ... echte LDAP Logik
```

## 📧 E-Mail Testing

Nutze [MailHog](https://github.com/mailhog/MailHog) für lokales E-Mail-Testing:

```bash
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog
```

`.env`:
```
SMTP_HOST=localhost
SMTP_PORT=1025
```

Web-UI: http://localhost:8025

## 🐛 Debugging

### Backend Debugging

PyCharm/VSCode Launch Config:
```json
{
  "name": "FastAPI",
  "type": "python",
  "request": "launch",
  "module": "uvicorn",
  "args": [
    "app.main:app",
    "--reload"
  ],
  "jinja": true
}
```

### Frontend Debugging

React DevTools installieren:
- Chrome: [React DevTools](https://chrome.google.com/webstore/detail/react-developer-tools/fmkadmapgofadopljbjfkapdkoienihi)

## 📦 Build & Deploy

### Backend Docker Image

```bash
cd backend
docker build -t absenzflow-backend:latest .
docker push your-registry/absenzflow-backend:latest
```

### Frontend Build

```bash
cd frontend-wp
npm run build
# Build-Artefakte in build/
```

### WordPress Plugin Packaging

```bash
cd frontend-wp
npm run build
cd ..
zip -r absenzflow-wp.zip frontend-wp/ -x "*/node_modules/*" "*/.git/*"
```

## 🔄 Git Workflow

### Branch Strategy

- `main`: Production
- `develop`: Development
- `feature/*`: Features
- `bugfix/*`: Bugfixes

### Commit Messages

Format: `<type>: <subject>`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Tests
- `chore`: Maintenance

Beispiel:
```
feat: add absence approval workflow
fix: correct WebUntis API auth
docs: update API documentation
```

## 📚 Nützliche Links

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [React Docs](https://react.dev/)
- [TailwindCSS Docs](https://tailwindcss.com/)
- [WebUntis API](https://help.untis.at/hc/de/articles/4403351094034)

## 🤝 Code Review Guidelines

- ✅ Code ist getestet
- ✅ Dokumentation aktualisiert
- ✅ Keine Secrets im Code
- ✅ Style Guide befolgt
- ✅ Migrations getestet
- ✅ API-Änderungen dokumentiert

## 💡 Best Practices

### Backend

- Nutze Type Hints
- Async wo möglich
- Dependency Injection mit FastAPI
- Proper Error Handling
- Logging statt print()

### Frontend

- TypeScript statt JavaScript
- Functional Components
- Proper State Management
- Error Boundaries
- Accessibility (a11y)

## 🚨 Common Issues

### "LDAP Connection Failed"

- LDAP Server erreichbar?
- Credentials korrekt?
- Firewall-Regeln?

### "WebUntis API Error"

- Credentials korrekt?
- School Name richtig?
- Rate Limits beachten

### "Database Connection Error"

- PostgreSQL läuft?
- DATABASE_URL korrekt?
- Migrations ausgeführt?

## 📞 Support

Bei Fragen:
1. Issues auf GitHub erstellen
2. Interne Slack-Channel
3. Dokumentation checken

Happy Coding! 🚀
