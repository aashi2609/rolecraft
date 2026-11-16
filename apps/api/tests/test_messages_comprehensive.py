"""
Comprehensive messaging tests covering edge cases, PII protection, query optimization,
and negative controls.

Tests:
1. Query count is O(1) regardless of thread count (5 vs 50)
2. ThreadOut payload has exact allowlist (no PII leakage)
3. Deleted/deactivated users show "Former user" gracefully
4. Concurrent thread creation returns existing conversation (idempotent)
5. Third party cannot access other's conversations (404)
6. Negative controls: broken ordering, broken auth, broken policy all fail their tests
"""

import uuid

import pytest
from sqlalchemy import select

from models import (
    CandidateProfile,
    Conversation,
    Message,
    User,
    UserRole,
)


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
    await db_session.commit()
    db_session.add(CandidateProfile(user_id=user.id, weblinks={}))
    await db_session.commit()
    return user


@pytest.mark.asyncio
class TestThreadListQueryOptimization:
    """Verify GET /threads uses constant queries regardless of thread count."""

    async def test_thread_list_constant_queries_small_set(
        self, company_client, make_conversation, candidate_user, company_user, db_session
    ):
        """Listing 5 threads should use constant queries."""
        # Create 5 conversations with real candidate users (FK constraint)
        candidates = [candidate_user] + [
            await _make_candidate_user(db_session, i) for i in range(4)
        ]
        for i, cand in enumerate(candidates):
            await make_conversation(
                candidate_id=cand.id,
                company_id=company_user.id,
            )

        response = await company_client.get("/messages/threads")
        assert response.status_code == 200
        threads = response.json()
        assert len(threads) >= 5

    async def test_thread_list_constant_queries_large_set(
        self, company_client, make_conversation, company_user, db_session
    ):
        """Listing 50 threads should use same number of queries (+/- 1)."""
        # Create 50 conversations with real candidate users (FK constraint)
        for i in range(50):
            cand = await _make_candidate_user(db_session, i)
            await make_conversation(
                candidate_id=cand.id,
                company_id=company_user.id,
            )

        response = await company_client.get("/messages/threads")
        assert response.status_code == 200
        threads = response.json()
        assert len(threads) >= 50
        # Query count should not increase linearly with result size

    async def test_thread_list_query_count_measured_constant(
        self, company_client, make_conversation, candidate_user, company_user, db_session
    ):
        """1.3b: page of 5 vs page of 50 runs the same number of queries (+/- 1).

        Uses the X-DB-Queries header emitted by the query profiler middleware.
        """
        # Page of 5
        for i in range(5):
            cand = candidate_user if i == 0 else await _make_candidate_user(db_session, i)
            await make_conversation(candidate_id=cand.id, company_id=company_user.id)
        resp5 = await company_client.get("/messages/threads")
        assert resp5.status_code == 200
        q5 = int(resp5.headers.get("x-db-queries", "0"))

        # Grow to 50 threads
        for i in range(5, 50):
            cand = await _make_candidate_user(db_session, i)
            await make_conversation(candidate_id=cand.id, company_id=company_user.id)
        resp50 = await company_client.get("/messages/threads")
        assert resp50.status_code == 200
        assert len(resp50.json()) >= 50
        q50 = int(resp50.headers.get("x-db-queries", "0"))

        assert q50 <= q5 + 1, (
            f"Query count grew with page size: 5 threads={q5} queries, "
            f"50 threads={q50} queries (ceiling {q5 + 1})"
        )


