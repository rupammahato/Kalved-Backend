# app/services/sms_service.py
import os
from typing import Optional
import logging

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.core.config import settings

logger = logging.getLogger(__name__)

def _get_client() -> Client:
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None) or os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None) or os.getenv("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        # Check if we should warn or if execution handles it gracefully later
        pass # Client init might fail if used, handled in send_sms_message
    return Client(account_sid, auth_token)


def send_sms_message(
    to_number: str,
    body: str,
    from_number: Optional[str] = None,
) -> bool:
    """
    Send a transactional SMS.
    Returns True if successful, False otherwise.
    """
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None) or os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None) or os.getenv("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        logger.warning("Twilio credentials not configured. Skipping SMS.")
        return False

    if not from_number:
        from_number = getattr(settings, "TWILIO_PHONE_NUMBER", None) or os.getenv("TWILIO_PHONE_NUMBER")

    if not to_number or not from_number:
        logger.warning(f"Missing phone numbers. To: {to_number}, From: {from_number}")
        return False

    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            to=to_number,
            from_=from_number,
            body=body,
        )
        logger.info(f"SMS sent to {to_number}. SID: {message.sid}")
        return True
    except TwilioRestException as e:
        logger.error(f"Twilio error sending SMS to {to_number}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending SMS to {to_number}: {e}")
        return False

def send_otp_sms(to_phone: str, otp_code: str) -> bool:
    """Convenience helper to send OTP code via SMS."""
    # Using getattr with default fallback to avoid attribute errors if setting is missing
    app_name = getattr(settings, "APP_NAME", "Kalved")
    expire_min = getattr(settings, "OTP_EXPIRE_MINUTES", 10)
    
    message = (
        f"Your {app_name} verification code is {otp_code}. "
        f"It expires in {expire_min} minutes."
    )
    return send_sms_message(to_phone, message)
