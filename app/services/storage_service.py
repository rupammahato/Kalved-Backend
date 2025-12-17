import os
import uuid
from typing import Optional

import boto3
from fastapi import UploadFile

from app.core.config import settings


def _get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=settings.AWS_REGION or os.getenv("AWS_REGION", "ap-south-1"),
    )


async def upload_chat_attachment(file: UploadFile, folder: str = "chat") -> str:
    """
    Uploads file to S3 and returns public URL (or key).
    """
    s3 = _get_s3_client()
    bucket = settings.AWS_S3_BUCKET or os.getenv("AWS_S3_BUCKET")
    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    key = f"{folder}/{uuid.uuid4().hex}{ext}"

    # Reset pointer before upload
    await file.seek(0)
    # Using underlying file object for upload_fileobj if it's a SpooledTemporaryFile
    # file.file is the BinaryIO
    s3.upload_fileobj(file.file, bucket, key)
    
    # base_url could be a cloudfront url or similar
    # In settings we seem to not have AWS_PUBLIC_BASE_URL, but let's assume standard logic or check config again
    # The config file didn't show AWS_PUBLIC_BASE_URL. Let's return the s3:// path or standard http url
    
    # Standard S3 URL construction
    return f"https://{bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
