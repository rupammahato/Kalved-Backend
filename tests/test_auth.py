"""Integration tests for authentication routes.

These tests run against the FastAPI app using an in-memory/test DB
configured by `.env.test`. Email sending is stubbed so no SMTP is required.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest


async def test_register_verify_login_refresh_logout(async_client, db_session):
    # Register a new user (patient)
    payload = {
        "email": "testuser@example.com",
        "phone": "",
        "password": "StrongPassw0rd!",
        "first_name": "Test",
        "last_name": "User",
        "user_type": "patient",
    }

    r = await async_client.post("/auth/register", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body.get("success") is True
    assert body.get("data") and body["data"].get("user_id")

    # Attempt login before verification should fail
    r = await async_client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert r.status_code == 401

    # Fetch OTP from DB (generate_otp stores otp_code/otp_secret on user)
    from app.models.user import User
    user = db_session.query(User).filter(User.email == payload["email"]).first()
    assert user is not None
    assert user.otp_code or user.otp_secret

    otp_to_use = user.otp_code
    assert otp_to_use is not None

    # Verify OTP
    r = await async_client.post("/auth/verify-otp", json={"email": payload["email"], "otp_code": otp_to_use})
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True

    # Login should now succeed
    r = await async_client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert r.status_code == 200
    tokens = r.json()
    assert tokens.get("access_token")
    assert tokens.get("refresh_token")

    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # Refresh tokens (rotation) should return new refresh token
    r = await async_client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    new_tokens = r.json()
    assert new_tokens.get("access_token")
    assert new_tokens.get("refresh_token")
    assert new_tokens["refresh_token"] != refresh_token

    # Logout using Authorization header
    headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
    r = await async_client.post("/auth/logout", headers=headers)
    assert r.status_code == 200
    assert r.json().get("success") is True

    # Attempt to refresh using previous (now-rotated but still stored) token should fail
    r = await async_client.post("/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    # After logout the session should be revoked; expect 401
    assert r.status_code == 401


async def test_login_invalid_credentials(async_client, db_session):
    # Create a user directly in DB to test invalid credential path
    from app.models.user import User
    from app.core.security import hash_password

    email = "invalid@example.com"
    user = User(
        email=email,
        phone="",
        password_hash=hash_password("RightPassword123!"),
        first_name="Bad",
        last_name="Creds",
        user_type="patient",
        status="active",
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    # Wrong password
    r = await async_client.post("/auth/login", json={"email": email, "password": "WrongPass"})
    assert r.status_code == 401


async def test_resend_otp_for_unverified_user(async_client, db_session):
    # Register user
    email = f"unverified-{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "phone": "",
        "password": "StrongPassw0rd!",
        "first_name": "Test",
        "last_name": "User",
        "user_type": "patient",
    }
    r = await async_client.post("/auth/register", json=payload)
    assert r.status_code == 201

    # Resend OTP should succeed while still unverified
    r = await async_client.post("/auth/resend-otp", json={"email": email})
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True


async def test_resend_otp_for_verified_user_fails(async_client, db_session):
    from app.models.user import User
    from app.core.security import hash_password

    email = f"verified-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        phone=None,
        password_hash=hash_password("StrongPassw0rd!"),
        first_name="Ver",
        last_name="User",
        user_type="patient",
        status="active",
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    r = await async_client.post("/auth/resend-otp", json={"email": email})
    assert r.status_code == 400


async def test_verify_otp_invalid_code(async_client, db_session):
    email = f"otp-invalid-{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "phone": "",
        "password": "StrongPassw0rd!",
        "first_name": "Otp",
        "last_name": "User",
        "user_type": "patient",
    }
    r = await async_client.post("/auth/register", json=payload)
    assert r.status_code == 201

    r = await async_client.post("/auth/verify-otp", json={"email": email, "otp_code": "000000"})
    assert r.status_code == 400


async def test_verify_otp_expired(async_client, db_session):
    from app.models.user import User

    email = f"otp-expired-{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "phone": "",
        "password": "StrongPassw0rd!",
        "first_name": "Otp",
        "last_name": "Expired",
        "user_type": "patient",
    }
    r = await async_client.post("/auth/register", json=payload)
    assert r.status_code == 201

    user = db_session.query(User).filter(User.email == email).first()
    user.otp_expires_at = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()

    r = await async_client.post("/auth/verify-otp", json={"email": email, "otp_code": user.otp_code})
    assert r.status_code == 400


async def test_forgot_password_unknown_email_is_ok(async_client):
    email = f"missing-{uuid.uuid4().hex[:8]}@example.com"
    r = await async_client.post("/auth/forgot-password", json={"email": email})
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True


async def test_reset_password_allows_login(async_client, db_session):
    from app.models.user import User
    from app.core.security import hash_password, create_password_reset_token

    email = f"reset-{uuid.uuid4().hex[:8]}@example.com"
    original_password = "OldPassw0rd!"
    new_password = "NewPassw0rd!"

    user = User(
        email=email,
        phone=None,
        password_hash=hash_password(original_password),
        first_name="Reset",
        last_name="User",
        user_type="patient",
        status="active",
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    token, _ = create_password_reset_token(user.id, expires_minutes=30)

    r = await async_client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": new_password, "confirm_password": new_password},
    )
    assert r.status_code == 200

    # Login with new password should now work
    r = await async_client.post("/auth/login", json={"email": email, "password": new_password})
    assert r.status_code == 200
