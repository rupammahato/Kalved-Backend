from datetime import date, datetime, time
from typing import Optional, List

from pydantic import BaseModel, Field


class AppointmentSlotBase(BaseModel):
    id: int
    clinic_id: int
    doctor_id: int
    slot_start: datetime
    slot_end: datetime
    slot_date: date
    slot_status: str

    class Config:
        from_attributes = True  # Pydantic v2 (Use orm_mode=True for v1)


class AvailableSlotResponse(BaseModel):
    slot_id: int
    start_time: datetime
    end_time: datetime
    available: bool = True


class AppointmentBookRequest(BaseModel):
    slot_id: int = Field(..., description="ID of the AppointmentSlot to book")
    appointment_type: Optional[str] = Field(
        default="consultation", description="consultation, follow-up, treatment, etc."
    )
    reason_for_visit: Optional[str] = Field(default=None, max_length=2000)


class AppointmentCancelRequest(BaseModel):
    cancellation_reason: str = Field(..., min_length=3, max_length=2000)


class AppointmentConfirmResponse(BaseModel):
    appointment_id: int
    status: str
    message: str


class AppointmentBasic(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    clinic_id: int
    appointment_date: date
    appointment_time: time
    status: str
    is_confirmed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AppointmentDetail(AppointmentBasic):
    appointment_start: datetime
    appointment_end: datetime
    appointment_type: Optional[str] = None
    reason_for_visit: Optional[str] = None
    appointment_notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    doctor_notes: Optional[str] = None
    completed_at: Optional[datetime] = None


class AppointmentListResponse(BaseModel):
    items: List[AppointmentDetail]
    total: int


class AppointmentBookResponse(BaseModel):
    appointment_id: int
    status: str
    appointment_date: date
    appointment_time: time
    message: str
