
import pytest
import uuid
from datetime import datetime, date, time, timedelta
from unittest.mock import MagicMock, patch, call

from app.models.user import User
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.clinic import Clinic
from app.models.appointment import Appointment, AppointmentSlot
from app.models.notification import Notification, NotificationPreferences
from app.core.config import settings

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def notification_test_data(db_session):
    """Create test data for notification tests."""
    # Create User with email and phone
    user_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=user_email,
        phone=f"+1{uuid.uuid4().int.__str__()[:10]}",
        password_hash="hashed_secret",
        first_name="Test",
        last_name="User",
        user_type="patient",
        status="active",
        email_verified=True
    )
    db_session.add(user)
    db_session.commit()
    
    # Create Patient
    patient = Patient(user_id=user.id)
    db_session.add(patient)
    db_session.commit()
    
    # Create Doctor User
    doc_email = f"doc_{uuid.uuid4().hex[:8]}@example.com"
    doctor_user = User(
        email=doc_email,
        phone=f"+1{uuid.uuid4().int.__str__()[:10]}",
        password_hash="hashed_secret",
        first_name="Dr",
        last_name="Smith",
        user_type="doctor",
        status="active",
        email_verified=True
    )
    db_session.add(doctor_user)
    db_session.commit()
    
    doctor = Doctor(
        user_id=doctor_user.id, 
        brc_number=f"BRC{uuid.uuid4().hex[:6]}", 
        brc_verification_status="approved"
    )
    db_session.add(doctor)
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
        "user": user,
        "patient": patient,
        "doctor_user": doctor_user,
        "doctor": doctor,
        "clinic": clinic
    }


@pytest.fixture
def mock_email_sms():
    """Mock email and SMS services."""
    with patch('app.tasks.notification_tasks.send_email') as mock_email, \
         patch('app.tasks.notification_tasks.send_sms_message') as mock_sms:
        mock_email.return_value = True
        mock_sms.return_value = True
        yield {
            "email": mock_email,
            "sms": mock_sms
        }


# ============================================================================
# NOTIFICATION MODEL TESTS
# ============================================================================

def test_create_notification(notification_test_data, db_session):
    """Test creating a notification record."""
    user = notification_test_data["user"]
    
    notification = Notification(
        user_id=user.id,
        notification_type="test_notification",
        title="Test Title",
        body="Test body content",
        is_in_app=True,
        is_read=False
    )
    db_session.add(notification)
    db_session.commit()
    
    assert notification.id is not None
    assert notification.user_id == user.id
    assert notification.notification_type == "test_notification"
    assert notification.is_read is False
    assert notification.created_at is not None


def test_notification_with_related_entity(notification_test_data, db_session):
    """Test creating a notification with related entity."""
    user = notification_test_data["user"]
    
    notification = Notification(
        user_id=user.id,
        notification_type="appointment_reminder",
        title="Appointment Reminder",
        body="Your appointment is tomorrow",
        related_entity_type="appointment",
        related_entity_id=123,
        is_in_app=True
    )
    db_session.add(notification)
    db_session.commit()
    
    assert notification.related_entity_type == "appointment"
    assert notification.related_entity_id == 123


def test_mark_notification_as_read(notification_test_data, db_session):
    """Test marking a notification as read."""
    user = notification_test_data["user"]
    
    notification = Notification(
        user_id=user.id,
        notification_type="test",
        title="Test",
        body="Test",
        is_read=False
    )
    db_session.add(notification)
    db_session.commit()
    
    # Mark as read
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db_session.commit()
    
    db_session.refresh(notification)
    assert notification.is_read is True
    assert notification.read_at is not None


