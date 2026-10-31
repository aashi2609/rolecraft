"""Step 5E: Experience calculation from date ranges with interval merging.

Handles overlapping jobs, current roles, gaps, and edge cases correctly.
"""

from datetime import date, datetime
from typing import Optional
from decimal import Decimal


def total_experience_years(
    experience_rows,
    as_of: Optional[date] = None,
    include_internships: bool = True
) -> tuple[float, float]:
    """
    Calculate total years of experience by merging overlapping intervals.
    
    Args:
        experience_rows: List of Experience ORM objects with from_date, to_date, is_current, employment_type
        as_of: Reference date (default: today). Used for current roles.
        include_internships: If True, internships count toward total. Return separate internship total.
    
    Returns:
        (total_years, internship_years) as floats rounded to 1 decimal place
        
    Algorithm:
    1. Normalize dates (is_current or null to_date → as_of)
    2. Filter invalid rows (no from_date, to_date < from_date)
    3. Merge overlapping intervals
    4. Sum non-overlapping intervals
    5. Split internship vs regular experience
    6. Return both totals
    """
    if not experience_rows:
        return 0.0, 0.0
    
    if as_of is None:
        as_of = date.today()
    
    # Normalize intervals
    intervals = []
    for exp in experience_rows:
        from_dt = _to_date(exp.from_date)
        if not from_dt:
            continue  # Skip rows with no usable from_date
        
        # Determine to_date
        if exp.is_current or exp.to_date is None:
            to_dt = as_of
        else:
            to_dt = _to_date(exp.to_date)
            if not to_dt:
                continue
        
        # Clamp to_date to as_of
        if to_dt > as_of:
            to_dt = as_of
        
        # Skip invalid intervals
        if to_dt < from_dt:
            continue
        
        # Only include if interval has positive duration or is current/today
        if to_dt >= from_dt:
            is_internship = exp.employment_type and "internship" in exp.employment_type.lower()
            intervals.append((from_dt, to_dt, is_internship))
    
    if not intervals:
        return 0.0, 0.0
    
    # Merge overlapping intervals
    merged = _merge_intervals(intervals)
    
    # Calculate years, splitting by internship
    total_days = 0
    internship_days = 0
    
    for from_dt, to_dt, is_internship in merged:
        days = (to_dt - from_dt).days
        if is_internship and include_internships:
            internship_days += days
        elif not is_internship:
            total_days += days
    
    total_years = round(total_days / 365.25, 1)
    internship_years = round(internship_days / 365.25, 1)
    
    # Decide internship contribution
    if include_internships:
        return round(total_years + internship_years, 1), internship_years
    else:
        return total_years, internship_years


def _to_date(value) -> Optional[date]:
    """Convert datetime/date/string to date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    return None


def _merge_intervals(intervals: list[tuple[date, date, bool]]) -> list[tuple[date, date, bool]]:
    """
    Merge overlapping intervals, preserving internship flag.
    
    Args:
        intervals: List of (from_date, to_date, is_internship) tuples
    
    Returns:
        List of merged intervals with adjusted internship flags
    """
    if not intervals:
        return []
    
    # Sort by from_date, then to_date
    sorted_intervals = sorted(intervals, key=lambda x: (x[0], x[1]))
    
    merged = []
    current_start, current_end, current_is_internship = sorted_intervals[0]
    
    for next_start, next_end, next_is_internship in sorted_intervals[1:]:
        # Check if overlapping or adjacent
        if next_start <= current_end:
            # Merge
            current_end = max(current_end, next_end)
            # If either is internship, mark merged as internship
            current_is_internship = current_is_internship or next_is_internship
        else:
            # Gap found - save current interval
            merged.append((current_start, current_end, current_is_internship))
            current_start, current_end, current_is_internship = next_start, next_end, next_is_internship
    
    # Don't forget last interval
    merged.append((current_start, current_end, current_is_internship))
    
    return merged


def experience_in_role(experience_rows, target_job_role: str, as_of: Optional[date] = None) -> float:
    """
    Calculate years of experience in roles matching target job role/vertical.
    
    Args:
        experience_rows: List of Experience objects
        target_job_role: Job role to match (e.g., "Software Engineering", "Data")
        as_of: Reference date (default: today)
    
    Returns:
        Years of matching experience rounded to 1 decimal
    """
    if not experience_rows or not target_job_role:
        return 0.0
    
    if as_of is None:
        as_of = date.today()
    
    # Filter matching roles
    matching_intervals = []
    for exp in experience_rows:
        from_dt = _to_date(exp.from_date)
        if not from_dt:
            continue
        
        # Check if role matches (simple substring match)
        role_text = (exp.role or "") + " " + (exp.designation or "")
        if target_job_role.lower() not in role_text.lower():
            continue
        
        if exp.is_current or exp.to_date is None:
            to_dt = as_of
        else:
            to_dt = _to_date(exp.to_date)
            if not to_dt:
                continue
        
        if to_dt > as_of:
            to_dt = as_of
        
        if to_dt < from_dt:
            continue
        
        matching_intervals.append((from_dt, to_dt, False))
    
    if not matching_intervals:
        return 0.0
    
    merged = _merge_intervals(matching_intervals)
    total_days = sum((to_dt - from_dt).days for from_dt, to_dt, _ in merged)
    
    return round(total_days / 365.25, 1)
