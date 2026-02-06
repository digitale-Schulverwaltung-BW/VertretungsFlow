"""
PDF Forms API Routes
Download pre-filled PDF forms for absences
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session, selectinload, joinedload
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.models.models import User, Absence, UserRole
from app.api.auth import get_wordpress_proxy_user
from app.services.pdf_service import pdf_service
from app.services.permission_service import permission_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)


@router.get("/absences/{absence_id}/pdf-forms")
@limiter.limit("20/minute")
async def list_available_forms(
    request: Request,
    absence_id: int,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    List available PDF forms for an absence

    Args:
        absence_id: Absence ID
        current_user: Current user
        db: Database session

    Returns:
        List of available form info dicts

    Raises:
        HTTPException: If absence not found or not authorized
    """
    logger.info(f"📋 List available PDF forms for absence {absence_id}")

    # Load absence with relationships
    absence = (
        db.query(Absence)
        .options(joinedload(Absence.teacher), selectinload(Absence.affected_lessons))
        .filter(Absence.id == absence_id)
        .first()
    )

    if not absence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Absence not found"
        )

    # Permission check: User can only download their own forms (unless admin/planner)
    if not permission_service.can_view_absence(current_user, absence):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this absence",
        )

    # Get available forms from service
    available_forms = pdf_service.get_available_forms(absence)

    return available_forms


@router.get("/absences/{absence_id}/pdf-forms/{form_type}")
@limiter.limit("10/minute")
async def download_pdf_form(
    request: Request,
    absence_id: int,
    form_type: str,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db),
) -> Response:
    """
    Download pre-filled PDF form for an absence

    Args:
        absence_id: Absence ID
        form_type: Form type identifier (e.g., "excursion_form", "business_trip_form")
        current_user: Current user
        db: Database session

    Returns:
        PDF file as binary response

    Raises:
        HTTPException: If absence not found, not authorized, or form generation fails
    """
    logger.info(
        f"📥 Download PDF form '{form_type}' for absence {absence_id} by user {current_user.username}"
    )

    # Load absence with relationships
    absence = (
        db.query(Absence)
        .options(joinedload(Absence.teacher), selectinload(Absence.affected_lessons))
        .filter(Absence.id == absence_id)
        .first()
    )

    if not absence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Absence not found"
        )

    # Permission check: User can only download their own forms (unless admin/planner)
    if not permission_service.can_view_absence(current_user, absence):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to download forms for this absence",
        )

    # Check if form type is applicable for this absence
    available_forms = pdf_service.get_available_forms(absence)
    form_types = [f["type"] for f in available_forms]

    if form_type not in form_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Form type '{form_type}' not applicable for absence reason '{absence.reason}'",
        )

    # Generate filled PDF
    pdf_bytes = await pdf_service.generate_filled_pdf(absence, form_type, db)

    # Determine filename
    form_label = next(
        (f["label"] for f in available_forms if f["type"] == form_type), form_type
    )
    # Sanitize filename (remove special characters)
    safe_label = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_" for c in form_label
    )
    filename = f"Antrag_Absenz_{absence_id}_{safe_label}.pdf"

    logger.info(f"✅ PDF generated: {len(pdf_bytes)} bytes, filename: {filename}")

    # Return PDF as response
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
