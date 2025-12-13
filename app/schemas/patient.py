"""Patient schemas."""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date


class PatientProfileUpdate(BaseModel):
    date_of_birth: Optional[date]
    gender: Optional[str]
    blood_group: Optional[str]
    medical_history: Optional[str]
    allergies: Optional[str]
    medications: Optional[str]
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    pincode: Optional[str]
    country: Optional[str]


class PatientRead(PatientProfileUpdate):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
