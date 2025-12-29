import os
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv

# Load .env from project root or container root
load_dotenv()


@dataclass
class Settings:
    """Application settings loaded from environment variables.

    This centralizes all configuration values and provides safe defaults for development.
    DATABASE_URL is required for DB connectivity. If not present, we try to read it
    from the sibling database container's db_connection.txt. If the helper file points
    to a local dev port (e.g., 5000) but a preview database runs on another port (e.g., 5001),
    you can set DB_FALLBACK_PORT_OVERRIDE or POSTGRES_PORT to adjust dynamically.
    """
    app_title: str = "Secure API Gateway"
    app_description: str = (
        "Backend service providing REST API endpoints with JWT-based authentication. "
        "Versioned endpoints are exposed under /v1.0."
    )
    app_version: str = "1.0.0"

    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expires_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", "30"))

    database_url: Optional[str] = os.getenv("DATABASE_URL")

    cors_allow_origins: list[str] = None
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = None
    cors_allow_headers: list[str] = None

    def _apply_port_override(self, url: str) -> str:
        """Apply optional port override ONLY to postgres URLs when override env is set.

        Guard: Modify URLs that start with 'postgres://' or 'postgresql://'. Return unchanged otherwise.
        """
        try:
            # Only consider override for Postgres URLs
            if not (url.startswith("postgres://") or url.startswith("postgresql://")):
                return url

            override = os.getenv("DB_FALLBACK_PORT_OVERRIDE") or os.getenv("POSTGRES_PORT")
            if not override:
                return url

            port_int = int(override)
            parsed = urlparse(url)

            # Extract components safely
            hostname = parsed.hostname or ""
            username = parsed.username or ""
            password = parsed.password or ""
            # Preserve IPv6 formatting and hostname casing as parsed provides lowercased hostnames.
            # Reconstruct netloc with auth and override port
            auth = ""
            if username and password:
                auth = f"{username}:{password}@"
            elif username:
                auth = f"{username}@"

            # If hostname was empty or parsing failed for some reason, just return original
            if not hostname:
                return url

            new_netloc = f"{auth}{hostname}:{port_int}"
            # Preserve path, params, query, fragment
            rebuilt = parsed._replace(netloc=new_netloc)
            return urlunparse(rebuilt)
        except Exception:
            # If anything goes wrong, return the original URL unchanged
            return url

    # PUBLIC_INTERFACE
    def access_token_expires_delta(self) -> timedelta:
        """Return a timedelta representing the access token expiration interval."""
        return timedelta(minutes=self.access_token_expires_minutes)

    def __post_init__(self):
        # Set permissive CORS defaults for development
        if self.cors_allow_origins is None:
            self.cors_allow_origins = ["*"]
        if self.cors_allow_methods is None:
            self.cors_allow_methods = ["*"]
        if self.cors_allow_headers is None:
            self.cors_allow_headers = ["*"]

        # Try to read DATABASE_URL from database container's db_connection.txt if not set
        if not self.database_url:
            potential_path = os.path.join(
                os.getcwd(),
                "..",
                "secure-api-gateway-226162-226172",
                "database",
                "db_connection.txt",
            )
            try:
                with open(potential_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    # File may contain a line like: psql postgresql://user:pass@host:port/db
                    if content.startswith("psql "):
                        content = content[len("psql "):]
                    if content.startswith("postgres://") or content.startswith("postgresql://"):
                        self.database_url = self._apply_port_override(content)
            except FileNotFoundError:
                # Leave as None; app will raise a clear error at startup if needed
                pass

        # If database_url came from env directly, still allow port override for preview convenience
        if self.database_url:
            self.database_url = self._apply_port_override(self.database_url)


settings = Settings()
