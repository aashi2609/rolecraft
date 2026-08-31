"""Central upload size/type limits and validation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from fastapi import HTTPException, UploadFile, status

UploadCategory = Literal["photo", "document"]

PHOTO_MAX_BYTES = 5 * 1024 * 1024
DOCUMENT_MAX_BYTES = 10 * 1024 * 1024

ALLOWED_PHOTO_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
ALLOWED_DOCUMENT_TYPES = frozenset({"application/pdf", "image/jpeg", "image/png"})

_MAX_BYTES: dict[UploadCategory, int] = {
    "photo": PHOTO_MAX_BYTES,
    "document": DOCUMENT_MAX_BYTES,
}

_ALLOWED_TYPES: dict[UploadCategory, frozenset[str]] = {
    "photo": ALLOWED_PHOTO_TYPES,
    "document": ALLOWED_DOCUMENT_TYPES,
}

_EXT_BY_MIME: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}

_EXT_TO_MIME: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}

_SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def sanitize_filename(filename: str) -> str:
    """Strip path components and unsafe characters from a client filename."""
    name = filename.replace("\x00", "").replace("\\", "/").split("/")[-1].strip()
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    safe = _SAFE_FILENAME_RE.sub("_", name)
    if not safe or safe.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return safe


def _detect_mime(data: bytes) -> str | None:
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 4 and data[:4] == b"%PDF":
        return "application/pdf"
    return None


def _reject_oversized(content_length: int | None, max_bytes: int) -> None:
    if content_length is not None and content_length > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {max_bytes // (1024 * 1024)} MB",
        )


async def _read_bounded(file: UploadFile, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {max_bytes // (1024 * 1024)} MB",
            )
        chunks.append(chunk)
    return b"".join(chunks)


async def validate_upload(
    file: UploadFile,
    category: UploadCategory,
    *,
    content_length: int | None = None,
) -> tuple[bytes, str, str]:
    """Validate and read an upload. Returns (data, safe_extension, detected_mime)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    safe_name = sanitize_filename(file.filename)

    max_bytes = _MAX_BYTES[category]
    allowed = _ALLOWED_TYPES[category]

    _reject_oversized(content_length, max_bytes)

    declared = (file.content_type or "").split(";")[0].strip().lower()
    if declared and declared not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{declared}' is not allowed for {category} uploads",
        )

    ext = Path(file.filename).suffix
    if ext and ext.lower() in _EXT_TO_MIME:
        ext_mime = _EXT_TO_MIME[ext.lower()]
        if declared and ext_mime != declared:
            raise HTTPException(status_code=400, detail="Filename extension does not match content type")

    data = await _read_bounded(file, max_bytes)
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    detected = _detect_mime(data)
    if not detected or detected not in allowed:
        raise HTTPException(
            status_code=400,
            detail="File content does not match an allowed type for this upload",
        )

    if declared and detected != declared:
        raise HTTPException(
            status_code=400,
            detail="Declared content type does not match file content",
        )

    if ext and ext.lower() in _EXT_TO_MIME and _EXT_TO_MIME[ext.lower()] != detected:
        raise HTTPException(status_code=400, detail="Filename extension does not match file content")

    return data, _EXT_BY_MIME[detected], detected
