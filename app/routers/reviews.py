# app/routers/reviews.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.review import (
    DoctorReviewCreate,
    DoctorReviewResponse,
    DoctorReviewListResponse,
    ClinicReviewCreate,
    ClinicReviewResponse,
    ClinicReviewListResponse,
    HelpfulVoteRequest,
    HelpfulVoteResponse,
    ReviewModerationRequest,
)
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


# ---------------- Doctor reviews ----------------

@router.post(
    "/doctors/{doctor_id}",
    response_model=DoctorReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_doctor_review(
    doctor_id: int,
    payload: DoctorReviewCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user["user_type"] != "patient":
        raise HTTPException(status_code=403, detail="Only patients can submit reviews")

    try:
        review = ReviewService.create_doctor_review(
            db=db,
            doctor_id=doctor_id,
            patient_id=current_user["sub"],
            payload=payload,
        )
        return review
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/doctors/{doctor_id}",
    response_model=DoctorReviewListResponse,
)
def get_doctor_reviews(
    doctor_id: int,
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    items, avg = ReviewService.list_doctor_reviews(
        db=db,
        doctor_id=doctor_id,
        min_rating=min_rating,
        only_approved=True,
        skip=skip,
        limit=limit,
    )
    return DoctorReviewListResponse(
        items=[DoctorReviewResponse.from_orm(r) for r in items],
        total=len(items),
        average_rating=avg,
    )


# ---------------- Helpful votes ----------------

@router.post(
    "/doctors/{review_id}/helpful",
    response_model=HelpfulVoteResponse,
)
def mark_review_helpful(
    review_id: int,
    payload: HelpfulVoteRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user["user_type"] not in ("patient", "doctor"):
        raise HTTPException(status_code=403, detail="Not allowed")

    try:
        review = ReviewService.vote_helpful(
            db=db,
            review_id=review_id,
            user_id=current_user["sub"],
            is_helpful=payload.is_helpful,
        )
        return HelpfulVoteResponse(review_id=review.id, helpful_count=review.helpful_count)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------- Clinic reviews ----------------

@router.post(
    "/clinics/{clinic_id}",
    response_model=ClinicReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_clinic_review(
    clinic_id: int,
    payload: ClinicReviewCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Both patients and general users who had an appointment can review
    if current_user["user_type"] not in ("patient", "user"):
        raise HTTPException(status_code=403, detail="Not allowed")

    try:
        review = ReviewService.create_clinic_review(
            db=db,
            clinic_id=clinic_id,
            user_id=current_user["sub"],
            payload=payload,
        )
        return review
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/clinics/{clinic_id}",
    response_model=ClinicReviewListResponse,
)
def get_clinic_reviews(
    clinic_id: int,
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    items, avg = ReviewService.list_clinic_reviews(
        db=db,
        clinic_id=clinic_id,
        min_rating=min_rating,
        only_approved=True,
        skip=skip,
        limit=limit,
    )
    return ClinicReviewListResponse(
        items=[ClinicReviewResponse.from_orm(r) for r in items],
        total=len(items),
        average_rating=avg,
    )


# ---------------- Moderation (Admin) ----------------

@router.get("/pending", response_model=DoctorReviewListResponse)
def get_pending_reviews(
    skip: int = 0,
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    q = (
        db.query(DoctorReview)
        .filter(DoctorReview.is_approved == False)  # noqa: E712
        .order_by(DoctorReview.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = q.all()
    return DoctorReviewListResponse(
        items=[DoctorReviewResponse.from_orm(r) for r in items],
        total=len(items),
        average_rating=None,
    )


@router.post("/{review_id}/moderate", response_model=DoctorReviewResponse)
def moderate_review(
    review_id: int,
    payload: ReviewModerationRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    try:
        review = ReviewService.moderate_doctor_review(
            db=db,
            review_id=review_id,
            is_approved=payload.is_approved,
            moderation_notes=payload.moderation_notes,
        )
        return review
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
