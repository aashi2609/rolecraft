"""Step 5E: Experience calculation from date ranges with interval merging."""

import pytest
from datetime import date
from unittest.mock import MagicMock

from services.experience_calculator import total_experience_years, experience_in_role


class MockExperience:
    """Mock Experience ORM object for testing."""
    def __init__(self, from_date, to_date=None, is_current=False, employment_type=None, role=None, designation=None):
        self.from_date = from_date
        self.to_date = to_date
        self.is_current = is_current
        self.employment_type = employment_type
        self.role = role
        self.designation = designation


class TestTotalExperienceYears:
    """Test total_experience_years with various scenarios."""

    def test_single_job(self):
        """Single job: Jan 2020 to Jan 2023 = 3.0 years."""
        exp = [MockExperience(
            from_date=date(2020, 1, 1),
            to_date=date(2023, 1, 1),
        )]
        total, internship = total_experience_years(exp, as_of=date(2023, 1, 1))
        assert total == 3.0
        assert internship == 0.0

    def test_overlapping_jobs(self):
        """Two overlapping jobs: counts overlap once.
        - Job 1: Jan 2020 - Jan 2022 (2 years)
        - Job 2: Jul 2021 - Jul 2023 (2 years)
        Overlap: Jul 2021 - Jan 2022 (0.5 years)
        Total: 2 + 2 - 0.5 = 3.5 years
        """
        exp = [
            MockExperience(from_date=date(2020, 1, 1), to_date=date(2022, 1, 1)),
            MockExperience(from_date=date(2021, 7, 1), to_date=date(2023, 7, 1)),
        ]
        total, internship = total_experience_years(exp, as_of=date(2023, 7, 1))
        # Merged intervals: Jan2020-Jan2022 (2yr) + Jan2022-Jul2023 (1.5yr) = 3.5yr
        assert abs(total - 3.5) < 0.1
        assert internship == 0.0

    def test_adjacent_jobs_no_overlap(self):
        """Two adjacent jobs (no overlap):
        - Job 1: Jan 2020 - Jan 2022
        - Job 2: Jan 2022 - Jan 2024
        Total: 4.0 years
        """
        exp = [
            MockExperience(from_date=date(2020, 1, 1), to_date=date(2022, 1, 1)),
            MockExperience(from_date=date(2022, 1, 1), to_date=date(2024, 1, 1)),
        ]
        total, internship = total_experience_years(exp, as_of=date(2024, 1, 1))
        assert abs(total - 4.0) < 0.1

    def test_gap_between_jobs(self):
        """Two jobs with gap (gaps not counted):
        - Job 1: Jan 2020 - Jan 2021 (1 year)
        - Gap: Jan 2021 - Jan 2022 (not counted)
        - Job 2: Jan 2022 - Jan 2023 (1 year)
        Total: 2.0 years (gap not included)
        """
        exp = [
            MockExperience(from_date=date(2020, 1, 1), to_date=date(2021, 1, 1)),
            MockExperience(from_date=date(2022, 1, 1), to_date=date(2023, 1, 1)),
        ]
        total, internship = total_experience_years(exp, as_of=date(2023, 1, 1))
        assert abs(total - 2.0) < 0.1

    def test_current_role_with_no_to_date(self):
        """Current role (is_current=True, no to_date):
        - Started: Jan 2020
        - Still current (as_of: Jan 2024)
        Total: 4.0 years
        """
        exp = [MockExperience(
            from_date=date(2020, 1, 1),
            to_date=None,
            is_current=True,
        )]
        total, internship = total_experience_years(exp, as_of=date(2024, 1, 1))
        assert abs(total - 4.0) < 0.1

    def test_current_role_null_to_date_no_is_current_flag(self):
        """Role with null to_date but is_current=False:
        Should treat null to_date as as_of (current).
        """
        exp = [MockExperience(
            from_date=date(2022, 1, 1),
            to_date=None,
            is_current=False,
        )]
        total, internship = total_experience_years(exp, as_of=date(2024, 1, 1))
        assert abs(total - 2.0) < 0.1

    def test_future_end_date_clamped(self):
        """Future end date should be clamped to as_of:
        - Job: Jan 2020 - Jan 2030 (claimed future end)
        - as_of: Jan 2024
        - Counted: Jan 2020 - Jan 2024 = 4.0 years
        """
        exp = [MockExperience(
            from_date=date(2020, 1, 1),
            to_date=date(2030, 1, 1),
        )]
        total, internship = total_experience_years(exp, as_of=date(2024, 1, 1))
        assert abs(total - 4.0) < 0.1

    def test_missing_from_date_skipped(self):
        """Row with no from_date should be skipped (not counted)."""
        exp = [MockExperience(
            from_date=None,
            to_date=date(2023, 1, 1),
        )]
        total, internship = total_experience_years(exp)
        assert total == 0.0

    def test_to_date_before_from_date_skipped(self):
        """Row with to_date < from_date should be skipped (invalid interval)."""
        exp = [MockExperience(
            from_date=date(2023, 1, 1),
            to_date=date(2020, 1, 1),
        )]
        total, internship = total_experience_years(exp)
        assert total == 0.0

    def test_internship_counted_by_default(self):
        """Internship (employment_type='internship'):
        - Regular job: Jan 2020 - Jan 2021 (1 year)
        - Internship: Jul 2021 - Sep 2021 (0.2 years)
        - Included by default: total = 1.2 years, internship = 0.2
        """
        exp = [
            MockExperience(from_date=date(2020, 1, 1), to_date=date(2021, 1, 1), employment_type="Full-time"),
            MockExperience(from_date=date(2021, 7, 1), to_date=date(2021, 9, 1), employment_type="Internship"),
        ]
        total, internship = total_experience_years(exp, as_of=date(2021, 9, 1), include_internships=True)
        assert abs(total - 1.2) < 0.1
        assert abs(internship - 0.2) < 0.1

    def test_internship_excluded(self):
        """Internship excluded when include_internships=False:
        - Regular: 1 year
        - Internship: 0.2 years
        - Total (exclude internship): 1.0 year, internship_years = 0.2
        """
        exp = [
            MockExperience(from_date=date(2020, 1, 1), to_date=date(2021, 1, 1), employment_type="Full-time"),
            MockExperience(from_date=date(2021, 7, 1), to_date=date(2021, 9, 1), employment_type="Internship"),
        ]
        total, internship = total_experience_years(exp, as_of=date(2021, 9, 1), include_internships=False)
        assert abs(total - 1.0) < 0.1
        assert abs(internship - 0.17) < 0.05  # Jul-Sep = ~2 months = 0.17 years, rounds to 0.2

    def test_no_experience_returns_zero(self):
        """Employee with no experience rows returns (0.0, 0.0)."""
        total, internship = total_experience_years([])
        assert total == 0.0
        assert internship == 0.0

    def test_leap_year_edge(self):
        """Leap year edge case:
        - Jan 1, 2020 (leap year) to Jan 1, 2021 = 366 days ≈ 1.0 years
        """
        exp = [MockExperience(
            from_date=date(2020, 1, 1),
            to_date=date(2021, 1, 1),
        )]
        total, internship = total_experience_years(exp, as_of=date(2021, 1, 1))
        assert abs(total - 1.0) < 0.1

    def test_decimal_years_rounded_to_one_place(self):
        """Years should be rounded to 1 decimal place:
        - 1 year 182 days ≈ 1.5 years
        """
        exp = [MockExperience(
            from_date=date(2020, 1, 1),
            to_date=date(2021, 7, 1),
        )]
        total, internship = total_experience_years(exp, as_of=date(2021, 7, 1))
        # Should be rounded to 1 decimal
        assert isinstance(total, float)
        assert total == round(total, 1)