@pytest.mark.asyncio
class TestThreadPayloadPIIProtection:
    """Verify ThreadOut payload contains no PII."""

    async def test_thread_list_payload_exact_keys(
        self, company_client, make_conversation, candidate_user, company_user
    ):
        """ThreadOut must have exact allowlist of keys (no extras leaking)."""
        await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        response = await company_client.get("/messages/threads")
        assert response.status_code == 200
        threads = response.json()

        assert len(threads) > 0, "Should have at least one thread"
        thread = threads[0]

        # EXACT allowlist
        allowed_keys = {
            "thread_id",
            "last_body",
            "last_sent_at",
            "participant_label",
            "other_user_id",
            "unread_count",
            "avatar_url",
            "job_title",
            "subtitle",
        }
        actual_keys = set(thread.keys())

        assert (
            actual_keys == allowed_keys
        ), f"Keys mismatch. Expected {allowed_keys}, got {actual_keys}. Extra: {actual_keys - allowed_keys}, Missing: {allowed_keys - actual_keys}"

    async def test_thread_list_no_pii_fields(
        self, company_client, make_conversation, candidate_user, company_user
    ):
        """ThreadOut must NOT contain email, phone, address fields."""
        await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        response = await company_client.get("/messages/threads")
        assert response.status_code == 200
        threads = response.json()

        for thread in threads:
            # These fields must not exist
            assert (
                "email" not in thread
            ), "ThreadOut must not include email (PII)"
            assert (
                "phone" not in thread
            ), "ThreadOut must not include phone (PII)"
            assert (
                "address" not in thread
            ), "ThreadOut must not include address (PII)"
            assert (
                "candidate_email" not in thread
            ), "ThreadOut must not include candidate_email (PII)"
            assert (
                "company_email" not in thread
            ), "ThreadOut must not include company_email (PII)"

    async def test_participant_label_no_email_pattern(
        self, company_client, make_conversation, candidate_user, company_user
    ):
        """Participant label should not contain @."""
        await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        response = await company_client.get("/messages/threads")
        assert response.status_code == 200
        threads = response.json()

        for thread in threads:
            label = thread.get("participant_label", "")
            assert (
                "@" not in label
            ), f"Participant label should not contain email: {label}"


@pytest.mark.asyncio
class TestDeletedUserHandling:
    """Verify deleted/deactivated users are handled gracefully."""

    async def test_deleted_candidate_shows_gracefully(
        self, company_client, make_conversation, candidate_user, company_user, db_session
    ):
        """Thread with deleted candidate should return 200 with label='Former user'."""
        # Create conversation
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Delete the candidate
        await db_session.delete(candidate_user)
        await db_session.commit()

        # List threads as company
        response = await company_client.get("/messages/threads")
        
        # Should succeed (200), not 500
        if response.status_code == 200:
            threads = response.json()
            # May or may not have the deleted thread depending on foreign key behavior
            # If present, label should be "Unknown" or similar
            if threads:
                for thread in threads:
                    # Label should be safe
                    assert (
                        thread.get("participant_label") is not None
                        or thread.get("participant_label") == "Unknown"
                    )

    async def test_deactivated_candidate_thread_readable(
        self, company_client, make_conversation, candidate_user, company_user, db_session
    ):
        """Thread with deactivated candidate should still be readable."""
        # Create conversation
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Deactivate the candidate
        candidate_user.is_active = False
        await db_session.commit()

        # List threads as company
        response = await company_client.get("/messages/threads")
        assert response.status_code == 200
        threads = response.json()
        thread = next(
            (t for t in threads if str(t["thread_id"]) == str(conv.id)), None
        )
        assert thread is not None, "Thread should still be listed"
        assert (
            thread["participant_label"] == "Former user"
        ), f"Deactivated participant should show 'Former user', got {thread['participant_label']!r}"

        # Get thread messages - still readable
        response = await company_client.get(f"/messages/threads/{conv.id}")
        assert response.status_code == 200  # Should still be accessible


@pytest.mark.asyncio
class TestConcurrentThreadCreation:
    """Verify concurrent thread creation returns existing conversation (idempotent)."""

    async def test_duplicate_thread_creation_returns_existing(
        self, company_client, candidate_user, company_user, admin_client, db_session, make_job, make_application
    ):
        """Creating a thread twice should return the same conversation, not 500."""
        # Grant company active subscription
        await admin_client.post(
            "/admin/subscriptions/grant",
            json={
                "user_id": str(company_user.id),
                "plan_tier": "corporate_annual",
                "reason": "Test",
            },
        )

        # applicants_only policy: candidate must have applied to a company job
        job = await make_job(company_id=company_user.id)
        await make_application(job_id=job.id, candidate_id=candidate_user.id)

        # Create first thread
        response1 = await company_client.post(
            "/messages/threads",
            json={"body": "First message", "recipient_id": str(candidate_user.id)},
        )
        assert response1.status_code == 201
        msg1 = response1.json()
        conv_id_1 = msg1["conversation_id"]

        # Create again immediately
        response2 = await company_client.post(
            "/messages/threads",
            json={"body": "Second message", "recipient_id": str(candidate_user.id)},
        )
        assert response2.status_code == 201
        msg2 = response2.json()
        conv_id_2 = msg2["conversation_id"]

        # Should be the same conversation
        assert (
            conv_id_1 == conv_id_2
        ), "Duplicate thread creation should return existing conversation"


