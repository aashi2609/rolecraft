"""Verify upload validation. Run: PYTHONPATH=. python -m pytest tests/security/test_uploads.py -v"""
from __future__ import annotations

import uuid

import httpx

BASE = "http://127.0.0.1:8000"


def _signup() -> str:
    uid = uuid.uuid4().hex[:8]
    r = httpx.post(
        f"{BASE}/auth/signup",
        json={"email": f"up_{uid}@t.com", "password": "testpass123", "role": "candidate", "name": "U"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def test_oversized_photo_rejected() -> None:
    tok = _signup()
    headers = {"Authorization": f"Bearer {tok}"}
    big = b"\xff\xd8\xff" + b"x" * (5 * 1024 * 1024 + 1)
    r = httpx.post(
        f"{BASE}/uploads/photo",
        headers=headers,
        files={"file": ("big.jpg", big, "image/jpeg")},
        timeout=30,
    )
    assert r.status_code in (400, 413), f"{r.status_code} {r.text[:80]}"


def test_fake_jpg_rejected_by_magic_bytes() -> None:
    tok = _signup()
    headers = {"Authorization": f"Bearer {tok}"}
    r = httpx.post(
        f"{BASE}/uploads/photo",
        headers=headers,
        files={"file": ("fake.jpg", b"not an image", "image/jpeg")},
        timeout=10,
    )
    assert r.status_code == 400, f"{r.status_code}"


def test_valid_png_accepted() -> None:
    tok = _signup()
    headers = {"Authorization": f"Bearer {tok}"}
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    r = httpx.post(
        f"{BASE}/uploads/photo",
        headers=headers,
        files={"file": ("ok.png", png, "image/png")},
        timeout=10,
    )
    assert r.status_code == 200, f"{r.status_code} {r.text[:80]}"


def test_traversal_filename_sanitized() -> None:
    tok = _signup()
    headers = {"Authorization": f"Bearer {tok}"}
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    r = httpx.post(
        f"{BASE}/uploads/photo",
        headers=headers,
        files={"file": ("../../../evil.png", png, "image/png")},
        timeout=10,
    )
    assert r.status_code == 200, f"{r.status_code}"
    path = r.json().get("path", "")
    assert ".." not in path and not path.startswith("/"), path
