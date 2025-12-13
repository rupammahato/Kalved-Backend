from datetime import datetime, date, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.doctor import Doctor, DoctorQualification
from app.models.clinic import Clinic, ClinicTiming
from app.models.audit import AdminActivityLog
from app.models.user import User
from app.utils.errors import UserNotFoundError


class DoctorService:
    @staticmethod
    def get_by_id(db: Session, doctor_id: int) -> Doctor:
        return db.query(Doctor).filter(Doctor.id == doctor_id).first()

    @staticmethod
    def ensure_doctor(db: Session, user_id: int) -> Doctor:
        doctor = db.query(Doctor).filter(Doctor.user_id == int(user_id)).first()
        if not doctor:
            raise UserNotFoundError("Doctor profile not found")
        return doctor

    @staticmethod
    def update_profile(db: Session, user_id: int, payload: dict) -> Doctor:
        doctor = DoctorService.ensure_doctor(db, user_id)

        # Basic profile fields
        for field in [
            "brc_number",
            "brc_issued_date",
            "brc_valid_until",
            "years_of_experience",
            "specializations",
            "languages",
            "default_consultation_fee",
            "identity_proof_url",
            "clinic_registration_certificate",
            "gst_number",
        ]:
            if field in payload and payload[field] is not None:
                setattr(doctor, field, payload[field])

        # Reset verification if BRC changes
        if "brc_number" in payload and payload["brc_number"]:
            doctor.brc_verification_status = "pending"
            doctor.brc_verification_notes = None

        # Qualifications replacement
        if "qualifications" in payload and payload["qualifications"] is not None:
            doctor.qualifications.clear()
            for q in payload["qualifications"]:
                doctor.qualifications.append(
                    DoctorQualification(
                        degree_name=q.get("degree_name"),
                        institution=q.get("institution"),
                        country=q.get("country"),
                        year_of_graduation=q.get("year_of_graduation"),
                    )
                )

        doctor.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        db.refresh(doctor)
        return doctor

    @staticmethod
    def add_clinic(db: Session, user_id: int, clinic_payload: dict) -> Clinic:
        doctor = DoctorService.ensure_doctor(db, user_id)
        clinic = Clinic(
            doctor_id=doctor.id,
            name=clinic_payload["name"],
            address=clinic_payload.get("address"),
            city=clinic_payload.get("city"),
            state=clinic_payload.get("state"),
            pincode=clinic_payload.get("pincode"),
            country=clinic_payload.get("country"),
            phone=clinic_payload.get("phone"),
            latitude=clinic_payload.get("latitude"),
            longitude=clinic_payload.get("longitude"),
        )
        timings = clinic_payload.get("timings") or []
        for t in timings:
            clinic.timings.append(
                ClinicTiming(
                    day=t.get("day"),
                    open_time=t.get("open_time"),
                    close_time=t.get("close_time"),
                    notes=t.get("notes"),
                )
            )
        db.add(clinic)
        db.commit()
        db.refresh(clinic)
        return clinic

    @staticmethod
    def list_pending(db: Session):
        return (
            db.query(Doctor)
            .filter(and_(Doctor.brc_verification_status == "pending"))
            .all()
        )

    @staticmethod
    def approve_doctor(db: Session, admin_id: int, doctor_id: int, notes: str | None = None):
        doctor = DoctorService.get_by_id(db, doctor_id)
        if not doctor:
            raise UserNotFoundError("Doctor not found")

        # Simple BRC validity check
        # Use local date to avoid timezone-driven off-by-one for date-only field
        today = date.today()
        if doctor.brc_valid_until and doctor.brc_valid_until < today:
            raise ValueError("BRC expired; cannot approve")

        doctor.brc_verification_status = "verified"
        doctor.admin_approved_by = admin_id
        now = datetime.now(timezone.utc)
        doctor.admin_approved_at = now.replace(tzinfo=None)
        doctor.admin_approval_notes = notes

        # Update user status to active
        user = db.query(User).filter(User.id == doctor.user_id).first()
        if user:
            user.status = "active"

        db.add(
            AdminActivityLog(
                admin_id=str(admin_id),
                activity=f"doctor:{doctor_id}:approved",
            )
        )

        db.commit()
        db.refresh(doctor)
        return doctor

    @staticmethod
    def reject_doctor(db: Session, admin_id: int, doctor_id: int, reason: str | None = None):
        doctor = DoctorService.get_by_id(db, doctor_id)
        if not doctor:
            raise UserNotFoundError("Doctor not found")
        doctor.brc_verification_status = "rejected"
        doctor.brc_verification_notes = reason
        doctor.admin_approved_by = admin_id
        doctor.admin_approved_at = datetime.now(timezone.utc).replace(tzinfo=None)

        user = db.query(User).filter(User.id == doctor.user_id).first()
        if user:
            user.status = "suspended"

        db.add(
            AdminActivityLog(
                admin_id=str(admin_id),
                activity=f"doctor:{doctor_id}:rejected",
            )
        )
        db.commit()
        db.refresh(doctor)
        return doctor
