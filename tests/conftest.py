"""Pytest fixtures for async FastAPI testing.

Loads `.env.test`, initializes a clean test database, and provides an
`AsyncClient` for integration tests. It also stubs outgoing email
helpers so tests don't require an SMTP server.
"""
import os
import pathlib
import pytest
from dotenv import load_dotenv


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def load_test_env():
    """Ensure .env.test is loaded before app modules import settings."""
    root = pathlib.Path(__file__).resolve().parent.parent
    dotenv_path = root / ".env.test"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=str(dotenv_path))
    else:
        # fallback to environment as-is
        pass


@pytest.fixture(scope="session")
def prepare_database(load_test_env):
    """Create clean schema for the test session."""
    # Import here after env is loaded so settings pick up .env.test
    from app.core.database import engine, Base, SessionLocal

    # Drop / create all tables to ensure clean DB
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    # Teardown: drop all tables
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(prepare_database):
    """Yield a SQLAlchemy session for direct DB access in tests."""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def patch_email_helpers(load_test_env):
    """Patch email sending helpers so tests don't attempt SMTP connections."""
    import app.services.email_service as email_service

    original_send_otp = getattr(email_service, "send_otp_email", None)
    original_send_password = getattr(email_service, "send_password_reset_email", None)
    original_send_email = getattr(email_service, "send_email", None)

    email_service.send_otp_email = lambda *a, **k: True
    email_service.send_password_reset_email = lambda *a, **k: True
    email_service.send_email = lambda *a, **k: True

    yield

    if original_send_otp is not None:
        email_service.send_otp_email = original_send_otp
    if original_send_password is not None:
        email_service.send_password_reset_email = original_send_password
    if original_send_email is not None:
        email_service.send_email = original_send_email


@pytest.fixture(scope="session")
def patch_sms_helpers(load_test_env):
    """Patch SMS sending helpers so tests don't hit Twilio."""
    import app.services.sms_service as sms_service

    original_send_otp_sms = getattr(sms_service, "send_otp_sms", None)
    original_send_sms = getattr(sms_service, "send_sms", None)

    sms_service.send_otp_sms = lambda *a, **k: True
    sms_service.send_sms = lambda *a, **k: True

    yield

    if original_send_otp_sms is not None:
        sms_service.send_otp_sms = original_send_otp_sms
    if original_send_sms is not None:
        sms_service.send_sms = original_send_sms


@pytest.fixture
async def async_client(patch_email_helpers, patch_sms_helpers, prepare_database):
    """Provide an httpx AsyncClient configured with the FastAPI app."""
    from httpx import AsyncClient
    from app.main import create_app

    app = create_app()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client
