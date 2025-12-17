"""Doctor schemas."""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import date, time


class DoctorQualificationCreate(BaseModel):
    degree_name: Optional[str]
    institution: Optional[str]
    country: Optional[str]
    year_of_graduation: Optional[int]


class ClinicTimingCreate(BaseModel):
    day: str = Field(..., pattern="^(MON|TUE|WED|THU|FRI|SAT|SUN)$")
    open_time: Optional[time]
    close_time: Optional[time]
    notes: Optional[str]

    @field_validator("close_time")
    def validate_time_order(cls, v, info):
        open_time = info.data.get("open_time") if info and info.data else None
        if v and open_time and v <= open_time:
            raise ValueError("close_time must be after open_time")
        return v


class ClinicCreate(BaseModel):
    name: str
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    pincode: Optional[str]
    country: Optional[str]
    phone: Optional[str]
    latitude: Optional[str]
    longitude: Optional[str]
    timings: Optional[List[ClinicTimingCreate]] = None


class DoctorProfileUpdate(BaseModel):
    brc_number: Optional[str]
    brc_issued_date: Optional[date]
    brc_valid_until: Optional[date]
    years_of_experience: Optional[int] = Field(None, ge=0)
    specializations: Optional[List[str]]
    languages: Optional[List[str]]
    default_consultation_fee: Optional[int] = Field(None, ge=0)
    identity_proof_url: Optional[str]
    clinic_registration_certificate: Optional[str]
    gst_number: Optional[str]
    qualifications: Optional[List[DoctorQualificationCreate]] = None


class DoctorRead(BaseModel):
    id: int
    user_id: int
    brc_number: Optional[str]
    brc_verification_status: Optional[str]
    years_of_experience: Optional[int]
    specializations: Optional[List[str]]
    languages: Optional[List[str]]
    default_consultation_fee: Optional[int]
    average_rating: Optional[float] = None
    total_reviews: int = 0
    clinics: Optional[list] = None
    qualifications: Optional[list] = None

    model_config = ConfigDict(from_attributes=True)