def test_notification_email_tracking(notification_test_data, db_session):
    """Test notification email sent tracking."""
    user = notification_test_data["user"]
    
    notification = Notification(
        user_id=user.id,
        notification_type="test",
        title="Test",
        body="Test",
        is_email_sent=False
    )
    db_session.add(notification)
    db_session.commit()
    
    # Mark email as sent
    notification.is_email_sent = True
    notification.email_sent_at = datetime.utcnow()
    db_session.commit()
    
    db_session.refresh(notification)
    assert notification.is_email_sent is True
    assert notification.email_sent_at is not None


def test_notification_sms_tracking(notification_test_data, db_session):
    """Test notification SMS sent tracking."""
    user = notification_test_data["user"]
    
    notification = Notification(
        user_id=user.id,
        notification_type="test",
        title="Test",
        body="Test",
        is_sms_sent=False
    )
    db_session.add(notification)
    db_session.commit()
    
    # Mark SMS as sent
    notification.is_sms_sent = True
    notification.sms_sent_at = datetime.utcnow()
    db_session.commit()
    
    db_session.refresh(notification)
    assert notification.is_sms_sent is True
    assert notification.sms_sent_at is not None


# ============================================================================
# NOTIFICATION PREFERENCES TESTS
# ============================================================================

def test_create_notification_preferences(notification_test_data, db_session):
    """Test creating notification preferences."""
    user = notification_test_data["user"]
    
    prefs = NotificationPreferences(
        user_id=user.id,
        email_enabled=True,
        sms_enabled=True,
        push_enabled=True,
        appointment_reminders=True,
        appointment_reminder_hours=24
    )
    db_session.add(prefs)
    db_session.commit()
    
    assert prefs.id is not None
    assert prefs.email_enabled is True
    assert prefs.sms_enabled is True
    assert prefs.appointment_reminder_hours == 24


def test_update_notification_preferences(notification_test_data, db_session):
    """Test updating notification preferences."""
    user = notification_test_data["user"]
    
    prefs = NotificationPreferences(
        user_id=user.id,
        email_enabled=True,
        sms_enabled=True
    )
    db_session.add(prefs)
    db_session.commit()
    
    # Update preferences
    prefs.sms_enabled = False
    prefs.appointment_reminders = False
    db_session.commit()
    
    db_session.refresh(prefs)
    assert prefs.sms_enabled is False
    assert prefs.appointment_reminders is False


def test_notification_preferences_defaults(notification_test_data, db_session):
    """Test notification preferences have correct defaults."""
    user = notification_test_data["user"]
    
    prefs = NotificationPreferences(user_id=user.id)
    db_session.add(prefs)
    db_session.commit()
    
    assert prefs.email_enabled is True
    assert prefs.sms_enabled is True
    assert prefs.push_enabled is True
    assert prefs.appointment_reminders is True
    assert prefs.prescription_notifications is True
    assert prefs.message_notifications is True


# ============================================================================
# NOTIFICATION TASK TESTS (UNIT TESTS)
# ============================================================================

def test_send_notification_task_creates_record(notification_test_data, db_session, mock_email_sms):
    """Test send_notification_task creates notification record."""
    user = notification_test_data["user"]
    
    # Import task and run synchronously
    from app.tasks.notification_tasks import send_notification_task
    
    # Mock SessionLocal to return our test session
    with patch('app.tasks.notification_tasks.SessionLocal', return_value=db_session):
        # Run task synchronously (without celery)
        send_notification_task(
            user_id=user.id,
            notification_type="test_notification",
            title="Test Title",
            body="Test Body",
            channels=["in_app"]
        )
    
    # Verify notification was created
    notifications = db_session.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.notification_type == "test_notification"
    ).all()
    
    assert len(notifications) >= 1


def test_send_notification_task_sends_email(notification_test_data, db_session, mock_email_sms):
    """Test send_notification_task dispatches email when enabled."""
    user = notification_test_data["user"]
    
    # Create preferences with email enabled
    prefs = NotificationPreferences(
        user_id=user.id,
        email_enabled=True,
        sms_enabled=False
    )
    db_session.add(prefs)
    db_session.commit()
    
    from app.tasks.notification_tasks import send_notification_task
    
    with patch('app.tasks.notification_tasks.SessionLocal', return_value=db_session):
        send_notification_task(
            user_id=user.id,
            notification_type="test",
            title="Email Test",
            body="Email body",
            channels=["email"]
        )
    
    # Verify email was called
    mock_email_sms["email"].assert_called()


