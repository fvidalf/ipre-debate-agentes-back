"""
Authentication routes for the minimal auth system.
Provides login endpoint only.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.dependencies import get_db
from app.models import User
from app.auth import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/login")
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login endpoint that accepts email/password and returns JWT token.
    Uses OAuth2PasswordRequestForm for compatibility with OpenAPI docs.
    """
    logger.info(f"Login attempt for user: {form_data.username}")
    
    # Find user by email (username field in OAuth2 form)
    stmt = select(User).where(User.email == form_data.username)
    user = db.exec(stmt).first()
    
    if not user:
        logger.warning(f"Login failed: user not found for {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        logger.warning(f"Login failed: inactive user {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    if not verify_password(form_data.password, user.password_hash):
        logger.warning(f"Login failed: incorrect password for {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    
    # Update last login timestamp
    user.last_login_at = datetime.utcnow()
    db.add(user)
    db.commit()
    
    # Generate access token
    access_token = create_access_token(user.id, user.email)
    
    # Set httpOnly cookie (secure in production)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=3600  # 1 hour, matching token expiration
    )
    
    logger.info(f"Successful login for user: {user.email}")
    
    return {
        "message": "Login successful",
        "user": {
            "email": user.email,
            "id": str(user.id)
        }
    }


@router.post("/logout")
def logout(response: Response):
    """
    Logout endpoint that clears the httpOnly access token cookie.
    """
    logger.info("User logged out")
    
    # Clear the httpOnly cookie by setting it to expire immediately
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=0  # Expire immediately
    )
    
    return {
        "message": "Logout successful"
    }