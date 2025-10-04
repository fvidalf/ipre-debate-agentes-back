"""
Minimal authentication utilities for JWT-based auth.
Focused on simplicity and security without overcomplication.
"""
import os
import hashlib
import secrets
import base64
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from jose import jwt, JWTError

# Auth configuration - use environment variables in production
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def hash_password(password: str) -> str:
    """Hash a plain password using scrypt."""
    # Generate a random salt
    salt = secrets.token_bytes(32)
    # Hash password with scrypt
    password_hash = hashlib.scrypt(
        password.encode('utf-8'),
        salt=salt,
        n=16384,  # CPU/memory cost factor
        r=8,      # Block size
        p=1       # Parallelization factor
    )
    # Combine salt and hash, encode as base64
    combined = salt + password_hash
    return base64.b64encode(combined).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    try:
        # Decode the stored hash
        combined = base64.b64decode(hashed_password.encode('utf-8'))
        # Extract salt (first 32 bytes) and hash (rest)
        salt = combined[:32]
        stored_hash = combined[32:]
        # Hash the provided password with the same salt
        password_hash = hashlib.scrypt(
            plain_password.encode('utf-8'),
            salt=salt,
            n=16384,
            r=8,
            p=1
        )
        # Compare hashes using constant-time comparison
        return secrets.compare_digest(stored_hash, password_hash)
    except Exception:
        return False


def create_access_token(user_id: UUID, email: str) -> str:
    """Create a JWT access token for a user."""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.
    Returns the payload if valid, None if invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None