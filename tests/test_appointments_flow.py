
import pytest
import datetime
from datetime import date, time, timedelta
import uuid
from unittest.mock import MagicMock, patch

from app.models.user import User
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.clinic import Clinic
from app.models.appointment import ClinicAvailabilityTemplate, AppointmentSlot, Appointment
from app.services.appointment_service import AppointmentService
from app.core.config import settings

# ============================================================================
# FIXTURES
# ============================================================================

class MockRedis:
    """Mock Redis for testing without a real Redis instance."""
    def __init__(self):
        self.store = {}
        
    async def get(self, key):
        return self.store.get(key)
        
    async def set(self, key, value, ttl=None):
        self.store[key] = value
        
    async def delete_pattern(self, pattern):
        prefix = pattern.replace("*", "")
        keys_to_del = [k for k in self.store if k.startswith(prefix)]
        for k in keys_to_del:
            del self.store[k]


@pytest.fixture
def mock_redis(monkeypatch):
    """Fixture to mock Redis cache."""
    from app.services.appointment_service import redis_cache
    mm = MockRedis()
    monkeypatch.setattr(redis_cache, "get", mm.get)
    monkeypatch.setattr(redis_cache, "set", mm.set)
    monkeypatch.setattr(redis_cache, "delete_pattern", mm.delete_pattern)
    return mm


@pytest.fixture
def mock_celery_tasks():
    """Fixture to mock Celery notification tasks."""
    with patch('app.tasks.notification_tasks.send_appointment_confirmation') as mock_confirm, \
         patch('app.tasks.notification_tasks.notify_doctor_appointment_confirmed') as mock_doc_confirm, \
         patch('app.tasks.notification_tasks.notify_doctor_appointment_cancelled') as mock_doc_cancel:
        mock_confirm.delay = MagicMock()
        mock_doc_confirm.delay = MagicMock()
        mock_doc_cancel.delay = MagicMock()
        yield {
            "confirm": mock_confirm,
            "doc_confirm": mock_doc_confirm,
            "doc_cancel": mock_doc_cancel
        }


@pytest.fixture
def test_data(db_session):
    """Create base test data: doctor, patient, clinic."""
    # Create Doctor User
    doc_email = f"doc_{uuid.uuid4().hex[:8]}@example.com"
    doctor_user = User(
        email=doc_email,
        phone=f"+1{uuid.uuid4().int.__str__()[:10]}",
        password_hash="hashed_secret",
        user_type="doctor",
        status="active",
        email_verified=True
    )
    db_session.add(doctor_user)
    db_session.commit()
    
    doctor = Doctor(user_id=doctor_user.id, brc_number=f"BRC{uuid.uuid4().hex[:6]}", brc_verification_status="approved")
    db_session.add(doctor)
    db_session.commit()
    
    # Create Patient User
    pat_email = f"pat_{uuid.uuid4().hex[:8]}@example.com"
    patient_user = User(
        email=pat_email,
        phone=f"+1{uuid.uuid4().int.__str__()[:10]}",
        password_hash="hashed_secret",
        user_type="patient",
        status="active",
        email_verified=True
    )
    db_session.add(patient_user)
    db_session.commit()
    
    patient = Patient(user_id=patient_user.id)
    db_session.add(patient)
    db_session.commit()
    
    # Create Second Patient for multi-patient tests
    pat2_email = f"pat2_{uuid.uuid4().hex[:8]}@example.com"
    patient2_user = User(
        email=pat2_email,
        phone=f"+1{uuid.uuid4().int.__str__()[:10]}",
        password_hash="hashed_secret",
        user_type="patient",
        status="active",
        email_verified=True
    )
    db_session.add(patient2_user)
    db_session.commit()
    
    patient2 = Patient(user_id=patient2_user.id)
    db_session.add(patient2)
    db_session.commit()
    
    # Create Clinic
    clinic = Clinic(
        doctor_id=doctor.id,
        name="Test Clinic",
        address="123 Health St",
        city="Wellness City",
        phone="1234567890"
    )
    db_session.add(clinic)
    db_session.commit()
    
    return {
        "doctor_user": doctor_user,
        "doctor": doctor,
        "patient_user": patient_user,
        "patient": patient,
        "patient2_user": patient2_user,
        "patient2": patient2,
        "clinic": clinic
    }


