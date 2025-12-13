"""Patient endpoints integration tests."""

import uuid

import pytest


async def _register_verify_login_patient(async_client, db_session):
    email = f"patient-{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "phone": "",
        "password": "StrongPassw0rd!",
        "first_name": "Pat",
        "last_name": "Ient",
        "user_type": "patient",
    }

    r = await async_client.post("/auth/register", json=payload)
    assert r.status_code == 201

    from app.models.user import User
    user = db_session.query(User).filter(User.email == email).first()
    otp = user.otp_code

    r = await async_client.post("/auth/verify-otp", json={"email": email, "otp_code": otp})
    assert r.status_code == 200

    r = await async_client.post("/auth/login", json={"email": email, "password": payload["password"]})
    assert r.status_code == 200
    tokens = r.json()
    return tokens, user.id


@pytest.mark.asyncio
async def test_patient_get_and_update_profile(async_client, db_session):
    tokens, user_id = await _register_verify_login_patient(async_client, db_session)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = await async_client.get("/patients/me", headers=headers)
    assert r.status_code == 200, r.text
    patient = r.json()
    assert patient["user_id"] == user_id

    update_payload = {
        "date_of_birth": "1990-01-01",
        "gender": "female",
        "blood_group": "O+",
        "city": "Pune",
        "country": "IN",
        "medical_history": None,
        "allergies": None,
        "medications": None,
        "emergency_contact_name": None,
        "emergency_contact_phone": None,
        "address": None,
        "state": None,
        "pincode": None,
    }

    r = await async_client.post("/patients/me", json=update_payload, headers=headers)
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["gender"] == "female"
    assert updated["city"] == "Pune"
