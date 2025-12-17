import os
import uuid
from typing import Optional

import boto3
from fastapi import UploadFile

from app.core.config import settings



from pathlib import Path
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
    if settings.STORAGE_BACKEND == "local":
        return await _upload_local(file, folder)
    return await _upload_s3(file, folder)


async def _upload_local(file: UploadFile, folder: str) -> str:
    base_dir = Path("uploads") / folder
    base_dir.mkdir(parents=True, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1]
    name = f"{uuid.uuid4().hex}{ext}"
    path = base_dir / name

    contents = await file.read()
    with path.open("wb") as f:
        f.write(contents)
    await file.close()

    # Return a URL path your frontend can serve via static files
    return f"/static/{folder}/{name}"


async def _upload_s3(file: UploadFile, folder: str) -> str:
    s3 = _get_s3_client()
    bucket = settings.AWS_S3_BUCKET or os.getenv("AWS_S3_BUCKET")
    ext = os.path.splitext(file.filename or "")[1]
    key = f"{folder}/{uuid.uuid4().hex}{ext}"

    # Reset pointer before upload
    await file.seek(0)
    # Using underlying file object for upload_fileobj if it's a SpooledTemporaryFile
    # file.file is the BinaryIO
    s3.upload_fileobj(file.file, bucket, key)
    await file.close()

    base_url = getattr(settings, "AWS_PUBLIC_BASE_URL", None)
    if base_url:
        return f"{base_url}/{key}"
    
    # Standard S3 URL construction
    return f"https://{bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

