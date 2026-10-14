"""File storage — local disk in development, GCS in production.

Uploaded files are NEVER made public. Instead, every upload creates a
FileRecord row and the file is served through the authenticated
GET /files/{file_id} endpoint.

Company logos are the only exception: they use a ``logos/`` prefix and are
served from a separate, public-by-design path.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.upload_limits import UploadCategory, validate_upload

settings = get_settings()
LOCAL_ROOT = Path(__file__).resolve().parent.parent / "uploads"

# ── Public logo prefix ──────────────────────────────────────────────────────
# Company logos are intentionally public because they appear on unauthenticated
# job listing and company profile pages.  They are stored under a distinct
# ``logos/`` prefix so we can allow public reads for that prefix only.
LOGO_PREFIX = "logos"


async def upload_file(
    file: UploadFile,
    *,
    prefix: str,
    owner_id: str,
    category: UploadCategory,
    content_length: int | None = None,
    db: AsyncSession | None = None,
) -> tuple[str, str, str | None]:
    """Upload a file and register it in the database.

    Returns (file_endpoint_url, storage_path, file_id).
    ``file_id`` is None only when ``db`` is not provided (should not happen
    in production).
    """
    data, ext, detected_mime = await validate_upload(
        file, category, content_length=content_length
    )

    # Never use client filename in storage path — uuid + validated extension only.
    object_name = f"{prefix}/{uuid.uuid4().hex}{ext}"
    _assert_safe_object_path(object_name)

    if settings.storage_backend == "gcs":
        _upload_gcs(object_name, data, detected_mime)
    else:
        _upload_local(object_name, data)

    # Persist a FileRecord so the authenticated /files/ endpoint can serve it.
    file_id: str | None = None
    if db is not None:
        from models import FileCategory, FileRecord

        cat_map = {"photo": FileCategory.photo, "document": FileCategory.document}
        is_logo = object_name.startswith(LOGO_PREFIX + "/")
        fr = FileRecord(
            owner_id=owner_id,
            category=FileCategory.logo if is_logo else cat_map.get(category, FileCategory.document),
            storage_path=object_name,
            original_filename=file.filename,
            mime_type=detected_mime,
        )
        db.add(fr)
        await db.flush()
        file_id = str(fr.id)

    # Return the API-served URL (not a static path).
    if file_id:
        url = f"/files/logo/{file_id}" if is_logo else f"/files/{file_id}"
    else:
        # Fallback: return storage path (should not happen with proper db usage).
        url = object_name
    return url, object_name, file_id


def _assert_safe_object_path(object_name: str) -> None:
    """Ensure the resolved path stays under LOCAL_ROOT."""
    dest = (LOCAL_ROOT / object_name).resolve()
    root = LOCAL_ROOT.resolve()
    if not str(dest).startswith(str(root)):
        raise HTTPException(status_code=400, detail="Invalid upload path")


def _upload_local(object_name: str, data: bytes) -> None:
    dest = LOCAL_ROOT / object_name
    _assert_safe_object_path(object_name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def _upload_gcs(
    object_name: str, data: bytes, content_type: str | None
) -> None:
    try:
        from google.cloud import storage
    except ImportError as exc:
        raise HTTPException(
            status_code=500, detail="google-cloud-storage not installed"
        ) from exc

    client = storage.Client(project=settings.gcs_project_id or None)
    bucket = client.bucket(settings.gcs_bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_string(
        data, content_type=content_type or "application/octet-stream"
    )
    # NEVER call blob.make_public() — files are private.
    # Signed URLs are generated at request time in the /files/ endpoint.


def get_local_file_path(storage_path: str) -> Path:
    """Resolve a storage_path to a local filesystem Path, safely."""
    dest = (LOCAL_ROOT / storage_path).resolve()
    root = LOCAL_ROOT.resolve()
    if not str(dest).startswith(str(root)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return dest


def generate_signed_url(storage_path: str, expiration_seconds: int = 300) -> str:
    """Generate a short-lived GCS signed URL (default 5 minutes)."""
    try:
        from google.cloud import storage
    except ImportError as exc:
        raise HTTPException(
            status_code=500, detail="google-cloud-storage not installed"
        ) from exc

    client = storage.Client(project=settings.gcs_project_id or None)
    bucket = client.bucket(settings.gcs_bucket_name)
    blob = bucket.blob(storage_path)
    return blob.generate_signed_url(
        expiration=expiration_seconds,
        method="GET",
    )
