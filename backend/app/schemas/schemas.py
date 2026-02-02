"""
Pydantic Schemas für Request/Response Validierung
"""
import re
from datetime import datetime, date
from typing import Optional, List, Union
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.models import UserRole, AbsenceStatus


# ============ Security: Text Sanitization ============

def sanitize_text_input(
    value: Optional[str],
    max_length: int = 5000,
    allow_newlines: bool = True
) -> Optional[str]:
    """
    Sanitizes user text input to prevent XSS and injection attacks

    Security measures:
    - Strips HTML tags (e.g., <script>, <img>)
    - Removes dangerous control characters
    - Enforces max length
    - Allows normal text characters including <, >, etc. in text context

    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length
        allow_newlines: Whether to keep newline characters

    Returns:
        Sanitized string or None
    """
    if value is None:
        return None

    if not isinstance(value, str):
        return str(value)

    # Strip leading/trailing whitespace
    value = value.strip()

    if not value:
        return None

    # Remove HTML tags (simple but effective for most cases)
    # This removes <tag>, </tag>, <tag attr="value">, etc.
    value = re.sub(r'<[^>]+>', '', value)

    # Remove dangerous control characters (keep \n, \r, \t if allowed)
    if allow_newlines:
        # Keep newlines and tabs, remove other control chars
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
    else:
        # Remove all control characters
        value = re.sub(r'[\x00-\x1f\x7f]', '', value)

    # Remove NULL bytes (can cause issues in databases)
    value = value.replace('\x00', '')

    # Enforce max length
    if len(value) > max_length:
        value = value[:max_length]

    return value if value else None


# ============ User Schemas ============

class UserBase(BaseModel):
    """Basis User Schema"""
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    webuntis_teacher_code: Optional[str] = None


class UserCreate(UserBase):
    """User Creation Schema"""
    role: UserRole = UserRole.TEACHER


class UserResponse(UserBase):
    """User Response Schema"""
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ Auth Schemas ============

class Token(BaseModel):
    """JWT Token Response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token Payload"""
    username: Optional[str] = None


class LoginRequest(BaseModel):
    """Login Request"""
    username: str
    password: str


# ============ Absence Schemas ============

# Affected Lessons müssen VOR Absence definiert werden wegen Forward Reference

class AffectedLessonBase(BaseModel):
    """Basis für betroffene Stunden (kann auch Doppelstunden-Block sein)"""
    date: datetime
    period: int  # Start-Stunde
    end_period: Optional[int] = None  # End-Stunde (für Doppelstunden)
    subject: Optional[str] = None
    class_name: Optional[str] = None
    room: Optional[str] = None
    notes: Optional[str] = None
    can_be_canceled: Optional[bool] = False  # Kann die Stunde entfallen?

    @field_validator('date', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Akzeptiert sowohl date als auch datetime Strings"""
        if isinstance(v, str):
            # Wenn nur Datum (ohne Zeit), füge Mitternacht hinzu
            if 'T' not in v and ' ' not in v:
                v = f"{v}T00:00:00"
        return v


class AbsenceBase(BaseModel):
    """Basis Absence Schema"""
    reason: str = Field(..., min_length=1, max_length=100)
    start_date: datetime
    end_date: datetime
    start_period: int = Field(..., ge=1, le=16)  # Max 16 Stunden pro Tag
    end_period: int = Field(..., ge=1, le=16)  # Max 16 Stunden pro Tag

    # Conditional fields
    excursion_classes: Optional[str] = None
    personal_reason: Optional[str] = None
    admin_notes: Optional[str] = None

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Akzeptiert sowohl date als auch datetime Strings"""
        if isinstance(v, str):
            # Wenn nur Datum (ohne Zeit), füge Mitternacht hinzu
            if 'T' not in v and ' ' not in v:
                v = f"{v}T00:00:00"
        return v

    @field_validator('excursion_classes')
    @classmethod
    def validate_excursion_classes(cls, v, info):
        """Validierung: Pflicht bei Exkursion + Sanitization"""
        # Sanitize input first
        v = sanitize_text_input(v, max_length=500, allow_newlines=False)

        # Then validate required field logic
        reason = info.data.get('reason')
        if reason == 'excursion' and (not v or not v.strip()):
            raise ValueError('Klasse(n) sind bei Exkursionen Pflichtfeld')
        return v

    @field_validator('personal_reason')
    @classmethod
    def validate_personal_reason(cls, v, info):
        """Validierung: Pflicht bei Privat/Sonstiges + Sanitization"""
        # Sanitize input first
        v = sanitize_text_input(v, max_length=2000, allow_newlines=True)

        # Then validate required field logic
        reason = info.data.get('reason')
        if reason in ['personal', 'other'] and (not v or not v.strip()):
            raise ValueError('Begründung ist bei Privat/Sonstiges Pflichtfeld')
        return v

    @field_validator('admin_notes')
    @classmethod
    def validate_admin_notes(cls, v):
        """Sanitization for admin notes"""
        return sanitize_text_input(v, max_length=2000, allow_newlines=True)


class AbsenceCreate(AbsenceBase):
    """Absence Creation Schema"""
    affected_lessons: Optional[List[AffectedLessonBase]] = None


class AffectedLessonResponse(AffectedLessonBase):
    """Response für betroffene Stunden"""
    id: int
    absence_id: int
    
    class Config:
        from_attributes = True


class AffectedLessonUpdate(BaseModel):
    """Update für Hinweise zu betroffenen Stunden"""
    notes: Optional[str] = None

    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v):
        """Sanitization for lesson notes"""
        return sanitize_text_input(v, max_length=1000, allow_newlines=True)


