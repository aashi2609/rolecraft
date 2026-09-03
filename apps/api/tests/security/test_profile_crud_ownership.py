"""Verify ProfileItemService CRUD ownership for education/certs/experience/projects."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

RESOURCES = (
    (
        "education",
        {"degree": "BSc", "institute": "Test U", "passing_year": 2020},
        {"degree": "MSc", "institute": "Test U", "passing_year": 2022},
    ),
    (
        "certifications",
        {"name": "AWS SAA", "issuing_org": "Amazon"},
        {"name": "AWS SAP", "issuing_org": "Amazon"},
    ),
    (
        "experience",
        {
            "company_name": "Acme",
            "role": "Eng",
            "from_date": "2020-01-01",
            "to_date": "2021-01-01",
            "is_current": False,
        },
        {
            "company_name": "Acme",
            "role": "Sr Eng",
            "from_date": "2020-01-01",
            "to_date": "2022-01-01",
            "is_current": False,
        },
    ),
    (
        "projects",
        {
            "project_name": "Portal",
            "org": "Acme",
            "from_date": "2020-01-01",
            "to_date": "2020-06-01",
        },
        {
            "project_name": "Portal v2",
            "org": "Acme",
            "from_date": "2020-01-01",
            "to_date": "2020-12-01",
        },
    ),
)


def test_all_profile_item_crud_and_ownership(client: TestClient) -> None:
    """Uses shared security conftest client; engine disposed after test."""
    for path, create_body, update_body in RESOURCES:
        uid = uuid.uuid4().hex[:8]
        r = client.post(
            "/auth/signup",
            json={
                "email": f"crud_own_{path}_{uid}@test.com",
                "password": "testpass123",
                "role": "candidate",
                "name": "CRUD Test",
            },
        )
        assert r.status_code == 200, r.text
        owner = r.json()

        r = client.post(
            "/auth/signup",
            json={
                "email": f"crud_oth_{path}_{uid}@test.com",
                "password": "testpass123",
                "role": "candidate",
                "name": "CRUD Other",
            },
        )
        assert r.status_code == 200, r.text
        other = r.json()

        h_own = {"Authorization": f"Bearer {owner['access_token']}"}
        h_oth = {"Authorization": f"Bearer {other['access_token']}"}

        r = client.post(f"/candidates/me/{path}", headers=h_own, json=create_body)
        assert r.status_code == 200, f"{path} create: {r.text}"
        item = r.json()
        item_id = item["id"]
        assert item["candidate_id"] == owner["user_id"]

        r = client.get(f"/candidates/me/{path}", headers=h_own)
        assert r.status_code == 200
        assert any(x["id"] == item_id for x in r.json()), f"{path} list: {r.text}"

        r = client.put(f"/candidates/me/{path}/{item_id}", headers=h_own, json=update_body)
        assert r.status_code == 200, f"{path} update: {r.text}"

        r = client.put(f"/candidates/me/{path}/{item_id}", headers=h_oth, json=update_body)
        assert r.status_code == 404, f"{path} other update: {r.status_code} {r.text}"

        r = client.delete(f"/candidates/me/{path}/{item_id}", headers=h_oth)
        assert r.status_code == 404, f"{path} other delete: {r.status_code} {r.text}"

        r = client.delete(f"/candidates/me/{path}/{item_id}", headers=h_own)
        assert r.status_code == 200
        assert r.json().get("ok") is True
