from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.auth import (
    OTPSendRequest, OTPVerifyRequest, EmailRegisterRequest,
    LoginRequest, GoogleOAuthRequest, TokenResponse
)
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest, RefreshTokenRequest
from app.services.auth_service import AuthService
from app.utils.errors import (
    InvalidCredentialsError, UserNotFoundError, UserAlreadyExistsError,
    OTPExpiredError, InvalidOTPError, UserNotVerifiedError
)
from app.dependencies.auth import get_current_user
from app.dependencies.rate_limit import rate_limit
from app.utils.helpers import get_client_ip
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/send-otp", status_code=200)
async def send_otp(
    request: OTPSendRequest,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit),
):
    """
    Step 1: Send OTP to email
    - User provides email
    - System generates OTP and sends via email
    """
    try:
        result = AuthService.register_with_email(
            db=db,
            email=request.email,
            phone="",
            password="",
            first_name="",
            last_name="",
            user_type="",
        )
        return {
            "success": True,
            "data": result,
        }
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/register", status_code=201)
async def register(
    request: EmailRegisterRequest,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit),
):
    """
    Complete registration with email/password
    - Validate inputs
    - Create user
    - Send OTP
    """
    try:
        result = AuthService.register_with_email(
            db=db,
            email=request.email,
            phone=request.phone,
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name,
            user_type=request.user_type,
        )
        return {
            "success": True,
            "data": result,
        }
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/forgot-password", status_code=200)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit),
):
    """Request a password reset email."""
    try:
        result = AuthService.send_password_reset(db=db, email=request.email)
        return {"success": True, "data": result}
    except UserNotFoundError as e:
        # Don't reveal whether email exists in production — mirror typical behavior
        return {"success": True, "data": {"message": "If the email exists, a reset link was sent."}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reset-password", status_code=200)
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit),
):
    """Reset password using token sent to email."""
    try:
        result = AuthService.reset_password(db=db, token=request.token, new_password=request.new_password)
        return {"success": True, "data": result}
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
@router.post("/verify-otp", status_code=200)
async def verify_otp(
    request: OTPVerifyRequest,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit),
):
    """
    Verify OTP and complete email verification
    - Validate OTP
    - Mark user as verified
    - Create doctor/patient profile
    """
    try:
        result = AuthService.verify_otp(
            db=db,
            email=request.email,
            otp_code=request.otp_code,
        )
        return {
            "success": True,
            "data": result,
        }
    except (OTPExpiredError, InvalidOTPError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/resend-otp", status_code=200)
async def resend_otp(
    request: OTPSendRequest,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit),
):
    """Resend OTP to email"""
    try:
        result = AuthService.resend_otp(db=db, email=request.email)
        return {
            "success": True,
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=TokenResponse, status_code=200)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit),
):
    """
    Email/password login
    - Verify credentials
    - Return JWT tokens
    """
    try:
        ip_address = get_client_ip(http_request)
        user_agent = http_request.headers.get("user-agent", "") if http_request else ""
        result = AuthService.login(
            db=db,
            email=request.email,
            password=request.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return result
    except (InvalidCredentialsError, UserNotVerifiedError) as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/google", response_model=TokenResponse, status_code=200)
async def google_oauth(
    request: GoogleOAuthRequest,
    user_type: str = "patient",  # Query param: 'doctor' or 'patient'
    http_request: Request = None,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit),
):
    """
    Google OAuth login/register
    - Verify Google token from NextAuth
    - Create or retrieve user
    - Return JWT tokens
    """
    try:
        ip_address = get_client_ip(http_request)
        user_agent = http_request.headers.get("user-agent", "") if http_request else ""
        result = AuthService.google_oauth_login(
            db=db,
            id_token_str=request.id_token,
            user_type=user_type,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh", response_model=TokenResponse, status_code=200)
async def refresh_tokens(
    request: RefreshTokenRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit),
):
    """Exchange a valid refresh token for a new access + refresh token pair (rotation)."""
    try:
        ip_address = get_client_ip(http_request)
        user_agent = http_request.headers.get("user-agent", "") if http_request else ""
        result = AuthService.refresh_tokens(
            db=db,
            refresh_token=request.refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return result
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/logout", status_code=200)
async def logout(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit),
):
    """Logout user (revoke current session)"""
    try:
        from app.models.session import UserSession
        
        session = db.query(UserSession).filter(
            UserSession.user_id == current_user['sub'],
            UserSession.token_jti == current_user['jti'],
        ).first()
        
        if session:
            session.is_revoked = True
            session.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
            session.revoked_reason = "logout"
            session.refresh_token_hash = ""
            db.commit()
        
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