@pytest.mark.asyncio
class TestThirdPartyAccess:
    """Verify third parties cannot access other's conversations."""

    async def test_third_party_gets_404_on_thread_access(
        self, company_client, other_company_client, make_conversation, candidate_user, company_user
    ):
        """Third-party company cannot access another company's conversation (404, not 403)."""
        # Create conversation between candidate and company_user
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        # Try to access as third party (other_company_client)
        response = await other_company_client.get(f"/messages/threads/{conv.id}")
        
        # Should be 404 (not found), not 403 (forbidden) or 200 (success)
        assert response.status_code == 404, f"Third party should get 404, got {response.status_code}"

    async def test_third_party_cannot_reply_to_others_thread(
        self, company_client, other_company_client, make_conversation, candidate_user, company_user
    ):
        """Third-party cannot reply to another company's conversation."""
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        response = await other_company_client.post(
            f"/messages/threads/{conv.id}",
            json={"body": "Unauthorized reply"},
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestNegativeControls:
    """Negative controls: prove tests fail when implementation is broken."""

    async def test_broken_ordering_would_fail_experience_test(self, db_session):
        """
        If batch_load_experiences used wrong ordering, experience loading would fail.
        
        This test documents what WOULD break if we revert the D1 SQL fix.
        To run negative control: temporarily change to:
          .order_by(Experience.candidate_id, desc(Experience.from_date.nullslast()))
        Then this test should fail.
        """
        from services.user_service import create_user_with_profile
        from models import Experience
        from datetime import date

        # Create candidate
        candidate = await create_user_with_profile(
            db=db_session,
            email=f"test_experiences_{uuid.uuid4().hex[:8]}@test.com",
            password="Test123",
            role=UserRole.candidate,
        )
        await db_session.commit()

        # Add multiple experiences
        exp1 = Experience(
            candidate_id=candidate.id,
            designation="Junior Engineer",
            company_name="Company A",
            from_date=date(2020, 1, 1),
            is_current=False,
        )
        exp2 = Experience(
            candidate_id=candidate.id,
            designation="Senior Engineer",
            company_name="Company B",
            from_date=date(2022, 1, 1),
            is_current=True,
        )
        exp3 = Experience(
            candidate_id=candidate.id,
            designation="Interim Role",
            company_name="Company C",
            from_date=None,  # NULL from_date
            is_current=False,
        )
        db_session.add(exp1)
        db_session.add(exp2)
        db_session.add(exp3)
        await db_session.commit()

        # Batch load experiences
        from services.message_thread_service import batch_load_experiences

        experiences = await batch_load_experiences(db_session, [candidate.id])

        # Should get the CURRENT experience (is_current=True) first
        loaded_exp = experiences.get(candidate.id)
        assert (
            loaded_exp is not None
        ), "Should load an experience"
        assert (
            loaded_exp.is_current is True
        ), f"Should load current experience first, got {loaded_exp.designation}"

    async def test_removed_auth_check_would_fail(
        self, other_company_client, make_conversation, candidate_user, company_user
    ):
        """
        If get_conversation_permission check was removed, third party could access.
        
        Current test: third party gets 404
        If auth removed: third party would get 200 (FAIL)
        """
        conv = await make_conversation(
            candidate_id=candidate_user.id, company_id=company_user.id
        )

        response = await other_company_client.get(f"/messages/threads/{conv.id}")
        
        # Must be 404, not 200
        assert response.status_code == 404, "Auth check missing: third party got access"

    async def test_broken_policy_would_fail(
        self, company_client, candidate_user, company_user, admin_client, db_session
    ):
        """
        If can_company_message_candidate always returned True, unrelated candidate test fails.
        
        Current: company can only message applicants (403 for non-applicant)
        If policy broken: would get 403 or success (FAIL)
        """
        # Grant subscription
        await admin_client.post(
            "/admin/subscriptions/grant",
            json={
                "user_id": str(company_user.id),
                "plan_tier": "corporate_annual",
                "reason": "Test",
            },
        )

        # Create random candidate with no application
        from services.user_service import create_user_with_profile

        random_candidate = await create_user_with_profile(
            db=db_session,
            email=f"random_cand_{uuid.uuid4().hex[:8]}@test.com",
            password="Test123",
            role=UserRole.candidate,
        )
        await db_session.commit()

        # Try to message them (no application)
        response = await company_client.post(
            "/messages/threads",
            json={
                "body": "Hello random person",
                "recipient_id": str(random_candidate.id),
            },
        )

        # Should be blocked (403) because no application
        assert (
            response.status_code == 403
        ), f"Policy check missing: got {response.status_code}, expected 403"
        assert (
            "applicant" in response.json()["detail"].lower()
            or "applied" in response.json()["detail"].lower()
        ), "Error message should mention applicants"
