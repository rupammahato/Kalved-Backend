from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime


class OTPSendRequest(BaseModel):
    """Request to send OTP to email/phone"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=0, max_length=20)
    channel: str = Field("email", pattern="^(email|sms|both)$")

    @field_validator("channel")
    def validate_channel(cls, v, info):
        data = info.data if info and info.data else {}
        email = data.get("email")
        phone = data.get("phone")
        if v in ("email", "both") and not email:
            raise ValueError("email is required when channel is email/both")
        if v in ("sms", "both") and not phone:
            raise ValueError("phone is required when channel is sms/both")
        return v


class OTPVerifyRequest(BaseModel):
    """Request to verify OTP"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=0, max_length=20)
    otp_code: str = Field(..., min_length=6, max_length=6)

    @field_validator("otp_code")
    def require_contact(cls, v, info):
        data = info.data if info and info.data else {}
        if not data.get("email") and not data.get("phone"):
            raise ValueError("email or phone is required")
        return v


class EmailRegisterRequest(BaseModel):
    """Email/password registration request"""
    email: EmailStr
    phone: str = Field("", min_length=0, max_length=20)
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=2)
    last_name: str = Field(..., min_length=2)
    user_type: str = Field(..., pattern="^(doctor|patient)$")
    notification_channel: str = Field("email", pattern="^(email|sms|both)$")
    
    @field_validator('password')
    def password_strength(cls, v):
        """Password must contain uppercase, lowercase, digit, special char"""
        import re
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain digit')
        if not re.search(r'[!@#$%^&*]', v):
            raise ValueError('Password must contain special character')
        return v

    @field_validator("notification_channel")
    def validate_channel(cls, v, info):
        data = info.data if info and info.data else {}
        phone = data.get("phone")
        if v in ("sms", "both") and not phone:
            raise ValueError("phone is required when notification_channel is sms/both")
        return v

class LoginRequest(BaseModel):
    """Email/password login request"""
    email: EmailStr
    password: str


class GoogleOAuthRequest(BaseModel):
    """Google OAuth token verification"""
    id_token: str  # From NextAuth google provider
    access_token: str  # Optional


class TokenResponse(BaseModel):
    """Token response (access + refresh)"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user_id: int
    email: str
    user_type: str
    first_name: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token"""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Request to change password"""
    old_password: str
    new_password: str
    confirm_password: str
    
    @field_validator('confirm_password')
    def passwords_match(cls, v, info):
        new_password = info.data.get('new_password') if info and info.data else None
        if new_password and v != new_password:
            raise ValueError('Passwords must match')
        return v


class UserResponse(BaseModel):
    """User profile response"""
    id: int
    email: str
    phone: str
    first_name: Optional[str]
    last_name: Optional[str]
    profile_picture_url: Optional[str]
    city: Optional[str]
    state: Optional[str]
    user_type: str
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str

    @field_validator('confirm_password')
    def passwords_match(cls, v, info):
        new_password = info.data.get('new_password') if info and info.data else None
        if new_password and v != new_password:
            raise ValueError('Passwords must match')
        return v