# ============================================================================
# SLOT GENERATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_generate_slots_success(test_data, db_session, mock_redis):
    """Test successful slot generation from availability template."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    
    target_date = date.today() + timedelta(days=1)
    day_name = target_date.strftime("%A")
    
    # Create availability template
    template = ClinicAvailabilityTemplate(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        day_of_week=day_name,
        opening_time=time(9, 0),
        closing_time=time(12, 0),  # 3 hours -> 6 slots of 30 mins
        slot_duration_minutes=30,
        is_active=True
    )
    db_session.add(template)
    db_session.commit()
    
    result = await AppointmentService.generate_slots_for_clinic(
        db_session, clinic.id, target_date, days_ahead=1
    )
    
    assert result["status"] == "success"
    assert result["slots_created"] == 6


@pytest.mark.asyncio
async def test_generate_slots_with_break_time(test_data, db_session, mock_redis):
    """Test slot generation skips break periods."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    
    target_date = date.today() + timedelta(days=2)
    day_name = target_date.strftime("%A")
    
    # Create template with break
    template = ClinicAvailabilityTemplate(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        day_of_week=day_name,
        opening_time=time(9, 0),
        closing_time=time(13, 0),  # 4 hours
        break_start=time(11, 0),
        break_end=time(12, 0),  # 1 hour break
        slot_duration_minutes=30,
        is_active=True
    )
    db_session.add(template)
    db_session.commit()
    
    result = await AppointmentService.generate_slots_for_clinic(
        db_session, clinic.id, target_date, days_ahead=1
    )
    
    # 4 hours - 1 hour break = 3 hours = 6 slots
    assert result["status"] == "success"
    assert result["slots_created"] == 6


@pytest.mark.asyncio
async def test_generate_slots_no_template(test_data, db_session, mock_redis):
    """Test slot generation with no template returns 0 slots."""
    clinic = test_data["clinic"]
    target_date = date.today() + timedelta(days=10)
    
    result = await AppointmentService.generate_slots_for_clinic(
        db_session, clinic.id, target_date, days_ahead=1
    )
    
    assert result["status"] == "success"
    assert result["slots_created"] == 0


@pytest.mark.asyncio
async def test_generate_slots_inactive_template(test_data, db_session, mock_redis):
    """Test slot generation ignores inactive templates."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    
    target_date = date.today() + timedelta(days=3)
    day_name = target_date.strftime("%A")
    
    # Create inactive template
    template = ClinicAvailabilityTemplate(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        day_of_week=day_name,
        opening_time=time(9, 0),
        closing_time=time(12, 0),
        slot_duration_minutes=30,
        is_active=False  # Inactive
    )
    db_session.add(template)
    db_session.commit()
    
    result = await AppointmentService.generate_slots_for_clinic(
        db_session, clinic.id, target_date, days_ahead=1
    )
    
    assert result["slots_created"] == 0


@pytest.mark.asyncio
async def test_generate_slots_already_generated(test_data, db_session, mock_redis):
    """Test slot generation caching prevents duplicate generation."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    
    target_date = date.today() + timedelta(days=4)
    day_name = target_date.strftime("%A")
    
    template = ClinicAvailabilityTemplate(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        day_of_week=day_name,
        opening_time=time(9, 0),
        closing_time=time(11, 0),
        slot_duration_minutes=30,
        is_active=True
    )
    db_session.add(template)
    db_session.commit()
    
    # First generation
    result1 = await AppointmentService.generate_slots_for_clinic(
        db_session, clinic.id, target_date, days_ahead=1
    )
    assert result1["status"] == "success"
    assert result1["slots_created"] == 4
    
    # Second generation should be cached
    result2 = await AppointmentService.generate_slots_for_clinic(
        db_session, clinic.id, target_date, days_ahead=1
    )
    assert result2["status"] == "already_generated"


@pytest.mark.asyncio
async def test_generate_slots_invalid_clinic(db_session, mock_redis):
    """Test slot generation with non-existent clinic raises error."""
    with pytest.raises(ValueError) as excinfo:
        await AppointmentService.generate_slots_for_clinic(
            db_session, clinic_id=99999, start_date=date.today(), days_ahead=1
        )
    assert "Clinic not found" in str(excinfo.value)


