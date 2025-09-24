"""
Shared dependencies for FastAPI routes.
"""
from typing import Generator
from fastapi import HTTPException, Request
from sqlmodel import Session


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