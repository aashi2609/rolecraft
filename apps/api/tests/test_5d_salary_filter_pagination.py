"""Step 5D: Salary filtering before pagination — SQL WHERE clause, deterministic ordering."""

import pytest
from uuid import uuid4

from models import CandidateProfile, User, Experience, UserRole
from services.candidate_search_service import search_candidates


@pytest.mark.asyncio
class TestSalaryFilterBeforePagination:
    """Verify salary filtering happens in SQL BEFORE LIMIT/OFFSET."""

    async def test_page_size_respected_with_salary_filter(self, db_session):
        """Request page 1 with page_size 10 and salary filter returns exactly 10 candidates."""
        # Seed 30 candidates with varied salaries (5-34 LPA)
        for i in range(30):
            user = User(
                id=uuid4(),
                email=f"ps_{i}_{uuid4().hex[:4]}@test.com",  # Unique
                password_hash="hash",
                role=UserRole.candidate,
                is_active=True,
            )
            db_session.add(user)

            profile = CandidateProfile(user_id=user.id, weblinks={})
            db_session.add(profile)

            salary_lpa = 5 + i  # 5, 6, ..., 34 LPA (12 match 10-20)
            exp = Experience(
                candidate_id=user.id,
                role="Engineer",
                expected_salary=f"{salary_lpa} LPA",
            )
            db_session.add(exp)

        await db_session.commit()

        # Request page 1, salary 10-20 LPA (matches 12 candidates)
        result, total = await search_candidates(
            db_session,
            salary_min=10,
            salary_max=20,
            page=1,
            page_size=10,
        )

        assert len(result) == 10
        assert total == 12

    async def test_total_count_includes_salary_filter(self, db_session):
        """Total count reflects salary filter applied BEFORE LIMIT/OFFSET."""
        for i in range(5):
            user = User(
                id=uuid4(),
                email=f"c_{i}_{uuid4().hex[:4]}@test.com",
                password_hash="h",
                role=UserRole.candidate,
                is_active=True,
            )
            db_session.add(user)
            profile = CandidateProfile(user_id=user.id, weblinks={})
            db_session.add(profile)
            # Salaries: 5, 6, 7, 8, 9 LPA
            exp = Experience(
                candidate_id=user.id,
                role="Dev",
                expected_salary=f"{5 + i} LPA",
            )
            db_session.add(exp)

        await db_session.commit()

        _, total = await search_candidates(
            db_session,
            salary_min=6,
            salary_max=8,
            page=1,
            page_size=100,
        )

        # Should match 6, 7, 8 LPA = 3 candidates
        assert total == 3

    async def test_last_page_partial(self, db_session):
        """Last page with fewer results than page_size."""
        for i in range(25):
            user = User(
                id=uuid4(),
                email=f"c_{i}_{uuid4().hex[:4]}@test.com",
                password_hash="h",
                role=UserRole.candidate,
                is_active=True,
            )
            db_session.add(user)
            profile = CandidateProfile(user_id=user.id, weblinks={})
            db_session.add(profile)
            exp = Experience(
                candidate_id=user.id,
                role="Dev",
                expected_salary="15 LPA",
            )
            db_session.add(exp)

        await db_session.commit()

        result3, _ = await search_candidates(
            db_session, salary_min=10, salary_max=20, page=3, page_size=10
        )
        assert len(result3) == 5

    async def test_empty_result_with_salary_filter(self, db_session):
        """Salary filter matching no candidates returns empty page."""
        for i in range(5):
            user = User(
                id=uuid4(),
                email=f"c_{i}_{uuid4().hex[:4]}@test.com",
                password_hash="h",
                role=UserRole.candidate,
                is_active=True,
            )
            db_session.add(user)
            profile = CandidateProfile(user_id=user.id, weblinks={})
            db_session.add(profile)
            exp = Experience(
                candidate_id=user.id,
                role="Dev",
                expected_salary="5 LPA",
            )
            db_session.add(exp)

        await db_session.commit()

        result, total = await search_candidates(
            db_session,
            salary_min=50,
            salary_max=100,
            page=1,
            page_size=10,
        )

        assert len(result) == 0
        assert total == 0

    async def test_boundary_inclusive_min_salary(self, db_session):
        """salary_min=10 includes candidates with exactly 10 LPA."""
        for salary in [8, 9, 10, 11, 12]:
            user = User(
                id=uuid4(),
                email=f"c_{salary}_{uuid4().hex[:4]}@test.com",
                password_hash="h",
                role=UserRole.candidate,
                is_active=True,
            )
            db_session.add(user)
            profile = CandidateProfile(user_id=user.id, weblinks={})
            db_session.add(profile)
            exp = Experience(
                candidate_id=user.id,
                role="Dev",
                expected_salary=f"{salary} LPA",
            )
            db_session.add(exp)

        await db_session.commit()

        result, total = await search_candidates(
            db_session,
            salary_min=10,
            salary_max=12,
            page=1,
            page_size=10,
        )

        # Should match 10, 11, 12
        assert total == 3
        assert len(result) == 3

    async def test_null_salary_excluded_when_filter_active(self, db_session):
        """When salary filter is active, NULL expected_salary candidates are excluded."""
        # 5 with NULL salary
        for i in range(5):
            user = User(
                id=uuid4(),
                email=f"cnull_{i}@test.com",
                password_hash="h",
                role=UserRole.candidate,
                is_active=True,
            )
            db_session.add(user)
            profile = CandidateProfile(user_id=user.id, weblinks={})
            db_session.add(profile)
            exp = Experience(
                candidate_id=user.id,
                role="Dev",
                expected_salary=None,
            )
            db_session.add(exp)

        # 5 with 10-20 LPA
        for i in range(5):
            user = User(
                id=uuid4(),
                email=f"cwith_{i}@test.com",
                password_hash="h",
                role=UserRole.candidate,
                is_active=True,
            )
            db_session.add(user)
            profile = CandidateProfile(user_id=user.id, weblinks={})
            db_session.add(profile)
            exp = Experience(
                candidate_id=user.id,
                role="Dev",
                expected_salary="15 LPA",
            )
            db_session.add(exp)

        await db_session.commit()

        result, total = await search_candidates(
            db_session,
            salary_min=10,
            salary_max=20,
            page=1,
            page_size=100,
        )

        # Should match only 5 with salary, exclude 5 with NULL
        assert total == 5
        assert len(result) == 5

    async def test_deterministic_ordering_no_overlap(self, db_session):
        """Deterministic ordering (by user_id) prevents row overlap across pages."""
        for i in range(30):
            user = User(
                id=uuid4(),
                email=f"c_{i}_{uuid4().hex[:4]}@test.com",
                password_hash="h",
                role=UserRole.candidate,
                is_active=True,
            )
            db_session.add(user)
            profile = CandidateProfile(user_id=user.id, weblinks={})
            db_session.add(profile)
            exp = Experience(
                candidate_id=user.id,
                role="Dev",
                expected_salary="15 LPA",
            )
            db_session.add(exp)

        await db_session.commit()

        # Fetch all pages
        all_ids = []
        for page in range(1, 4):
            result, _ = await search_candidates(
                db_session,
                salary_min=10,
                salary_max=20,
                page=page,
                page_size=10,
            )
            all_ids.extend([c.id for c in result])

        # Check no duplicates
        assert len(all_ids) == len(set(all_ids))
        assert len(all_ids) == 30