# ============ Attachment Schemas ============

class AttachmentBase(BaseModel):
    """Basis für Anhänge"""
    filename: str
    mime_type: str
    file_size: int


class AttachmentResponse(AttachmentBase):
    """Response für Anhänge"""
    id: int
    absence_id: int
    stored_filename: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class AbsenceResponse(AbsenceBase):
    """Absence Response Schema"""
    id: int
    teacher_id: int
    status: AbsenceStatus
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Relationships
    teacher: UserResponse
    affected_lessons: List[AffectedLessonResponse] = []
    attachments: List[AttachmentResponse] = []

    class Config:
        from_attributes = True


class AbsenceUpdate(BaseModel):
    """Absence Update Schema"""
    reason: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    start_period: Optional[int] = Field(None, ge=1, le=16)  # Max 16 Stunden pro Tag
    end_period: Optional[int] = Field(None, ge=1, le=16)  # Max 16 Stunden pro Tag

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Akzeptiert sowohl date als auch datetime Strings"""
        if v is None:
            return v
        if isinstance(v, str):
            # Wenn nur Datum (ohne Zeit), füge Mitternacht hinzu
            if 'T' not in v and ' ' not in v:
                v = f"{v}T00:00:00"
        return v


class AbsenceApproval(BaseModel):
    """Absence Approval/Rejection Schema"""
    approved: bool
    notes: Optional[str] = None


# ============ WebUntis Schemas ============

class FetchLessonsRequest(BaseModel):
    """Request zum Abrufen von Stunden aus WebUntis"""
    start_date: datetime
    end_date: datetime
    start_period: int = Field(..., ge=1, le=16)
    end_period: int = Field(..., ge=1, le=16)

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Akzeptiert sowohl date als auch datetime Strings"""
        if isinstance(v, str):
            # Wenn nur Datum (ohne Zeit), füge Mitternacht hinzu
            if 'T' not in v and ' ' not in v:
                v = f"{v}T00:00:00"
        return v


class WebUntisLesson(BaseModel):
    """WebUntis Stunde (kann auch Doppelstunden-Block sein)"""
    date: datetime
    period: int  # Start-Stunde
    end_period: Optional[int] = None  # End-Stunde (für Doppelstunden, None = Einzelstunde)
    subject: str
    class_name: str
    room: Optional[str] = None

    @field_validator('date', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Akzeptiert sowohl date als auch datetime Strings"""
        if isinstance(v, str):
            # Wenn nur Datum (ohne Zeit), füge Mitternacht hinzu
            if 'T' not in v and ' ' not in v:
                v = f"{v}T00:00:00"
        return v


class WebUntisTimetableResponse(BaseModel):
    """Response mit Stundenplan aus WebUntis"""
    lessons: List[WebUntisLesson]


# ============ Admin Schemas ============

class RoleAssignment(BaseModel):
    """Rollen-Zuweisung"""
    user_id: int
    role: UserRole


class DashboardStats(BaseModel):
    """Dashboard Statistiken für Vertretungsplaner"""
    pending_absences: int
    approved_absences: int
    completed_absences: int
    total_affected_lessons: int
