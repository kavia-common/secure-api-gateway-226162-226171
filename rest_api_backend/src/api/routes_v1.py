from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

from .config import settings
from .database import get_db, get_user_by_username, verify_connection, User
from .security import create_access_token, verify_password, decode_access_token
from sqlalchemy.orm import Session

router = APIRouter(prefix="/v1.0", tags=["v1.0"])

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/v1.0/get_token",
    scheme_name="Bearer",
    description="Include the token as: Authorization: Bearer <token>",
)


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type, always 'bearer'")


class LoginRequest(BaseModel):
    username: str = Field(..., examples=["testuser"])
    password: str = Field(..., examples=["changeme"])


class UserProfile(BaseModel):
    username: str
    created_at: Optional[datetime]


class HealthResponse(BaseModel):
    status: str = "ok"


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency that returns the current user from the JWT token."""
    username = decode_access_token(token)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Simple health check endpoint to verify API availability.",
    operation_id="v1_health",
)
def health() -> HealthResponse:
    """Health check endpoint.

    Returns the service status and also verifies DB connectivity in logs.
    """
    # Optional: log DB connectivity check; do not fail health on DB unavailability
    verify_connection()
    return HealthResponse(status="ok")


@router.post(
    "/get_token",
    response_model=TokenResponse,
    summary="Obtain JWT access token",
    description="Authenticate with username and password to receive a JWT access token.",
    operation_id="v1_get_token",
)
def get_token(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate user and issue JWT.

    Parameters:
    - username: user's unique username
    - password: user's plain text password

    Returns:
    - access_token: signed JWT token
    - token_type: 'bearer'
    """
    if not settings.jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret is not configured",
        )

    user = get_user_by_username(db, payload.username)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=user.username, expires_delta=settings.access_token_expires_delta())
    return TokenResponse(access_token=token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user's profile",
    description="Retrieve the current user's profile using the Bearer JWT token.",
    operation_id="v1_me",
)
def me(current_user: User = Depends(get_current_user)) -> UserProfile:
    """Return the profile of the authenticated user."""
    profile = current_user.to_profile_dict()
    return UserProfile(**profile)
