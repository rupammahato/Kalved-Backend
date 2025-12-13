"""Clinic related schemas."""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import time


class ClinicTiming(BaseModel):
    day: str
    open_time: Optional[time]
    close_time: Optional[time]
    notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ClinicBase(BaseModel):
    name: str
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    pincode: Optional[str]
    country: Optional[str]
    phone: Optional[str]
    latitude: Optional[str]
    longitude: Optional[str]
    timings: Optional[List[ClinicTiming]] = None


class ClinicRead(ClinicBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
