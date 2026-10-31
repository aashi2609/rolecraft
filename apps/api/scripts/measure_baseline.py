#!/usr/bin/env python
"""Measure baseline performance for key endpoints (7A Item 3).

Measures query count, DB time, and total latency for each endpoint.
- Runs 20 calls per endpoint
- Reports p50 (median) latency
- Requires seeded data (run seed_perf.py first)

Usage:
    python scripts/measure_baseline.py
"""

import asyncio
import os
import sys
import time
import statistics
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from httpx import AsyncClient
from main import app
from core.config import get_settings
from core.security import create_access_token

# Settings
ITERATIONS = 20
PAGE_SIZE = 10

# Test user IDs (create these via seed or from database)
CANDIDATE_ID = None
COMPANY_ID = None


async def get_test_users() -> tuple:
    """Get or create test users."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from core.database import asyncpg_engine_kwargs
    
    test_db_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not test_db_url:
        print("ERROR: TEST_DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    
    db_url, connect_args = asyncpg_engine_kwargs(test_db_url)
    engine = create_async_engine(db_url, connect_args=connect_args)
    
    async with engine.connect() as conn:
        # Get a candidate
        candidate_row = await conn.execute(
            text("SELECT id FROM users WHERE role = 'candidate' AND seed_group = 'perf_test' LIMIT 1")
        )
        candidate_id = candidate_row.scalar()
        
        # Get a company
        company_row = await conn.execute(
            text("SELECT id FROM users WHERE role = 'company' AND seed_group = 'perf_test' LIMIT 1")
        )
        company_id = company_row.scalar()
    
    await engine.dispose()
    
    if not candidate_id or not company_id:
        print("ERROR: No seeded test users found. Run seed_perf.py first.", file=sys.stderr)
        sys.exit(1)
    
    return candidate_id, company_id


async def measure_endpoint(
    client: AsyncClient,
    method: str,
    path: str,
    headers: dict = None,
    params: dict = None,
    name: str = None,
) -> dict:
    """Measure a single endpoint."""
    name = name or f"{method} {path}"
    
    latencies = []
    query_counts = []
    db_times = []
    
    print(f"\n  Measuring {name}...", end=" ", flush=True)
    
    for i in range(ITERATIONS):
        start = time.time()
        
        try:
            if method == "GET":
                response = await client.get(path, headers=headers, params=params)
            elif method == "POST":
                response = await client.post(path, headers=headers, json=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            latency_ms = (time.time() - start) * 1000
            latencies.append(latency_ms)
            
            # Extract profiler headers
            query_count = int(response.headers.get("X-DB-Queries", 0))
            db_time = float(response.headers.get("X-DB-Time-Ms", 0))
            
            query_counts.append(query_count)
            db_times.append(db_time)
            
            if response.status_code >= 400:
                print(f"X", end="", flush=True)
            else:
                print(f".", end="", flush=True)
        
        except Exception as e:
            print(f"E", end="", flush=True)
            latencies.append(0)
            query_counts.append(0)
            db_times.append(0)
    
    print()
    
    # Calculate stats
    p50_latency = statistics.median(latencies)
    avg_query_count = statistics.mean(query_counts)
    avg_db_time = statistics.mean(db_times)
    
    return {
        "endpoint": name,
        "method": method,
        "path": path,
        "iterations": ITERATIONS,
        "p50_latency_ms": round(p50_latency, 2),
        "avg_queries": round(avg_query_count, 1),
        "avg_db_time_ms": round(avg_db_time, 2),
        "min_latency_ms": round(min(latencies), 2),
        "max_latency_ms": round(max(latencies), 2),
    }


async def main():
    global CANDIDATE_ID, COMPANY_ID
    
    print("=" * 70)
    print("BASELINE PERFORMANCE MEASUREMENT (7A Item 3)")
    print("=" * 70)
    
    # Get test users
    print("\nFetching test users...", end=" ", flush=True)
    CANDIDATE_ID, COMPANY_ID = await get_test_users()
    print(f"✓ (candidate: {CANDIDATE_ID}, company: {COMPANY_ID})")
    
    # Create tokens
    candidate_token = create_access_token(str(CANDIDATE_ID), UserRole.candidate)
    company_token = create_access_token(str(COMPANY_ID), UserRole.company)
    
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
    company_headers = {"Authorization": f"Bearer {company_token}"}
    
    # Measurement results
    results = []
    
    # Create async client
    async with AsyncClient(app=app, base_url="http://test") as client:
        print(f"\nRunning {ITERATIONS} iterations per endpoint...")
        
        # 1. Job search (candidate)
        result = await measure_endpoint(
            client,
            "GET",
            "/jobs/search",
            headers=candidate_headers,
            params={"page": 1, "page_size": PAGE_SIZE},
            name="Job Search (Candidate)",
        )
        results.append(result)
        
        # 2. My jobs (company)
        result = await measure_endpoint(
            client,
            "GET",
            "/company/jobs",
            headers=company_headers,
            params={"page": 1, "page_size": PAGE_SIZE},
            name="My Jobs (Company)",
        )
        results.append(result)
        
        # 3. My applications (candidate)
        result = await measure_endpoint(
            client,
            "GET",
            "/applications",
            headers=candidate_headers,
            params={"page": 1, "page_size": PAGE_SIZE},
            name="My Applications (Candidate)",
        )
        results.append(result)
        
        # 4. Notifications
        result = await measure_endpoint(
            client,
            "GET",
            "/notifications",
            headers=candidate_headers,
            params={"page": 1, "page_size": PAGE_SIZE},
            name="Notifications",
        )
        results.append(result)
        
        # 5. Message thread list
        result = await measure_endpoint(
            client,
            "GET",
            "/messages",
            headers=candidate_headers,
            params={"page": 1, "page_size": PAGE_SIZE},
            name="Message Thread List (Candidate)",
        )
        results.append(result)
    
    # Print results
    print("\n" + "=" * 70)
    print("BASELINE RESULTS")
    print("=" * 70)
    
    print(f"\n{'Endpoint':<40} {'p50 (ms)':<12} {'Queries':<10} {'DB (ms)':<10}")
    print("-" * 70)
    
    for result in results:
        print(
            f"{result['endpoint']:<40} "
            f"{result['p50_latency_ms']:<12} "
            f"{result['avg_queries']:<10} "
            f"{result['avg_db_time_ms']:<10}"
        )
    
    print("\n" + "=" * 70)
    print("RAW JSON OUTPUT")
    print("=" * 70)
    
    import json
    print(json.dumps(results, indent=2))
    
    print("\nBaseline measurement complete.")
    print("Save these results for comparison after fixes.")


if __name__ == "__main__":
    # Import here to avoid issues
    from models import UserRole
    
    asyncio.run(main())
