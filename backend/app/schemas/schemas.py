"""
Pydantic Schemas für Request/Response Validierung
"""
from datetime import datetime, date
from typing import Optional, List, Union
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.models import UserRole, AbsenceStatus


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

class AbsenceBase(BaseModel):
    """Basis Absence Schema"""
    reason: str = Field(..., min_length=1, max_length=100)
    start_date: datetime
    end_date: datetime
    start_period: int = Field(..., ge=1, le=16)  # Max 16 Stunden pro Tag
    end_period: int = Field(..., ge=1, le=16)  # Max 16 Stunden pro Tag

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Akzeptiert sowohl date als auch datetime Strings"""
        if isinstance(v, str):
            # Wenn nur Datum (ohne Zeit), füge Mitternacht hinzu
            if 'T' not in v and ' ' not in v:
                v = f"{v}T00:00:00"
        return v


class AbsenceCreate(AbsenceBase):
    """Absence Creation Schema"""
    affected_lessons: Optional[List['AffectedLessonBase']] = None  # Optional: Frontend kann Stunden mit Hinweisen senden


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


class AffectedLessonResponse(AffectedLessonBase):
    """Response für betroffene Stunden"""
    id: int
    absence_id: int
    
    class Config:
        from_attributes = True


class AffectedLessonUpdate(BaseModel):
    """Update für Hinweise zu betroffenen Stunden"""
    notes: Optional[str] = None


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
