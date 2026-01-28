"""
API dependencies for authentication and authorization
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User, UserRole

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
    
    Returns:
        Current user
    
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_teacher(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user and verify they are a teacher"""
    if current_user.role not in [UserRole.TEACHER, UserRole.DEPARTMENT_HEAD, UserRole.PLANNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    return current_user


async def get_current_department_head(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user and verify they are a department head or admin"""
    if current_user.role not in [UserRole.DEPARTMENT_HEAD, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Department head privileges required"
        )
    return current_user


async def get_current_planner(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user and verify they are a substitution planner or admin"""
    if current_user.role not in [UserRole.PLANNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Substitution planner privileges required"
        )
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user and verify they are an admin"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user
