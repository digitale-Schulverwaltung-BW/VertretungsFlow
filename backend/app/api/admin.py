"""
Admin API Routes
Verwaltung von Benutzerrollen, Dashboard, WebUntis Cache
"""

import logging
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.models.models import (
    User,
    Absence,
    AffectedLesson,
    UserRole,
    AbsenceStatus,
    WebUntisCache,
)
from app.schemas.schemas import (
    UserResponse,
    RoleAssignment,
    DashboardStats,
    AbsenceResponse,
)
from app.api.auth import get_current_active_user, get_wordpress_proxy_user, require_role

router = APIRouter()
logger = logging.getLogger(__name__)

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)


@router.get("/users", response_model=List[UserResponse])
@limiter.limit("30/minute")
async def list_users(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db),
):
    """
    Listet alle Benutzer auf

    Nur für Admins und Abteilungsleiter

    Args:
        skip: Anzahl zu überspringen
        limit: Maximale Anzahl
        current_user: Aktueller User
        db: Database Session

    Returns:
        Liste von Benutzern
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.DEPARTMENT_HEAD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.post("/users/{user_id}/role", response_model=UserResponse)
@limiter.limit("10/minute")
async def assign_role(
    request: Request,
    user_id: int,
    role_assignment: RoleAssignment,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    Weist einem Benutzer eine Rolle zu

    Nur für Admins

    Args:
        user_id: ID des Benutzers
        role_assignment: Rollen-Zuweisung
        current_user: Aktueller User (muss Admin sein)
        db: Database Session

    Returns:
        Aktualisierter Benutzer
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.role = role_assignment.role
    db.commit()
    db.refresh(user)

    return user


@router.get("/dashboard", response_model=DashboardStats)
@limiter.limit("60/minute")
async def get_dashboard_stats(
    request: Request,
    current_user: User = Depends(
        require_role([UserRole.PLANNER, UserRole.DEPARTMENT_HEAD, UserRole.ADMIN])
    ),
    db: Session = Depends(get_db),
):
    """
    Dashboard Statistiken für Vertretungsplaner

    Args:
        current_user: Aktueller User
        db: Database Session

    Returns:
        Dashboard Statistiken
    """
    # Zähle Abwesenheiten nach Status
    pending = (
        db.query(func.count(Absence.id))
        .filter(Absence.status == AbsenceStatus.SUBMITTED)
        .scalar()
    )

    approved = (
        db.query(func.count(Absence.id))
        .filter(Absence.status == AbsenceStatus.APPROVED)
        .scalar()
    )

    completed = (
        db.query(func.count(Absence.id))
        .filter(Absence.status == AbsenceStatus.COMPLETED)
        .scalar()
    )

    # Zähle betroffene Stunden (nur für genehmigte Abwesenheiten)
    total_lessons = (
        db.query(func.count(AffectedLesson.id))
        .join(Absence)
        .filter(Absence.status.in_([AbsenceStatus.APPROVED, AbsenceStatus.COMPLETED]))
        .scalar()
    )

    return DashboardStats(
        pending_absences=pending,
        approved_absences=approved,
        completed_absences=completed,
        total_affected_lessons=total_lessons,
    )


@router.get("/absences/pending", response_model=List[AbsenceResponse])
@limiter.limit("60/minute")
async def list_pending_absences(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(
        require_role([UserRole.PLANNER, UserRole.DEPARTMENT_HEAD, UserRole.ADMIN])
    ),
    db: Session = Depends(get_db),
):
    """
    Listet ausstehende Abwesenheiten für Vertretungsplaner

    Sortiert nach Fälligkeitsdatum (start_date)

    Args:
        skip: Anzahl zu überspringen
        limit: Maximale Anzahl
        current_user: Aktueller User
        db: Database Session

    Returns:
        Liste von Abwesenheiten
    """
    absences = (
        db.query(Absence)
        .filter(Absence.status.in_([AbsenceStatus.SUBMITTED, AbsenceStatus.APPROVED]))
        .order_by(Absence.start_date.asc())  # Sortiert nach Datum aufsteigend
        .offset(skip)
        .limit(limit)
        .all()
    )

    return absences


@router.get("/absences/by-date")
@limiter.limit("60/minute")
async def list_absences_by_date(
    request: Request,
    from_date: str,
    to_date: str,
    current_user: User = Depends(
        require_role([UserRole.PLANNER, UserRole.DEPARTMENT_HEAD, UserRole.ADMIN])
    ),
    db: Session = Depends(get_db),
):
    """
    Listet Abwesenheiten in einem Datumsbereich

    Args:
        from_date: Startdatum (YYYY-MM-DD)
        to_date: Enddatum (YYYY-MM-DD)
        current_user: Aktueller User
        db: Database Session

    Returns:
        Liste von Abwesenheiten
    """
    from datetime import datetime

    try:
        start = datetime.strptime(from_date, "%Y-%m-%d")
        end = datetime.strptime(to_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD",
        )

    absences = (
        db.query(Absence)
        .filter(
            Absence.start_date >= start,
            Absence.end_date <= end,
            Absence.status != AbsenceStatus.REJECTED,
        )
        .order_by(Absence.start_date.asc())
        .all()
    )

    return absences


# ============ WebUntis Cache Management ============


@router.post("/webuntis-cache/refresh")
@limiter.limit("5/minute")
async def refresh_webuntis_cache(
    request: Request,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.PLANNER])),
    db: Session = Depends(get_db),
):
    """
    Manuelles Refresh der WebUntis Stammdaten
    Nur für Admin/Planner
    """
    # Import here to avoid circular dependency
    from app.services.webuntis import webuntis_service

    # Clear in-memory cache
    webuntis_service._subjects_cache = None
    webuntis_service._classes_cache = None
    webuntis_service._rooms_cache = None
    webuntis_service._timegrid_cache = None

    # Delete DB cache (force re-fetch)
    db.query(WebUntisCache).delete()
    db.commit()

    logger.info(f"WebUntis cache cleared by {current_user.username}")

    return {
        "message": "WebUntis cache cleared. Next absence will refresh data.",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/webuntis-cache/status")
@limiter.limit("30/minute")
async def get_cache_status(
    request: Request,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.PLANNER])),
    db: Session = Depends(get_db),
):
    """
    Cache-Status anzeigen
    Nur für Admin/Planner
    """
    # Import here to avoid circular dependency
    from app.services.webuntis import webuntis_service

    cache_entries = db.query(WebUntisCache).all()

    return {
        "cached_keys": [
            {
                "key": entry.cache_key,
                "created_at": entry.created_at.isoformat(),
                "expires_at": (
                    entry.expires_at.isoformat() if entry.expires_at else None
                ),
                "is_expired": (
                    entry.expires_at < datetime.utcnow() if entry.expires_at else False
                ),
                "items_count": (
                    len(entry.cache_data) if isinstance(entry.cache_data, dict) else 0
                ),
            }
            for entry in cache_entries
        ],
        "in_memory_cache": {
            "subjects": webuntis_service._subjects_cache is not None,
            "classes": webuntis_service._classes_cache is not None,
            "rooms": webuntis_service._rooms_cache is not None,
            "timegrid": webuntis_service._timegrid_cache is not None,
        },
    }


# ============ Absence Auto-Deletion Management ============


@router.post("/cleanup-old-absences")
@limiter.limit("5/minute")
async def trigger_cleanup(
    request: Request,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    Manually trigger cleanup of old absences (Admin only)

    Deletes absences older than ABSENCE_RETENTION_DAYS (based on end_date).
    This is normally run automatically at 02:00 AM via APScheduler.

    Args:
        current_user: Current authenticated user (must be Admin)
        db: Database session

    Returns:
        Cleanup result with statistics
    """
    from app.core.config import settings
    from app.services.absence_service import absence_service

    logger.info(f"Manual cleanup triggered by {current_user.username}")

    result = absence_service.cleanup_old_absences(
        db=db, retention_days=settings.ABSENCE_RETENTION_DAYS
    )

    return {
        "message": "Cleanup completed",
        "result": result,
        "triggered_by": current_user.username,
        "timestamp": datetime.utcnow().isoformat(),
    }
