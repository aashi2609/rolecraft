"""Verify upload validation. Run: PYTHONPATH=. python scripts/verify_uploads.py"""
from __future__ import annotations

import io
import uuid

import httpx

BASE = "http://127.0.0.1:8000"
PASS = FAIL = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


def signup() -> str:
    uid = uuid.uuid4().hex[:8]
    r = httpx.post(
        f"{BASE}/auth/signup",
        json={"email": f"up_{uid}@t.com", "password": "testpass123", "role": "candidate", "name": "U"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


print("=== Upload validation ===")
tok = signup()
headers = {"Authorization": f"Bearer {tok}"}

# Oversized photo (>5MB)
big = b"\xff\xd8\xff" + b"x" * (5 * 1024 * 1024 + 1)
r = httpx.post(
    f"{BASE}/uploads/photo",
    headers=headers,
    files={"file": ("big.jpg", big, "image/jpeg")},
    timeout=30,
)
ok("oversized photo rejected", r.status_code in (400, 413), f"{r.status_code} {r.text[:80]}")

# Fake jpg (text content)
r = httpx.post(
    f"{BASE}/uploads/photo",
    headers=headers,
    files={"file": ("fake.jpg", b"not an image", "image/jpeg")},
    timeout=10,
)
ok("fake jpg rejected by magic bytes", r.status_code == 400, f"{r.status_code}")

# Valid tiny PNG
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
ok("valid png accepted", r.status_code == 200, f"{r.status_code} {r.text[:80]}")

# Path traversal filename — should still store safely
r = httpx.post(
    f"{BASE}/uploads/photo",
    headers=headers,
    files={"file": ("../../../evil.png", png, "image/png")},
    timeout=10,
)
ok("traversal filename upload succeeds with safe path", r.status_code == 200, f"{r.status_code}")
if r.status_code == 200:
    path = r.json().get("path", "")
    ok("storage path has no traversal", ".." not in path and not path.startswith("/"), path)

print(f"\n{PASS} passed, {FAIL} failed")
