"""
Authentication API Routes
Login, JWT Token Management
"""

import hmac
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from urllib.parse import unquote
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import get_db
from app.core.audit import audit_log
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

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)


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
        "dept_head": UserRole.DEPARTMENT_HEAD,
        "planner": UserRole.PLANNER,
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
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
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
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
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


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
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
                status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
            )
        return current_user

    return role_checker


def _decode_wordpress_name(header_value: Optional[str]) -> Optional[str]:
    """
    URL-decode WordPress header name

    Args:
        header_value: URL-encoded name from WordPress header

    Returns:
        Decoded and stripped name, or None
    """
    return unquote(header_value).strip() if header_value else None


def _create_wordpress_user(
    db: Session,
    username: str,
    email: str,
    full_name: str,
    first_name: Optional[str],
    last_name: Optional[str],
    role: UserRole,
    webuntis_code: Optional[str],
) -> User:
    """
    Create new user from WordPress proxy data

    Args:
        db: Database session
        username: WordPress username
        email: User email
        full_name: User display name
        first_name: User first name (URL-decoded)
        last_name: User last name (URL-decoded)
        role: User role
        webuntis_code: WebUntis teacher code

    Returns:
        Created User object
    """
    user = User(
        username=username,
        email=email,
        full_name=full_name,
        first_name=first_name,
        last_name=last_name,
        role=role,
        webuntis_teacher_code=webuntis_code,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Audit log for user creation
    audit_log(
        action="user_created",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        details={
            "username": username,
            "email": email,
            "role": role.value,
            "webuntis_code": webuntis_code,
            "source": "wordpress_proxy",
        },
        ip_address="wordpress-proxy",
    )

    return user


def _update_wordpress_user_fields(
    user: User,
    email: str,
    full_name: str,
    first_name: Optional[str],
    last_name: Optional[str],
    role: UserRole,
    webuntis_code: Optional[str],
) -> Tuple[bool, Dict[str, Any]]:
    """
    Update user fields from WordPress data (smart update)

    Compares current user fields with new values and updates only what changed.

    Args:
        user: Existing user to update
        email: New email
        full_name: New display name
        first_name: New first name
        last_name: New last name
        role: New role
        webuntis_code: New WebUntis code

    Returns:
        Tuple of (needs_update, update_details):
        - needs_update: True if any field changed
        - update_details: Dict of changes (old/new values)
    """
    needs_update = False
    update_details = {}

    if user.email != email:
        update_details["old_email"] = user.email
        update_details["new_email"] = email
        user.email = email
        needs_update = True

    if user.full_name != full_name:
        update_details["old_name"] = user.full_name
        update_details["new_name"] = full_name
        user.full_name = full_name
        needs_update = True

    if user.first_name != first_name:
        user.first_name = first_name
        needs_update = True

    if user.last_name != last_name:
        user.last_name = last_name
        needs_update = True

    if user.role != role:
        update_details["old_role"] = user.role.value
        update_details["new_role"] = role.value
        user.role = role
        needs_update = True

    if user.webuntis_teacher_code != webuntis_code:
        update_details["old_webuntis_code"] = user.webuntis_teacher_code
        update_details["new_webuntis_code"] = webuntis_code
        user.webuntis_teacher_code = webuntis_code
        needs_update = True

    return needs_update, update_details


def _create_ldap_user(
    db: Session,
    username: str,
    ldap_info: dict,
) -> User:
    """
    Create new user from LDAP data

    Args:
        db: Database session
        username: LDAP username
        ldap_info: User info from LDAP (email, full_name)

    Returns:
        Created User object
    """
    user = User(
        username=username,
        email=ldap_info.get("email"),
        full_name=ldap_info.get("full_name", username),
        role=UserRole.TEACHER,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Audit log for LDAP user creation
    audit_log(
        action="user_created",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        details={
            "username": username,
            "email": ldap_info.get("email"),
            "role": UserRole.TEACHER.value,
            "source": "ldap",
        },
        ip_address="wordpress-proxy",
    )

    return user


async def get_wordpress_proxy_user(
    x_wordpress_secret: Optional[str] = Header(None),
    x_wordpress_user: Optional[str] = Header(None),
    x_wordpress_email: Optional[str] = Header(None),
    x_wordpress_name: Optional[str] = Header(None),
    x_wordpress_first_name: Optional[str] = Header(None),
    x_wordpress_last_name: Optional[str] = Header(None),
    x_wordpress_role: Optional[str] = Header(None),
    x_wordpress_webuntis_code: Optional[str] = Header(None),
    db: Session = Depends(get_db),
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
    # Validate secret and username
    if not x_wordpress_secret or not x_wordpress_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    # Shared Secret validieren (constant-time comparison to prevent timing attacks)
    if not hmac.compare_digest(x_wordpress_secret, settings.WORDPRESS_PROXY_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid proxy secret"
        )

    # Load existing user from database
    user = db.query(User).filter(User.username == x_wordpress_user).first()

    # Route to appropriate handler based on auth mode
    if settings.AUTH_MODE == "wordpress":
        user = _handle_wordpress_proxy_user(
            user,
            db,
            x_wordpress_user,
            x_wordpress_email,
            x_wordpress_name,
            x_wordpress_first_name,
            x_wordpress_last_name,
            x_wordpress_role,
            x_wordpress_webuntis_code,
        )
    else:
        user = await _handle_ldap_proxy_user(user, db, x_wordpress_user)

    # Validate user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    return user


def _handle_wordpress_proxy_user(
    user: Optional[User],
    db: Session,
    username: str,
    email: Optional[str],
    display_name: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    role: Optional[str],
    webuntis_code: Optional[str],
) -> User:
    """
    Handle WordPress proxy authentication flow

    Args:
        user: Existing user or None
        db: Database session
        username: WordPress username
        email: WordPress user email
        display_name: WordPress user display name
        first_name: WordPress user first name (URL-encoded)
        last_name: WordPress user last name (URL-encoded)
        role: WordPress user role
        webuntis_code: WebUntis teacher code

    Returns:
        User object (created or updated)
    """
    user_email = email
    user_role = map_wordpress_role(role) if role else UserRole.TEACHER
    webuntis_code_clean = _decode_wordpress_name(webuntis_code)

    # Decode first and last names
    first_name_decoded = _decode_wordpress_name(first_name)
    last_name_decoded = _decode_wordpress_name(last_name)

    # Prefer explicit first+last name over display_name (which defaults to username in WP)
    if first_name_decoded and last_name_decoded:
        user_name = f"{first_name_decoded} {last_name_decoded}"
    else:
        user_name = display_name or username

    if not user:
        # Create new user from WordPress headers
        user = _create_wordpress_user(
            db,
            username,
            user_email,
            user_name,
            first_name_decoded,
            last_name_decoded,
            user_role,
            webuntis_code_clean,
        )
    else:
        # Update existing user if needed
        needs_update, update_details = _update_wordpress_user_fields(
            user,
            user_email,
            user_name,
            first_name_decoded,
            last_name_decoded,
            user_role,
            webuntis_code_clean,
        )

        if needs_update:
            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)

            # Audit log for user update
            audit_log(
                action="user_updated",
                user_id=user.id,
                resource_type="user",
                resource_id=user.id,
                details={
                    "username": username,
                    "changes": update_details,
                    "source": "wordpress_proxy",
                },
                ip_address="wordpress-proxy",
            )

    return user


async def _handle_ldap_proxy_user(
    user: Optional[User],
    db: Session,
    username: str,
) -> User:
    """
    Handle LDAP proxy authentication flow

    Args:
        user: Existing user or None
        db: Database session
        username: LDAP username

    Returns:
        User object (created from LDAP)
    """
    if user:
        return user

    # User doesn't exist - try to create from LDAP
    if ldap_service is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LDAP service not available",
        )

    ldap_info = ldap_service.get_user_info(username)

    if not ldap_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in LDAP",
        )

    return _create_ldap_user(db, username, ldap_info)


# Login-Endpoint nur im Standalone-Modus verfügbar
if settings.AUTH_MODE == "standalone":

    @router.post("/login", response_model=Token)
    @limiter.limit("5/minute")
    async def login(
        request: Request, login_data: LoginRequest, db: Session = Depends(get_db)
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
                detail="LDAP service not available",
            )

        # LDAP Authentifizierung
        is_authenticated = ldap_service.authenticate(
            login_data.username, login_data.password
        )

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
                full_name=(
                    ldap_info.get("full_name") if ldap_info else login_data.username
                ),
                role=UserRole.TEACHER,  # Standard-Rolle
                is_active=True,
            )

            db.add(user)
            db.commit()
            db.refresh(user)

        # JWT Token erstellen
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
@limiter.limit("30/minute")
async def read_users_me(
    request: Request, current_user: User = Depends(get_wordpress_proxy_user)
):
    """
    Gibt Informationen über aktuellen User zurück

    Unterstützt sowohl JWT-Auth als auch WordPress Proxy Auth

    Args:
        request: HTTP Request
        current_user: Current User

    Returns:
        User Information
    """
    return current_user


@router.post("/logout")
@limiter.limit("10/minute")
async def logout(
    request: Request, current_user: User = Depends(get_current_active_user)
):
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
