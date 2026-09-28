import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import select
from models import Conversation, Message, Notification, Application, ApplicationStatus, JobPosting

pytestmark = pytest.mark.asyncio

async def test_messaging_flow(
    company_client: AsyncClient,
    candidate_client: AsyncClient,
    db_session,
    company_user,
    candidate_user,
    other_company_user,
    other_company_client: AsyncClient
):
    # 1. Candidate cannot start a conversation
    resp = await candidate_client.post("/messages/threads", json={"recipient_id": str(company_user.id), "body": "Hello"})
    assert resp.status_code == 403
    assert "Only companies can start conversations" in resp.json()["detail"]

    # 2. Company cannot message candidate who hasn't applied
    resp = await company_client.post("/messages/threads", json={"recipient_id": str(candidate_user.id), "body": "Hi there"})
    assert resp.status_code == 403
    assert "Cannot message a candidate" in resp.json()["detail"]

    # Let's create an application
    job = JobPosting(id=uuid.uuid4(), company_id=company_user.id, title="Test Job", description="Desc")
    db_session.add(job)
    app = Application(id=uuid.uuid4(), job_id=job.id, candidate_id=candidate_user.id, status=ApplicationStatus.applied)
    db_session.add(app)
    await db_session.commit()

    # 3. Company sends a message
    resp = await company_client.post("/messages/threads", json={"recipient_id": str(candidate_user.id), "body": "Hi Candidate"})
    assert resp.status_code == 200
    msg_data = resp.json()
    conv_id = msg_data["conversation_id"]

    # 4. Check notifications
    notifs = (await db_session.execute(select(Notification).where(Notification.user_id == candidate_user.id))).scalars().all()
    assert len(notifs) == 1
    assert notifs[0].type == "new_message"

    # 5. Candidate sees the message in threads
    resp = await candidate_client.get("/messages/threads")
    assert resp.status_code == 200
    threads = resp.json()
    assert len(threads) == 1
    assert threads[0]["thread_id"] == conv_id
    assert threads[0]["unread_count"] == 1
    assert threads[0]["last_body"] == "Hi Candidate"

    # 6. Candidate views thread (marks as read)
    resp = await candidate_client.get(f"/messages/threads/{conv_id}")
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) == 1
    assert messages[0]["body"] == "Hi Candidate"

    # Check unread count is 0
    resp = await candidate_client.get("/messages/threads")
    assert resp.json()[0]["unread_count"] == 0

    # 7. Candidate replies
    resp = await candidate_client.post(f"/messages/threads/{conv_id}", json={"body": "Hi Company"})
    assert resp.status_code == 200
    
    # 8. Company sees the reply
    resp = await company_client.get(f"/messages/threads/{conv_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    assert resp.json()[1]["body"] == "Hi Company"

    # 9. Third user cannot read the thread
    resp = await other_company_client.get(f"/messages/threads/{conv_id}")
    assert resp.status_code == 404

    # 10. Third user cannot post to thread
    resp = await other_company_client.post(f"/messages/threads/{conv_id}", json={"body": "Intruder"})
    assert resp.status_code == 404
