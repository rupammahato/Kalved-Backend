from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import pyotp
import hashlib
import hmac
from app.core.config import settings

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)
def hash_password(password: str) -> str:
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    if not isinstance(plain_password, str):
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def _create_jwt(payload: Dict[str, Any], expires_delta: timedelta) -> tuple[str, str]:
    expire = datetime.now(timezone.utc) + expires_delta
    jti = secrets.token_urlsafe(32)

    payload.update({
        "exp": expire,
        "jti": jti,
    })

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return token, jti


def create_access_token(
    user_id: int,
    email: str,
    user_type: str,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, str]:
    return _create_jwt(
        payload={
            "sub": str(user_id),
            "email": email,
            "user_type": user_type,
        },
        expires_delta=expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> tuple[str, str]:
    return _create_jwt(
        payload={
            "sub": str(user_id),
            "type": "refresh",
        },
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def create_password_reset_token(
    user_id: int,
    expires_minutes: int = 30,
) -> tuple[str, str]:
    return _create_jwt(
        payload={
            "sub": str(user_id),
            "type": "password_reset",
        },
        expires_delta=timedelta(minutes=expires_minutes),
    )

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    payload = decode_token(token)
    if payload and payload.get("type") == "refresh":
        return payload
    return None


def decode_password_reset_token(token: str) -> Optional[Dict[str, Any]]:
    payload = decode_token(token)
    if payload and payload.get("type") == "password_reset":
        return payload
    return None

def generate_otp() -> tuple[str, str]:
    secret = pyotp.random_base32()
    interval = max(30, settings.OTP_EXPIRE_MINUTES * 60)
    totp = pyotp.TOTP(secret, digits=settings.OTP_LENGTH, interval=interval)
    return totp.now(), secret


def verify_otp(stored_otp: str, provided_otp: str) -> bool:
    if not stored_otp or not provided_otp:
        return False
    return hmac.compare_digest(stored_otp, provided_otp)
