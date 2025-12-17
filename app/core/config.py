import os
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

class Settings:
    ENV: str = os.getenv("ENV", "local")
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")
    EMAIL_BACKEND: str = os.getenv("EMAIL_BACKEND", "console")
    SMS_BACKEND: str = os.getenv("SMS_BACKEND", "console")

    # Database
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "False").lower() == "true"
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", 20))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", 10))

    # JWT / Security
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

    # OTP
    OTP_LENGTH: int = int(os.getenv("OTP_LENGTH", 6))
    OTP_EXPIRE_MINUTES: int = int(os.getenv("OTP_EXPIRE_MINUTES", 10))
    OTP_MAX_ATTEMPTS: int = int(os.getenv("OTP_MAX_ATTEMPTS", 3))

    # App identity / email
    APP_NAME: str = os.getenv("APP_NAME", "Kalved")
    SENDER_NAME: str = os.getenv("SENDER_NAME", "Kalved Team")

    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: Optional[int] = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URL: str = os.getenv("GOOGLE_REDIRECT_URL")
    
    # Frontend URLs
    FRONTEND_URL: str = os.getenv("FRONTEND_URL")

    # AWS S3
    AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET")
    AWS_REGION: str = os.getenv("AWS_REGION")
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")

    # CORS
    BACKEND_CORS_ORIGINS: Optional[str] = os.getenv("BACKEND_CORS_ORIGINS",)

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", 100))
    RATE_LIMIT_PERIOD_SECONDS: int = int(os.getenv("RATE_LIMIT_PERIOD_SECONDS", 60))

    # Admin
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL")

    # Role-based Access
    DOCTOR_APPROVAL_REQUIRED: bool = (os.getenv("DOCTOR_APPROVAL_REQUIRED", "True").lower() == "true")

    # SMS (Twilio)
    TWILIO_ACCOUNT_SID: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_FROM_NUMBER: Optional[str] = os.getenv("TWILIO_FROM_NUMBER")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")



settings = Settings()