# ============================================================================
# AVAILABLE SLOTS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_available_slots(test_data, db_session, mock_redis):
    """Test retrieving available slots for a date."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    
    target_date = date.today() + timedelta(days=5)
    day_name = target_date.strftime("%A")
    
    template = ClinicAvailabilityTemplate(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        day_of_week=day_name,
        opening_time=time(10, 0),
        closing_time=time(12, 0),
        slot_duration_minutes=30,
        is_active=True
    )
    db_session.add(template)
    db_session.commit()
    
    await AppointmentService.generate_slots_for_clinic(
        db_session, clinic.id, target_date, days_ahead=1
    )
    
    slots = await AppointmentService.get_available_slots(
        db_session, clinic.id, doctor.id, target_date
    )
    
    assert len(slots) == 4
    assert all(s["available"] for s in slots)


@pytest.mark.asyncio
async def test_get_available_slots_empty(test_data, db_session, mock_redis):
    """Test retrieving available slots when none exist."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    
    # Far future date with no slots
    target_date = date.today() + timedelta(days=100)
    
    slots = await AppointmentService.get_available_slots(
        db_session, clinic.id, doctor.id, target_date
    )
    
    assert len(slots) == 0


# ============================================================================
# BOOKING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_book_appointment_success(test_data, db_session, mock_redis, mock_celery_tasks):
    """Test successful appointment booking."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    patient = test_data["patient"]
    
    target_date = date.today() + timedelta(days=6)
    day_name = target_date.strftime("%A")
    
    template = ClinicAvailabilityTemplate(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        day_of_week=day_name,
        opening_time=time(9, 0),
        closing_time=time(10, 0),
        slot_duration_minutes=30,
        is_active=True
    )
    db_session.add(template)
    db_session.commit()
    
    await AppointmentService.generate_slots_for_clinic(
        db_session, clinic.id, target_date, days_ahead=1
    )
    
    slots = await AppointmentService.get_available_slots(
        db_session, clinic.id, doctor.id, target_date
    )
    slot_id = slots[0]["slot_id"]
    
    result = await AppointmentService.book_appointment(
        db_session,
        patient_id=patient.id,
        slot_id=slot_id,
        appointment_type="Consultation",
        reason_for_visit="General checkup"
    )
    
    assert result["status"] == "booked"
    assert "appointment_id" in result
    
    # Verify notification task was triggered
    mock_celery_tasks["confirm"].delay.assert_called_once()


@pytest.mark.asyncio
async def test_book_appointment_slot_not_found(test_data, db_session, mock_redis, mock_celery_tasks):
    """Test booking with invalid slot ID raises error."""
    patient = test_data["patient"]
    
    with pytest.raises(ValueError) as excinfo:
        await AppointmentService.book_appointment(
            db_session,
            patient_id=patient.id,
            slot_id=99999,
            appointment_type="Test",
            reason_for_visit="Test"
        )
    assert "Slot not available" in str(excinfo.value)


@pytest.mark.asyncio
async def test_book_appointment_double_booking(test_data, db_session, mock_redis, mock_celery_tasks):
    """Test that double booking the same slot fails."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    patient = test_data["patient"]
    patient2 = test_data["patient2"]
    
    target_date = date.today() + timedelta(days=7)
    day_name = target_date.strftime("%A")
    
    template = ClinicAvailabilityTemplate(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        day_of_week=day_name,
        opening_time=time(9, 0),
        closing_time=time(10, 0),
        slot_duration_minutes=30,
        is_active=True
    )
    db_session.add(template)
    db_session.commit()
    
    await AppointmentService.generate_slots_for_clinic(
        db_session, clinic.id, target_date, days_ahead=1
    )
    
    slots = await AppointmentService.get_available_slots(
        db_session, clinic.id, doctor.id, target_date
    )
    slot_id = slots[0]["slot_id"]
    
    # First booking succeeds
    await AppointmentService.book_appointment(
        db_session,
        patient_id=patient.id,
        slot_id=slot_id,
        appointment_type="First",
        reason_for_visit="First booking"
    )
    
    # Second booking fails
    with pytest.raises(ValueError) as excinfo:
        await AppointmentService.book_appointment(
            db_session,
            patient_id=patient2.id,
            slot_id=slot_id,
            appointment_type="Second",
            reason_for_visit="Double booking attempt"
        )
    assert "Slot not available" in str(excinfo.value)


