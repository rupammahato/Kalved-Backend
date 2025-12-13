"""Request/response logging middleware."""
import logging
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.middleware.logging")


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"{request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response
