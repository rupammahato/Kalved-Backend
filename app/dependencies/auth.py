from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.session import UserSession

security = HTTPBearer()

def get_current_user_from_token(
    token: str,
    db: Session,
):
    """
    Verify JWT token string (for WebSockets) and return current user.
    """
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    user_id = int(payload.get("sub"))
    jti = payload.get("jti")
    
    # Check if token is revoked
    session = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.token_jti == jti,
        UserSession.is_revoked == False,
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked or invalid",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if session.expires_at and session.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return {
        **payload,
        "jti": jti,
    }

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Verify JWT token and return current user"""
    return get_current_user_from_token(credentials.credentials, db)

async def get_current_doctor(
    current_user = Depends(get_current_user),
):
    """Verify current user is a doctor"""
    if current_user.get("user_type") != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can access this resource",
        )
    return current_user

async def get_current_admin(
    current_user = Depends(get_current_user),
):
    """Verify current user is an admin"""
    if current_user.get("user_type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def get_current_patient(
    current_user = Depends(get_current_user),
):
    """Verify current user is a patient"""
    if current_user.get("user_type") != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access this resource",
        )
    return current_user
