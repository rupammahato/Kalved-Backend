from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.patient import Patient
from app.utils.errors import UserNotFoundError


class PatientService:
    @staticmethod
    def ensure_patient(db: Session, user_id: int) -> Patient:
        patient = db.query(Patient).filter(Patient.user_id == int(user_id)).first()
        if not patient:
            raise UserNotFoundError("Patient profile not found")
        return patient

    @staticmethod
    def update_profile(db: Session, user_id: int, payload: dict) -> Patient:
        patient = PatientService.ensure_patient(db, user_id)
        for field in [
            "date_of_birth",
            "gender",
            "blood_group",
            "medical_history",
            "allergies",
            "medications",
            "emergency_contact_name",
            "emergency_contact_phone",
            "address",
            "city",
            "state",
            "pincode",
            "country",
        ]:
            if field in payload and payload[field] is not None:
                setattr(patient, field, payload[field])
        patient.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        db.refresh(patient)
        return patient
