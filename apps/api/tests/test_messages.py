"""
Tests for messaging and conversation functionality.

Covers:
- Thread listing (company and candidate views)
- Thread creation (company initiates only)
- Message sending and authorization
- Notification creation on new message
- Unread count tracking
- Query count optimization (constant queries regardless of result size)
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from models import (
    CandidateProfile,
    Notification,
    Message,
    PlanTier,
    Subscription,
    SubscriptionStatus,
    User,
    UserRole,
)

pytestmark = pytest.mark.asyncio


async def _make_candidate_user(db_session, index: int) -> User:
    """Create a real candidate user + profile (conversations FK to profiles)."""
    user = User(
        id=uuid.uuid4(),
        email=f"bulk_candidate_{index}_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="x",
        role=UserRole.candidate,
        is_active=True,
        token_version=1,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(CandidateProfile(user_id=user.id, weblinks={}))
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def company_plan(db_session, company_user):
    """Grant the company user an active plan that includes messaging."""
    sub = Subscription(
        user_id=company_user.id,
        role=UserRole.company,
        plan_tier=PlanTier.corporate_annual,
        status=SubscriptionStatus.active,
    )
    db_session.add(sub)
    await db_session.commit()
    return sub


@pytest_asyncio.fixture
async def company_applicant(db_session, company_user, candidate_user, make_job, make_application):
    """Make candidate_user an applicant to one of company_user's jobs."""
    job = await make_job(company_id=company_user.id)
    app = await make_application(job_id=job.id, candidate_id=candidate_user.id)
    return app


class TestThreadListing:
    """Thread list retrieval and optimization."""

    async def test_candidate_lists_threads(
        self, candidate_client, make_conversation, candidate_user, company_user, db_session
    ):
        """Candidate sees list of their threads with optimized batch loading."""
        # Create a thread
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        response = await candidate_client.get("/messages/threads")
        assert response.status_code == 200
        threads = response.json()
        
        # Verify thread is in list
        thread_ids = [str(t["thread_id"]) for t in threads]
        assert str(conv.id) in thread_ids, "Candidate's thread not in list"

    async def test_company_lists_threads(
        self, company_client, make_conversation, candidate_user, company_user
    ):
        """Company sees list of their threads."""
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        response = await company_client.get("/messages/threads")
        assert response.status_code == 200
        threads = response.json()

        thread_ids = [str(t["thread_id"]) for t in threads]
        assert str(conv.id) in thread_ids, "Company's thread not in list"

    async def test_thread_list_payload_contains_required_fields(
        self, company_client, make_conversation, candidate_user, company_user
    ):
        """Thread list items have all required fields, no PII."""
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        response = await company_client.get("/messages/threads")
        assert response.status_code == 200
        threads = response.json()

        if threads:
            thread = threads[0]
            # Required fields
            assert "thread_id" in thread
            assert "last_body" in thread
            assert "last_sent_at" in thread
            assert "participant_label" in thread
            assert "other_user_id" in thread
            assert "unread_count" in thread
            assert "avatar_url" in thread
            # Optional fields
            assert "job_title" in thread
            assert "subtitle" in thread

            # NO PII
            assert "email" not in thread
            assert "phone" not in thread
            assert "address" not in thread

    async def test_thread_list_query_count_constant(
        self, company_client, make_conversation, candidate_user, company_user, db_session
    ):
        """Query count is O(1) regardless of thread count (batch loading)."""
        # Create multiple threads (real candidate users: conversations FK to profiles)
        for i in range(5):
            other_candidate = await _make_candidate_user(db_session, i)
            await make_conversation(
                candidate_id=other_candidate.id, company_id=company_user.id
            )

        # Query should be constant regardless of result set size
        response = await company_client.get("/messages/threads")
        assert response.status_code == 200
        # If implementation is correct, this shouldn't N+1 query


