"""Service layer tests."""

import datetime
import uuid

import pytest

from app.services.doctor_service import DoctorService
from app.models.user import User
from app.models.doctor import Doctor


def test_approve_doctor_rejects_expired_brc(db_session):
    admin = User(
        email=f"admin-{uuid.uuid4().hex[:6]}@example.com",
        phone=None,
        user_type="admin",
        status="active",
        email_verified=True,
    )
    db_session.add(admin)
    db_session.commit()

    doc_user = User(
        email=f"doc-{uuid.uuid4().hex[:6]}@example.com",
        phone=None,
        user_type="doctor",
        status="pending",
        email_verified=True,
    )
    db_session.add(doc_user)
    db_session.commit()

    doctor = Doctor(
        user_id=doc_user.id,
        brc_verification_status="pending",
        brc_valid_until=datetime.date.today() - datetime.timedelta(days=1),
    )
    db_session.add(doctor)
    db_session.commit()

    with pytest.raises(ValueError):
        DoctorService.approve_doctor(db_session, admin.id, doctor.id, notes=None)
