#!/usr/bin/env python
"""Seed realistic volume for performance testing (7A Item 2).

Idempotent script that creates:
- 20,000 candidates with profiles/skills/experience
- 300 companies
- 5,000 jobs (mixed statuses)
- 30,000 applications
- 2,000 conversations with 50,000 messages
- 20,000 notifications

All data is tagged with seed_group='perf_test' for cleanup.

Usage:
    python scripts/seed_perf.py
    python scripts/seed_perf.py --cleanup  # Remove seeded data
    python scripts/seed_perf.py --check    # Show current counts
"""

import asyncio
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from core.database import asyncpg_engine_kwargs
from models import (
    User, UserRole, Company, CandidateProfile, Experience,
    JobPosting, JobStatus, Skill, Application, ApplicationStatus,
    Conversation, Message, Notification, NotificationType,
    Subscription, SubscriptionStatus, PlanTier
)

SEED_GROUP = "perf_test"
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "").strip()

if not TEST_DB_URL:
    print("ERROR: TEST_DATABASE_URL not set", file=sys.stderr)
    sys.exit(1)


async def get_session() -> AsyncSession:
    """Create async session."""
    db_url, connect_args = asyncpg_engine_kwargs(TEST_DB_URL)
    engine = create_async_engine(db_url, connect_args=connect_args)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return factory(), engine


async def check_counts(session: AsyncSession):
    """Display current row counts."""
    tables = [
        "users", "companies", "candidate_profiles", "job_postings",
        "applications", "conversations", "messages", "notifications",
        "subscriptions"
    ]
    print("\n--- Current Row Counts ---")
    for table in tables:
        try:
            cnt = await session.scalar(text(f"SELECT COUNT(*) FROM {table};"))
            print(f"  {table}: {cnt}")
        except Exception as e:
            print(f"  {table}: ERROR ({e.__class__.__name__})")


async def cleanup(session: AsyncSession):
    """Remove all seeded data (marked with seed_group='perf_test')."""
    print("\n--- Cleaning up seeded data ---")
    
    # Delete in order of dependencies
    # Messages first (FK to conversations)
    result = await session.execute(
        text("DELETE FROM messages WHERE seed_group = :sg"),
        {"sg": SEED_GROUP}
    )
    print(f"  Deleted {result.rowcount} messages")
    
    # Conversations
    result = await session.execute(
        text("DELETE FROM conversations WHERE seed_group = :sg"),
        {"sg": SEED_GROUP}
    )
    print(f"  Deleted {result.rowcount} conversations")
    
    # Notifications
    result = await session.execute(
        text("DELETE FROM notifications WHERE seed_group = :sg"),
        {"sg": SEED_GROUP}
    )
    print(f"  Deleted {result.rowcount} notifications")
    
    # Applications
    result = await session.execute(
        text("DELETE FROM applications WHERE seed_group = :sg"),
        {"sg": SEED_GROUP}
    )
    print(f"  Deleted {result.rowcount} applications")
    
    # Subscriptions
    result = await session.execute(
        text("DELETE FROM subscriptions WHERE seed_group = :sg"),
        {"sg": SEED_GROUP}
    )
    print(f"  Deleted {result.rowcount} subscriptions")
    
    # Job postings
    result = await session.execute(
        text("DELETE FROM job_postings WHERE seed_group = :sg"),
        {"sg": SEED_GROUP}
    )
    print(f"  Deleted {result.rowcount} job_postings")
    
    # Skills
    result = await session.execute(
        text("DELETE FROM skills WHERE seed_group = :sg"),
        {"sg": SEED_GROUP}
    )
    print(f"  Deleted {result.rowcount} skills")
    
    # Experience
    result = await session.execute(
        text("DELETE FROM experience WHERE seed_group = :sg"),
        {"sg": SEED_GROUP}
    )
    print(f"  Deleted {result.rowcount} experience")
    
    # Candidate profiles
    result = await session.execute(
        text("DELETE FROM candidate_profiles WHERE seed_group = :sg"),
        {"sg": SEED_GROUP}
    )
    print(f"  Deleted {result.rowcount} candidate_profiles")
    
    # Companies
    result = await session.execute(
        text("DELETE FROM companies WHERE seed_group = :sg"),
        {"sg": SEED_GROUP}
    )
    print(f"  Deleted {result.rowcount} companies")
    
    # Users
    result = await session.execute(
        text("DELETE FROM users WHERE seed_group = :sg"),
        {"sg": SEED_GROUP}
    )
    print(f"  Deleted {result.rowcount} users")
    
    await session.commit()
    print("\nCleanup complete")


