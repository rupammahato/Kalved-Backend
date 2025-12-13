"""Custom validators (placeholder)."""
from pydantic import EmailStr


def validate_email(value: str) -> EmailStr:
    return EmailStr.validate(value)
