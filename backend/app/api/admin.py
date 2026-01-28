"""
Admin API Routes
Verwaltung von Benutzerrollen, Dashboard
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.models import User, Absence, AffectedLesson, UserRole, AbsenceStatus
from app.schemas.schemas import (
    UserResponse,
    RoleAssignment,
    DashboardStats,
    AbsenceResponse
)
from app.api.auth import get_current_active_user, require_role

router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.DEPARTMENT_HEAD])),
    db: Session = Depends(get_db)
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
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.post("/users/{user_id}/role", response_model=UserResponse)
async def assign_role(
    user_id: int,
    role_assignment: RoleAssignment,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.role = role_assignment.role
    db.commit()
    db.refresh(user)
    
    return user


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(require_role([UserRole.PLANNER, UserRole.DEPARTMENT_HEAD, UserRole.ADMIN])),
    db: Session = Depends(get_db)
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
    pending = db.query(func.count(Absence.id)).filter(
        Absence.status == AbsenceStatus.SUBMITTED
    ).scalar()
    
    approved = db.query(func.count(Absence.id)).filter(
        Absence.status == AbsenceStatus.APPROVED
    ).scalar()
    
    completed = db.query(func.count(Absence.id)).filter(
        Absence.status == AbsenceStatus.COMPLETED
    ).scalar()
    
    # Zähle betroffene Stunden (nur für genehmigte Abwesenheiten)
    total_lessons = db.query(func.count(AffectedLesson.id)).join(
        Absence
    ).filter(
        Absence.status.in_([AbsenceStatus.APPROVED, AbsenceStatus.COMPLETED])
    ).scalar()
    
    return DashboardStats(
        pending_absences=pending,
        approved_absences=approved,
        completed_absences=completed,
        total_affected_lessons=total_lessons
    )


@router.get("/absences/pending", response_model=List[AbsenceResponse])
async def list_pending_absences(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role([UserRole.PLANNER, UserRole.DEPARTMENT_HEAD, UserRole.ADMIN])),
    db: Session = Depends(get_db)
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
    absences = db.query(Absence).filter(
        Absence.status.in_([AbsenceStatus.SUBMITTED, AbsenceStatus.APPROVED])
    ).order_by(
        Absence.start_date.asc()  # Sortiert nach Datum aufsteigend
    ).offset(skip).limit(limit).all()
    
    return absences


@router.get("/absences/by-date")
async def list_absences_by_date(
    from_date: str,
    to_date: str,
    current_user: User = Depends(require_role([UserRole.PLANNER, UserRole.DEPARTMENT_HEAD, UserRole.ADMIN])),
    db: Session = Depends(get_db)
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
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    absences = db.query(Absence).filter(
        Absence.start_date >= start,
        Absence.end_date <= end,
        Absence.status != AbsenceStatus.REJECTED
    ).order_by(Absence.start_date.asc()).all()
    
    return absences
