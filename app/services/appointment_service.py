from datetime import datetime, timedelta, date as date_type
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.appointment import (
    AppointmentSlot,
    Appointment,
    ClinicAvailabilityTemplate,
)
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.user import User
from app.cache.cache_service import redis_cache

import json


class AppointmentService:
    """
    Core business logic for:
    - Slot generation
    - Availability querying
    - Booking / confirming / cancelling appointments
    - Listing appointments
    """

    # -------------------------------------------------------------------------
    # Slot generation
    # -------------------------------------------------------------------------
    @staticmethod
    async def generate_slots_for_clinic(
        db: Session,
        clinic_id: int,
        start_date: date_type,
        days_ahead: int = 30,
    ) -> Dict[str, Any]:
        """
        Generate appointment slots for a clinic based on availability templates.

        - Reads ClinicAvailabilityTemplate for each day
        - Generates AppointmentSlot rows if they don't already exist
        - Uses Redis to avoid regenerating the same window twice
        """
        cache_key = f"slots_generated:{clinic_id}:{start_date.isoformat()}"
        if await redis_cache.get(cache_key):
            return {"status": "already_generated", "clinic_id": clinic_id}

        clinic: Optional[Clinic] = (
            db.query(Clinic).filter(Clinic.id == clinic_id).first()
        )
        if not clinic:
            raise ValueError("Clinic not found")

        # Assuming 1 doctor per clinic; adapt if you support multi-doctor clinics per template
        doctor: Optional[Doctor] = clinic.doctor  # relationship on Clinic

        if not doctor:
            raise ValueError("No doctor associated with this clinic")

        current_date = start_date
        slots_to_insert: List[AppointmentSlot] = []

        for _ in range(days_ahead):
            day_name = current_date.strftime("%A")

            template: Optional[ClinicAvailabilityTemplate] = (
                db.query(ClinicAvailabilityTemplate)
                .filter(
                    and_(
                        ClinicAvailabilityTemplate.clinic_id == clinic_id,
                        ClinicAvailabilityTemplate.day_of_week == day_name,
                        ClinicAvailabilityTemplate.is_active == True,  # noqa: E712
                    )
                )
                .first()
            )

            if not template:
                current_date += timedelta(days=1)
                continue

            opening_dt = datetime.combine(current_date, template.opening_time)
            closing_dt = datetime.combine(current_date, template.closing_time)
            break_start_dt = (
                datetime.combine(current_date, template.break_start)
                if template.break_start
                else None
            )
            break_end_dt = (
                datetime.combine(current_date, template.break_end)
                if template.break_end
                else None
            )

            slot_duration = timedelta(minutes=template.slot_duration_minutes)
            cursor = opening_dt

            while cursor < closing_dt:
                # Skip break interval
                if break_start_dt and break_end_dt:
                    if break_start_dt <= cursor < break_end_dt:
                        cursor += slot_duration
                        continue

                slot_start = cursor
                slot_end = cursor + slot_duration

                # Avoid duplicates
                exists = (
                    db.query(AppointmentSlot)
                    .filter(
                        and_(
                            AppointmentSlot.clinic_id == clinic_id,
                            AppointmentSlot.doctor_id == doctor.id,
                            AppointmentSlot.slot_start == slot_start,
                        )
                    )
                    .first()
                )
                if not exists:
                    slot = AppointmentSlot(
                        clinic_id=clinic_id,
                        doctor_id=doctor.id,
                        slot_start=slot_start,
                        slot_end=slot_end,
                        slot_date=current_date,
                        slot_status="available",
                        is_active=True,
                    )
                    slots_to_insert.append(slot)

                cursor += slot_duration

            current_date += timedelta(days=1)

        if slots_to_insert:
            db.bulk_save_objects(slots_to_insert)
            db.commit()

        await redis_cache.set(cache_key, "1", ttl=24 * 3600)

        return {
            "status": "success",
            "clinic_id": clinic_id,
            "slots_created": len(slots_to_insert),
        }

    # -------------------------------------------------------------------------
    # Availability querying
    # -------------------------------------------------------------------------
    @staticmethod
    async def get_available_slots(
        db: Session,
        clinic_id: int,
        doctor_id: int,
        query_date: date_type,
    ) -> List[Dict[str, Any]]:
        """
        Get all available slots for a given clinic/doctor/date.

        Uses Redis caching for 1 hour to reduce DB load.
        """
        cache_key = (
            f"available_slots:{clinic_id}:{doctor_id}:{query_date.isoformat()}"
        )
        cached = await redis_cache.get(cache_key)
        if cached:
            return json.loads(cached)

        slots: List[AppointmentSlot] = (
            db.query(AppointmentSlot)
            .filter(
                and_(
                    AppointmentSlot.clinic_id == clinic_id,
                    AppointmentSlot.doctor_id == doctor_id,
                    AppointmentSlot.slot_date == query_date,
                    AppointmentSlot.slot_status == "available",
                    AppointmentSlot.is_active == True,  # noqa: E712
                )
            )
            .order_by(AppointmentSlot.slot_start.asc())
            .all()
        )

        result = [
            {
                "slot_id": s.id,
                "start_time": s.slot_start.isoformat(),
                "end_time": s.slot_end.isoformat(),
                "available": True,
            }
            for s in slots
        ]

        await redis_cache.set(cache_key, json.dumps(result), ttl=3600)
        return result

    # -------------------------------------------------------------------------
    # Booking / confirm / cancel
    # -------------------------------------------------------------------------
    @staticmethod
    async def book_appointment(
        db: Session,
        patient_id: int,
        slot_id: int,
        appointment_type: Optional[str],
        reason_for_visit: Optional[str],
    ) -> Dict[str, Any]:
        """
        Book a free appointment (no payment step).
        - Locks the selected slot row to prevent double booking.
        - Creates an Appointment.
        - Marks slot as 'booked'.
        - Triggers an async confirmation email task.
        """
        slot: Optional[AppointmentSlot] = (
            db.query(AppointmentSlot)
            .filter(
                AppointmentSlot.id == slot_id,
                AppointmentSlot.slot_status == "available",
                AppointmentSlot.is_active == True,  # noqa: E712
            )
            .with_for_update()
            .first()
        )

        if not slot:
            raise ValueError("Slot not available or already booked")

        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=slot.doctor_id,
            clinic_id=slot.clinic_id,
            appointment_slot_id=slot.id,
            appointment_date=slot.slot_date,
            appointment_time=slot.slot_start.time(),
            appointment_start=slot.slot_start,
            appointment_end=slot.slot_end,
            appointment_type=appointment_type,
            reason_for_visit=reason_for_visit,
            status="scheduled",
            is_confirmed=False,
        )

        slot.slot_status = "booked"

        db.add(appointment)
        db.commit()
        db.refresh(appointment)

        # Invalidate cache for that date
        cache_pattern = (
            f"available_slots:{slot.clinic_id}:{slot.doctor_id}:{slot.slot_date.isoformat()}"
        )
        await redis_cache.delete_pattern(cache_pattern)

        # Trigger async confirmation email
        from app.tasks.notification_tasks import send_appointment_confirmation

        send_appointment_confirmation.delay(appointment.id)

        return {
            "appointment_id": appointment.id,
            "status": "booked",
            "appointment_date": appointment.appointment_date,
            "appointment_time": appointment.appointment_time,
            "message": "Appointment booked successfully. Please confirm your attendance.",
        }

    @staticmethod
    async def confirm_appointment(
        db: Session,
        appointment_id: int,
        patient_id: int,
    ) -> Dict[str, Any]:
        """
        Patient confirms they will attend.
        """
        appt: Optional[Appointment] = (
            db.query(Appointment)
            .filter(
                Appointment.id == appointment_id,
                Appointment.patient_id == patient_id,
                Appointment.status == "scheduled",
            )
            .first()
        )
        if not appt:
            raise ValueError("Appointment not found or cannot be confirmed")

        if appt.is_confirmed:
            return {
                "appointment_id": appt.id,
                "status": "confirmed",
                "message": "Appointment already confirmed.",
            }

        appt.is_confirmed = True
        appt.confirmed_at = datetime.utcnow()
        db.commit()

        from app.tasks.notification_tasks import notify_doctor_appointment_confirmed

        notify_doctor_appointment_confirmed.delay(appt.id)

        return {
            "appointment_id": appt.id,
            "status": "confirmed",
            "message": "Appointment confirmed. The doctor will be notified.",
        }

    @staticmethod
    async def cancel_appointment(
        db: Session,
        appointment_id: int,
        cancelled_by_user_id: int,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Cancel an appointment (no refund logic, since booking is free).
        """
        appt: Optional[Appointment] = (
            db.query(Appointment).filter(Appointment.id == appointment_id).first()
        )
        if not appt:
            raise ValueError("Appointment not found")

        if appt.status != "scheduled":
            raise ValueError("Only scheduled appointments can be cancelled")

        appt.status = "cancelled"
        appt.cancellation_reason = reason
        appt.cancelled_by = cancelled_by_user_id
        appt.cancelled_at = datetime.utcnow()

        slot: AppointmentSlot = appt.slot
        slot.slot_status = "available"

        # Write audit row
        from app.models.appointment import AppointmentCancellation

        cancellation = AppointmentCancellation(
            appointment_id=appt.id,
            cancelled_by=cancelled_by_user_id,
            cancellation_reason=reason,
        )
        db.add(cancellation)

        db.commit()

        # Invalidate cache
        cache_pattern = (
            f"available_slots:{slot.clinic_id}:{slot.doctor_id}:{slot.slot_date.isoformat()}"
        )
        await redis_cache.delete_pattern(cache_pattern)

        # Notify doctor
        from app.tasks.notification_tasks import notify_doctor_appointment_cancelled

        notify_doctor_appointment_cancelled.delay(appt.id, reason)

        return {
            "status": "cancelled",
            "message": "Appointment cancelled and slot released.",
        }

    # -------------------------------------------------------------------------
    # Listing helpers
    # -------------------------------------------------------------------------
    @staticmethod
    def list_patient_appointments(
        db: Session,
        patient_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Appointment]:
        return (
            db.query(Appointment)
            .filter(Appointment.patient_id == patient_id)
            .order_by(Appointment.appointment_date.desc(), Appointment.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def list_doctor_appointments(
        db: Session,
        doctor_id: int,
        status: Optional[str] = None,
        from_date: Optional[date_type] = None,
        to_date: Optional[date_type] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Appointment]:
        q = db.query(Appointment).filter(Appointment.doctor_id == doctor_id)

        if status:
            q = q.filter(Appointment.status == status)

        if from_date:
            q = q.filter(Appointment.appointment_date >= from_date)
        if to_date:
            q = q.filter(Appointment.appointment_date <= to_date)

        return (
            q.order_by(Appointment.appointment_date.asc(), Appointment.appointment_time.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
