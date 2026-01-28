"""
User management API endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas import User as UserSchema, UserUpdate
from app.api.deps import get_current_user, get_current_admin

router = APIRouter()


@router.get("", response_model=List[UserSchema])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    role: UserRole = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    List all users (admin only)
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        role: Filter by role
        db: Database session
        current_user: Current authenticated user (must be admin)
    
    Returns:
        List of users
    """
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific user
    
    Args:
        user_id: User ID
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        User details
    """
    # Users can only view their own profile unless they're admin
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.patch("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Update a user (admin only)
    
    Args:
        user_id: User ID
        user_data: Updated user data
        db: Database session
        current_user: Current authenticated user (must be admin)
    
    Returns:
        Updated user
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user fields
    for key, value in user_data.dict(exclude_unset=True).items():
        setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    
    return user


@router.get("/search/{username}", response_model=UserSchema)
async def search_user_by_username(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Search for a user by username (admin only)
    
    Args:
        username: Username to search for
        db: Database session
        current_user: Current authenticated user (must be admin)
    
    Returns:
        User if found
    """
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user
