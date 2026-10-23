"""Fire auth endpoints until 429; print raw status / Retry-After / body.

Usage (from apps/api, with API already running):
  python scripts/verify_rate_limits.py
  python scripts/verify_rate_limits.py --base http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid

import httpx


def _dump(label: str, response: httpx.Response) -> None:
    retry = response.headers.get("Retry-After") or response.headers.get("retry-after")
    print(f"\n=== {label} ===")
    print(f"status={response.status_code}")
    print(f"Retry-After={retry!r}")
    try:
        print(f"body={json.dumps(response.json(), ensure_ascii=True)}")
    except Exception:
        print(f"body_text={response.text[:500]!r}")


def verify_signin(client: httpx.Client, base: str) -> None:
    print("\n########## SIGNIN: 6 attempts (limit 5/minute per IP) ##########")
    email = f"nolimit_signin_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"email": email, "password": "WrongPass1!"}
    for i in range(1, 7):
        r = client.post(f"{base}/auth/signin", json=payload)
        _dump(f"signin attempt {i}", r)
        if i < 6:
            assert r.status_code in (401, 429), f"unexpected {r.status_code}"
        else:
            assert r.status_code == 429, f"6th signin expected 429, got {r.status_code}"
            assert r.headers.get("Retry-After") or r.headers.get("retry-after"), (
                "missing Retry-After"
            )
            assert "Too many requests" in r.text


def verify_signup(client: httpx.Client, base: str) -> None:
    print("\n########## SIGNUP: 6 attempts (limit 5/hour per IP) ##########")
    for i in range(1, 7):
        email = f"rl_signup_{uuid.uuid4().hex[:10]}_{i}@example.com"
        payload = {
            "email": email,
            "password": "TestPass123!",
            "role": "candidate",
            "name": f"RL {i}",
        }
        r = client.post(f"{base}/auth/signup", json=payload)
        _dump(f"signup attempt {i}", r)
        if i < 6:
            # May be 200 (created) or 429 if prior tests burned the IP budget
            assert r.status_code in (200, 429), f"unexpected {r.status_code}"
        else:
            assert r.status_code == 429, f"6th signup expected 429, got {r.status_code}"
            assert r.headers.get("Retry-After") or r.headers.get("retry-after")
            assert "Too many requests" in r.text


def verify_forgot(client: httpx.Client, base: str) -> None:
    print("\n########## FORGOT-PASSWORD: 4 attempts same email (limit 3/hour) ##########")
    email = f"rl_forgot_{uuid.uuid4().hex[:8]}@example.com"
    for i in range(1, 5):
        r = client.post(f"{base}/auth/forgot-password", json={"email": email})
        _dump(f"forgot-password attempt {i} email={email}", r)
        if i < 4:
            assert r.status_code in (200, 429), f"unexpected {r.status_code}"
        else:
            assert r.status_code == 429, f"4th forgot expected 429, got {r.status_code}"
            assert r.headers.get("Retry-After") or r.headers.get("retry-after")
            assert "Too many requests" in r.text
            # Must not reveal account existence
            assert "registered" not in r.text.lower()
            assert "not found" not in r.text.lower()


def verify_isolation(client: httpx.Client, base: str) -> None:
    print("\n########## ISOLATION: different email not blocked by prior forgot ##########")
    other = f"rl_other_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(f"{base}/auth/forgot-password", json={"email": other})
    _dump(f"forgot-password other email={other}", r)
    # May still 429 on IP bucket (10/hour) if exhausted — report either way
    print(
        f"isolation_note: status={r.status_code} "
        "(200 = email bucket isolated; 429 = shared IP bucket exhausted)"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    with httpx.Client(timeout=30.0) as client:
        health = client.get(f"{base}/health")
        print(f"health status={health.status_code} body={health.text}")
        if health.status_code != 200:
            print("API not healthy — start uvicorn first", file=sys.stderr)
            return 2

        # Order: forgot (email) first while IP budget fresh, then signin, then signup
        verify_forgot(client, base)
        verify_isolation(client, base)
        verify_signin(client, base)
        verify_signup(client, base)

    print("\nALL RATE-LIMIT CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
