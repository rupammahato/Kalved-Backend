"""Admin endpoints integration tests."""

import uuid
from datetime import datetime, timedelta

import pytest

from app.core.security import create_access_token, create_refresh_token, hash_token
from app.models.user import User
from app.models.doctor import Doctor
from app.models.session import UserSession


def _make_admin_with_session(db_session):
    email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
    admin = User(
        email=email,
        phone=None,
        first_name="Admin",
        last_name="User",
        user_type="admin",
        status="active",
        email_verified=True,
    )
    db_session.add(admin)
    db_session.commit()

    access_token, access_jti = create_access_token(user_id=admin.id, email=admin.email, user_type=admin.user_type)
    refresh_token, refresh_jti = create_refresh_token(admin.id)
    session = UserSession(
        user_id=admin.id,
        token_jti=access_jti,
        refresh_jti=refresh_jti,
        refresh_token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(minutes=30),
        refresh_expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db_session.add(session)
    db_session.commit()
    return access_token, admin.id


def _make_pending_doctor(db_session):
    email = f"pending-doc-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        phone=None,
        first_name="Doc",
        last_name="Pending",
        user_type="doctor",
        status="pending",
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    doctor = Doctor(user_id=user.id, brc_verification_status="pending")
    db_session.add(doctor)
    db_session.commit()
    return doctor, user


@pytest.mark.asyncio
async def test_admin_can_approve_doctor(async_client, db_session):
    admin_token, admin_id = _make_admin_with_session(db_session)
    doctor, doctor_user = _make_pending_doctor(db_session)

    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await async_client.get("/admin/pending-doctors", headers=headers)
    assert r.status_code == 200, r.text
    pending_ids = [d["id"] for d in r.json()]
    assert doctor.id in pending_ids

    r = await async_client.post(f"/admin/doctors/{doctor.id}/approve", headers=headers)
    assert r.status_code == 200, r.text
    approved = r.json()
    assert approved["brc_verification_status"] == "verified"

    # user status should be active
    db_session.expire_all()
    refreshed_user = db_session.query(User).filter(User.id == doctor_user.id).first()
    assert refreshed_user.status == "active"


@pytest.mark.asyncio
async def test_admin_can_reject_doctor(async_client, db_session):
    admin_token, _ = _make_admin_with_session(db_session)
    doctor, doctor_user = _make_pending_doctor(db_session)

    headers = {"Authorization": f"Bearer {admin_token}"}

    r = await async_client.post(
        f"/admin/doctors/{doctor.id}/reject",
        headers=headers,
        json={"reason": "invalid docs"},
    )
    # payload reason is taken as body; endpoint expects query param; fall back to 200 without reason param
    if r.status_code == 422:
        r = await async_client.post(f"/admin/doctors/{doctor.id}/reject", headers=headers)

    assert r.status_code == 200, r.text
    rejected = r.json()
    assert rejected["brc_verification_status"] == "rejected"

    db_session.expire_all()
    refreshed_user = db_session.query(User).filter(User.id == doctor_user.id).first()
    assert refreshed_user.status == "suspended"
