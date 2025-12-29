import os
import types
from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Import the FastAPI app and dependencies
from src.api.main import create_app
from src.api import routes_v1
from src.api.security import create_access_token

# ---- Test configuration and fixtures ----
#
# We avoid network/database access by overriding dependencies:
# - database.get_db -> yields a dummy session object not used by our overrides
# - routes_v1.get_user_by_username -> in-memory lookup
# - routes_v1.verify_password -> compares against a stored bcrypt hash or simple check
#
# The application code requires JWT_SECRET; we ensure it is set for tests.


@pytest.fixture(scope="session", autouse=True)
def _ensure_test_env():
    # Ensure a deterministic JWT secret for tests
    if not os.getenv("JWT_SECRET"):
        os.environ["JWT_SECRET"] = "test-secret-key"
    # Shorten token lifetime to speed up (but still valid for duration of tests)
    os.environ.setdefault("ACCESS_TOKEN_EXPIRES_MINUTES", "5")
    # Ensure no DATABASE_URL is required since we override DB dependencies
    # Note: the database module raises if imported without DATABASE_URL. Tests import app via create_app,
    # but routes_v1 imports database symbols. We'll override the DB-dependent callables in routes_v1.
    return


@pytest.fixture()
def seeded_user():
    """
    Seeded in-memory user object with fields similar to the SQLAlchemy model used by the API.
    """
    user = types.SimpleNamespace(
        username="testuser",
        # Simulate created_at value; /me response_model permits Optional[datetime]
        created_at=datetime.now(timezone.utc),
        # password_hash is not strictly needed by tests because we override verify_password,
        # but include for completeness
        password_hash="$2b$12$dummyhashfor-tests-not-used"
    )

    # Provide the same interface method as the model for /me
    def to_profile_dict():
        return {
            "username": user.username,
            "created_at": user.created_at.isoformat(),
        }

    user.to_profile_dict = to_profile_dict
    return user


@pytest.fixture()
def users_store(seeded_user):
    """
    In-memory users 'table'.
    """
    return {
        seeded_user.username: seeded_user
    }


@pytest.fixture()
def app_overridden(users_store):
    """
    Build the app and override dependencies to use in-memory user lookups
    and bypass the real database session.
    """
    app = create_app()

    # Dummy DB session generator (never used due to function overrides, but required by signature)
    def _dummy_get_db() -> Generator[Session, None, None]:
        yield None  # Placeholder; functions we depend on won't use this

    # Override DB dependency
    app.dependency_overrides[__import__("src.api.database", fromlist=["get_db"]).get_db] = _dummy_get_db  # type: ignore

    # Override get_user_by_username to use in-memory store
    def _get_user_by_username(_db, username: str):
        return users_store.get(username)

    # Override verify_password: return True if username exists and provided password is 'testpass'
    def _verify_password(plain: str, _password_hash: str) -> bool:
        return plain == "testpass"

    # Apply overrides on the module functions used by routes
    routes_v1.get_user_by_username = _get_user_by_username  # type: ignore
    routes_v1.verify_password = _verify_password  # type: ignore

    return app


@pytest.fixture()
def client(app_overridden) -> TestClient:
    """
    FastAPI TestClient with dependency overrides.
    """
    return TestClient(app_overridden)


@pytest.fixture()
def bearer_token(seeded_user) -> str:
    """
    Produce a valid bearer token for the seeded user using the application's signing settings.
    """
    # Use a small but safe expiration window
    delta = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", "5")))
    token = create_access_token(subject=seeded_user.username, expires_delta=delta)
    return token
