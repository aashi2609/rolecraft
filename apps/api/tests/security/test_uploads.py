"""Verify upload validation. Run: PYTHONPATH=. python -m pytest tests/security/test_uploads.py -v"""

from __future__ import annotations

import uuid
from fastapi.testclient import TestClient


def _signup(client: TestClient) -> str:
    uid = uuid.uuid4().hex[:8]
    r = client.post(
        "/auth/signup",
        json={
            "email": f"up_{uid}@t.com",
            "password": "testpass123A",
            "role": "candidate",
            "name": "U",
        },
    )
    assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def test_oversized_photo_rejected(client: TestClient) -> None:
    tok = _signup(client)
    headers = {"Authorization": f"Bearer {tok}"}
    big = b"\xff\xd8\xff" + b"x" * (5 * 1024 * 1024 + 1)
    r = client.post(
        "/uploads/photo",
        headers=headers,
        files={"file": ("big.jpg", big, "image/jpeg")},
    )
    assert r.status_code in (400, 413), f"{r.status_code} {r.text[:80]}"


def test_fake_jpg_rejected_by_magic_bytes(client: TestClient) -> None:
    tok = _signup(client)
    headers = {"Authorization": f"Bearer {tok}"}
    r = client.post(
        "/uploads/photo",
        headers=headers,
        files={"file": ("fake.jpg", b"not an image", "image/jpeg")},
    )
    assert r.status_code == 400, f"{r.status_code}"


def test_valid_png_accepted(client: TestClient) -> None:
    tok = _signup(client)
    headers = {"Authorization": f"Bearer {tok}"}
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    r = client.post(
        "/uploads/photo",
        headers=headers,
        files={"file": ("ok.png", png, "image/png")},
    )
    assert r.status_code == 200, f"{r.status_code} {r.text[:80]}"


def test_traversal_filename_sanitized(client: TestClient) -> None:
    tok = _signup(client)
    headers = {"Authorization": f"Bearer {tok}"}
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    r = client.post(
        "/uploads/photo",
        headers=headers,
        files={"file": ("../../../evil.png", png, "image/png")},
    )
    assert r.status_code == 200, f"{r.status_code}"
    path = r.json().get("path", "")
    assert ".." not in path and not path.startswith("/"), path
