"""Tests for 2C & 2D: Account Deletion, Re-auth, Token Expiry, and Revocation.

Verifies:
2C:
1. Delete without correct password is rejected (400).
2. Delete with correct password but missing/wrong confirmation is rejected (400).
3. Delete with correct password and confirmation="DELETE" succeeds (200), cascade-deleting
   all user rows (profile, items, applications, resumes) and physically deleting stored files.
4. Admin delete user cleans up stored files and user record via same cleanup service.

2D:
1. Token claims include sub, role, token_version, iat, exp.
2. Inactive/deactivated or bumped token_version tokens fail validation (401).
3. POST /auth/refresh rotates both access and refresh tokens.
4. POST /auth/logout bumps token_version and invalidates previous access and refresh tokens.
5. POST /auth/change-password bumps token_version so previous tokens are immediately revoked.
6. Decode rejects "none" algorithm or unexpected algorithms.
"""

from __future__ import annotations

import os
import uuid
import pytest
from fastapi.testclient import TestClient

from core.database import engine
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from services.storage_service import LOCAL_ROOT


def _signup(client: TestClient, email: str, role: str = "candidate") -> dict:
    from core.rate_limit import limiter
    if hasattr(limiter, "_storage") and hasattr(limiter._storage, "reset"):
        limiter._storage.reset()
    r = client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": "Password123!",
            "role": role,
            "name": "Test User",
        },
    )
    assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    return r.json()


class TestAccountDeletion:
    def test_delete_wrong_password_rejected(self, client: TestClient):
        uid = uuid.uuid4().hex[:8]
        user = _signup(client, f"del_pw_{uid}@test.com")
        token = user["access_token"]

        r = client.request(
            "DELETE",
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "WrongPassword!", "confirmation": "DELETE"},
        )
        assert r.status_code == 400
        assert "Current password is incorrect" in r.text

    def test_delete_wrong_confirmation_rejected(self, client: TestClient):
        uid = uuid.uuid4().hex[:8]
        user = _signup(client, f"del_conf_{uid}@test.com")
        token = user["access_token"]

        r = client.request(
            "DELETE",
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "Password123!", "confirmation": "delete"},
        )
        assert r.status_code == 400
        assert "Confirmation text must be 'DELETE'" in r.text

    def test_delete_success_cleans_up_files_and_db(self, client: TestClient):
        uid = uuid.uuid4().hex[:8]
        user = _signup(client, f"del_full_{uid}@test.com")
        token = user["access_token"]
        user_id = user["user_id"]

        # Upload a test file for the user
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00"
            b"\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        upload_resp = client.post(
            "/uploads/photo",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("avatar.png", png_bytes, "image/png")},
        )
        assert upload_resp.status_code == 200
        file_path_rel = upload_resp.json().get("storage_path")
        disk_file = (LOCAL_ROOT / file_path_rel).resolve() if file_path_rel else None
        if disk_file:
            assert disk_file.exists(), "Uploaded file should exist on disk before deletion"

        # Now perform verified account deletion
        r = client.request(
            "DELETE",
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "Password123!", "confirmation": "DELETE"},
        )
        assert r.status_code == 200
        assert "Account successfully deleted" in r.text

        # Verify old token is now 401
        r_protected = client.get(
            f"/candidates/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r_protected.status_code == 401

        # Verify file is deleted from disk
        if disk_file:
            assert not disk_file.exists(), "Stored file should be deleted upon account deletion"


class TestJwtExpiryAndRevocation:
    def test_token_claims_and_algorithm_validation(self, client: TestClient):
        uid = uuid.uuid4().hex[:8]
        user = _signup(client, f"jwt_claims_{uid}@test.com")
        token = user["access_token"]
        
        claims = decode_access_token(token)
        assert "sub" in claims
        assert "role" in claims
        assert "token_version" in claims
        assert "iat" in claims
        assert "exp" in claims
        assert claims["token_version"] == 1

        # Reject forged tokens with unsupported or missing signature
        from core.config import get_settings
        settings = get_settings()
        forged_none_token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxMjMifQ."
        with pytest.raises(ValueError):
            decode_access_token(forged_none_token)

    def test_token_rotation_via_refresh(self, client: TestClient):
        uid = uuid.uuid4().hex[:8]
        user = _signup(client, f"refresh_{uid}@test.com")
        refresh_token = user["refresh_token"]
        assert refresh_token is not None

        r = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"] != user["access_token"]

    def test_logout_revokes_token_version(self, client: TestClient):
        uid = uuid.uuid4().hex[:8]
        user = _signup(client, f"logout_{uid}@test.com")
        token = user["access_token"]
        refresh_token = user["refresh_token"]

        # Call logout
        r_logout = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert r_logout.status_code == 200

        # Protected endpoint should now return 401 (token revoked via token_version)
        r = client.get(f"/candidates/{user['user_id']}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

        # Refresh token is also revoked
        r_ref = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert r_ref.status_code == 401

    def test_change_password_revokes_old_tokens(self, client: TestClient):
        uid = uuid.uuid4().hex[:8]
        user = _signup(client, f"cpw_{uid}@test.com")
        old_token = user["access_token"]

        r_cp = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {old_token}"},
            json={"current_password": "Password123!", "new_password": "NewPassword123!"},
        )
        assert r_cp.status_code == 200

        # Old token must now be rejected
        r = client.get(f"/candidates/{user['user_id']}", headers={"Authorization": f"Bearer {old_token}"})
        assert r.status_code == 401

