# AGENTS.md - VertretungsFlow Development Guide

This document provides essential information for agentic coding agents working with the VertretungsFlow repository.

## Build, Lint, and Test Commands

### Frontend (React/TypeScript)
```bash
cd wordpress-plugin

# Development (Hot Reload)
npm run dev

# Production Build
npm run build

# Preview Production Build
npm run preview
```

### Backend (Python/FastAPI)
```bash
cd backend

# Install dependencies (from requirements-dev.txt)
pip install -r requirements-dev.txt

# Run backend (Docker)
docker-compose up -d backend

# Backend Logs
docker-compose logs -f backend

# Restart backend (quick)
docker-compose restart backend

# Rebuild backend (after requirements changes)
docker-compose up -d --build backend
```

### Testing
```bash
# Backend tests (pytest)
cd backend
pytest tests/                    # Run all tests
pytest tests/test_specific.py    # Run specific test file
pytest tests/test_specific.py::test_function  # Run single test
pytest --cov=app --cov-report=html  # Coverage report
pytest -v                         # Verbose output

# Code Quality (Black, Flake8, MyPy)
black .                           # Format code
flake8 .                          # Linting
mypy .                            # Type checking
```

### Database
```bash
# Database shell
docker-compose exec postgres psql -U absenzflow -d absenzflow

# Manual migrations (SQL files in backend/migrations/)
docker-compose exec -T postgres psql -U absenzflow -d absenzflow < backend/migrations/001_initial.sql
```

## Code Style Guidelines

### Backend (Python)

#### Import Organization
```python
# Standard library imports
import logging
from datetime import datetime
from typing import List, Dict, Any

# FastAPI imports
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session, selectinload, joinedload

# Local imports (absolute paths)
from app.models.models import User, Absence, AffectedLesson
from app.schemas.schemas import AbsenceCreate
from app.services.absence_service import AbsenceService
from app.utils.absence_utils import validate_date_range
```

#### Type Hints
- Use type hints for all function parameters and return values
- Use `Optional[T]` for nullable fields
- Use `List[T]`, `Dict[K, V]` for collections
- Use `Any` sparingly, prefer specific types

```python
def create_absence(
    absence_data: AbsenceCreate,
    current_user: User,
    db: Session
) -> Absence:
    pass
```

#### Naming Conventions
- **Classes**: `PascalCase` (e.g., `AbsenceService`, `AbsenceNotificationService`)
- **Functions/Methods**: `snake_case` (e.g., `create_absence`, `send_notification`)
- **Variables**: `snake_case` (e.g., `absence_data`, `current_user`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `REASON_LABELS`)
- **Private methods**: Prefix with underscore (e.g., `_validate_data`)

#### Error Handling
- Use `HTTPException` for API errors with appropriate status codes
- Log errors with `logger.error()`
- Use specific exception types when possible

```python
try:
    result = some_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=400, detail="Operation failed")
```

#### Docstrings
- All public functions must have docstrings
- Include Args, Returns, and Raises sections
- Use triple quotes and proper formatting

```python
def create_absence(
    absence_data: AbsenceCreate,
    current_user: User,
    db: Session
) -> Absence:
    """
    Creates a new absence with affected lessons

    Args:
        absence_data: Absence data
        current_user: Current user
        db: Database session

    Returns:
        Created absence

    Raises:
        HTTPException: If validation fails
    """
    pass
```

#### Logging
- Use `logger.info()` for important events
- Use `logger.error()` for errors
- Use structured logging with context

```python
logger.info(f"📝 Create absence request from user {current_user.username}")
logger.error(f"❌ Failed to create absence: {str(error)}")
```

### Frontend (TypeScript/React)

#### Type Safety
- Never use `any` type
- Use `unknown` for untyped data, then narrow
- Use `Partial<T>` for partial updates
- Use `Pick<T, K>` for selective properties

```typescript
interface Absence {
  id: number;
  reason: string;
  startDate: string;
  endDate: string;
}

const createAbsence = async (data: Partial<Absence>): Promise<Absence> => {
  // Implementation
};
```

#### Component Structure
- Use functional components with TypeScript
- Use `React.FC` for component types
- Use props interface for component props

```tsx
interface DashboardProps {
  absences: Absence[];
  onApprove: (id: number) => void;
}

const Dashboard: React.FC<DashboardProps> = ({ absences, onApprove }) => {
  return (
    <div>
      {/* Component JSX */}
    </div>
  );
};
```

#### State Management
- Use `useState` for local component state
- Use props for parent-child communication
- Use context for global state

```tsx
const [selectedAbsence, setSelectedAbsence] = useState<Absence | null>(null);
const [isLoading, setIsLoading] = useState(false);
```

#### API Client Usage
- All backend calls must go through `api` singleton
- Use proper error handling
- Include authentication headers

```typescript
const createAbsence = async (data: AbsenceCreate): Promise<Absence> => {
  try {
    const response = await api.absence.createAbsence(data);
    return response.data;
  } catch (error) {
    console.error("Failed to create absence:", error);
    throw error;
  }
};
```

