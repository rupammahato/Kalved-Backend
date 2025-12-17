# app/services/review_service.py
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.models.review import DoctorReview, ClinicReview, ReviewHelpfulVote
from app.models.appointment import Appointment
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.schemas.review import (
    DoctorReviewCreate,
    ClinicReviewCreate,
)


class ReviewService:
    # ---------------- Doctor Reviews ----------------

    @staticmethod
    def _check_doctor_review_authenticity(
        db: Session,
        doctor_id: int,
        patient_id: int,
        appointment_id: int,
    ) -> Appointment:
        """
        Ensure that:
        - Appointment exists
        - Belongs to given doctor and patient
        - Is completed or at least in the past
        - Not already reviewed for this appointment
        """
        appt = (
            db.query(Appointment)
            .filter(
                Appointment.id == appointment_id,
                Appointment.doctor_id == doctor_id,
                Appointment.patient_id == patient_id,
            )
            .first()
        )
        if not appt:
            raise ValueError("Appointment not found for this doctor and patient")

        # Basic authenticity: appointment started in the past
        if appt.appointment_start > datetime.utcnow():
            raise ValueError("Cannot review an appointment that has not happened yet")

        existing = (
            db.query(DoctorReview)
            .filter(
                DoctorReview.appointment_id == appointment_id,
                DoctorReview.patient_id == patient_id,
            )
            .first()
        )
        if existing:
            raise ValueError("You have already reviewed this appointment")

        return appt

    @staticmethod
    def create_doctor_review(
        db: Session,
        doctor_id: int,
        patient_id: int,
        payload: DoctorReviewCreate,
    ) -> DoctorReview:
        appt = ReviewService._check_doctor_review_authenticity(
            db=db,
            doctor_id=doctor_id,
            patient_id=patient_id,
            appointment_id=payload.appointment_id,
        )

        review = DoctorReview(
            doctor_id=doctor_id,
            patient_id=patient_id,
            appointment_id=payload.appointment_id,
            overall_rating=payload.overall_rating,
            communication_rating=payload.communication_rating,
            expertise_rating=payload.expertise_rating,
            time_spent_rating=payload.time_spent_rating,
            cleanliness_rating=payload.cleanliness_rating,
            review_title=payload.review_title,
            review_text=payload.review_text,
            is_verified=True,   # because of appointment check
            is_approved=True,   # or False if you want manual approval
        )
        db.add(review)
        db.commit()
        db.refresh(review)

        # Update doctor's average rating
        ReviewService.recalculate_doctor_rating(db, doctor_id)

        return review

    @staticmethod
    def list_doctor_reviews(
        db: Session,
        doctor_id: int,
        min_rating: Optional[int] = None,
        only_approved: bool = True,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[DoctorReview], Optional[float]]:
        q = db.query(DoctorReview).filter(DoctorReview.doctor_id == doctor_id)
        if only_approved:
            q = q.filter(DoctorReview.is_approved == True)  # noqa: E712
        if min_rating:
            q = q.filter(DoctorReview.overall_rating >= min_rating)

        items = (
            q.order_by(DoctorReview.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        avg_q = db.query(func.avg(DoctorReview.overall_rating)).filter(
            DoctorReview.doctor_id == doctor_id,
            DoctorReview.is_approved == True,  # noqa: E712
        )
        avg_rating = avg_q.scalar()
        return items, float(avg_rating) if avg_rating is not None else None

    @staticmethod
    def recalculate_doctor_rating(db: Session, doctor_id: int) -> Optional[float]:
        """
        Recalculate and store doctor's average rating and total reviews.
        """
        # Query both average and count in one go
        query = db.query(
            func.avg(DoctorReview.overall_rating),
            func.count(DoctorReview.id)
        ).filter(
            DoctorReview.doctor_id == doctor_id,
            DoctorReview.is_approved == True,  # noqa: E712
        )
        
        result = query.first()
        if not result:
            return None
            
        avg_val, count_val = result
        avg = float(avg_val) if avg_val is not None else None
        total = int(count_val) if count_val else 0

        doc = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if doc:
            doc.average_rating = avg
            doc.total_reviews = total
            db.commit()

        return avg

    @staticmethod
    def moderate_doctor_review(
        db: Session,
        review_id: int,
        is_approved: bool,
        moderation_notes: Optional[str],
    ) -> DoctorReview:
        review = db.query(DoctorReview).filter(DoctorReview.id == review_id).first()
        if not review:
            raise ValueError("Review not found")

        review.is_approved = is_approved
        review.moderation_notes = moderation_notes
        review.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(review)

        # Update rating after moderation
        ReviewService.recalculate_doctor_rating(db, review.doctor_id)

        return review

    # ---------------- Helpful Votes ----------------

    @staticmethod
    def vote_helpful(
        db: Session,
        review_id: int,
        user_id: int,
        is_helpful: bool,
    ) -> DoctorReview:
        review = db.query(DoctorReview).filter(DoctorReview.id == review_id).first()
        if not review:
            raise ValueError("Review not found")

        vote = (
            db.query(ReviewHelpfulVote)
            .filter(
                ReviewHelpfulVote.review_id == review_id,
                ReviewHelpfulVote.user_id == user_id,
            )
            .first()
        )

        if vote:
            # If they flip from helpful to not helpful, adjust count
            if vote.is_helpful and not is_helpful:
                review.helpful_count = max(0, review.helpful_count - 1)
            elif not vote.is_helpful and is_helpful:
                review.helpful_count += 1
            vote.is_helpful = is_helpful
        else:
            vote = ReviewHelpfulVote(
                review_id=review_id,
                user_id=user_id,
                is_helpful=is_helpful,
            )
            db.add(vote)
            if is_helpful:
                review.helpful_count += 1

        db.commit()
        db.refresh(review)
        return review

    # ---------------- Clinic Reviews ----------------

    @staticmethod
    def _check_clinic_review_authenticity(
        db: Session,
        clinic_id: int,
        user_id: int,
    ) -> None:
        """
        Simple version:
        - At least one appointment for this clinic and user (as patient).
        """
        exists = (
            db.query(Appointment)
            .filter(
                Appointment.clinic_id == clinic_id,
                Appointment.patient_id == user_id,
            )
            .first()
        )
        if not exists:
            raise ValueError("You must have an appointment at this clinic to review it")

    @staticmethod
    def create_clinic_review(
        db: Session,
        clinic_id: int,
        user_id: int,
        payload: ClinicReviewCreate,
    ) -> ClinicReview:
        ReviewService._check_clinic_review_authenticity(db, clinic_id, user_id)

        review = ClinicReview(
            clinic_id=clinic_id,
            user_id=user_id,
            rating=payload.rating,
            ambiance_rating=payload.ambiance_rating,
            staff_rating=payload.staff_rating,
            hygiene_rating=payload.hygiene_rating,
            review_title=payload.review_title,
            review_text=payload.review_text,
            is_verified=True,
            is_approved=True,
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        return review

    @staticmethod
    def list_clinic_reviews(
        db: Session,
        clinic_id: int,
        min_rating: Optional[int] = None,
        only_approved: bool = True,
        skip: int = 0,
        limit: int = 20,
    ):
        q = db.query(ClinicReview).filter(ClinicReview.clinic_id == clinic_id)
        if only_approved:
            q = q.filter(ClinicReview.is_approved == True)  # noqa: E712
        if min_rating:
            q = q.filter(ClinicReview.rating >= min_rating)

        items = (
            q.order_by(ClinicReview.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        avg_q = db.query(func.avg(ClinicReview.rating)).filter(
            ClinicReview.clinic_id == clinic_id,
            ClinicReview.is_approved == True,  # noqa: E712
        )
        avg = avg_q.scalar()
        return items, float(avg) if avg is not None else None
