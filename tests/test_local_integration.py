
import os
import shutil
import pytest
from unittest.mock import MagicMock
from fastapi import UploadFile
from pathlib import Path

from app.core.config import settings
from app.services.storage_service import upload_chat_attachment
from app.services.email_service import send_email
from app.services.sms_service import send_sms_message

# We use this to prevent actual S3/SMTP/Twilio calls even if logic fails, 
# although the logic should catch it.

@pytest.fixture
def mock_upload_file(tmp_path):
    filename = "test_image.png"
    file_path = tmp_path / filename
    with open(file_path, "wb") as f:
        f.write(b"fake image content")
        
    # Create a mock generic generic file-like object
    file_obj = open(file_path, "rb")
    
    upload_file = UploadFile(file=file_obj, filename=filename)
    yield upload_file
    file_obj.close()


@pytest.mark.asyncio
async def test_local_storage_upload(mock_upload_file, monkeypatch):
    """Test that setting STORAGE_BACKEND='local' saves to local disk."""
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    
    # Ensure clean slate for uploads dir in test environment
    # We might want to use a temp dir for uploads instead of real 'uploads'
    # but for this specific test let's just use the current directory logic 
    # but verify the file exists.
    # To be safe, let's patch the hardcoded "uploads" path in the service 
    # if possible, or just accept it creates "uploads/chat" in the repo root.
    # For now, we will check if the file appears in uploads/chat.
    
    result_path = await upload_chat_attachment(mock_upload_file, folder="chat")
    
    assert result_path.startswith("/static/chat/")
    
    # Verify file exists on disk
    # The service code uses: Path("uploads") / folder / name
    # "uploads" is relative to CWD.
    filename = result_path.split("/")[-1]
    local_path = Path("uploads") / "chat" / filename
    
    assert local_path.exists()
    
    # Cleanup
    if local_path.exists():
        os.remove(local_path)
    # Optional: remove dir if empty
    try:
        os.rmdir(Path("uploads") / "chat")
    except:
        pass


def test_console_email_backend(monkeypatch, caplog):
    """Test that EMAIL_BACKEND='console' logs the email."""
    monkeypatch.setattr(settings, "EMAIL_BACKEND", "console")
    
    import logging
    caplog.set_level(logging.INFO)
    
    to_email = "test@example.com"
    subject = "Hello World"
    body = "This is a test email."
    
    result = send_email(to_email, subject, body)
    
    assert result is True
    assert "[EMAIL]" in caplog.text
    assert f"to={to_email}" in caplog.text
    assert f"subject={subject}" in caplog.text
    assert body in caplog.text


def test_console_sms_backend(monkeypatch, caplog):
    """Test that SMS_BACKEND='console' logs the SMS."""
    monkeypatch.setattr(settings, "SMS_BACKEND", "console")
    
    import logging
    caplog.set_level(logging.INFO)
    
    to_number = "+15550000000"
    body = "Test SMS"
    
    result = send_sms_message(to_number, body)
    
    assert result is True
    assert "[SMS]" in caplog.text
    assert f"to={to_number}" in caplog.text
    assert body in caplog.text