# ============================================================================
# CONFIRMATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_confirm_appointment_success(test_data, db_session, mock_redis, mock_celery_tasks):
    """Test successful appointment confirmation."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    patient = test_data["patient"]
    
    target_date = date.today() + timedelta(days=8)
    day_name = target_date.strftime("%A")
    
    template = ClinicAvailabilityTemplate(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        day_of_week=day_name,
        opening_time=time(9, 0),
        closing_time=time(10, 0),
        slot_duration_minutes=30,
        is_active=True
    )
    db_session.add(template)
    db_session.commit()
    
    await AppointmentService.generate_slots_for_clinic(
        db_session, clinic.id, target_date, days_ahead=1
    )
    
    slots = await AppointmentService.get_available_slots(
        db_session, clinic.id, doctor.id, target_date
    )
    slot_id = slots[0]["slot_id"]
    
    booking = await AppointmentService.book_appointment(
        db_session,
        patient_id=patient.id,
        slot_id=slot_id,
        appointment_type="Test",
        reason_for_visit="Test"
    )
    
    result = await AppointmentService.confirm_appointment(
        db_session, booking["appointment_id"], patient.id
    )
    
    assert result["status"] == "confirmed"
    
    # Verify doctor notification was triggered
    mock_celery_tasks["doc_confirm"].delay.assert_called_once()


@pytest.mark.asyncio
async def test_confirm_appointment_already_confirmed(test_data, db_session, mock_redis, mock_celery_tasks):
    """Test confirming already confirmed appointment returns appropriate message."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    patient = test_data["patient"]
    
    target_date = date.today() + timedelta(days=9)
    day_name = target_date.strftime("%A")
    
    template = ClinicAvailabilityTemplate(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        day_of_week=day_name,
        opening_time=time(9, 0),
        closing_time=time(10, 0),
        slot_duration_minutes=30,
        is_active=True
    )
    db_session.add(template)
    db_session.commit()
    
    await AppointmentService.generate_slots_for_clinic(
        db_session, clinic.id, target_date, days_ahead=1
    )
    
    slots = await AppointmentService.get_available_slots(
        db_session, clinic.id, doctor.id, target_date
    )
    slot_id = slots[0]["slot_id"]
    
    booking = await AppointmentService.book_appointment(
        db_session,
        patient_id=patient.id,
        slot_id=slot_id,
        appointment_type="Test",
        reason_for_visit="Test"
    )
    
    # First confirmation
    await AppointmentService.confirm_appointment(
        db_session, booking["appointment_id"], patient.id
    )
    
    # Second confirmation
    result = await AppointmentService.confirm_appointment(
        db_session, booking["appointment_id"], patient.id
    )
    
    assert result["status"] == "confirmed"
    assert "already" in result["message"].lower()


