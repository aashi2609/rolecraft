import pytest
from httpx import AsyncClient
from sqlalchemy import select
from models import CandidateProfile, Resume, PlanTier

@pytest.mark.asyncio
async def test_stale_resume_flow(
    candidate_client: AsyncClient,
    candidate_user,
    db_session,
    add_plan,
):
    # 1. Give candidate a complete plan so they can generate and regenerate
    await add_plan(candidate_user.id, PlanTier.complete)
    
    # 2. Setup initial profile
    profile_data = {
        "full_name": "Initial Name",
        "career_level": "Mid Level"
    }
    resp = await candidate_client.put("/candidates/me", json=profile_data)
    assert resp.status_code == 200
    
    # 3. Generate a resume
    resp = await candidate_client.post("/resumes/generate", json={"target_verticals": ["Software"]})
    assert resp.status_code == 200
    resumes = resp.json()
    assert len(resumes) == 1
    resume_id = resumes[0]["id"]
    assert resumes[0]["is_stale"] is False
    
    # 4. Make a non-resume-relevant edit (e.g., present_address)
    resp = await candidate_client.put("/candidates/me", json={"present_address": "123 Main St"})
    assert resp.status_code == 200
    
    # Verify resume is NOT stale
    resp = await candidate_client.get(f"/resumes/{resume_id}")
    assert resp.status_code == 200
    assert resp.json()["is_stale"] is False
    
    # 5. Make a resume-relevant edit (e.g., change full_name)
    resp = await candidate_client.put("/candidates/me", json={"full_name": "New Name"})
    assert resp.status_code == 200
    
    # Verify resume IS now stale
    resp = await candidate_client.get(f"/resumes/{resume_id}")
    assert resp.status_code == 200
    assert resp.json()["is_stale"] is True
    
    # 6. Regenerate resume
    resp = await candidate_client.post(f"/resumes/{resume_id}/regenerate")
    assert resp.status_code == 200
    new_resume = resp.json()
    new_resume_id = new_resume["id"]
    
    # Verify it created a new version
    assert new_resume_id != resume_id
    assert new_resume["version"] == 2
    assert new_resume["is_stale"] is False
    
    # Verify the old one still exists but is not default
    old_row = await db_session.get(Resume, resume_id)
    assert old_row is not None
    assert old_row.is_default is False

@pytest.mark.asyncio
async def test_stale_resume_skills_and_items(
    candidate_client: AsyncClient,
    candidate_user,
    db_session,
    add_plan,
):
    await add_plan(candidate_user.id, PlanTier.complete)
    
    # Setup profile
    await candidate_client.put("/candidates/me", json={"full_name": "Name"})
    
    # Generate resume
    resp = await candidate_client.post("/resumes/generate", json={"target_verticals": ["Data"]})
    resume_id = resp.json()[0]["id"]
    
    # Add a skill (resume relevant)
    resp = await candidate_client.put("/candidates/me/skills", json=["Python"])
    assert resp.status_code == 200
    
    # Verify stale
    resp = await candidate_client.get(f"/resumes/{resume_id}")
    assert resp.json()["is_stale"] is True
    
    # Regenerate to clear stale
    resp = await candidate_client.post(f"/resumes/{resume_id}/regenerate")
    new_resume_id = resp.json()["id"]
    
    # Add an education (resume relevant)
    resp = await candidate_client.post("/candidates/me/education", json={
        "institution_name": "MIT",
        "degree": "BS",
        "start_date": "2020-01-01"
    })
    assert resp.status_code == 200
    
    # Verify stale again
    resp = await candidate_client.get(f"/resumes/{new_resume_id}")
    assert resp.json()["is_stale"] is True

@pytest.mark.asyncio
async def test_regenerate_plan_gating(
    candidate_client: AsyncClient,
    candidate_user,
    db_session,
):
    # Free tier user (no plan added)
    await candidate_client.put("/candidates/me", json={"full_name": "Name"})
    
    # Generate first resume (allowed on free tier limit 1)
    resp = await candidate_client.post("/resumes/generate", json={"target_verticals": ["Sales"]})
    assert resp.status_code == 200
    resume_id = resp.json()[0]["id"]
    
    # Try to regenerate (should fail because free tier cannot regenerate)
    resp = await candidate_client.post(f"/resumes/{resume_id}/regenerate")
    assert resp.status_code == 403
    assert "Your current plan doesn't include resume generation" in resp.json()["detail"]