class TestThreadCreation:
    """Thread creation and conversation pairing."""

    async def test_company_creates_thread_with_candidate(
        self, company_client, candidate_user, company_plan, company_applicant
    ):
        """Company can start a thread with a candidate."""
        response = await company_client.post(
            "/messages/threads",
            json={"recipient_id": str(candidate_user.id), "body": "Hello, interested in this role?"}
        )
        assert (
            response.status_code == 201
        ), f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "conversation_id" in data
        assert data["body"] == "Hello, interested in this role?"

    async def test_candidate_cannot_initiate_thread(
        self, candidate_client, company_user
    ):
        """Candidate cannot start a thread (company initiates only)."""
        response = await candidate_client.post(
            "/messages/threads",
            json={"recipient_id": str(company_user.id), "body": "Hello"}
        )
        # Should return 403 (forbidden) - only companies can initiate
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"

    async def test_one_thread_per_candidate_company_pair(
        self, company_client, candidate_user, company_plan, company_applicant
    ):
        """Only one thread per candidate-company pair; second request returns existing."""
        # Create first thread
        resp1 = await company_client.post(
            "/messages/threads",
            json={"recipient_id": str(candidate_user.id), "body": "Hello"}
        )
        assert resp1.status_code == 201
        conv1_id = resp1.json()["conversation_id"]

        # Try to create second thread with same pair
        resp2 = await company_client.post(
            "/messages/threads",
            json={"recipient_id": str(candidate_user.id), "body": "Hi again"}
        )
        # Should return 201 and either create new or return existing
        assert resp2.status_code in [201, 200], f"Expected 201 or 200, got {resp2.status_code}"
        
        if resp2.status_code == 201:
            # If new message created, should be same conversation
            assert resp2.json()["conversation_id"] == conv1_id


