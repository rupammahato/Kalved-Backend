# app/tasks/notification_tasks.py
from celery import shared_task
from datetime import datetime
from typing import Optional, List

from app.core.database import SessionLocal
from app.models.notification import Notification, NotificationPreferences
from app.models.user import User
from app.models.appointment import Appointment
from app.services.email_service import send_email
from app.services.sms_service import send_sms_message
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_notification_task(
    self,
    user_id: int,
    notification_type: str,
    title: str,
    body: str,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[int] = None,
    channels: Optional[List[str]] = None,  # ["email", "sms", "push", "in_app"]
):
    """
    Central task to send notifications via multiple channels.
    - Creates Notification record.
    - Checks user preferences.
    - Dispatches to Email/SMS services.
    - Updates Notification record status.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found for notification.")
            return

        # 1. Check Preferences
        prefs = db.query(NotificationPreferences).filter(NotificationPreferences.user_id == user_id).first()
        
        # Default channels if not specified
        if not channels:
            channels = ["in_app", "email"] # Default
        
        # Override based on preferences (simplified logic)
        email_enabled = True
        sms_enabled = False # specific opt-in usually
        push_enabled = True
        
        if prefs:
            email_enabled = prefs.email_enabled
            sms_enabled = prefs.sms_enabled
            push_enabled = prefs.push_enabled
            
            # Specific category checks
            if notification_type == "appointment_reminder" and not prefs.appointment_reminders:
                email_enabled = False; sms_enabled = False; push_enabled = False
            # ... add more category checks as needed
        
        # 2. Create Notification Record
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            is_in_app=True, # Always create in-app record
            is_read=False,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        # 3. Dispatch Channels
        
        # Email
        if "email" in channels and email_enabled and user.email:
            try:
                # Assuming send_email is synchronous or handles its own async
                # For simplicity here, calling it directly. In prod, maybe another task?
                # Using a generic template or constructing html body
                send_email(
                    to_email=user.email,
                    subject=title,
                    html_content=f"<p>{body}</p>" # Simple fallback
                )
                notification.is_email_sent = True
                notification.email_sent_at = datetime.utcnow()
            except Exception as e:
                logger.error(f"Failed to send email to {user.email}: {e}")

        # SMS
        if "sms" in channels and sms_enabled and user.phone:
            try:
                success = send_sms_message(to_number=user.phone, body=f"{title}: {body}")
                if success:
                    notification.is_sms_sent = True
                    notification.sms_sent_at = datetime.utcnow()
            except Exception as e:
                logger.error(f"Failed to send SMS to {user.phone}: {e}")

        # Push (Placeholder for now)
        if "push" in channels and push_enabled:
            # send_push_notification(...)
            pass

        db.commit()

    except Exception as e:
        logger.error(f"Error in send_notification_task: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()

# Specific Helpers that were referenced in appointment_service.py

@shared_task
def send_appointment_confirmation(appointment_id: int):
    """
    Wrapper to send confirmation notification.
    """
    db = SessionLocal()
    try:
        appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appt: 
            return
            
        # Notify Patient
        # 1) Email (Generic helper or specific if you want)
        try:
            send_appointment_reminder_email(
                email=appt.patient.user.email,
                patient_name=appt.patient.user.first_name,
                doctor_name=appt.doctor.user.first_name,
                appointment_date=str(appt.appointment_date),
                appointment_time=str(appt.appointment_time),
                clinic_name=appt.clinic.name,
                is_final_reminder=False, # Reusing template
            )
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

        # 2) SMS to patient
        if appt.patient.user.phone:
            sms_body = (
                f"Appt booked with Dr {appt.doctor.user.first_name} at {appt.clinic.name} "
                f"on {appt.appointment_date} at {appt.appointment_time}. "
                f"Please confirm in the app."
            )
            try:
                send_sms_message(to_number=appt.patient.user.phone, body=sms_body)
            except Exception as e:
                logger.error(f"Failed to send SMS: {e}")

        # 3) In-App Notification (System of Record)
        send_notification_task.delay(
            user_id=appt.patient.user_id,
            notification_type="appointment_confirmation",
            title="Appointment Confirmed",
            body=f"Your appointment with Dr. {appt.doctor.user.last_name} on {appt.appointment_date} at {appt.appointment_time} is booked.",
            related_entity_type="appointment",
            related_entity_id=appt.id,
            channels=["in_app"] # SMS/Email handled explicitly above
        )
        
        # Notify Doctor (Optional for same-day/next-day - implementing simple version)
        send_notification_task.delay(
            user_id=appt.doctor.user_id,
            notification_type="new_appointment",
            title="New Appointment Booked",
            body=f"New appointment with {appt.patient.user.first_name} on {appt.appointment_date} at {appt.appointment_time}.",
            related_entity_type="appointment",
            related_entity_id=appt.id,
            channels=["in_app", "email"]
        )
        
    finally:
        db.close()

@shared_task
def notify_doctor_appointment_confirmed(appointment_id: int):
    """
    Patient hit 'Confirm'.
    """
    db = SessionLocal()
    try:
        appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appt: return

        # 1) Notify Doctor via Email/SMS
        doctor_user = appt.doctor.user
        patient_user = appt.patient.user
        
        sms_body = (
            f"{patient_user.first_name} confirmed appt on "
            f"{appt.appointment_date} at {appt.appointment_time}."
        )
        if doctor_user.phone:
            send_sms_message(to_number=doctor_user.phone, body=sms_body)
            
        send_notification_task.delay(
            user_id=appt.doctor.user_id,
            notification_type="appointment_patient_confirmed",
            title="Patient Confirmed Attendance",
            body=f"Patient {patient_user.first_name} has confirmed their appointment on {appt.appointment_date}.",
            related_entity_type="appointment",
            related_entity_id=appt.id,
            channels=["in_app", "email"] 
        )
    finally:
        db.close()

@shared_task
def notify_doctor_appointment_cancelled(appointment_id: int, reason: str):
    db = SessionLocal()
    try:
        appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appt: return

        # Notify Doctor
        doctor_user = appt.doctor.user
        patient_user = appt.patient.user
        
        sms_body = (
            f"Appt with {patient_user.first_name} on {appt.appointment_date} "
            f"at {appt.appointment_time} was cancelled. Reason: {reason[:120]}"
        )
        if doctor_user.phone:
            send_sms_message(to_number=doctor_user.phone, body=sms_body)

        send_notification_task.delay(
            user_id=appt.doctor.user_id,
            notification_type="appointment_cancelled",
            title="Appointment Cancelled",
            body=f"Appointment with {appt.patient.user.first_name} on {appt.appointment_date} was cancelled. Reason: {reason}",
            related_entity_type="appointment",
            related_entity_id=appt.id,
            channels=["in_app", "email"]
        )
        
        # Notify Patient (Confirmation of their cancellation)
        send_notification_task.delay(
            user_id=appt.patient.user_id,
            notification_type="appointment_cancelled",
            title="Blocking Released",
            body=f"Your appointment cancellation is confirmed.",
            related_entity_type="appointment",
            related_entity_id=appt.id,
            channels=["email", "sms"] # Optional SMS to patient
        )
    finally:
        db.close()

@shared_task
def send_appointment_reminder_email(
    email: str,
    patient_name: str,
    doctor_name: str,
    appointment_date: str,
    appointment_time: str,
    clinic_name: str,
    is_final_reminder: bool,
):
    """
    Legacy/Specific task called by appointment_tasks.py.
    We can refactor this to use send_notification_task internally or keep as is for specific email templating.
    For now, keeping valid signature but potentially integrating SMS logic if we can resolve user_id.
    
    Since this task signature only takes strings (email, names), it's hard to look up the user for SMS 
    WITHOUT user_id.
    
    BEST PRACTICE: Refactor appointment_tasks.py to pass user_ids/objects instead of raw strings, 
    OR look up user by email here.
    """
    # ... Implementation using send_email ...
    subject = "Appointment Reminder" if not is_final_reminder else "Urgent: Appointment in 1 Hour"
    body = f"Hello {patient_name}, reminder for your appointment with Dr. {doctor_name} at {clinic_name} on {appointment_date} at {appointment_time}."
    
    try:
        send_email(to_email=email, subject=subject, html_content=f"<p>{body}</p>")
        # SMS Integration here would be tricky without phone number passed in.
        # Assuming appointment_tasks.py will be updated to use the new robust system eventually.
    except Exception as e:
        logger.error(f"Error sending legacy reminder: {e}")