@pytest.mark.asyncio
async def test_confirm_appointment_wrong_patient(test_data, db_session, mock_redis, mock_celery_tasks):
    """Test that wrong patient cannot confirm appointment."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    patient = test_data["patient"]
    patient2 = test_data["patient2"]
    
    target_date = date.today() + timedelta(days=10)
    day_name = target_date.strftime("%A")
    
    template = ClinicAvailabilityTemplate(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        day_of_week=day_name,
        opening_time=time(9, 0),
        closing_time=time(10, 0),
        slot_duration_minutes=30,
        is_active=True
    )
    db_session.add(template)
    db_session.commit()
    
    await AppointmentService.generate_slots_for_clinic(
        db_session, clinic.id, target_date, days_ahead=1
    )
    
    slots = await AppointmentService.get_available_slots(
        db_session, clinic.id, doctor.id, target_date
    )
    slot_id = slots[0]["slot_id"]
    
    booking = await AppointmentService.book_appointment(
        db_session,
        patient_id=patient.id,
        slot_id=slot_id,
        appointment_type="Test",
        reason_for_visit="Test"
    )
    
    # Wrong patient tries to confirm
    with pytest.raises(ValueError) as excinfo:
        await AppointmentService.confirm_appointment(
            db_session, booking["appointment_id"], patient2.id
        )
    assert "not found" in str(excinfo.value).lower()


# ============================================================================
# CANCELLATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_cancel_appointment_success(test_data, db_session, mock_redis, mock_celery_tasks):
    """Test successful appointment cancellation."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    patient = test_data["patient"]
    
    target_date = date.today() + timedelta(days=11)
    day_name = target_date.strftime("%A")
    
    template = ClinicAvailabilityTemplate(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        day_of_week=day_name,
        opening_time=time(9, 0),
        closing_time=time(10, 0),
        slot_duration_minutes=30,
        is_active=True
    )
    db_session.add(template)
    db_session.commit()
    
    await AppointmentService.generate_slots_for_clinic(
        db_session, clinic.id, target_date, days_ahead=1
    )
    
    slots = await AppointmentService.get_available_slots(
        db_session, clinic.id, doctor.id, target_date
    )
    slot_id = slots[0]["slot_id"]
    
    booking = await AppointmentService.book_appointment(
        db_session,
        patient_id=patient.id,
        slot_id=slot_id,
        appointment_type="Test",
        reason_for_visit="Test"
    )
    
    result = await AppointmentService.cancel_appointment(
        db_session,
        booking["appointment_id"],
        patient.user_id,
        "Personal reasons"
    )
    
    assert result["status"] == "cancelled"
    
    # Verify slot is released
    slot = db_session.query(AppointmentSlot).filter(AppointmentSlot.id == slot_id).first()
    assert slot.slot_status == "available"
    
    # Verify cancellation notification
    mock_celery_tasks["doc_cancel"].delay.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_appointment_not_found(test_data, db_session, mock_redis, mock_celery_tasks):
    """Test cancelling non-existent appointment raises error."""
    patient = test_data["patient"]
    
    with pytest.raises(ValueError) as excinfo:
        await AppointmentService.cancel_appointment(
            db_session,
            appointment_id=99999,
            cancelled_by_user_id=patient.user_id,
            reason="Test"
        )
    assert "not found" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_cancel_already_cancelled_appointment(test_data, db_session, mock_redis, mock_celery_tasks):
    """Test cancelling already cancelled appointment fails."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    patient = test_data["patient"]
    
    target_date = date.today() + timedelta(days=12)
    day_name = target_date.strftime("%A")
    
    template = ClinicAvailabilityTemplate(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        day_of_week=day_name,
        opening_time=time(9, 0),
        closing_time=time(10, 0),
        slot_duration_minutes=30,
        is_active=True
    )
    db_session.add(template)
    db_session.commit()
    
    await AppointmentService.generate_slots_for_clinic(
        db_session, clinic.id, target_date, days_ahead=1
    )
    
    slots = await AppointmentService.get_available_slots(
        db_session, clinic.id, doctor.id, target_date
    )
    slot_id = slots[0]["slot_id"]
    
    booking = await AppointmentService.book_appointment(
        db_session,
        patient_id=patient.id,
        slot_id=slot_id,
        appointment_type="Test",
        reason_for_visit="Test"
    )
    
    # First cancellation
    await AppointmentService.cancel_appointment(
        db_session,
        booking["appointment_id"],
        patient.user_id,
        "First cancellation"
    )
    
    # Second cancellation should fail
    with pytest.raises(ValueError) as excinfo:
        await AppointmentService.cancel_appointment(
            db_session,
            booking["appointment_id"],
            patient.user_id,
            "Second cancellation"
        )
    assert "scheduled" in str(excinfo.value).lower()


# ============================================================================
# LISTING TESTS
# ============================================================================

def test_list_patient_appointments(test_data, db_session):
    """Test listing patient appointments."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    patient = test_data["patient"]
    
    # Create slots directly for this test
    target_date = date.today() + timedelta(days=20)
    
    slot = AppointmentSlot(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        slot_start=datetime.datetime.combine(target_date, time(9, 0)),
        slot_end=datetime.datetime.combine(target_date, time(9, 30)),
        slot_date=target_date,
        slot_status="booked",
        is_active=True
    )
    db_session.add(slot)
    db_session.commit()
    
    appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        clinic_id=clinic.id,
        appointment_slot_id=slot.id,
        appointment_date=target_date,
        appointment_time=time(9, 0),
        appointment_start=slot.slot_start,
        appointment_end=slot.slot_end,
        status="scheduled"
    )
    db_session.add(appt)
    db_session.commit()
    
    appointments = AppointmentService.list_patient_appointments(
        db_session, patient.id
    )
    
    assert len(appointments) >= 1
    assert any(a.id == appt.id for a in appointments)


