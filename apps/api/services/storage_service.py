"""File storage — local disk in development, GCS in production."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from core.config import get_settings

settings = get_settings()
LOCAL_ROOT = Path(__file__).resolve().parent.parent / "uploads"


async def upload_file(file: UploadFile, *, prefix: str, owner_id: str) -> tuple[str, str]:
    """
    Returns (public_url, storage_path).
    prefix examples: photos/{user_id}, documents/{candidate_id}, logos/{company_id}
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    ext = Path(file.filename).suffix or ".bin"
    object_name = f"{prefix}/{owner_id}/{uuid.uuid4().hex}{ext}"
    data = await file.read()

    if settings.storage_backend == "gcs":
        return _upload_gcs(object_name, data, file.content_type)
    return _upload_local(object_name, data)


def _upload_local(object_name: str, data: bytes) -> tuple[str, str]:
    dest = LOCAL_ROOT / object_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    # Served via /static mounts in main.py
    url = f"/static/{object_name}"
    return url, object_name


def _upload_gcs(object_name: str, data: bytes, content_type: str | None) -> tuple[str, str]:
    try:
        from google.cloud import storage
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="google-cloud-storage not installed") from exc

    client = storage.Client(project=settings.gcs_project_id or None)
    bucket = client.bucket(settings.gcs_bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_string(data, content_type=content_type or "application/octet-stream")
    try:
        blob.make_public()
        url = blob.public_url
    except Exception:
        url = blob.generate_signed_url(expiration=60 * 60 * 24 * 7, method="GET")
    return url, object_name
