"""User request/response schemas."""
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str]


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: str
    is_active: bool
    role: str

    model_config = ConfigDict(from_attributes=True)
