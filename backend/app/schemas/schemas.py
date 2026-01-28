"""
Pydantic Schemas für Request/Response Validierung
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.models.models import UserRole, AbsenceStatus


# ============ User Schemas ============

class UserBase(BaseModel):
    """Basis User Schema"""
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


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
    start_period: int = Field(..., ge=1, le=10)
    end_period: int = Field(..., ge=1, le=10)


class AbsenceCreate(AbsenceBase):
    """Absence Creation Schema"""
    pass


class AffectedLessonBase(BaseModel):
    """Basis für betroffene Stunden"""
    date: datetime
    period: int
    subject: Optional[str] = None
    class_name: Optional[str] = None
    room: Optional[str] = None
    notes: Optional[str] = None


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
    start_period: Optional[int] = Field(None, ge=1, le=10)
    end_period: Optional[int] = Field(None, ge=1, le=10)


class AbsenceApproval(BaseModel):
    """Absence Approval/Rejection Schema"""
    approved: bool
    notes: Optional[str] = None


# ============ WebUntis Schemas ============

class WebUntisLesson(BaseModel):
    """WebUntis Stunde"""
    date: datetime
    period: int
    subject: str
    class_name: str
    room: Optional[str] = None


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