#### Naming Conventions
- **Components**: `PascalCase` (e.g., `AbsenceDetail`, `CreateAbsence`)
- **Functions**: `camelCase` (e.g., `handleCreateAbsence`, `fetchAbsences`)
- **Variables**: `camelCase` (e.g., `absenceData`, `isLoading`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `API_BASE_URL`)

## Project Architecture

### Backend Layers
1. **API Routes** (`backend/app/api/`): Thin controllers that delegate to services
2. **Services** (`backend/app/services/`): Business logic
3. **Models** (`backend/app/models/`): SQLAlchemy ORM models
4. **Schemas** (`backend/app/schemas/`): Pydantic validation
5. **Utils** (`backend/app/utils/`): Pure helper functions

### Frontend Structure
1. **API Client** (`wordpress-plugin/src/api/client.ts`): Centralized API calls
2. **Pages** (`wordpress-plugin/src/pages/`): Main page components
3. **Types** (`wordpress-plugin/src/types/`): TypeScript type definitions
4. **Components**: Reusable UI components

## Authentication & Security

### WordPress Proxy Authentication
- All requests must include `withCredentials: true`
- Include `X-WP-Nonce` header for CSRF protection
- Use `X-WP-Nonce: window.vertretungsflowConfig?.nonce`

### File Uploads
- Uploads stored in `/app/uploads/absence_{id}/`
- Files deleted when absence status changes to "erledigt"
- Use UUID-based filenames for security

## Testing Guidelines

### Backend Tests
- Use `pytest` for unit and integration tests
- Test services, not API routes directly
- Mock external dependencies (WebUntis, email)
- Test validation logic and error cases

### Frontend Tests
- Use Jest/Vitest for component testing
- Test user interactions and state changes
- Mock API calls with MSW or similar

## Database & Migrations

### Migration Conventions
- Name files with prefix: `001_initial.sql`, `002_add_field.sql`
- Use descriptive names
- Test migrations on staging before production

### Query Performance
- Use eager loading to prevent N+1 queries
- Use `selectinload()` and `joinedload()` appropriately
- Monitor query performance with logging

## Docker & Deployment

### Development
```bash
docker-compose up -d                    # Start all services
docker-compose logs -f backend         # Watch backend logs
docker-compose exec backend bash       # Access backend container
```

### Production
- Use `docker-compose.prod.yml` if available
- Set `UPLOAD_DIR=/app/uploads` for persistent storage
- Ensure `WORDPRESS_PROXY_SECRET` matches WordPress config

## Common Patterns

### Conditional Fields (Backend)
```python
@field_validator('excursion_classes')
@classmethod
def validate_excursion_classes(cls, v, info):
    reason = info.data.get('reason')
    if reason == 'excursion' and (not v or not v.strip()):
        raise ValueError('Klasse(n) sind bei Exkursionen Pflichtfeld')
    return v
```

### Conditional Fields (Frontend)
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

### Permission Checks
```python
if current_user.role != UserRole.ADMIN:
    raise HTTPException(status_code=403, detail="Not authorized")
```

## Git Conventions

### Branch Naming
- `feature/feature-name`
- `fix/bug-description`
- `refactor/component-name`

### Commit Messages
- Use descriptive messages in German or English
- Include context about what and why
- Use conventional commits if preferred

### Co-Authoring
```
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

## Troubleshooting

### Common Issues
- **401 Invalid proxy secret**: Check `.env` and WordPress config
- **401 Not authenticated**: Ensure user is logged in WordPress
- **Uploads missing**: Check `UPLOAD_DIR` mounting in Docker
- **Build failures**: Check Node version and dependencies

### Debug Commands
```bash
# Check backend secret
docker-compose exec backend env | grep WORDPRESS_PROXY_SECRET

# Check WordPress nonce
window.vertretungsflowConfig?.nonce

# Check uploads
docker-compose exec backend ls -la /app/uploads/absence_*/

# Check backend logs
docker-compose logs backend | grep -i error
```

## Environment Variables

### Critical Variables
- `WORDPRESS_PROXY_SECRET`: Must match WordPress admin settings
- `UPLOAD_DIR`: Path for persistent file storage
- `DATABASE_URL`: PostgreSQL connection string
- `LDAP_*`: Active Directory configuration (if used)
- `WEBUNTIS_*`: WebUntis API credentials

## File Locations

### Backend
- Services: `backend/app/services/`
- API Routes: `backend/app/api/`
- Models: `backend/app/models/`
- Schemas: `backend/app/schemas/`
- Utils: `backend/app/utils/`
- Migrations: `backend/migrations/`

### Frontend
- API Client: `wordpress-plugin/src/api/client.ts`
- Types: `wordpress-plugin/src/types/index.ts`
- Pages: `wordpress-plugin/src/pages/`
- Build output: `wordpress-plugin/build/`

## Last Updated
- 2026-02-06
- Based on VertretungsFlow architecture and recent service refactorings