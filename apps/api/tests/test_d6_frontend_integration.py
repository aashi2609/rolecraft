"""
D6: Frontend integration contract verification.

Tests verify that:
1. API responses match frontend expected schema (ThreadOut)
2. Message sending returns correct response (MessageOut with status 201)
3. Thread listing includes all required fields with correct types
4. Message body limited to 2000 characters
5. No PII leakage in thread listings
6. Subscription error messages are user-friendly
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from core.security import create_access_token
from main import app
from models import (
    Application,
    ApplicationStatus,
    JobPosting,
    JobStatus,
    Subscription,
    SubscriptionStatus,
    UserRole,
)
from services.user_service import create_user_with_profile


@pytest.mark.asyncio
class TestFrontendThreadListingContract:
    """Verify thread listing response matches frontend ThreadOut schema."""

    async def test_thread_list_has_required_fields(
        self, company_client, make_conversation, candidate_user, company_user, db_session
    ):
        """Thread list items have all required ThreadOut fields."""
        # Create a thread
        await make_conversation(candidate_id=candidate_user.id, company_id=company_user.id)

        response = await company_client.get("/messages/threads")
        assert response.status_code == 200
        threads = response.json()

        assert len(threads) > 0, "Should have at least one thread"
        thread = threads[0]

        # Verify all required fields exist
        required_fields = [
            "thread_id",
            "last_body",
            "last_sent_at",
            "participant_label",
            "other_user_id",
            "unread_count",
            "avatar_url",
            "job_title",
            "subtitle",
        ]
        for field in required_fields:
            assert field in thread, f"Thread must include {field}"

        # Verify field types
        assert isinstance(thread["thread_id"], str), "thread_id must be string"
        assert isinstance(thread["participant_label"], str), "participant_label must be string"
        assert isinstance(thread["other_user_id"], str), "other_user_id must be string"
        assert isinstance(thread["unread_count"], int), "unread_count must be int"
        # avatar_url, job_title, subtitle can be null or string

    async def test_thread_list_no_pii_in_participant_label(
        self, company_client, make_conversation, candidate_user, company_user
    ):
        """Participant label should not contain email or phone."""
        await make_conversation(candidate_id=candidate_user.id, company_id=company_user.id)

        response = await company_client.get("/messages/threads")
        assert response.status_code == 200
        threads = response.json()

        assert len(threads) > 0
        thread = threads[0]
        label = thread["participant_label"]

        # Should not contain email-like patterns
        assert "@" not in label, "Participant label should not contain email"
        assert "+" not in label, "Participant label should avoid email patterns"

    async def test_thread_id_is_valid_uuid(
        self, company_client, make_conversation, candidate_user, company_user
    ):
        """Thread IDs should be valid UUIDs."""
        await make_conversation(candidate_id=candidate_user.id, company_id=company_user.id)

        response = await company_client.get("/messages/threads")
        assert response.status_code == 200
        threads = response.json()

        assert len(threads) > 0
        thread = threads[0]

        # Verify it's a valid UUID
        try:
            parsed_uuid = uuid.UUID(thread["thread_id"])
            assert str(parsed_uuid) == thread["thread_id"]
        except ValueError:
            pytest.fail(f"thread_id {thread['thread_id']} is not a valid UUID")


@pytest.mark.asyncio
class TestFrontendMessageSendingContract:
    """Verify message send response matches frontend MessageOut schema."""

    async def test_message_send_returns_201(
        self,
        company_client,
        candidate_user,
        company_user,
        admin_client,
        make_conversation,
        db_session,
    ):
        """Sending a message returns status 201."""
        # Grant company active subscription first
        response = await admin_client.post(
            "/admin/subscriptions/grant",
            json={
                "user_id": str(company_user.id),
                "plan_tier": "corporate_annual",
                "reason": "Test grant",
            },
        )
        assert response.status_code == 200

        # Create application to allow messaging
        # Create a job
        job = JobPosting(
            id=uuid.uuid4(),
            company_id=company_user.id,
            title="Test Job",
            status=JobStatus.live,
        )
        db_session.add(job)
        await db_session.commit()

        # Create application
        app_model = Application(
            id=uuid.uuid4(),
            candidate_id=candidate_user.id,
            job_id=job.id,
            status=ApplicationStatus.applied,
        )
        db_session.add(app_model)
        await db_session.commit()

        # Create conversation
        conv = await make_conversation(candidate_id=candidate_user.id, company_id=company_user.id)

        response = await company_client.post(
            f"/messages/threads/{conv.id}",
            json={"body": "Test message"},
        )

        assert (
            response.status_code == 201
        ), f"Send should return 201, got {response.status_code}: {response.json()}"

    async def test_message_response_has_required_fields(
        self,
        company_client,
        candidate_user,
        company_user,
        admin_client,
        make_conversation,
        db_session,
    ):
        """Message response has all required MessageOut fields."""
        # Grant subscription
        await admin_client.post(
            "/admin/subscriptions/grant",
            json={
                "user_id": str(company_user.id),
                "plan_tier": "corporate_annual",
                "reason": "Test",
            },
        )

        conv = await make_conversation(candidate_id=candidate_user.id, company_id=company_user.id)

        response = await company_client.post(
            f"/messages/threads/{conv.id}",
            json={"body": "Test message"},
        )

        assert response.status_code == 201
        msg = response.json()

        # Required fields for MessageOut
        required_fields = ["id", "sender_id", "sender_role", "body", "sent_at"]
        for field in required_fields:
            assert field in msg, f"Message must include {field}"

        # Verify types
        assert isinstance(msg["id"], str), "id must be string (UUID)"
        assert isinstance(msg["sender_id"], str), "sender_id must be string (UUID)"
        assert isinstance(msg["sender_role"], str), "sender_role must be string"
        assert isinstance(msg["body"], str), "body must be string"
        assert isinstance(msg["sent_at"], str), "sent_at must be ISO datetime string"

    async def test_message_body_truncated_to_2000_chars(
        self, company_client, candidate_user, company_user, admin_client, make_conversation
    ):
        """Message body is limited to 2000 characters."""
        # Grant subscription
        await admin_client.post(
            "/admin/subscriptions/grant",
            json={
                "user_id": str(company_user.id),
                "plan_tier": "corporate_annual",
                "reason": "Test",
            },
        )

        conv = await make_conversation(candidate_id=candidate_user.id, company_id=company_user.id)

        # Send message with content > 2000 chars
        long_body = "x" * 3000

        response = await company_client.post(
            f"/messages/threads/{conv.id}",
            json={"body": long_body},
        )

        assert response.status_code == 201
        msg = response.json()

        # Body should be truncated
        assert len(msg["body"]) <= 2000, f"Body should be ≤2000 chars, got {len(msg['body'])}"


@pytest.mark.asyncio
class TestFrontendSubscriptionErrorHandling:
    """Verify subscription error messages are user-friendly."""

    async def test_pending_subscription_error_message(self, db_session, candidate_user):
        """Pending subscription error message is clear."""
        # Create company with pending subscription
        company = await create_user_with_profile(
            db=db_session,
            email=f"pending_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.company,
        )
        await db_session.commit()

        # Try to start a thread
        company_token = create_access_token(
            user_id=company.id, role=company.role.value, token_version=company.token_version
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/messages/threads",
                json={"body": "Hello", "recipient_id": str(candidate_user.id)},
                headers={"Authorization": f"Bearer {company_token}"},
            )

            assert response.status_code == 403, "Should block with pending subscription"
            error = response.json()

            assert "detail" in error
            detail = error["detail"].lower()
            assert (
                "subscription" in detail or "upgrade" in detail
            ), "Error should mention subscription"

    async def test_cancelled_subscription_error_message(
        self, db_session, candidate_user, admin_client
    ):
        """Cancelled subscription error message is clear."""
        # Create company and cancel subscription
        company = await create_user_with_profile(
            db=db_session,
            email=f"cancelled_{uuid.uuid4().hex[:8]}@test.com",
            password="TestPass123",
            role=UserRole.company,
        )
        await db_session.commit()

        # Cancel subscription
        sub = await db_session.scalar(
            select(Subscription).where(Subscription.user_id == company.id)
        )
        sub.status = SubscriptionStatus.cancelled
        await db_session.commit()

        company_token = create_access_token(
            user_id=company.id, role=company.role.value, token_version=company.token_version
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/messages/threads",
                json={"body": "Hello", "recipient_id": str(candidate_user.id)},
                headers={"Authorization": f"Bearer {company_token}"},
            )

            assert response.status_code == 403
            error = response.json()
            assert "subscription" in error["detail"].lower() or "upgrade" in error["detail"].lower()


@pytest.mark.asyncio
class TestFrontendThreadReplyContract:
    """Verify replying to threads works correctly."""

    async def test_reply_to_thread_returns_201(
        self, candidate_client, company_user, candidate_user, admin_client, make_conversation
    ):
        """Replying to thread returns 201."""
        # Grant company subscription
        await admin_client.post(
            "/admin/subscriptions/grant",
            json={
                "user_id": str(company_user.id),
                "plan_tier": "corporate_annual",
                "reason": "Test",
            },
        )

        conv = await make_conversation(candidate_id=candidate_user.id, company_id=company_user.id)

        # Candidate replies
        response = await candidate_client.post(
            f"/messages/threads/{conv.id}",
            json={"body": "Reply from candidate"},
        )

        assert response.status_code == 201

    async def test_get_thread_returns_messages_in_order(
        self,
        company_client,
        candidate_client,
        company_user,
        candidate_user,
        admin_client,
        make_conversation,
    ):
        """Getting thread messages returns them in chronological order."""
        # Grant subscription
        await admin_client.post(
            "/admin/subscriptions/grant",
            json={
                "user_id": str(company_user.id),
                "plan_tier": "corporate_annual",
                "reason": "Test",
            },
        )

        conv = await make_conversation(candidate_id=candidate_user.id, company_id=company_user.id)

        # Company sends first message
        response1 = await company_client.post(
            f"/messages/threads/{conv.id}",
            json={"body": "First message"},
        )
        assert response1.status_code == 201

        # Candidate replies
        response2 = await candidate_client.post(
            f"/messages/threads/{conv.id}",
            json={"body": "Reply"},
        )
        assert response2.status_code == 201

        # Get thread - should return in order
        response = await company_client.get(f"/messages/threads/{conv.id}")
        assert response.status_code == 200
        messages = response.json()

        assert len(messages) >= 2, "Should have at least 2 messages"
        # First message should be the company's initial message
        assert "First message" in messages[0]["body"]