def test_list_doctor_appointments(test_data, db_session):
    """Test listing doctor appointments."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    patient = test_data["patient"]
    
    target_date = date.today() + timedelta(days=21)
    
    slot = AppointmentSlot(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        slot_start=datetime.datetime.combine(target_date, time(10, 0)),
        slot_end=datetime.datetime.combine(target_date, time(10, 30)),
        slot_date=target_date,
        slot_status="booked",
        is_active=True
    )
    db_session.add(slot)
    db_session.commit()
    
    appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        clinic_id=clinic.id,
        appointment_slot_id=slot.id,
        appointment_date=target_date,
        appointment_time=time(10, 0),
        appointment_start=slot.slot_start,
        appointment_end=slot.slot_end,
        status="scheduled"
    )
    db_session.add(appt)
    db_session.commit()
    
    appointments = AppointmentService.list_doctor_appointments(
        db_session, doctor.id
    )
    
    assert len(appointments) >= 1
    assert any(a.id == appt.id for a in appointments)


def test_list_doctor_appointments_with_filters(test_data, db_session):
    """Test listing doctor appointments with status and date filters."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    patient = test_data["patient"]
    
    target_date = date.today() + timedelta(days=22)
    
    slot = AppointmentSlot(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        slot_start=datetime.datetime.combine(target_date, time(11, 0)),
        slot_end=datetime.datetime.combine(target_date, time(11, 30)),
        slot_date=target_date,
        slot_status="booked",
        is_active=True
    )
    db_session.add(slot)
    db_session.commit()
    
    appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        clinic_id=clinic.id,
        appointment_slot_id=slot.id,
        appointment_date=target_date,
        appointment_time=time(11, 0),
        appointment_start=slot.slot_start,
        appointment_end=slot.slot_end,
        status="scheduled"
    )
    db_session.add(appt)
    db_session.commit()
    
    # Filter by status
    scheduled = AppointmentService.list_doctor_appointments(
        db_session, doctor.id, status="scheduled"
    )
    assert any(a.id == appt.id for a in scheduled)
    
    # Filter by date range
    in_range = AppointmentService.list_doctor_appointments(
        db_session, doctor.id, from_date=target_date, to_date=target_date
    )
    assert any(a.id == appt.id for a in in_range)
    
    # Out of range
    out_of_range = AppointmentService.list_doctor_appointments(
        db_session, doctor.id, from_date=target_date + timedelta(days=100)
    )
    assert not any(a.id == appt.id for a in out_of_range)


# ============================================================================
# FULL LIFECYCLE TEST
# ============================================================================

@pytest.mark.asyncio
async def test_full_appointment_lifecycle(test_data, db_session, mock_redis, mock_celery_tasks):
    """Test complete appointment lifecycle: generate -> book -> confirm -> cancel."""
    doctor = test_data["doctor"]
    clinic = test_data["clinic"]
    patient = test_data["patient"]
    
    target_date = date.today() + timedelta(days=30)
    day_name = target_date.strftime("%A")
    
    # 1. Create template
    template = ClinicAvailabilityTemplate(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        day_of_week=day_name,
        opening_time=time(9, 0),
        closing_time=time(11, 0),
        slot_duration_minutes=30,
        is_active=True
    )
    db_session.add(template)
    db_session.commit()
    
    # 2. Generate slots
    gen_result = await AppointmentService.generate_slots_for_clinic(
        db_session, clinic.id, target_date, days_ahead=1
    )
    assert gen_result["slots_created"] == 4
    
    # 3. Get available slots
    slots = await AppointmentService.get_available_slots(
        db_session, clinic.id, doctor.id, target_date
    )
    assert len(slots) == 4
    slot_id = slots[0]["slot_id"]
    
    # 4. Book appointment
    booking = await AppointmentService.book_appointment(
        db_session,
        patient_id=patient.id,
        slot_id=slot_id,
        appointment_type="Full Test",
        reason_for_visit="Complete lifecycle test"
    )
    assert booking["status"] == "booked"
    appt_id = booking["appointment_id"]
    
    # 5. Verify slot is no longer available
    slots_after = await AppointmentService.get_available_slots(
        db_session, clinic.id, doctor.id, target_date
    )
    assert len(slots_after) == 3
    
    # 6. Confirm appointment
    confirm = await AppointmentService.confirm_appointment(
        db_session, appt_id, patient.id
    )
    assert confirm["status"] == "confirmed"
    
    # 7. Verify DB state
    appt = db_session.query(Appointment).filter(Appointment.id == appt_id).first()
    assert appt.is_confirmed is True
    
    # 8. Cancel appointment
    cancel = await AppointmentService.cancel_appointment(
        db_session, appt_id, patient.user_id, "Lifecycle test complete"
    )
    assert cancel["status"] == "cancelled"
    
    # 9. Verify slot released
    db_session.refresh(appt)
    assert appt.status == "cancelled"
    
    slot = db_session.query(AppointmentSlot).filter(AppointmentSlot.id == slot_id).first()
    assert slot.slot_status == "available"
    
    # 10. Verify all notifications were triggered
    assert mock_celery_tasks["confirm"].delay.call_count >= 1
    assert mock_celery_tasks["doc_confirm"].delay.call_count >= 1
    assert mock_celery_tasks["doc_cancel"].delay.call_count >= 1
