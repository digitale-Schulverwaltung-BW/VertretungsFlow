"""
Authentication API Routes
Login, JWT Token Management
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User, UserRole
from app.schemas.schemas import Token, TokenData, UserResponse, LoginRequest
from app.services.ldap_service import ldap_service

router = APIRouter()

# OAuth2 Schema für Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Erstellt JWT Access Token
    
    Args:
        data: Payload-Daten
        expires_delta: Ablaufzeit
        
    Returns:
        JWT Token String
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Holt aktuellen User aus JWT Token
    
    Args:
        token: JWT Token
        db: Database Session
        
    Returns:
        User Objekt
        
    Raises:
        HTTPException: Wenn Token ungültig
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
        
        token_data = TokenData(username=username)
        
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == token_data.username).first()
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Prüft ob User aktiv ist
    
    Args:
        current_user: Current User
        
    Returns:
        User Objekt
        
    Raises:
        HTTPException: Wenn User inaktiv
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return current_user


def require_role(allowed_roles: list[UserRole]):
    """
    Dependency für Rollen-basierte Zugriffskontrolle
    
    Args:
        allowed_roles: Liste erlaubter Rollen
        
    Returns:
        Dependency Function
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    
    return role_checker


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login Endpoint - Authentifiziert User gegen LDAP
    
    Args:
        login_data: Username und Password
        db: Database Session
        
    Returns:
        JWT Access Token
        
    Raises:
        HTTPException: Bei fehlerhaften Credentials
    """
    # LDAP Authentifizierung
    is_authenticated = ldap_service.authenticate(login_data.username, login_data.password)
    
    if not is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # User in DB suchen oder anlegen
    user = db.query(User).filter(User.username == login_data.username).first()
    
    if not user:
        # Neuer User - Info aus LDAP holen
        ldap_info = ldap_service.get_user_info(login_data.username)
        
        user = User(
            username=login_data.username,
            email=ldap_info.get("email") if ldap_info else None,
            full_name=ldap_info.get("full_name") if ldap_info else login_data.username,
            role=UserRole.TEACHER,  # Standard-Rolle
            is_active=True
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # JWT Token erstellen
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Gibt Informationen über aktuellen User zurück
    
    Args:
        current_user: Current User
        
    Returns:
        User Information
    """
    return current_user


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """
    Logout Endpoint
    
    Note: JWT Tokens können nicht server-seitig invalidiert werden.
    Client muss Token löschen.
    
    Args:
        current_user: Current User
        
    Returns:
        Success Message
    """
    return {"message": "Successfully logged out"}
