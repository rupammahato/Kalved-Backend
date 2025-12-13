"""Helper utilities (OTP generation, responses, request helpers)."""
import pyotp
from fastapi import Request


def generate_otp(length: int = 6) -> tuple[str, str]:
    """Generate a TOTP secret and current code.

    Returns a tuple of (otp_code, secret) so callers can store the secret.
    """
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret, digits=length)
    return totp.now(), secret


def format_response(data=None, success=True):
    return {"success": success, "data": data}


def get_client_ip(request: Request) -> str:
    """Return client's IP address from request headers or connection info.

    Checks `X-Forwarded-For` first (comma-separated), then falls back to
    `request.client.host`. Returns 'unknown' if not found.
    """
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        # X-Forwarded-For can contain a list of IPs
        return x_forwarded_for.split(",")[0].strip()

    client = getattr(request, "client", None)
    if client and getattr(client, "host", None):
        return client.host

    return "unknown"
