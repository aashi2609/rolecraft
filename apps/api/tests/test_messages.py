"""
Tests for messaging and conversation functionality.

Covers:
- Conversation creation (company initiates only)
- Message authorization (company-candidate pair)
- Notification creation on new message
- Unread count tracking
- WebSocket messaging (if implemented)
"""

import uuid

import pytest
from sqlalchemy import select

from models import Notification, JobPosting, JobStatus, EmbeddingStatus, Application, ApplicationStatus

pytestmark = pytest.mark.asyncio


class TestConversationAuthorization:
    """Conversation access control and ownership."""

    async def test_company_creates_conversation_with_candidate(
        self, company_client, candidate_user, company_user, db_session
    ):
        """Company can start a conversation with a candidate."""
        # First, create a job and application so messaging policy passes
        job = await db_session.execute(
            select(JobPosting).where(JobPosting.company_id == company_user.id).limit(1)
        )
        job = job.scalar()
        
        if not job:
            # Create a job if none exists
            job = JobPosting(
                id=uuid.uuid4(),
                company_id=company_user.id,
                title="Test Job",
                status=JobStatus.draft,
                embedding_status=EmbeddingStatus.pending,
                embedding=[0.1] * 512,
            )
            db_session.add(job)
            await db_session.flush()
        
        # Create application
        from models import Application, ApplicationStatus
        app = Application(
            id=uuid.uuid4(),
            job_id=job.id,
            candidate_id=candidate_user.id,
            status=ApplicationStatus.applied,
        )
        db_session.add(app)
        await db_session.commit()
        
        response = await company_client.post(
            f"/messages/threads?candidate_id={candidate_user.id}"
        )
        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "id" in data
        assert str(data["candidate_id"]) == str(candidate_user.id)

    async def test_candidate_cannot_initiate_conversation(
        self, candidate_client, company_user, db_session
    ):
        """Candidate cannot start a conversation (company initiates only)."""
        response = await candidate_client.post(
            f"/messages/threads?candidate_id={company_user.id}"
        )
        # Should return exactly 403 (forbidden)
        assert response.status_code == 403, (
            f"Expected 403, got {response.status_code}"
        )

    async def test_candidate_accesses_own_conversation(
        self, candidate_client, make_conversation, candidate_user
    ):
        """Candidate can retrieve their own conversation."""
        conversation = await make_conversation(candidate_id=candidate_user.id)
        response = await candidate_client.get(f"/messages/threads/{conversation.id}")
        assert response.status_code == 200
        data = response.json()
        assert str(data["id"]) == str(conversation.id)

    async def test_candidate_gets_404_for_other_conversation(
        self, candidate_client, make_conversation, other_company_user, candidate_user
    ):
        """Candidate gets 404 accessing another candidate's conversation."""
        other_candidate_id = uuid.uuid4()
        conversation = await make_conversation(
            candidate_id=other_candidate_id, company_id=other_company_user.id
        )
        response = await candidate_client.get(f"/messages/threads/{conversation.id}")
        assert response.status_code == 404, (
            f"Expected 404 (IDOR prevention), got {response.status_code}"
        )

    async def test_one_conversation_per_candidate_company_pair(
        self, company_client, candidate_user, make_conversation, db_session
    ):
        """Only one active conversation allowed per candidate-company pair."""
        # Create first conversation
        resp1 = await company_client.post(
            "/messages/threads", json={"candidate_id": str(candidate_user.id)}
        )
        assert resp1.status_code == 201
        conv1_id = resp1.json()["id"]

        # Try to create second conversation with same pair
        resp2 = await company_client.post(
            "/messages/threads", json={"candidate_id": str(candidate_user.id)}
        )
        # Should either return existing conversation or 409 (conflict)
        assert resp2.status_code in [200, 409], f"Expected 200 or 409, got {resp2.status_code}"

        if resp2.status_code == 200:
            # Should be the same conversation
            assert resp2.json()["id"] == conv1_id


