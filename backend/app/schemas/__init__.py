"""
Schemas package
"""
from app.schemas.schemas import (
    # User
    UserBase,
    UserCreate,
    UserResponse,
    # Auth
    Token,
    TokenData,
    LoginRequest,
    # Absence
    AbsenceBase,
    AbsenceCreate,
    AbsenceResponse,
    # Affected Lessons
    AffectedLessonBase,
    AffectedLessonResponse,
    AffectedLessonUpdate,
)

__all__ = [
    # User
    "UserBase",
    "UserCreate",
    "UserResponse",
    # Auth
    "Token",
    "TokenData",
    "LoginRequest",
    # Absence
    "AbsenceBase",
    "AbsenceCreate",
    "AbsenceResponse",
    # Affected Lessons
    "AffectedLessonBase",
    "AffectedLessonResponse",
    "AffectedLessonUpdate",
]
