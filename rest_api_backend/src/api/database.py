from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional

from sqlalchemy import Column, DateTime, String, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from .config import settings

logger = logging.getLogger(__name__)

if not settings.database_url:
    raise RuntimeError(
        "DATABASE_URL is not configured. Set it in .env, or ensure database/db_connection.txt "
        "exists with a valid psql URL."
    )

# Create engine; use pool_pre_ping for reliability with long-lived connections
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    """SQLAlchemy model for users table."""
    __tablename__ = "users"

    username = Column(String, primary_key=True, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    # PUBLIC_INTERFACE
    def to_profile_dict(self) -> dict:
        """Return a dictionary suitable for the /me endpoint."""
        return {
            "username": self.username,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) and self.created_at else None,
        }


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("DB transaction rolled back due to error: %s", exc)
        raise
    finally:
        db.close()


# PUBLIC_INTERFACE
def verify_connection() -> bool:
    """Try a simple SELECT 1 to verify DB connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        logger.exception("Failed to connect to the database.")
        return False


# PUBLIC_INTERFACE
def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Fetch a user by username."""
    return db.get(User, username)
