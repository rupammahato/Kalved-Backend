"""Application constants such as user roles and types."""
from enum import Enum


class UserRole(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"


class UserStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
