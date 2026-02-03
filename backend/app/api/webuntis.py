"""
WebUntis API Routes
Integration with WebUntis timetable system
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import User
from app.schemas.schemas import FetchLessonsRequest, WebUntisLesson
from app.api.auth import get_wordpress_proxy_user
from app.services.webuntis_service import webuntis_service
from app.services.absence_service import absence_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/absences/fetch-lessons", response_model=List[WebUntisLesson])
async def fetch_lessons_from_webuntis(
    request: FetchLessonsRequest,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db)
):
    """
    Lädt Stunden aus WebUntis für Vorschau (ohne DB-Speicherung)

    Wird vom WordPress-Frontend verwendet, um betroffene Stunden VOR dem Absenden anzuzeigen.
    Authentifizierung über WordPress Proxy Secret (kein JWT Token erforderlich).

    Args:
        request: Zeitraum und Perioden
        current_user: Aktueller User (via WordPress Proxy Auth)
        db: Database session

    Returns:
        Liste von WebUntis-Stunden im angegebenen Zeitraum
    """
    # Validierung (delegiert an Service)
    absence_service.validate_date_range(
        request.start_date,
        request.end_date,
        request.start_period,
        request.end_period
    )

    # Stunden aus WebUntis abrufen
    lessons = await webuntis_service.get_timetable_for_teacher(
        current_user.username,
        request.start_date,
        request.end_date,
        db=db,
        webuntis_code=current_user.webuntis_teacher_code
    )

    # Filtern nach Perioden (delegiert an Service)
    filtered_lessons = []
    for lesson in lessons:
        if absence_service.is_lesson_in_period(
            lesson,
            request.start_date,
            request.end_date,
            request.start_period,
            request.end_period
        ):
            filtered_lessons.append(lesson)

    return filtered_lessons
