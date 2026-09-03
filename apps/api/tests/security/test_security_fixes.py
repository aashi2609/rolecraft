"""Verify security fixes #1-#4. Run from apps/api with .venv313:

    PYTHONPATH=. python -m pytest tests/security/test_security_fixes.py -v

Uses in-process TestClient so results track the code under test (not a stale
uvicorn on :8000).
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from core.config import get_settings
from main import app
from services import resume_service

settings = get_settings()


def _signup(client: TestClient, email: str, role: str, password: str = "testpass123A") -> dict:
    r = client.post(
        "/auth/signup",
        json={"email": email, "password": password, "role": role, "name": "Test User"},
    )
    if r.status_code != 200:
        raise RuntimeError(f"signup failed for {email}: {r.status_code} {r.text}")
    return r.json()


def test_cors(client: TestClient) -> None:
    allowed = settings.cors_origin_list[0] if settings.cors_origin_list else "http://localhost:3000"

    evil = client.get("/health", headers={"Origin": "https://evil.com"})
    acao_evil = evil.headers.get("access-control-allow-origin")
    assert acao_evil != "https://evil.com", f"got {acao_evil!r}"

    good = client.get("/health", headers={"Origin": allowed})
    acao_good = good.headers.get("access-control-allow-origin")
    assert acao_good == allowed, f"got {acao_good!r}"


def test_idor_candidates_and_jobs(client: TestClient) -> None:
    uid = uuid.uuid4().hex[:8]
    cand_a = _signup(client, f"cand_a_{uid}@test.com", "candidate")
    cand_b = _signup(client, f"cand_b_{uid}@test.com", "candidate")
    company_a = _signup(client, f"company_a_{uid}@test.com", "company")

    token_a = cand_a["access_token"]
    token_b = cand_b["access_token"]
    token_co = company_a["access_token"]
    id_a = cand_a["user_id"]
    id_b = cand_b["user_id"]

    client.put(
        "/candidates/me",
        headers={"Authorization": f"Bearer {token_b}"},
        json={
            "full_name": "Candidate B",
            "present_address": "123 Secret St",
            "annual_family_income": "50000",
            "dob": "1990-01-15",
        },
    )

    r = client.get(f"/candidates/{id_b}", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 404, f"status={r.status_code}"

    r = client.get(f"/candidates/{id_a}", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 200, f"status={r.status_code}"

    r = client.get(
        f"/candidates/{id_b}/public-profile",
        headers={"Authorization": f"Bearer {token_co}"},
    )
    assert r.status_code == 200, f"status={r.status_code}"
    data = r.json()
    assert "present_address" not in data
    assert "annual_family_income" not in data
    assert "dob" not in data
    assert "email" not in data

    job = client.post(
        "/jobs",
        headers={"Authorization": f"Bearer {token_co}"},
        json={
            "title": "Draft Role",
            "status": "draft",
            "description": "secret draft",
            "min_salary": 0,
            "max_salary": 100,
        },
    )
    if job.status_code == 402:
        pytest.skip(f"draft job creation unavailable (plan limit: {job.status_code})")
    assert job.status_code == 200, f"{job.status_code} {job.text[:500]}"
    job_id = job.json()["id"]

    r = client.get(f"/jobs/{job_id}")
    assert r.status_code == 404, f"status={r.status_code}"

    r = client.get(f"/jobs/{job_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 404, f"status={r.status_code}"

    r = client.get(f"/jobs/{job_id}", headers={"Authorization": f"Bearer {token_co}"})
    assert r.status_code == 200, f"status={r.status_code}"


def test_parse_auth_required(client: TestClient) -> None:
    with patch("services.ai_client.generate_content", new_callable=AsyncMock) as mock_groq:
        r = client.post(
            "/resumes/parse",
            files={"file": ("resume.pdf", b"%PDF-1.4 minimal", "application/pdf")},
        )
        assert r.status_code == 401, f"status={r.status_code} body={r.text[:120]}"
        assert mock_groq.await_count == 0, f"calls={mock_groq.await_count}"


def test_plan_limit_before_groq(client: TestClient) -> None:
    uid = uuid.uuid4().hex[:8]
    cand = _signup(client, f"plan_{uid}@test.com", "candidate")
    token = cand["access_token"]

    gen = client.post(
        "/resumes/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={"target_verticals": ["software"]},
    )
    if gen.status_code not in (200, 402, 403):
        pytest.skip(f"initial generate failed ({gen.status_code})")

    with patch("services.ai_client.generate_content", new_callable=AsyncMock) as mock_groq:
        with patch.object(
            resume_service,
            "generate_resume_for_vertical",
            new_callable=AsyncMock,
        ) as mock_resume:
            mock_resume.return_value = {
                "content": {"summary": "x"},
                "ats_score": 80,
                "embedding": [0.0] * 10,
                "generation_metadata": {},
            }

            r = client.post(
                "/resumes/parse",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("resume.pdf", b"%PDF-1.4", "application/pdf")},
            )
            assert r.status_code == 403, f"status={r.status_code}"
            assert mock_groq.await_count == 0

            resumes = client.get("/resumes", headers={"Authorization": f"Bearer {token}"})
            if resumes.status_code == 200 and resumes.json():
                rid = resumes.json()[0]["id"]
                r = client.post(
                    f"/resumes/{rid}/regenerate",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert r.status_code == 403, f"status={r.status_code}"
                assert mock_resume.await_count == 0, f"calls={mock_resume.await_count}"

                r = client.post(
                    f"/resumes/{rid}/improve",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert r.status_code == 403, f"status={r.status_code}"

            r = client.post(
                "/resumes/download-tailored",
                headers={"Authorization": f"Bearer {token}"},
                json={"target_role": "Engineer"},
            )
            assert r.status_code == 403, f"status={r.status_code}"
