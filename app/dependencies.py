"""
Shared dependencies for FastAPI routes.
"""
import logging
from typing import Generator, Optional
from uuid import UUID

from fastapi import HTTPException, Request, Depends, status
from sqlmodel import Session

from app.models import User
from app.auth import decode_access_token

logger = logging.getLogger(__name__)


def get_db(request: Request) -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI routes.
    
    This creates a database session, yields it to the route handler,
    and ensures it's properly closed after the request completes.
    This prevents connection pool exhaustion by guaranteeing cleanup.
    """
    db_session_maker = getattr(request.app.state, "db_session", None)
    if db_session_maker is None:
        raise HTTPException(500, "Database not initialized")
    
    db = db_session_maker()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token in httpOnly cookie.
    Use this dependency on routes that require authentication.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Get token from httpOnly cookie
    token = request.cookies.get("access_token")
    if not token:
        logger.warning("No access token found in cookies")
        raise credentials_exception
    
    # Decode the token
    payload = decode_access_token(token)
    if payload is None:
        logger.warning("Invalid token provided")
        raise credentials_exception
    
    # Extract user ID from token
    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        logger.warning("Token missing user ID")
        raise credentials_exception
    
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        logger.warning(f"Invalid user ID format in token: {user_id_str}")
        raise credentials_exception
    
    # Get user from database
    user = db.get(User, user_id)
    if user is None:
        logger.warning(f"User not found for ID: {user_id}")
        raise credentials_exception
    
    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account"
        )
    
    return user