"""
API Routes package
"""
from app.api import auth, absences, admin, users, deps

__all__ = [
    "auth",
    "absences",
    "admin",
    "users",
    "deps",
]
