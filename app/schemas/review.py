# app/schemas/review.py
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ---------------- Doctor Reviews ----------------

class DoctorReviewCreate(BaseModel):
    appointment_id: int
    overall_rating: int = Field(..., ge=1, le=5)
    communication_rating: Optional[int] = Field(None, ge=1, le=5)
    expertise_rating: Optional[int] = Field(None, ge=1, le=5)
    time_spent_rating: Optional[int] = Field(None, ge=1, le=5)
    cleanliness_rating: Optional[int] = Field(None, ge=1, le=5)
    review_title: Optional[str] = Field(None, max_length=200)
    review_text: Optional[str] = Field(None, max_length=4000)


class DoctorReviewBase(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    appointment_id: int
    overall_rating: int
    communication_rating: Optional[int]
    expertise_rating: Optional[int]
    time_spent_rating: Optional[int]
    cleanliness_rating: Optional[int]
    review_title: Optional[str]
    review_text: Optional[str]
    is_verified: bool
    is_approved: bool
    helpful_count: int
    created_at: datetime

    class Config:
        from_attributes = True  # orm_mode=True for Pydantic v1


class DoctorReviewResponse(DoctorReviewBase):
    pass


class DoctorReviewListResponse(BaseModel):
    items: List[DoctorReviewResponse]
    total: int
    average_rating: Optional[float] = None


class ReviewModerationRequest(BaseModel):
    is_approved: bool
    moderation_notes: Optional[str] = None


# ---------------- Helpful Votes ----------------

class HelpfulVoteRequest(BaseModel):
    is_helpful: bool = True


class HelpfulVoteResponse(BaseModel):
    review_id: int
    helpful_count: int


# ---------------- Clinic Reviews ----------------

class ClinicReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    ambiance_rating: Optional[int] = Field(None, ge=1, le=5)
    staff_rating: Optional[int] = Field(None, ge=1, le=5)
    hygiene_rating: Optional[int] = Field(None, ge=1, le=5)
    review_title: Optional[str] = Field(None, max_length=200)
    review_text: Optional[str] = Field(None, max_length=4000)


class ClinicReviewBase(BaseModel):
    id: int
    clinic_id: int
    user_id: int
    rating: int
    ambiance_rating: Optional[int]
    staff_rating: Optional[int]
    hygiene_rating: Optional[int]
    review_title: Optional[str]
    review_text: Optional[str]
    is_verified: bool
    is_approved: bool
    helpful_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ClinicReviewResponse(ClinicReviewBase):
    pass


class ClinicReviewListResponse(BaseModel):
    items: List[ClinicReviewResponse]
    total: int
    average_rating: Optional[float] = None
