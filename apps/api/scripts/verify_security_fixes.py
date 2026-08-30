"""Verify security fixes #1-#4. Run from apps/api: PYTHONPATH=. python scripts/verify_security_fixes.py"""
from __future__ import annotations

import io
import sys
import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from core.config import get_settings
from main import app

settings = get_settings()
client = TestClient(app)

PASS = 0
FAIL = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


def test_cors() -> None:
    print("\n=== 1. CORS wildcard removed ===")
    allowed = settings.cors_origin_list[0] if settings.cors_origin_list else "http://localhost:3000"

    evil = client.get("/health", headers={"Origin": "https://evil.com"})
    acao_evil = evil.headers.get("access-control-allow-origin")
    ok("evil origin not reflected", acao_evil != "https://evil.com", f"got {acao_evil!r}")

    good = client.get("/health", headers={"Origin": allowed})
    acao_good = good.headers.get("access-control-allow-origin")
    ok(f"allowed origin {allowed} works", acao_good == allowed, f"got {acao_good!r}")


def _signup(email: str, role: str, password: str = "testpass123") -> dict:
    r = client.post(
        "/auth/signup",
        json={"email": email, "password": password, "role": role, "name": "Test User"},
    )
    if r.status_code != 200:
        raise RuntimeError(f"signup failed for {email}: {r.status_code} {r.text}")
    return r.json()


def test_idor_candidates_and_jobs() -> None:
    print("\n=== 2. IDOR fixes ===")
    uid = uuid.uuid4().hex[:8]
    cand_a = _signup(f"cand_a_{uid}@test.com", "candidate")
    cand_b = _signup(f"cand_b_{uid}@test.com", "candidate")
    company_a = _signup(f"company_a_{uid}@test.com", "company")

    token_a = cand_a["access_token"]
    token_b = cand_b["access_token"]
    token_co = company_a["access_token"]
    id_a = cand_a["user_id"]
    id_b = cand_b["user_id"]

    # Seed sensitive data on candidate B
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

    # Candidate A cannot read B's full profile
    r = client.get(
        f"/candidates/{id_b}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    ok("candidate A blocked from B full profile", r.status_code == 404, f"status={r.status_code}")

    # Candidate A can read own profile
    r = client.get(
        f"/candidates/{id_a}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    ok("candidate A can read own profile", r.status_code == 200, f"status={r.status_code}")

    # Company can read public profile without PII
    r = client.get(
        f"/candidates/{id_b}/public-profile",
        headers={"Authorization": f"Bearer {token_co}"},
    )
    ok("company can read public profile", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        ok("public profile excludes address", "present_address" not in data)
        ok("public profile excludes income", "annual_family_income" not in data)
        ok("public profile excludes dob", "dob" not in data)
        ok("public profile excludes email", "email" not in data)

    # Draft job IDOR
    job = client.post(
        "/jobs",
        headers={"Authorization": f"Bearer {token_co}"},
        json={"title": "Draft Role", "status": "draft", "description": "secret draft"},
    )
    if job.status_code != 200:
        print(f"  SKIP  draft job creation ({job.status_code}) — may hit plan limit")
        return
    job_id = job.json()["id"]

    r = client.get(f"/jobs/{job_id}")
    ok("unauthenticated draft job returns 404", r.status_code == 404, f"status={r.status_code}")

    r = client.get(
        f"/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    ok("other user draft job returns 404", r.status_code == 404, f"status={r.status_code}")

    r = client.get(
        f"/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token_co}"},
    )
    ok("owner can read draft job", r.status_code == 200, f"status={r.status_code}")


def test_parse_auth_required() -> None:
    print("\n=== 3. POST /resumes/parse requires auth ===")
    with patch("services.ai_client.generate_content", new_callable=AsyncMock) as mock_groq:
        r = client.post(
            "/resumes/parse",
            files={"file": ("resume.pdf", b"%PDF-1.4 minimal", "application/pdf")},
        )
        ok("no auth returns 401", r.status_code == 401, f"status={r.status_code} body={r.text[:120]}")
        ok("Groq not called without auth", mock_groq.await_count == 0, f"calls={mock_groq.await_count}")


def test_plan_limit_before_groq() -> None:
    print("\n=== 4. check_plan_limit before Groq ===")
    uid = uuid.uuid4().hex[:8]
    cand = _signup(f"plan_{uid}@test.com", "candidate")
    token = cand["access_token"]

    # Create one resume to hit free-tier cap
    gen = client.post(
        "/resumes/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={"target_verticals": ["software"]},
    )
    if gen.status_code not in (200, 402, 403):
        print(f"  SKIP  initial generate failed ({gen.status_code})")
        return

    if gen.status_code in (402, 403):
        print("  NOTE  user already at cap from generate — proceeding with limit tests")

    endpoints = [
        ("POST", "/resumes/parse", {"files": {"file": ("r.pdf", b"%PDF", "application/pdf")}}),
    ]

    with patch("services.ai_client.generate_content", new_callable=AsyncMock) as mock_groq:
        with patch(
            "services.resume_service.generate_resume_for_vertical",
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
            ok("parse blocked at plan cap", r.status_code == 403, f"status={r.status_code}")
            ok("parse: Groq not called when capped", mock_groq.await_count == 0)

            # Regenerate needs existing resume id
            resumes = client.get("/resumes", headers={"Authorization": f"Bearer {token}"})
            if resumes.status_code == 200 and resumes.json():
                rid = resumes.json()[0]["id"]
                r = client.post(
                    f"/resumes/{rid}/regenerate",
                    headers={"Authorization": f"Bearer {token}"},
                )
                ok("regenerate blocked at plan cap", r.status_code == 403, f"status={r.status_code}")
                ok(
                    "regenerate: generate_resume not called when capped",
                    mock_resume.await_count == 0,
                    f"calls={mock_resume.await_count}",
                )

                r = client.post(
                    f"/resumes/{rid}/improve",
                    headers={"Authorization": f"Bearer {token}"},
                )
                ok("improve blocked at plan cap", r.status_code == 403, f"status={r.status_code}")

            r = client.post(
                "/resumes/download-tailored",
                headers={"Authorization": f"Bearer {token}"},
                json={"target_role": "Engineer"},
            )
            ok("download-tailored blocked at plan cap", r.status_code == 403, f"status={r.status_code}")


def main() -> None:
    print("Security fix verification")
    print(f"CORS origins: {settings.cors_origin_list}")
    try:
        test_cors()
        test_idor_candidates_and_jobs()
        test_parse_auth_required()
        test_plan_limit_before_groq()
    except Exception as exc:
        print(f"\nABORTED: {exc}")
        sys.exit(1)

    print(f"\n{'='*40}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