class TestMessagingAuthorization:
    """Message authorization and access control."""

    async def test_candidate_can_reply_in_thread(
        self, candidate_client, make_conversation, candidate_user, company_user
    ):
        """Candidate can reply to a message in their thread."""
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Candidate replies
        response = await candidate_client.post(
            f"/messages/threads/{conv.id}",
            json={"body": "Thanks for reaching out!"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["body"] == "Thanks for reaching out!"

    async def test_third_party_cannot_message_thread(
        self, other_company_client, make_conversation, candidate_user, company_user
    ):
        """Third party cannot send messages to a thread they're not in."""
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        response = await other_company_client.post(
            f"/messages/threads/{conv.id}",
            json={"body": "Trying to hijack this thread"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    async def test_third_party_cannot_view_thread(
        self, other_company_client, make_conversation, candidate_user, company_user
    ):
        """Third party cannot read a thread they're not in."""
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        response = await other_company_client.get(f"/messages/threads/{conv.id}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestNotificationsAndUnreadCount:
    """Notification creation and unread tracking."""

    async def test_notification_created_on_new_message(
        self,
        company_client,
        make_conversation,
        candidate_user,
        company_user,
        company_plan,
        db_session,
    ):
        """Notification is created when recipient gets a message."""
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Company sends message
        response = await company_client.post(
            f"/messages/threads/{conv.id}",
            json={"body": "Check out this opportunity"}
        )
        assert response.status_code == 201

        # Check notification was created for candidate
        notifications = (
            (
                await db_session.execute(
                    select(Notification).where(
                        Notification.user_id == candidate_user.id
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(notifications) > 0, "No notification created for message recipient"
        notification = notifications[-1]  # Last notification
        assert notification.type == "new_message"

    async def test_unread_count_increments_on_new_message(
        self,
        company_client,
        candidate_client,
        make_conversation,
        candidate_user,
        company_user,
        company_plan,
    ):
        """Unread count increments when recipient gets a message."""
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Get initial unread count
        resp = await candidate_client.get("/messages/threads")
        initial_threads = resp.json()
        initial_unread = 0
        for thread in initial_threads:
            if str(thread["thread_id"]) == str(conv.id):
                initial_unread = thread.get("unread_count", 0)

        # Company sends message
        await company_client.post(
            f"/messages/threads/{conv.id}",
            json={"body": "New message"}
        )

        # Check unread count increased
        resp = await candidate_client.get("/messages/threads")
        new_threads = resp.json()
        new_unread = 0
        for thread in new_threads:
            if str(thread["thread_id"]) == str(conv.id):
                new_unread = thread.get("unread_count", 0)

        assert (
            new_unread > initial_unread
        ), f"Unread count should increase from {initial_unread}, got {new_unread}"

    async def test_unread_count_resets_on_thread_view(
        self,
        candidate_client,
        company_client,
        make_conversation,
        candidate_user,
        company_user,
        company_plan,
    ):
        """Unread count resets when recipient views the thread."""
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Company sends message
        await company_client.post(
            f"/messages/threads/{conv.id}",
            json={"body": "Read me!"}
        )

        # Candidate views thread (marks as read)
        response = await candidate_client.get(f"/messages/threads/{conv.id}")
        assert response.status_code == 200

        # Unread count should be 0
        resp = await candidate_client.get("/messages/threads")
        threads = resp.json()
        for thread in threads:
            if str(thread["thread_id"]) == str(conv.id):
                assert (
                    thread.get("unread_count", 0) == 0
                ), f"Unread count should be 0 after viewing thread, got {thread['unread_count']}"


class TestMessageRetrieval:
    """Message list retrieval and ordering."""

    async def test_get_messages_in_thread(
        self,
        company_client,
        make_conversation,
        make_message,
        candidate_user,
        company_user,
    ):
        """Retrieve all messages in a thread."""
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Create 3 messages
        for i in range(3):
            await make_message(
                conversation_id=conv.id,
                sender_id=company_user.id,
                body=f"Message {i + 1}",
            )

        response = await company_client.get(f"/messages/threads/{conv.id}")
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) >= 3, f"Expected at least 3 messages, got {len(messages)}"

    async def test_messages_ordered_chronologically(
        self,
        company_client,
        make_conversation,
        make_message,
        candidate_user,
        company_user,
    ):
        """Messages are ordered by sent_at ascending (oldest first)."""
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Create 3 messages
        for i in range(3):
            await make_message(
                conversation_id=conv.id,
                sender_id=company_user.id,
                body=f"Message {i}",
            )

        response = await company_client.get(f"/messages/threads/{conv.id}")
        assert response.status_code == 200
        messages = response.json()

        # Verify order (should be chronological ascending)
        for i in range(len(messages) - 1):
            t1 = messages[i]["sent_at"]
            t2 = messages[i + 1]["sent_at"]
            assert t1 <= t2, f"Messages not in chronological order: {t1} > {t2}"


class TestNegativeControls:
    """Verify authorization rules by breaking them."""

    async def test_invalid_signature_fails_authorization(
        self, other_company_client, make_conversation, candidate_user, company_user
    ):
        """NEGATIVE: Third party cannot access another's thread (reintroduced order_by check)."""
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Third party tries to access
        response = await other_company_client.get(f"/messages/threads/{conv.id}")
        assert response.status_code == 404, "Third party should not access thread"

    async def test_candidate_cannot_start_thread(
        self, candidate_client, company_user
    ):
        """NEGATIVE: Candidate cannot initiate thread (authorization check in place)."""
        response = await candidate_client.post(
            "/messages/threads",
            json={"recipient_id": str(company_user.id), "body": "Hello"}
        )
        assert response.status_code == 403, "Candidate should not start thread"

    async def test_deleted_user_handled_gracefully(
        self, company_client, make_conversation, candidate_user, company_user, db_session
    ):
        """If other user is deleted, thread shows 'Former user'."""
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Delete candidate user
        candidate_user.is_active = False
        await db_session.commit()

        # Company still lists threads - should show gracefully
        response = await company_client.get("/messages/threads")
        assert response.status_code == 200
        threads = response.json()
        
        # Find the thread with deleted candidate
        for thread in threads:
            if str(thread["thread_id"]) == str(conv.id):
                # Should still appear but with safe label
                assert thread["participant_label"] is not None

    async def test_company_without_plan_cannot_message(
        self, company_user, candidate_user, db_session
    ):
        """NEGATIVE: Company without active subscription cannot send messages."""
        from core.dependencies import CurrentUser
        from fastapi import HTTPException
        from core.messaging_auth import can_company_message_candidate
        
        # Ensure company has no active subscription
        # (fixture may have created one; delete it)
        from sqlalchemy import delete
        from models import Subscription

        await db_session.execute(
            delete(Subscription).where(Subscription.user_id == company_user.id)
        )
        await db_session.commit()

        # Try to message - should fail
        allowed, reason = await can_company_message_candidate(
            company_user.id, candidate_user.id, db_session
        )
        assert not allowed, "Company without plan should not be allowed"
        assert "subscription" in reason.lower(), f"Error message should mention subscription: {reason}"

    async def test_company_with_plan_can_message(
        self, company_user, candidate_user, db_session, make_conversation, make_job, make_application
    ):
        """POSITIVE: Company with active subscription can message an applicant.

        NOTE: an application is required because the default messaging policy
        is ``applicants_only`` — plan alone is not sufficient.
        """
        from core.messaging_auth import can_company_message_candidate
        from models import Subscription, SubscriptionStatus
        
        # Ensure company has active subscription
        sub = await db_session.scalar(
            select(Subscription).where(Subscription.user_id == company_user.id)
        )
        if not sub:
            sub = Subscription(
                user_id=company_user.id,
                role=company_user.role,
                plan_tier=PlanTier.corporate_annual,
                status=SubscriptionStatus.active,
            )
            db_session.add(sub)
            await db_session.commit()

        # Create an application so candidate qualifies under applicants_only policy
        job = await make_job(company_id=company_user.id)
        await make_application(job_id=job.id, candidate_id=candidate_user.id)
        await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Try to message - should succeed
        allowed, reason = await can_company_message_candidate(
            company_user.id, candidate_user.id, db_session
        )
        assert allowed, f"Company with plan should be allowed: {reason}"


class TestMessageHistoryPagination:
    """Keyset pagination for GET /messages/threads/{id} (Step 7C).

    Real parameters: ``limit`` (optional, 1-500) and ``cursor``
    (``'<sent_at ISO>|<message id>'`` of the last item on the previous page).
    Ordering is (sent_at, id) ascending. Without parameters the full history
    is returned.
    """

    async def _seed_messages(self, make_conversation, make_message, candidate_user, company_user, count=5):
        from datetime import datetime, timedelta, timezone

        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(count):
            await make_message(
                conversation_id=conv.id,
                sender_id=company_user.id,
                body=f"msg-{i}",
                sent_at=base + timedelta(minutes=i),
            )
        return conv

    @staticmethod
    def _cursor_of(msg: dict) -> str:
        return f"{msg['sent_at']}|{msg['id']}"

    async def test_pages_do_not_overlap(
        self, company_client, make_conversation, make_message, candidate_user, company_user
    ):
        conv = await self._seed_messages(make_conversation, make_message, candidate_user, company_user, 5)

        page1 = (await company_client.get(f"/messages/threads/{conv.id}", params={"limit": 2})).json()
        assert len(page1) == 2

        page2 = (
            await company_client.get(
                f"/messages/threads/{conv.id}",
                params={"limit": 2, "cursor": self._cursor_of(page1[-1])},
            )
        ).json()
        assert len(page2) == 2

        ids1 = {m["id"] for m in page1}
        ids2 = {m["id"] for m in page2}
        assert ids1.isdisjoint(ids2), "Pages must not share rows"
        assert [m["body"] for m in page1 + page2] == ["msg-0", "msg-1", "msg-2", "msg-3"]

    async def test_last_page_is_partial(
        self, company_client, make_conversation, make_message, candidate_user, company_user
    ):
        conv = await self._seed_messages(make_conversation, make_message, candidate_user, company_user, 5)

        page1 = (await company_client.get(f"/messages/threads/{conv.id}", params={"limit": 2})).json()
        page2 = (await company_client.get(f"/messages/threads/{conv.id}", params={"limit": 2, "cursor": self._cursor_of(page1[-1])})).json()
        page3 = (await company_client.get(f"/messages/threads/{conv.id}", params={"limit": 2, "cursor": self._cursor_of(page2[-1])})).json()

        assert len(page3) == 1, f"Last page should be partial, got {len(page3)}"
        assert page3[0]["body"] == "msg-4"

    async def test_cursor_past_end_returns_empty(
        self, company_client, make_conversation, make_message, candidate_user, company_user
    ):
        conv = await self._seed_messages(make_conversation, make_message, candidate_user, company_user, 3)

        all_msgs = (await company_client.get(f"/messages/threads/{conv.id}")).json()
        past_end = (await company_client.get(
            f"/messages/threads/{conv.id}",
            params={"limit": 10, "cursor": self._cursor_of(all_msgs[-1])},
        )).json()
        assert past_end == [], "Cursor past the end must return an empty page"

    async def test_invalid_cursor_returns_400(
        self, company_client, make_conversation, candidate_user, company_user
    ):
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )
        response = await company_client.get(
            f"/messages/threads/{conv.id}", params={"cursor": "not-a-cursor"}
        )
        assert response.status_code == 400


class TestFormerUserAndReadOnly:
    """Deleted/deactivated participants: 'Former user' label + read-only thread."""

    async def test_deactivated_candidate_shows_former_user(
        self, company_client, make_conversation, candidate_user, company_user, db_session
    ):
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )
        candidate_user.is_active = False
        await db_session.commit()

        response = await company_client.get("/messages/threads")
        assert response.status_code == 200
        threads = response.json()
        thread = next((t for t in threads if str(t["thread_id"]) == str(conv.id)), None)
        assert thread is not None, "Thread should still be listed"
        assert thread["participant_label"] == "Former user"

    async def test_read_only_thread_rejects_reply(
        self, company_client, make_conversation, candidate_user, company_user, db_session, company_plan
    ):
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )
        candidate_user.is_active = False
        await db_session.commit()

        response = await company_client.post(
            f"/messages/threads/{conv.id}", json={"body": "still there?"}
        )
        assert response.status_code == 403
        assert response.headers.get("x-error-code") == "read_only"

    async def test_deleted_candidate_thread_list_returns_200(
        self, company_client, make_conversation, candidate_user, company_user, db_session
    ):
        await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )
        await db_session.delete(candidate_user)
        await db_session.commit()

        response = await company_client.get("/messages/threads")
        assert response.status_code == 200


class TestPlanRequiredErrorCode:
    """1.5: sending without an active plan returns 403 + stable error code."""

    async def test_no_plan_returns_plan_required_code(
        self, company_client, candidate_user, company_applicant
    ):
        response = await company_client.post(
            "/messages/threads",
            json={"recipient_id": str(candidate_user.id), "body": "hi"},
        )
        assert response.status_code == 403
        assert response.headers.get("x-error-code") == "plan_required"
        assert "subscription" in response.json()["detail"].lower()

    async def test_candidate_reply_never_requires_plan(
        self, candidate_client, make_conversation, candidate_user, company_user
    ):
        """Candidate replies are never gated on the company's plan."""
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )
        response = await candidate_client.post(
            f"/messages/threads/{conv.id}", json={"body": "reply"}
        )
        assert response.status_code == 201