def test_send_notification_task_sends_sms(notification_test_data, db_session, mock_email_sms):
    """Test send_notification_task dispatches SMS when enabled."""
    user = notification_test_data["user"]
    
    # Create preferences with SMS enabled
    prefs = NotificationPreferences(
        user_id=user.id,
        email_enabled=False,
        sms_enabled=True
    )
    db_session.add(prefs)
    db_session.commit()
    
    from app.tasks.notification_tasks import send_notification_task
    
    with patch('app.tasks.notification_tasks.SessionLocal', return_value=db_session):
        send_notification_task(
            user_id=user.id,
            notification_type="test",
            title="SMS Test",
            body="SMS body",
            channels=["sms"]
        )
    
    # Verify SMS was called
    mock_email_sms["sms"].assert_called()


def test_send_notification_task_respects_preferences(notification_test_data, db_session, mock_email_sms):
    """Test send_notification_task respects user preferences."""
    user = notification_test_data["user"]
    
    # Create preferences with email disabled
    prefs = NotificationPreferences(
        user_id=user.id,
        email_enabled=False,
        sms_enabled=False
    )
    db_session.add(prefs)
    db_session.commit()
    
    from app.tasks.notification_tasks import send_notification_task
    
    with patch('app.tasks.notification_tasks.SessionLocal', return_value=db_session):
        send_notification_task(
            user_id=user.id,
            notification_type="test",
            title="Disabled Test",
            body="Should not send",
            channels=["email", "sms"]
        )
    
    # Email and SMS should NOT be called when disabled
    mock_email_sms["email"].assert_not_called()
    mock_email_sms["sms"].assert_not_called()


def test_send_notification_task_user_not_found(db_session, mock_email_sms, caplog):
    """Test send_notification_task handles missing user gracefully."""
    from app.tasks.notification_tasks import send_notification_task
    import logging
    
    caplog.set_level(logging.ERROR)
    
    with patch('app.tasks.notification_tasks.SessionLocal', return_value=db_session):
        # Use non-existent user ID
        send_notification_task(
            user_id=99999,
            notification_type="test",
            title="Test",
            body="Test",
            channels=["in_app"]
        )
    
    assert "not found" in caplog.text.lower()


def test_send_notification_task_appointment_reminder_disabled(notification_test_data, db_session, mock_email_sms):
    """Test appointment reminder respects category preference."""
    user = notification_test_data["user"]
    
    # Create preferences with appointment reminders disabled
    prefs = NotificationPreferences(
        user_id=user.id,
        email_enabled=True,
        sms_enabled=True,
        appointment_reminders=False  # Disabled
    )
    db_session.add(prefs)
    db_session.commit()
    
    from app.tasks.notification_tasks import send_notification_task
    
    with patch('app.tasks.notification_tasks.SessionLocal', return_value=db_session):
        send_notification_task(
            user_id=user.id,
            notification_type="appointment_reminder",  # This type
            title="Reminder",
            body="Appointment tomorrow",
            channels=["email", "sms"]
        )
    
    # Should not send email/SMS for disabled category
    mock_email_sms["email"].assert_not_called()
    mock_email_sms["sms"].assert_not_called()


# ============================================================================
# APPOINTMENT NOTIFICATION TESTS
# ============================================================================

