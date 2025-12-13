"""Doctor endpoints integration tests."""

import uuid
from datetime import datetime, timedelta

import pytest

from app.core.security import create_access_token, create_refresh_token, hash_token
from app.models.user import User
from app.models.doctor import Doctor
from app.models.session import UserSession


def _make_doctor_with_session(db_session):
    email = f"doc-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        phone=None,
        first_name="Doc",
        last_name="Tor",
        user_type="doctor",
        status="active",
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    doctor = Doctor(user_id=user.id, brc_verification_status="pending")
    db_session.add(doctor)
    db_session.commit()

    access_token, access_jti = create_access_token(user_id=user.id, email=user.email, user_type=user.user_type)
    refresh_token, refresh_jti = create_refresh_token(user.id)
    session = UserSession(
        user_id=user.id,
        token_jti=access_jti,
        refresh_jti=refresh_jti,
        refresh_token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(minutes=30),
        refresh_expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db_session.add(session)
    db_session.commit()

    return doctor, access_token


@pytest.mark.asyncio
async def test_doctor_profile_and_clinic_flow(async_client, db_session):
    doctor, token = _make_doctor_with_session(db_session)
    headers = {"Authorization": f"Bearer {token}"}

    profile_payload = {
        "brc_number": f"BRC-{uuid.uuid4().hex[:6]}",
        "brc_issued_date": "2020-01-01",
        "brc_valid_until": "2030-01-01",
        "years_of_experience": 5,
        "languages": ["en", "hi"],
        "specializations": ["ayurveda"],
        "default_consultation_fee": 500,
        "identity_proof_url": None,
        "clinic_registration_certificate": None,
        "gst_number": None,
        "qualifications": [],
    }

    r = await async_client.post("/doctors/profile", json=profile_payload, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["brc_number"] == profile_payload["brc_number"]
    assert data["years_of_experience"] == profile_payload["years_of_experience"]

    clinic_payload = {
        "name": "Main Clinic",
        "address": None,
        "city": "Delhi",
        "state": "DL",
        "pincode": None,
        "country": "IN",
        "phone": None,
        "latitude": None,
        "longitude": None,
        "timings": [
            {"day": "MON", "open_time": "09:00:00", "close_time": "12:00:00", "notes": "morning"}
        ],
    }

    r = await async_client.post("/doctors/clinics", json=clinic_payload, headers=headers)
    assert r.status_code == 200, r.text
    clinic = r.json()
    assert clinic["name"] == "Main Clinic"
