from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.user import User
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, generate_otp, decode_token,
    create_password_reset_token, decode_password_reset_token,
    hash_token, decode_refresh_token,
)
from app.core.config import settings
from app.services import email_service
from app.services import sms_service
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.utils.errors import (
    InvalidCredentialsError, UserNotFoundError, UserAlreadyExistsError,
    OTPExpiredError, InvalidOTPError, UserNotVerifiedError
)
from google.auth.transport import requests
from google.oauth2 import id_token
import logging

logger = logging.getLogger(__name__)

class AuthService:
    
    @staticmethod
    def register_with_email(
        db: Session,
        email: str,
        phone: str,
        password: str,
        first_name: str,
        last_name: str,
        user_type: str,  # 'doctor' or 'patient'
        notification_channel: str = "email",  # email | sms | both
    ) -> dict:
        """
        Step 1: Register user and send OTP
        - Create user with email_verified=False
        - Generate OTP and send via email
        """
        
        # Check if user already exists
        existing_user = db.query(User).filter(
            or_(User.email == email, User.phone == phone)
        ).first()
        
        if existing_user:
            if existing_user.email == email:
                raise UserAlreadyExistsError("Email already registered")
            raise UserAlreadyExistsError("Phone number already registered")
        
        # Create new user
        otp_code, otp_secret = generate_otp()
        now = datetime.now(timezone.utc)
        otp_expires_at = now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        new_user = User(
            email=email,
            phone=phone,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            user_type=user_type,
            status="pending",
            otp_code=otp_code,
            otp_secret=otp_secret,
            otp_sent_at=now.replace(tzinfo=None),
            otp_expires_at=otp_expires_at.replace(tzinfo=None),
            oauth_provider="email",
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Send OTP via selected channel(s)
        try:
            AuthService._send_otp_notifications(
                email=email,
                phone=phone,
                recipient_name=f"{first_name} {last_name}".strip(),
                otp_code=otp_code,
                channel=notification_channel,
            )
        except Exception as e:
            logger.error("Failed to send OTP notification", exc_info=e)
            raise Exception("Failed to send OTP. Please try again.")
        
        return {
            "user_id": new_user.id,
            "email": email,
            "message": "OTP sent. Please verify within 10 minutes."
        }
    
    @staticmethod
    def verify_otp(db: Session, email: str | None, otp_code: str, phone: str | None = None) -> dict:
        """
        Step 2: Verify OTP and confirm email
        - Validate OTP
        - Mark user as verified
        - Create doctor/patient profile based on user_type
        """
        
        query = db.query(User)
        user = None
        if email:
            user = query.filter(User.email == email).first()
        if not user and phone:
            user = query.filter(User.phone == phone).first()
        if not user:
            raise UserNotFoundError("User not found")
        
        # Check OTP expiry
        if user.otp_expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
            raise OTPExpiredError("OTP expired. Please request a new one.")
        
        # Check OTP attempts
        if user.otp_attempts >= settings.OTP_MAX_ATTEMPTS:
            user.status = "suspended"
            db.commit()
            raise InvalidOTPError(
                "Maximum OTP attempts exceeded. Account suspended. Contact support."
            )

        # Verify OTP using TOTP secret if present
        verified = False
        if user.otp_secret:
            try:
                import pyotp
                interval = max(30, settings.OTP_EXPIRE_MINUTES * 60)
                totp = pyotp.TOTP(user.otp_secret, digits=settings.OTP_LENGTH, interval=interval)
                verified = totp.verify(otp_code)
            except Exception:
                verified = False
        else:
            # Fallback to simple comparison
            verified = (user.otp_code == otp_code)

        if not verified:
            user.otp_attempts += 1
            db.commit()
            raise InvalidOTPError(f"Invalid OTP. {settings.OTP_MAX_ATTEMPTS - user.otp_attempts} attempts remaining.")
        
        # Mark as verified
        user.email_verified = True
        user.email_verified_at = datetime.now(timezone.utc).replace(tzinfo=None)
        user.otp_code = None
        user.otp_attempts = 0
        
        # Create doctor/patient profile based on user_type
        if user.user_type == "doctor":
            doctor = Doctor(user_id=user.id)
            db.add(doctor)
        elif user.user_type == "patient":
            patient = Patient(user_id=user.id)
            db.add(patient)
        
        db.commit()
        db.refresh(user)
        
        return {
            "user_id": user.id,
            "email": user.email,
            "message": "Email verified successfully. Please complete your profile."
        }
    
    @staticmethod
    def resend_otp(db: Session, email: str | None, phone: str | None, channel: str = "email") -> dict:
        """Resend OTP to chosen channel"""
        
        user_query = db.query(User)
        user = None
        if email:
            user = user_query.filter(User.email == email).first()
        if not user and phone:
            user = user_query.filter(User.phone == phone).first()
        if not user:
            raise UserNotFoundError("User not found")
        
        if user.email_verified:
            raise Exception("Email already verified")
        
        # Generate new OTP
        otp_code, otp_secret = generate_otp()
        now = datetime.now(timezone.utc)
        otp_expires_at = now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        user.otp_code = otp_code
        user.otp_secret = otp_secret
        user.otp_sent_at = now.replace(tzinfo=None)
        user.otp_expires_at = otp_expires_at.replace(tzinfo=None)
        user.otp_attempts = 0
        
        db.commit()
        
        # Send OTP
        try:
            AuthService._send_otp_notifications(
                email=user.email,
                phone=user.phone,
                recipient_name=f"{user.first_name} {user.last_name}".strip(),
                otp_code=otp_code,
                channel=channel,
            )
        except Exception as e:
            logger.error("Failed to send OTP notification", exc_info=e)
            raise Exception("Failed to send OTP. Please try again.")
        
        return {"message": "OTP resent"}
    
    @staticmethod
    def login(db: Session, email: str, password: str, ip_address: str, user_agent: str = "") -> dict:
        """
        Email/password login
        - Verify credentials
        - Create access & refresh tokens
        - Track session
        """
        
        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password_hash or ""):
            raise InvalidCredentialsError("Invalid email or password")
        
        if not user.email_verified:
            raise UserNotVerifiedError("Email not verified. Please verify OTP first.")
        
        if user.status == "suspended":
            raise Exception("Account suspended. Contact support.")
        
        if user.status == "pending" and settings.DOCTOR_APPROVAL_REQUIRED and user.user_type == "doctor":
            raise Exception("Doctor profile pending admin approval")
        
        # Create tokens
        access_token, access_jti = create_access_token(
            user_id=user.id,
            email=user.email,
            user_type=user.user_type,
        )
        refresh_token, refresh_jti = create_refresh_token(user.id)
        
        # Track session
        from app.models.session import UserSession
        now = datetime.now(timezone.utc)
        session = UserSession(
            user_id=user.id,
            token_jti=access_jti,
            refresh_jti=refresh_jti,
            refresh_token_hash=hash_token(refresh_token),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=now.replace(tzinfo=None) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            refresh_expires_at=now.replace(tzinfo=None) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(session)
        
        # Update last login
        user.last_login = now.replace(tzinfo=None)
        db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_id": user.id,
            "email": user.email,
            "user_type": user.user_type,
            "first_name": user.first_name,
        }

    @staticmethod
    def refresh_tokens(
        db: Session,
        refresh_token: str,
        ip_address: str,
        user_agent: str = "",
    ) -> dict:
        """
        Refresh access token using a valid refresh token with rotation.
        - Validate refresh JWT and session record
        - Rotate refresh token (new jti, hashed storage)
        - Issue new access token
        """

        payload = decode_refresh_token(refresh_token)
        if not payload:
            raise InvalidCredentialsError("Invalid refresh token")

        user_id = int(payload.get("sub"))
        refresh_jti = payload.get("jti")
        if not refresh_jti:
            raise InvalidCredentialsError("Invalid refresh token")

        from app.models.session import UserSession

        session = (
            db.query(UserSession)
            .filter(
                UserSession.user_id == user_id,
                UserSession.refresh_jti == refresh_jti,
                UserSession.is_revoked == False,
            )
            .first()
        )

        if not session:
            raise InvalidCredentialsError("Invalid or revoked refresh token")

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if session.refresh_expires_at and session.refresh_expires_at < now:
            session.is_revoked = True
            session.revoked_at = now
            session.revoked_reason = "refresh_expired"
            db.commit()
            raise InvalidCredentialsError("Refresh token expired")

        if session.refresh_token_hash != hash_token(refresh_token):
            session.is_revoked = True
            session.revoked_at = now
            session.revoked_reason = "refresh_mismatch"
            db.commit()
            raise InvalidCredentialsError("Invalid refresh token")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError("User not found")

        access_token, access_jti = create_access_token(
            user_id=user.id,
            email=user.email,
            user_type=user.user_type,
        )
        new_refresh_token, new_refresh_jti = create_refresh_token(user.id)

        # Rotate session tokens
        session.token_jti = access_jti
        session.refresh_jti = new_refresh_jti
        session.refresh_token_hash = hash_token(new_refresh_token)
        session.refresh_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        session.expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        session.ip_address = ip_address
        session.user_agent = user_agent
        session.is_revoked = False
        session.revoked_at = None
        session.revoked_reason = None

        user.last_login = now
        db.commit()

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_id": user.id,
            "email": user.email,
            "user_type": user.user_type,
            "first_name": user.first_name,
        }
    
    @staticmethod
    def verify_google_token(id_token_str: str, access_token: Optional[str] = None) -> dict:
        """
        Verify Google OAuth token from NextAuth
        - Validate token signature
        - Extract user info
        - Return decoded token data
        """
        
        try:
            # Verify token with Google's public keys
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
            
            return {
                "google_id": idinfo['sub'],
                "email": idinfo['email'],
                "first_name": idinfo.get('given_name', ''),
                "last_name": idinfo.get('family_name', ''),
                "profile_picture_url": idinfo.get('picture', ''),
            }
        except Exception as e:
            logger.error(f"Google token verification failed: {e}")
            raise Exception("Invalid Google token")
    
    @staticmethod
    def google_oauth_login(
        db: Session,
        id_token_str: str,
        user_type: str,
        ip_address: str,
        user_agent: str = "",
    ) -> dict:
        """
        Google OAuth login/register
        - Verify token
        - Find or create user
        - Return tokens
        """
        
        # Verify Google token
        google_data = AuthService.verify_google_token(id_token_str)
        google_id = google_data['google_id']
        email = google_data['email']
        
        # Find or create user
        user = db.query(User).filter(User.google_id == google_id).first()
        
        if not user:
            # Create new user
            user = User(
                google_id=google_id,
                email=email,
                phone="",  # Will be required later
                first_name=google_data['first_name'],
                last_name=google_data['last_name'],
                profile_picture_url=google_data['profile_picture_url'],
                user_type=user_type,
                email_verified=True,
                email_verified_at=datetime.now(timezone.utc).replace(tzinfo=None),
                oauth_provider="google",
                status="active",
            )
            db.add(user)
            
            # Create doctor/patient profile
            if user_type == "doctor":
                doctor = Doctor(user_id=user.id)
                db.add(doctor)
            elif user_type == "patient":
                patient = Patient(user_id=user.id)
                db.add(patient)
            
            db.commit()
            db.refresh(user)
        
        # Create tokens
        access_token, access_jti = create_access_token(
            user_id=user.id,
            email=user.email,
            user_type=user.user_type,
        )
        refresh_token, refresh_jti = create_refresh_token(user.id)
        
        # Track session
        from app.models.session import UserSession
        now = datetime.now(timezone.utc)
        session = UserSession(
            user_id=user.id,
            token_jti=access_jti,
            refresh_jti=refresh_jti,
            refresh_token_hash=hash_token(refresh_token),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=now.replace(tzinfo=None) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            refresh_expires_at=now.replace(tzinfo=None) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(session)
        
        user.last_login = now.replace(tzinfo=None)
        db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_id": user.id,
            "email": user.email,
            "user_type": user.user_type,
            "first_name": user.first_name,
            "requires_phone": not user.phone,  # Signal to frontend if phone needed
        }

    @staticmethod
    def send_password_reset(db: Session, email: str) -> dict:
        """Generate a password reset token for the given email and send an email."""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise UserNotFoundError("User not found")

        # Create reset token
        token, jti = create_password_reset_token(user.id, expires_minutes=30)

        # Build reset URL if frontend configured
        reset_url = getattr(settings, "FRONTEND_URL", None)
        try:
            email_service.send_password_reset_email(user.email, f"{user.first_name} {user.last_name}", token, reset_url)
        except Exception as e:
            logger.error("Failed to send password reset email", exc_info=e)
            raise Exception("Failed to send password reset email")

        return {"message": "Password reset email sent"}

    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> dict:
        """Reset the user's password using a password-reset token."""
        payload = decode_password_reset_token(token)
        if not payload:
            raise InvalidOTPError("Invalid or expired reset token")

        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError("User not found")

        # Update password
        user.password_hash = hash_password(new_password)
        db.commit()

        return {"message": "Password updated successfully"}

    @staticmethod
    def _send_otp_notifications(
        email: str | None,
        phone: str | None,
        recipient_name: str,
        otp_code: str,
        channel: str,
    ) -> None:
        """Dispatch OTP to configured channels."""
        errors = []

        if channel in ("email", "both"):
            if not email:
                errors.append("Email missing for email channel")
            else:
                try:
                    email_service.send_otp_email(email, recipient_name, otp_code)
                except Exception as exc:
                    errors.append(str(exc))

        if channel in ("sms", "both"):
            if not phone:
                errors.append("Phone missing for sms channel")
            else:
                try:
                    sms_service.send_otp_sms(phone, otp_code)
                except Exception as exc:
                    errors.append(str(exc))

        if errors:
            # If any channel failed, surface combined errors
            raise Exception("; ".join(errors))