async def seed_data(session: AsyncSession):
    """Seed realistic test data."""
    print("\n--- Seeding Performance Test Data ---")
    
    now = datetime.now(timezone.utc)
    
    # Skip if already seeded
    existing = await session.scalar(
        text("SELECT COUNT(*) FROM users WHERE seed_group = :sg"),
        {"sg": SEED_GROUP}
    )
    if existing and existing > 0:
        print(f"WARNING: {existing} seeded users already exist. Skipping seed.")
        return
    
    # 1. Create 300 companies
    print("  Creating 300 companies...")
    companies = []
    for i in range(300):
        company_user = User(
            id=uuid4(),
            email=f"company_perf_{i}@test.com",
            password_hash="$2b$12$hash",
            role=UserRole.company,
            is_active=True,
            seed_group=SEED_GROUP,
        )
        session.add(company_user)
        await session.flush()
        
        company = Company(
            user_id=company_user.id,
            name=f"Company {i}",
            seed_group=SEED_GROUP,
        )
        session.add(company)
        companies.append((company_user.id, company))
    
    await session.commit()
    print(f"    Created {len(companies)} companies")
    
    # 2. Create 20,000 candidates with profiles/skills/experience
    print("  Creating 20,000 candidates with profiles...")
    candidates = []
    for i in range(20000):
        if i % 2000 == 0:
            print(f"    {i}/20000...")
        
        user = User(
            id=uuid4(),
            email=f"candidate_perf_{i}@test.com",
            password_hash="$2b$12$hash",
            role=UserRole.candidate,
            is_active=True,
            seed_group=SEED_GROUP,
        )
        session.add(user)
        await session.flush()
        
        profile = CandidateProfile(
            user_id=user.id,
            weblinks={"linkedin": f"https://linkedin.com/{i}"},
            seed_group=SEED_GROUP,
        )
        session.add(profile)
        
        # Add 2-3 skills
        for j in range(2 + (i % 2)):
            skill = Skill(
                candidate_id=user.id,
                skill_name=f"Skill_{j}",
                seed_group=SEED_GROUP,
            )
            session.add(skill)
        
        # Add 1-2 experience entries
        for j in range(1 + (i % 2)):
            start = now - timedelta(days=365 * (5 - j))
            exp = Experience(
                candidate_id=user.id,
                role=f"Role_{j}",
                from_date=start.date(),
                to_date=(start + timedelta(days=365)).date(),
                designation=f"Designation_{j}",
                seed_group=SEED_GROUP,
            )
            session.add(exp)
        
        # Add subscription
        sub = Subscription(
            user_id=user.id,
            role=UserRole.candidate,
            plan_tier=PlanTier.complete,
            status=SubscriptionStatus.active,
            seed_group=SEED_GROUP,
        )
        session.add(sub)
        
        candidates.append(user)
    
    await session.commit()
    print(f"    Created {len(candidates)} candidates with skills/experience")
    
    # 3. Create 5,000 jobs (mixed statuses)
    print("  Creating 5,000 jobs...")
    jobs = []
    statuses = [JobStatus.open, JobStatus.closed, JobStatus.draft, JobStatus.filled]
    for i in range(5000):
        if i % 500 == 0:
            print(f"    {i}/5000...")
        
        company_user_id, _ = companies[i % len(companies)]
        
        job = JobPosting(
            company_id=company_user_id,
            title=f"Job_{i}",
            description=f"Job description {i}",
            status=statuses[i % len(statuses)],
            posted_at=now - timedelta(days=i % 90),
            seed_group=SEED_GROUP,
        )
        session.add(job)
        jobs.append(job)
    
    await session.commit()
    print(f"    Created {len(jobs)} jobs")
    
    # 4. Create 30,000 applications
    print("  Creating 30,000 applications...")
    app_statuses = [ApplicationStatus.applied, ApplicationStatus.rejected, 
                    ApplicationStatus.shortlisted, ApplicationStatus.accepted]
    for i in range(30000):
        if i % 3000 == 0:
            print(f"    {i}/30000...")
        
        candidate = candidates[i % len(candidates)]
        job = jobs[i % len(jobs)]
        
        app = Application(
            candidate_id=candidate.id,
            job_id=job.id,
            status=app_statuses[i % len(app_statuses)],
            applied_at=now - timedelta(days=i % 60),
            seed_group=SEED_GROUP,
        )
        session.add(app)
    
    await session.commit()
    print(f"    Created 30,000 applications")
    
    # 5. Create 2,000 conversations with 50,000 messages (25 per conversation avg)
    print("  Creating 2,000 conversations with ~50,000 messages...")
    conversations = []
    message_count = 0
    for i in range(2000):
        if i % 200 == 0:
            print(f"    {i}/2000 conversations...")
        
        candidate = candidates[i % len(candidates)]
        company_user_id, _ = companies[i % len(companies)]
        
        conv = Conversation(
            candidate_id=candidate.id,
            company_id=company_user_id,
            seed_group=SEED_GROUP,
        )
        session.add(conv)
        await session.flush()
        conversations.append(conv)
        
        # Add 25 messages per conversation
        for j in range(25):
            sender_id = candidate.id if j % 2 == 0 else company_user_id
            msg = Message(
                conversation_id=conv.id,
                sender_id=sender_id,
                body=f"Message {j} in conversation {i}",
                created_at=now - timedelta(hours=25 - j),
                seed_group=SEED_GROUP,
            )
            session.add(msg)
            message_count += 1
    
    await session.commit()
    print(f"    Created {len(conversations)} conversations with {message_count} messages")
    
    # 6. Create 20,000 notifications
    print("  Creating 20,000 notifications...")
    notif_types = [NotificationType.application_status, NotificationType.message,
                   NotificationType.job_match, NotificationType.subscription_expiry]
    for i in range(20000):
        if i % 2000 == 0:
            print(f"    {i}/20000...")
        
        user = candidates[i % len(candidates)] if i % 2 == 0 else User(id=companies[i % len(companies)][0])
        
        notif = Notification(
            user_id=user.id,
            type=notif_types[i % len(notif_types)],
            title=f"Notification {i}",
            body=f"Body for notification {i}",
            read=False,
            created_at=now - timedelta(hours=i % 24),
            seed_group=SEED_GROUP,
        )
        session.add(notif)
    
    await session.commit()
    print(f"    Created 20,000 notifications")
    
    print("\n--- Seed Complete ---")
    await check_counts(session)


async def main():
    parser = argparse.ArgumentParser(description="Performance test data seeding")
    parser.add_argument("--cleanup", action="store_true", help="Remove seeded data")
    parser.add_argument("--check", action="store_true", help="Show current counts")
    args = parser.parse_args()
    
    session, engine = await get_session()
    
    try:
        if args.check:
            await check_counts(session)
        elif args.cleanup:
            await cleanup(session)
        else:
            await seed_data(session)
    finally:
        await session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
