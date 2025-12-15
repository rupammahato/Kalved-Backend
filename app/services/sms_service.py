import logging

from twilio.base.exceptions import TwilioException
from twilio.rest import Client

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_client() -> Client:
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        raise Exception("Twilio not configured (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN)")
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def send_sms(to_phone: str, message: str) -> bool:
    """Send a text message via Twilio."""
    if not settings.TWILIO_FROM_NUMBER:
        raise Exception("Twilio sender number missing (TWILIO_FROM_NUMBER)")

    client = _get_client()
    try:
        client.messages.create(
            body=message,
            from_=settings.TWILIO_FROM_NUMBER,
            to=to_phone,
        )
        return True
    except TwilioException as exc:
        logger.exception("Failed to send SMS via Twilio")
        raise Exception("Failed to send SMS") from exc


def send_otp_sms(to_phone: str, otp_code: str) -> bool:
    """Convenience helper to send OTP code via SMS."""
    message = (
        f"Your {settings.APP_NAME} verification code is {otp_code}. "
        f"It expires in {settings.OTP_EXPIRE_MINUTES} minutes."
    )
    return send_sms(to_phone, message)

