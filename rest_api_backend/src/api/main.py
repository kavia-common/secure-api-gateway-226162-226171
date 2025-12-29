from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes_v1 import router as v1_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application with metadata, CORS, and routes."""
    app = FastAPI(
        title=settings.app_title,
        description=settings.app_description,
        version=settings.app_version,
        openapi_tags=[
            {"name": "v1.0", "description": "Version 1.0 API endpoints"},
        ],
    )

    # CORS middleware with permissive defaults for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Register versioned routes
    app.include_router(v1_router)

    @app.get(
        "/",
        summary="Root Health Check",
        description="Basic root endpoint to verify service is running.",
        operation_id="root_health",
        tags=["v1.0"],
    )
    def health_check():
        """Root health endpoint."""
        return {"status": "ok", "message": "Healthy"}

    return app


app = create_app()
