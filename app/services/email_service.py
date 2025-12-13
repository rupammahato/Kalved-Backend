import smtplib
import logging
from email.message import EmailMessage
from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body: str, html: str | None = None) -> bool:
    smtp_host = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT
    smtp_user = settings.SMTP_USER
    smtp_pass = settings.SMTP_PASSWORD

    if not smtp_user or not smtp_pass:
        raise Exception("SMTP credentials not configured (SMTP_USER / SMTP_PASSWORD)")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{settings.SENDER_NAME} <{smtp_user}>"
    msg["To"] = to_email
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.ehlo()
            if smtp_port == 587:
                server.starttls()
                server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.exception("Failed to send email")
        raise


def send_otp_email(to_email: str, recipient_name: str, otp_code: str) -> bool:
    """Convenience helper to send OTP emails.

    Builds a basic subject and body and sends via configured SMTP server.
    """
    subject = f"Your verification code for {settings.APP_NAME}"
    body = (
        f"Hi {recipient_name},\n\n"
        f"Your verification code is: {otp_code}\n\n"
        f"This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.\n\n"
        "If you did not request this, please ignore this email.\n\n"
        f"— {settings.SENDER_NAME}"
    )
    html = (
        f"<p>Hi {recipient_name},</p>"
        f"<p>Your verification code is: <strong>{otp_code}</strong></p>"
        f"<p>This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.</p>"
        f"<p>If you did not request this, please ignore this email.</p>"
        f"<br/><p>— {settings.SENDER_NAME}</p>"
    )

    return send_email(to_email, subject, body, html)


def send_password_reset_email(to_email: str, recipient_name: str, reset_token: str, reset_url: str | None = None) -> bool:
    """Send password reset email. If `reset_url` supplied it will be used as the clickable link; otherwise token is included."""
    subject = f"Reset your {settings.APP_NAME} password"
    if reset_url:
        link = f"{reset_url.rstrip('/')}/?token={reset_token}"
        body = (
            f"Hi {recipient_name},\n\n"
            f"Click the link below to reset your password:\n{link}\n\n"
            f"If you did not request a password reset, please ignore this email.\n\n"
            f"— {settings.SENDER_NAME}"
        )
        html = (
            f"<p>Hi {recipient_name},</p>"
            f"<p>Click the link below to reset your password:</p>"
            f"<p><a href=\"{link}\">Reset password</a></p>"
            f"<p>If you did not request a password reset, please ignore this email.</p>"
            f"<br/><p>— {settings.SENDER_NAME}</p>"
        )
    else:
        body = (
            f"Hi {recipient_name},\n\n"
            f"Use the following token to reset your password:\n\n{reset_token}\n\n"
            f"This token expires in a short time.\n\n"
            f"— {settings.SENDER_NAME}"
        )
        html = None

    return send_email(to_email, subject, body, html)


class EmailService:
    async def send_otp(self, to_email: str, otp: str) -> bool:
        return send_otp_email(to_email, "", otp)

    async def send_email(self, to_email: str, subject: str, body: str) -> bool:
        return send_email(to_email, subject, body)
