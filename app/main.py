from fastapi import FastAPI
from fastapi.exceptions import HTTPException as FastAPIHTTPException

from app.core.logger import setup_logging
from app.middleware.cors import configure_cors
from app.middleware.logging import RequestLoggerMiddleware
from app.middleware.auth import JWTMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware import error_handler

# Routers
from app.routers import auth as auth_router
from app.routers import users as users_router
from app.routers import doctors as doctors_router
from app.routers import patients as patients_router
from app.routers import admin as admin_router
from app.routers import health as health_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    setup_logging()
    description = (
        "Kalved Backend API.\n\n"
        "This service provides authentication, user, doctor and patient management endpoints."
    )

    openapi_tags = [
        {"name": "authentication", "description": "Endpoints to register, login, verify OTP and social auth."},
        {"name": "users", "description": "User profile and account management."},
        {"name": "doctors", "description": "Doctor profiles, qualifications and admin approvals."},
        {"name": "patients", "description": "Patient records and interactions."},
        {"name": "admin", "description": "Administrative endpoints for approvals and audits."},
        {"name": "health", "description": "Health checks and service status endpoints."},
    ]

    app = FastAPI(
        title="Kalved Ayurveda Backend API",
        version="0.1.0",
        description=description,
        openapi_tags=openapi_tags,
    )

    # Middleware
    configure_cors(app)
    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(JWTMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # Exception handlers
    app.add_exception_handler(FastAPIHTTPException, error_handler.http_exception_handler)

    # Include routers
    app.include_router(health_router.router)
    app.include_router(auth_router.router)
    app.include_router(users_router.router)
    app.include_router(doctors_router.router)
    app.include_router(patients_router.router)
    app.include_router(admin_router.router)

    return app


app = create_app()