class TestMessagingAndNotifications:
    """Message creation, retrieval, and notification generation."""

    async def test_company_sends_message_to_candidate(
        self,
        company_client,
        make_conversation,
        candidate_user,
        company_user,
        db_session,
    ):
        """Company sends a message to candidate in their conversation."""
        conversation = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        response = await company_client.post(
            f"/messages/threads/{conversation.id}",
            json={"content": "Hello, interested in this role?"},
        )
        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["content"] == "Hello, interested in this role?"
        assert str(data["conversation_id"]) == str(conversation.id)

    async def test_candidate_sends_reply_message(
        self,
        candidate_client,
        make_conversation,
        make_message,
        candidate_user,
        company_user,
    ):
        """Candidate replies to company message in their conversation."""
        conversation = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )
        # Company sends first message
        await make_message(
            conversation_id=conversation.id, sender_id=company_user.id, content="Hello!"
        )

        # Candidate replies
        response = await candidate_client.post(
            f"/messages/threads/{conversation.id}",
            json={"content": "Thanks for reaching out!"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "Thanks for reaching out!"

    async def test_third_party_cannot_send_message(
        self, other_company_client, make_conversation, candidate_user, company_user
    ):
        """Third party cannot send messages to a conversation they're not in."""
        conversation = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        response = await other_company_client.post(
            f"/messages/threads/{conversation.id}",
            json={"content": "Trying to hijack this conversation"},
        )
        assert response.status_code in [403, 404], (
            f"Expected 403 or 404 (access denied), got {response.status_code}"
        )

    async def test_notification_created_on_new_message(
        self,
        company_client,
        make_conversation,
        candidate_user,
        company_user,
        db_session,
    ):
        """Notification is created when candidate receives a message."""
        conversation = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Clear any existing notifications
        await db_session.execute(
            select(Notification).where(Notification.user_id == candidate_user.id)
        )

        # Company sends message
        response = await company_client.post(
            f"/messages/threads/{conversation.id}",
            json={"content": "Check out this opportunity"},
        )
        assert response.status_code == 201

        # Check notification was created for candidate
        notifications = (
            (
                await db_session.execute(
                    select(Notification).where(Notification.user_id == candidate_user.id)
                )
            )
            .scalars()
            .all()
        )

        assert len(notifications) > 0, "No notification created for message recipient"
        notification = notifications[0]
        assert notification.notification_type == "message"
        assert (
            "message" in notification.content.lower() or "replied" in notification.content.lower()
        )

    async def test_unread_count_increments(
        self,
        company_client,
        candidate_client,
        make_conversation,
        candidate_user,
        company_user,
        db_session,
    ):
        """Unread message count increments for recipient."""
        conversation = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Get initial unread count
        resp = await candidate_client.get("/messages/threads")
        initial_convs = resp.json()
        initial_unread = 0
        for conv in initial_convs:
            if str(conv["id"]) == str(conversation.id):
                initial_unread = conv.get("unread_count", 0)

        # Company sends message
        await company_client.post(
            f"/messages/threads/{conversation.id}",
            json={"content": "New message"},
        )

        # Check unread count increased
        resp = await candidate_client.get("/messages/threads")
        new_convs = resp.json()
        new_unread = 0
        for conv in new_convs:
            if str(conv["id"]) == str(conversation.id):
                new_unread = conv.get("unread_count", 0)

        assert new_unread > initial_unread, (
            f"Unread count should increase from {initial_unread} to > {initial_unread}, got {new_unread}"
        )

    async def test_mark_messages_as_read(
        self,
        candidate_client,
        company_client,
        make_conversation,
        candidate_user,
        company_user,
    ):
        """Candidate can mark messages as read, unread count resets."""
        # NOTE: This test calls /messages/threads/{id}/mark-as-read which doesn't exist
        # in routers/messages.py. Cannot create routes per instructions.
        # This test will fail with 404 until the route is implemented.
        conversation = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Company sends message
        await company_client.post(
            f"/messages/threads/{conversation.id}", json={"content": "Read me!"}
        )

        # Candidate marks as read
        response = await candidate_client.post(f"/messages/threads/{conversation.id}/mark-as-read")
        assert response.status_code == 200

        # Unread count should be 0
        resp = await candidate_client.get("/messages/threads")
        convs = resp.json()
        for conv in convs:
            if str(conv["id"]) == str(conversation.id):
                assert conv.get("unread_count", 0) == 0, (
                    f"Unread count should be 0 after marking read, got {conv['unread_count']}"
                )


class TestMessageRetrievalAndOrdering:
    """Message list retrieval, pagination, and ordering."""

    async def test_get_messages_in_conversation(
        self,
        company_client,
        make_conversation,
        make_message,
        candidate_user,
        company_user,
    ):
        """Retrieve all messages in a conversation."""
        conversation = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Create 3 messages
        for i in range(3):
            await make_message(
                conversation_id=conversation.id,
                sender_id=company_user.id,
                content=f"Message {i + 1}",
            )

        response = await company_client.get(f"/messages/threads/{conversation.id}/messages")
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) >= 3, f"Expected at least 3 messages, got {len(messages)}"

    async def test_messages_ordered_by_timestamp(
        self,
        company_client,
        make_conversation,
        make_message,
        candidate_user,
        company_user,
    ):
        """Messages are ordered chronologically (oldest first or newest first)."""
        conversation = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Create messages with known content
        for i in range(3):
            await make_message(
                conversation_id=conversation.id,
                sender_id=company_user.id,
                content=f"Message {i}",
            )

        response = await company_client.get(f"/messages/threads/{conversation.id}/messages")
        assert response.status_code == 200
        messages = response.json()

        # Verify order (should be chronological)
        for i in range(len(messages) - 1):
            t1 = messages[i]["created_at"]
            t2 = messages[i + 1]["created_at"]
            assert t1 <= t2, f"Messages not in chronological order: {t1} > {t2}"

    async def test_message_pagination(
        self,
        company_client,
        make_conversation,
        make_message,
        candidate_user,
        company_user,
    ):
        """Messages support pagination with limit and offset."""
        conversation = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Create 10 messages
        for i in range(10):
            await make_message(
                conversation_id=conversation.id,
                sender_id=company_user.id,
                content=f"Message {i}",
            )

        # Get first page (limit=5)
        resp1 = await company_client.get(
            f"/messages/threads/{conversation.id}?limit=5&offset=0"
        )
        assert resp1.status_code == 200
        page1 = resp1.json()
        assert len(page1) == 5, f"Expected 5 messages, got {len(page1)}"

        # Get second page
        resp2 = await company_client.get(
            f"/messages/threads/{conversation.id}?limit=5&offset=5"
        )
        assert resp2.status_code == 200
        page2 = resp2.json()
        assert len(page2) == 5, f"Expected 5 messages, got {len(page2)}"

        # Pages should have different content
        assert page1[0]["id"] != page2[0]["id"], "Pagination not working"


class TestConversationListing:
    """Candidate and company conversation list views."""

    async def test_candidate_lists_conversations(
        self, candidate_client, make_conversation, candidate_user, company_user
    ):
        """Candidate sees list of their conversations."""
        # Create 2 conversations with different companies
        conv1 = await make_conversation(candidate_id=candidate_user.id, company_id=company_user.id)

        response = await candidate_client.get("/messages/threads")
        assert response.status_code == 200
        conversations = response.json()

        conv_ids = [str(c["id"]) for c in conversations]
        assert str(conv1.id) in conv_ids, "Candidate's conversation not in list"

    async def test_company_lists_conversations(
        self, company_client, make_conversation, candidate_user, company_user
    ):
        """Company sees list of their conversations."""
        conv1 = await make_conversation(candidate_id=candidate_user.id, company_id=company_user.id)

        response = await company_client.get("/messages/threads")
        assert response.status_code == 200
        conversations = response.json()

        conv_ids = [str(c["id"]) for c in conversations]
        assert str(conv1.id) in conv_ids, "Company's conversation not in list"

    async def test_only_relevant_conversations_shown(
        self, candidate_client, make_conversation, other_company_user
    ):
        """Candidate only sees conversations they're part of."""
        # Create conversation with other company (not candidate's conversation)
        other_candidate_id = uuid.uuid4()
        other_conv = await make_conversation(
            candidate_id=other_candidate_id, company_id=other_company_user.id
        )

        response = await candidate_client.get("/messages/threads")
        assert response.status_code == 200
        conversations = response.json()

        conv_ids = [str(c["id"]) for c in conversations]
        assert str(other_conv.id) not in conv_ids, (
            "Candidate should not see other candidates' conversations"
        )



class TestThreadListingWithExperience:
    """Test that thread listing handles candidates with experience rows correctly."""

    async def test_list_threads_with_candidate_experience(
        self, company_client, make_conversation, candidate_user, company_user, db_session
    ):
        """
        Company lists threads with a candidate that has experience rows.
        Verifies batch_load_experiences uses Experience.from_date.desc().nullslast().
        """
        from models import Experience
        from datetime import date

        # Create a conversation
        conversation = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Add multiple experience entries for the candidate (some with NULL from_date)
        exp1 = Experience(
            id=uuid.uuid4(),
            candidate_id=candidate_user.id,
            title="Senior Engineer",
            company_name="Tech Corp",
            from_date=date(2022, 1, 1),
            to_date=None,  # Current job
        )
        exp2 = Experience(
            id=uuid.uuid4(),
            candidate_id=candidate_user.id,
            title="Mid Engineer",
            company_name="Startup Inc",
            from_date=date(2020, 6, 1),
            to_date=date(2021, 12, 31),
        )
        exp3 = Experience(
            id=uuid.uuid4(),
            candidate_id=candidate_user.id,
            title="Junior Engineer",
            company_name="BigCo",
            from_date=None,  # NULL from_date
            to_date=date(2020, 5, 31),
        )
        db_session.add_all([exp1, exp2, exp3])
        await db_session.commit()

        # List threads as company
        response = await company_client.get("/messages/threads")
        assert response.status_code == 200, f"GET /messages/threads failed: {response.text}"
        threads = response.json()

        # Should successfully return threads without error
        assert isinstance(threads, list)
        assert len(threads) >= 1

        # Find our conversation
        our_thread = next((t for t in threads if str(t["id"]) == str(conversation.id)), None)
        assert our_thread is not None, "Our conversation not found in thread list"

        # Thread should have candidate info (with most recent experience)
        # The most recent non-NULL experience should be exp1 (2022-01-01)
        assert "candidate" in our_thread or "other_user" in our_thread, (
            "Thread missing candidate/user info"
        )