def test_appointment_confirmation_notification(notification_test_data, db_session, mock_email_sms):
    """Test send_appointment_confirmation creates notifications."""
    patient = notification_test_data["patient"]
    doctor = notification_test_data["doctor"]
    clinic = notification_test_data["clinic"]
    
    target_date = date.today() + timedelta(days=5)
    
    # Create slot
    slot = AppointmentSlot(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        slot_start=datetime.combine(target_date, time(9, 0)),
        slot_end=datetime.combine(target_date, time(9, 30)),
        slot_date=target_date,
        slot_status="booked",
        is_active=True
    )
    db_session.add(slot)
    db_session.commit()
    
    # Create appointment
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
    
    from app.tasks.notification_tasks import send_appointment_confirmation
    
    # Mock the nested task calls
    with patch('app.tasks.notification_tasks.SessionLocal', return_value=db_session), \
         patch('app.tasks.notification_tasks.send_notification_task') as mock_task, \
         patch('app.tasks.notification_tasks.send_appointment_reminder_email') as mock_reminder:
        
        mock_task.delay = MagicMock()
        
        send_appointment_confirmation(appt.id)
        
        # Verify send_notification_task was called for patient and doctor
        assert mock_task.delay.call_count >= 2


def test_doctor_confirmation_notification(notification_test_data, db_session, mock_email_sms):
    """Test notify_doctor_appointment_confirmed sends notifications."""
    patient = notification_test_data["patient"]
    doctor = notification_test_data["doctor"]
    clinic = notification_test_data["clinic"]
    
    target_date = date.today() + timedelta(days=6)
    
    slot = AppointmentSlot(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        slot_start=datetime.combine(target_date, time(10, 0)),
        slot_end=datetime.combine(target_date, time(10, 30)),
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
        status="scheduled",
        is_confirmed=True
    )
    db_session.add(appt)
    db_session.commit()
    
    from app.tasks.notification_tasks import notify_doctor_appointment_confirmed
    
    with patch('app.tasks.notification_tasks.SessionLocal', return_value=db_session), \
         patch('app.tasks.notification_tasks.send_notification_task') as mock_task:
        
        mock_task.delay = MagicMock()
        
        notify_doctor_appointment_confirmed(appt.id)
        
        # Verify doctor notification was queued
        mock_task.delay.assert_called()
        
        # Verify SMS was sent to doctor
        mock_email_sms["sms"].assert_called()


def test_cancellation_notification(notification_test_data, db_session, mock_email_sms):
    """Test notify_doctor_appointment_cancelled sends notifications."""
    patient = notification_test_data["patient"]
    doctor = notification_test_data["doctor"]
    clinic = notification_test_data["clinic"]
    
    target_date = date.today() + timedelta(days=7)
    
    slot = AppointmentSlot(
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        slot_start=datetime.combine(target_date, time(11, 0)),
        slot_end=datetime.combine(target_date, time(11, 30)),
        slot_date=target_date,
        slot_status="available",
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
        status="cancelled"
    )
    db_session.add(appt)
    db_session.commit()
    
    from app.tasks.notification_tasks import notify_doctor_appointment_cancelled
    
    with patch('app.tasks.notification_tasks.SessionLocal', return_value=db_session), \
         patch('app.tasks.notification_tasks.send_notification_task') as mock_task:
        
        mock_task.delay = MagicMock()
        
        notify_doctor_appointment_cancelled(appt.id, "Patient requested cancellation")
        
        # Verify notifications were queued for both doctor and patient
        assert mock_task.delay.call_count >= 2
        
        # Verify SMS was sent to doctor
        mock_email_sms["sms"].assert_called()


# ============================================================================
# EMAIL SERVICE TESTS (LOCAL BACKEND)
# ============================================================================

def test_email_console_backend(monkeypatch, caplog):
    """Test EMAIL_BACKEND=console logs instead of sending."""
    import logging
    from app.services.email_service import send_email
    
    monkeypatch.setattr(settings, "EMAIL_BACKEND", "console")
    caplog.set_level(logging.INFO)
    
    result = send_email(
        to_email="test@example.com",
        subject="Test Subject",
        body="Test body content"
    )
    
    assert result is True
    assert "[EMAIL]" in caplog.text
    assert "test@example.com" in caplog.text
    assert "Test Subject" in caplog.text


