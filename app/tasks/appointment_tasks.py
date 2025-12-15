# app/tasks/appointment_tasks.py
from celery import shared_task
from datetime import datetime, timedelta, date

from sqlalchemy import and_
from app.core.database import SessionLocal
from app.models.appointment import Appointment, AppointmentSlot
from app.models.clinic import Clinic
from app.services.appointment_service import AppointmentService
from app.tasks.notification_tasks import (
    send_appointment_reminder_email,
)
from app.services.sms_service import send_sms_message
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_daily_slots(self):
    """
    Generate slots for all active clinics for the next N days.
    Usually scheduled once per night via Celery Beat.
    """
    db = SessionLocal()
    try:
        today = datetime.utcnow().date()
        clinics = db.query(Clinic).filter(Clinic.is_active == True).all()  # noqa: E712

        for clinic in clinics:
            try:
                # e.g., generate for next 30 days
                AppointmentService.generate_slots_for_clinic.s(
                    clinic_id=clinic.id,
                    start_date=today,
                    days_ahead=30,
                )  # called via async signature if you prefer
                # Or call directly in-process:
                # await AppointmentService.generate_slots_for_clinic(db, clinic.id, today, 30)
            except Exception as e:
                logger.error(f"Failed to generate slots for clinic {clinic.id}: {e}")

    except Exception as e:
        logger.error(f"Error in generate_daily_slots: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@shared_task(bind=True, max_retries=3)
def send_reminders_24h_before(self):
    """
    Send email reminders ~24 hours before appointment_start.
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        start_window = now + timedelta(hours=24)
        end_window = start_window + timedelta(hours=1)

        appts = (
            db.query(Appointment)
            .filter(
                and_(
                    Appointment.status == "scheduled",
                    Appointment.appointment_start >= start_window,
                    Appointment.appointment_start < end_window,
                    Appointment.reminder_sent_at.is_(None),
                )
            )
            .all()
        )

        logger.info(f"Found {len(appts)} appointments for 24h reminder window")

        for a in appts:
            try:
                send_appointment_reminder_email(
                    email=a.patient.user.email,
                    patient_name=a.patient.user.first_name,
                    doctor_name=a.doctor.user.first_name,
                    appointment_date=a.appointment_date,
                    appointment_time=a.appointment_time,
                    clinic_name=a.clinic.clinic_name,
                    is_final_reminder=False,
                )
                
                # SMS Reminder
                patient_user = a.patient.user
                if patient_user.phone:
                    sms_body = (
                        f"Reminder: appt with Dr {a.doctor.user.first_name} "
                        f"on {a.appointment_date} at {a.appointment_time}."
                    )
                    send_sms_message(to_number=patient_user.phone, body=sms_body)
                
                a.reminder_sent_at = datetime.utcnow()
                db.commit()
            except Exception as e:
                logger.error(f"Failed to send 24h reminder for appt {a.id}: {e}")
                db.rollback()
    except Exception as e:
        logger.error(f"Error in send_reminders_24h_before: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@shared_task(bind=True, max_retries=3)
def send_reminders_1h_before(self):
    """
    Send final reminders ~1 hour before appointment_start.
    Scheduled every 15 minutes via Celery Beat.
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        start_window = now + timedelta(hours=1)
        end_window = start_window + timedelta(minutes=30)

        appts = (
            db.query(Appointment)
            .filter(
                and_(
                    Appointment.status == "scheduled",
                    Appointment.appointment_start >= start_window,
                    Appointment.appointment_start < end_window,
                    Appointment.second_reminder_sent_at.is_(None),
                )
            )
            .all()
        )

        logger.info(f"Found {len(appts)} appointments for 1h reminder window")

        for a in appts:
            try:
                send_appointment_reminder_email(
                    email=a.patient.user.email,
                    patient_name=a.patient.user.first_name,
                    doctor_name=a.doctor.user.first_name,
                    appointment_date=a.appointment_date,
                    appointment_time=a.appointment_time,
                    clinic_name=a.clinic.clinic_name,
                    is_final_reminder=True,
                )
                
                # SMS Reminder (Urgent)
                patient_user = a.patient.user
                if patient_user.phone:
                    sms_body = (
                        f"URGENT: appt with Dr {a.doctor.user.first_name} "
                        f"starting in 1 hour ({a.appointment_time})."
                    )
                    send_sms_message(to_number=patient_user.phone, body=sms_body)

                a.second_reminder_sent_at = datetime.utcnow()
                db.commit()
            except Exception as e:
                logger.error(f"Failed to send 1h reminder for appt {a.id}: {e}")
                db.rollback()
    except Exception as e:
        logger.error(f"Error in send_reminders_1h_before: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()
