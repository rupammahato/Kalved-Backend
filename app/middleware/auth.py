"""Lightweight JWT verification middleware.

This middleware performs a best-effort JWT validation and session check. Route-level
dependencies (`get_current_user`) still enforce auth; this middleware simply rejects
obviously bad tokens early and attaches the decoded payload to `request.state.auth`.
"""
from datetime import datetime, timezone
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.security import decode_token
from app.core.database import SessionLocal
from app.models.session import UserSession


class JWTMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return await call_next(request)

        scheme, _, token = auth_header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return JSONResponse(status_code=401, content={"detail": "Invalid authorization header"})

        payload = decode_token(token)
        if not payload:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        jti = payload.get("jti")
        user_id = payload.get("sub")
        if not jti or not user_id:
            return JSONResponse(status_code=401, content={"detail": "Invalid token payload"})

        db = SessionLocal()
        try:
            session = db.query(UserSession).filter(
                UserSession.user_id == int(user_id),
                UserSession.token_jti == jti,
                UserSession.is_revoked == False,
            ).first()

            if not session:
                return JSONResponse(status_code=401, content={"detail": "Token revoked or invalid"})

            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if session.expires_at and session.expires_at < now:
                return JSONResponse(status_code=401, content={"detail": "Token expired"})

            request.state.auth = payload
            response = await call_next(request)
            return response
        finally:
            db.close()