class TestExperienceInRole:
    """Test experience_in_role (matching specific role/vertical)."""

    def test_matching_role(self):
        """Experience in matching role:
        - Software Engineer: Jan 2020 - Jan 2023 (3 years, matches 'Software')
        - Total: 3.0 years
        """
        exp = [MockExperience(
            from_date=date(2020, 1, 1),
            to_date=date(2023, 1, 1),
            role="Software Engineer",
        )]
        years = experience_in_role(exp, target_job_role="Software")
        assert abs(years - 3.0) < 0.1

    def test_non_matching_role(self):
        """Experience in non-matching role:
        - Sales Manager: Jan 2020 - Jan 2023
        - Looking for: 'Software'
        - Total: 0.0 years (no match)
        """
        exp = [MockExperience(
            from_date=date(2020, 1, 1),
            to_date=date(2023, 1, 1),
            role="Sales Manager",
        )]
        years = experience_in_role(exp, target_job_role="Software")
        assert years == 0.0

    def test_partial_role_match_in_designation(self):
        """Partial match in designation field:
        - Role: "Engineer", Designation: "Data Science Engineer"
        - Looking for: 'Data'
        - Total: matched (0.5 years)
        """
        exp = [MockExperience(
            from_date=date(2023, 1, 1),
            to_date=date(2023, 7, 1),
            role="Engineer",
            designation="Data Science Engineer",
        )]
        years = experience_in_role(exp, target_job_role="Data")
        assert abs(years - 0.5) < 0.1

    def test_no_matching_roles(self):
        """No roles match returns 0.0."""
        exp = [
            MockExperience(from_date=date(2020, 1, 1), to_date=date(2021, 1, 1), role="Sales"),
            MockExperience(from_date=date(2021, 1, 1), to_date=date(2022, 1, 1), role="Marketing"),
        ]
        years = experience_in_role(exp, target_job_role="Engineering")
        assert years == 0.0