def test_email_smtp_backend_requires_credentials(monkeypatch):
    """Test EMAIL_BACKEND=smtp requires credentials."""
    from app.services.email_service import send_email
    
    monkeypatch.setattr(settings, "EMAIL_BACKEND", "smtp")
    monkeypatch.setattr(settings, "SMTP_USER", None)
    monkeypatch.setattr(settings, "SMTP_PASSWORD", None)
    
    with pytest.raises(Exception) as excinfo:
        send_email(
            to_email="test@example.com",
            subject="Test",
            body="Test"
        )
    assert "SMTP" in str(excinfo.value) or "credentials" in str(excinfo.value).lower()


# ============================================================================
# SMS SERVICE TESTS (LOCAL BACKEND)
# ============================================================================

def test_sms_console_backend(monkeypatch, caplog):
    """Test SMS_BACKEND=console logs instead of sending."""
    import logging
    from app.services.sms_service import send_sms_message
    
    monkeypatch.setattr(settings, "SMS_BACKEND", "console")
    caplog.set_level(logging.INFO)
    
    result = send_sms_message(
        to_number="+15551234567",
        body="Test SMS message"
    )
    
    assert result is True
    assert "[SMS]" in caplog.text
    assert "+15551234567" in caplog.text
    assert "Test SMS message" in caplog.text


def test_sms_twilio_backend_without_credentials(monkeypatch, caplog):
    """Test SMS_BACKEND=twilio gracefully handles missing credentials."""
    import logging
    from app.services.sms_service import send_sms_message
    
    monkeypatch.setattr(settings, "SMS_BACKEND", "twilio")
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", None)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", None)
    caplog.set_level(logging.WARNING)
    
    result = send_sms_message(
        to_number="+15551234567",
        body="Test SMS"
    )
    
    # Should return False and log warning
    assert result is False
    assert "missing" in caplog.text.lower() or "twilio" in caplog.text.lower()


def test_sms_otp_helper(monkeypatch, caplog):
    """Test send_otp_sms helper function."""
    import logging
    from app.services.sms_service import send_otp_sms
    
    monkeypatch.setattr(settings, "SMS_BACKEND", "console")
    caplog.set_level(logging.INFO)
    
    result = send_otp_sms("+15551234567", "123456")
    
    assert result is True
    assert "123456" in caplog.text


# ============================================================================
# MULTIPLE NOTIFICATIONS QUERY TESTS
# ============================================================================

def test_query_user_notifications(notification_test_data, db_session):
    """Test querying notifications for a user."""
    user = notification_test_data["user"]
    
    # Create multiple notifications
    for i in range(5):
        notification = Notification(
            user_id=user.id,
            notification_type=f"type_{i}",
            title=f"Title {i}",
            body=f"Body {i}",
            is_read=i < 2  # First 2 are read
        )
        db_session.add(notification)
    db_session.commit()
    
    # Query all notifications
    all_notifs = db_session.query(Notification).filter(
        Notification.user_id == user.id
    ).all()
    assert len(all_notifs) == 5
    
    # Query unread only
    unread = db_session.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read == False
    ).all()
    assert len(unread) == 3


def test_query_notifications_by_type(notification_test_data, db_session):
    """Test querying notifications by type."""
    user = notification_test_data["user"]
    
    # Create notifications of different types
    types = ["appointment_reminder", "appointment_confirmation", "message", "appointment_reminder"]
    for t in types:
        notification = Notification(
            user_id=user.id,
            notification_type=t,
            title="Test",
            body="Test"
        )
        db_session.add(notification)
    db_session.commit()
    
    # Query by type
    reminders = db_session.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.notification_type == "appointment_reminder"
    ).all()
    assert len(reminders) == 2
