"""
Authentication API Routes
Login, JWT Token Management
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User, UserRole
from app.schemas.schemas import Token, TokenData, UserResponse, LoginRequest

# Conditional LDAP import
if settings.AUTH_MODE == "standalone":
    from app.services.ldap_service import ldap_service
else:
    ldap_service = None

router = APIRouter()

# OAuth2 Schema für Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def map_wordpress_role(wp_role: str) -> UserRole:
    """
    Mapped WordPress-Rolle zu AbsenzFlow UserRole

    Args:
        wp_role: WordPress-Rolle (admin/teacher/student)

    Returns:
        Entsprechende UserRole
    """
    role_mapping = {
        "admin": UserRole.ADMIN,
        "teacher": UserRole.TEACHER,
        "student": UserRole.STUDENT,
    }
    return role_mapping.get(wp_role.lower(), UserRole.TEACHER)


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


async def get_wordpress_proxy_user(
    x_wordpress_secret: Optional[str] = Header(None),
    x_wordpress_user: Optional[str] = Header(None),
    x_wordpress_email: Optional[str] = Header(None),
    x_wordpress_name: Optional[str] = Header(None),
    x_wordpress_role: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    WordPress Proxy Authentication

    Authentifiziert Requests vom WordPress-Plugin über Shared Secret.
    Verwendet für Server-to-Server Kommunikation ohne JWT Token.

    Im WordPress-Modus: Benutzerdaten kommen aus WordPress-Headers
    Im Standalone-Modus: Benutzerdaten kommen aus LDAP

    Args:
        x_wordpress_secret: Shared Secret aus WordPress Plugin
        x_wordpress_user: WordPress Username
        x_wordpress_email: WordPress User Email (nur WordPress-Modus)
        x_wordpress_name: WordPress User Display Name (nur WordPress-Modus)
        x_wordpress_role: WordPress User Role (nur WordPress-Modus)
        db: Database Session

    Returns:
        User Objekt

    Raises:
        HTTPException: Bei fehlerhaftem Secret oder User
    """
    if not x_wordpress_secret or not x_wordpress_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    # Shared Secret validieren
    if x_wordpress_secret != settings.WORDPRESS_PROXY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid proxy secret"
        )

    # User aus DB laden
    user = db.query(User).filter(User.username == x_wordpress_user).first()

    # Benutzerdaten je nach Auth-Modus holen
    if settings.AUTH_MODE == "wordpress":
        # WordPress-Modus: Daten aus Headers
        user_email = x_wordpress_email
        user_name = x_wordpress_name or x_wordpress_user
        user_role = map_wordpress_role(x_wordpress_role) if x_wordpress_role else UserRole.TEACHER

        if not user:
            # Neuer User - aus WordPress-Headers anlegen
            user = User(
                username=x_wordpress_user,
                email=user_email,
                full_name=user_name,
                role=user_role,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Smart Update: Nur aktualisieren wenn sich Daten geändert haben
            needs_update = False

            if user.email != user_email:
                user.email = user_email
                needs_update = True

            if user.full_name != user_name:
                user.full_name = user_name
                needs_update = True

            if user.role != user_role:
                user.role = user_role
                needs_update = True

            if needs_update:
                db.commit()
                db.refresh(user)

    else:
        # Standalone-Modus: Daten aus LDAP
        if not user:
            # User existiert noch nicht - aus LDAP laden und anlegen
            if ldap_service is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="LDAP service not available"
                )

            ldap_info = ldap_service.get_user_info(x_wordpress_user)

            if not ldap_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found in LDAP"
                )

            user = User(
                username=x_wordpress_user,
                email=ldap_info.get("email"),
                full_name=ldap_info.get("full_name", x_wordpress_user),
                role=UserRole.TEACHER,
                is_active=True
            )

            db.add(user)
            db.commit()
            db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return user


# Login-Endpoint nur im Standalone-Modus verfügbar
if settings.AUTH_MODE == "standalone":
    @router.post("/login", response_model=Token)
    async def login(
        login_data: LoginRequest,
        db: Session = Depends(get_db)
    ):
        """
        Login Endpoint - Authentifiziert User gegen LDAP

        Nur verfügbar im Standalone-Modus.
        Im WordPress-Modus erfolgt Authentifizierung über WordPress.

        Args:
            login_data: Username und Password
            db: Database Session

        Returns:
            JWT Access Token

        Raises:
            HTTPException: Bei fehlerhaften Credentials
        """
        if ldap_service is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LDAP service not available"
            )

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
