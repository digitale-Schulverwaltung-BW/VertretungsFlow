"""
Main API router
"""
from fastapi import APIRouter

from app.api.endpoints import auth, absences, users

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(absences.router, prefix="/absences", tags=["absences"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
