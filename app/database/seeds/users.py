"""
User seed data for testing and development.
"""

from uuid import UUID
from sqlmodel import Session
from app.models import User
from app.auth import hash_password


def seed_mock_users(session: Session) -> None:
    """Create mock users for testing purposes."""
    mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
    existing_user = session.get(User, mock_user_id)
    
    if not existing_user:
        mock_user = User(
            id=mock_user_id,
            email="test@example.com",
            password_hash=hash_password("password123"),  # Add required password hash
            is_active=True
        )
        session.add(mock_user)
        session.commit()
        print("✅ Created mock user for testing (email: test@example.com, password: password123)")
    else:
        print("ℹ️  Mock user already exists")
