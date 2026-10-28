"""Migration tests for RoleCraft database.

Tests run against a throwaway database using the real Alembic runner.
This ensures migrations work correctly end-to-end.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.database import asyncpg_engine_kwargs

# ── Test Configuration ────────────────────────────────────────────────────
TEST_DB_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DB_URL:
    pytest.skip("TEST_DATABASE_URL not set", allow_module_level=True)


def run_alembic_command(
    args: list[str], cwd: Path, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    """Run an Alembic command and return the result."""
    alembic_exe = Path(sys.executable).parent / ("alembic.exe" if os.name == "nt" else "alembic")
    cmd = [str(alembic_exe)] + args if alembic_exe.exists() else [sys.executable, "-m", "alembic"] + args
    env = os.environ.copy()
    env["TEST_DATABASE_URL"] = TEST_DB_URL
    env["DATABASE_URL"] = TEST_DB_URL
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )


def get_table_count(table_name: str) -> int:
    """Get row count for a table using asyncpg."""
    async def _query() -> int:
        db_url, connect_args = asyncpg_engine_kwargs(TEST_DB_URL)
        connect_args["statement_cache_size"] = 0
        engine = create_async_engine(db_url, connect_args=connect_args)
        async with engine.connect() as conn:
            cnt = (await conn.execute(text(f"SELECT COUNT(*) FROM {table_name};"))).scalar()
        await engine.dispose()
        return cnt or 0
    return asyncio.run(_query())


def seed_old_structure_messages() -> None:
    """Seed messages with old structure for conversation migration testing."""
    async def _seed() -> None:
        db_url, connect_args = asyncpg_engine_kwargs(TEST_DB_URL)
        connect_args["statement_cache_size"] = 0
        engine = create_async_engine(db_url, connect_args=connect_args)
        async with engine.begin() as conn:
            # Insert test users
            await conn.execute(text("""
                INSERT INTO users (id, email, password_hash, role) VALUES
                    ('11111111-1111-1111-1111-111111111111', 'company@test.com', 'hash', 'company'),
                    ('22222222-2222-2222-2222-222222222222', 'candidate@test.com', 'hash', 'candidate')
                ON CONFLICT (id) DO NOTHING;
            """))
            # Insert profiles
            await conn.execute(text("""
                INSERT INTO companies (user_id, name) VALUES
                    ('11111111-1111-1111-1111-111111111111', 'Test Company')
                ON CONFLICT (user_id) DO NOTHING;
            """))
            await conn.execute(text("""
                INSERT INTO candidate_profiles (user_id) VALUES
                    ('22222222-2222-2222-2222-222222222222')
                ON CONFLICT (user_id) DO NOTHING;
            """))
            # Clean up old messages before seeding
            await conn.execute(text("DELETE FROM messages;"))
            # Seed messages with old structure (thread_id based)
            # Tier 1: Direct (sender_role + recipient_id)
            await conn.execute(text("""
                INSERT INTO messages (id, thread_id, sender_id, sender_role, recipient_id, body) VALUES
                    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
                     '33333333-3333-3333-3333-333333333333',
                     '11111111-1111-1111-1111-111111111111',
                     'company',
                     '22222222-2222-2222-2222-222222222222',
                     'Direct message test');
            """))
            # Tier 2: Thread peers (no recipient_id on message)
            await conn.execute(text("""
                INSERT INTO messages (id, thread_id, sender_id, sender_role, body) VALUES
                    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
                     '33333333-3333-3333-3333-333333333333',
                     '22222222-2222-2222-2222-222222222222',
                     'candidate',
                     'Thread peer test');
            """))
            # Tier 3: Unmappable (isolated thread, no other participant/company peer)
            await conn.execute(text("""
                INSERT INTO messages (id, thread_id, sender_id, sender_role, body) VALUES
                    ('cccccccc-cccc-cccc-cccc-cccccccccccc',
                     '44444444-4444-4444-4444-444444444444',
                     '22222222-2222-2222-2222-222222222222',
                     'candidate',
                     'Unmappable message (isolated thread, no company peer)');
            """))
        await engine.dispose()
    asyncio.run(_seed())


def get_enum_values(enum_type: str) -> list[str]:
    """Get enum values for a Postgres enum type."""
    async def _query() -> list[str]:
        db_url, connect_args = asyncpg_engine_kwargs(TEST_DB_URL)
        connect_args["statement_cache_size"] = 0
        engine = create_async_engine(db_url, connect_args=connect_args)
        async with engine.connect() as conn:
            rows = (await conn.execute(text(
                "SELECT e.enumlabel FROM pg_enum e "
                "JOIN pg_type t ON e.enumtypid = t.oid "
                f"WHERE t.typname = '{enum_type}';"
            ))).scalars().all()
        await engine.dispose()
        return list(rows)
    return asyncio.run(_query())


@pytest.fixture(scope="module")
def api_root() -> Path:
    """Get the API root directory."""
    return Path(__file__).resolve().parent.parent


class TestConversationMigration:
    """Test the conversation model migration (e6c7d8e9f0a1)."""

    def test_upgrade_to_conversation_preserves_data(self, api_root: Path) -> None:
        """Test that upgrading to conversation model preserves all messages."""
        # Build to revision before conversation migration (downgrade first if already past it)
        run_alembic_command(
            ["downgrade", "d5b69ec5aecb"],
            api_root,
            extra_env={"ALLOW_DESTRUCTIVE_DOWNGRADE": "1"},
        )
        result = run_alembic_command(["upgrade", "d5b69ec5aecb"], api_root)
        assert result.returncode == 0, f"Alembic upgrade failed: {result.stderr}"

        # Seed old-structure messages
        seed_old_structure_messages()

        # Get original message count
        original_count = get_table_count("messages")
        assert original_count == 3, f"Expected 3 messages, got {original_count}"

        # Upgrade to conversation migration
        result = run_alembic_command(["upgrade", "e6c7d8e9f0a1"], api_root)
        assert result.returncode == 0, f"Conversation migration failed: {result.stderr}"

        # Check row conservation: messages + quarantine = original
        messages_count = get_table_count("messages")
        quarantine_count = get_table_count("messages_quarantine")

        assert messages_count + quarantine_count == original_count, (
            f"Row count mismatch: messages({messages_count}) + quarantine({quarantine_count}) "
            f"= {messages_count + quarantine_count}, expected {original_count}"
        )

        # Verify conversations table was created
        conversations_count = get_table_count("conversations")
        assert conversations_count > 0, "Conversations table should have at least one conversation"

    def test_upgrade_to_head(self, api_root: Path) -> None:
        """Test upgrading from conversation migration to head."""
        result = run_alembic_command(["upgrade", "head"], api_root)
        assert result.returncode == 0, f"Upgrade to head failed: {result.stderr}"

    def test_downgrade_requires_flag(self, api_root: Path) -> None:
        """Test that downgrade requires ALLOW_DESTRUCTIVE_DOWNGRADE flag."""
        result = run_alembic_command(["downgrade", "-1"], api_root)
        assert result.returncode != 0, "Downgrade should fail without ALLOW_DESTRUCTIVE_DOWNGRADE"
        assert "ALLOW_DESTRUCTIVE_DOWNGRADE" in result.stderr or "Refusing" in result.stderr

    def test_downgrade_with_flag(self, api_root: Path) -> None:
        """Test that downgrade succeeds with ALLOW_DESTRUCTIVE_DOWNGRADE flag."""
        result = run_alembic_command(
            ["downgrade", "-1"],
            api_root,
            extra_env={"ALLOW_DESTRUCTIVE_DOWNGRADE": "1"},
        )
        assert result.returncode == 0, f"Downgrade with flag failed: {result.stderr}"

    def test_upgrade_again(self, api_root: Path) -> None:
        """Test upgrading again after downgrade."""
        result = run_alembic_command(["upgrade", "head"], api_root)
        assert result.returncode == 0, f"Re-upgrade failed: {result.stderr}"


class TestFullMigrationChain:
    """Test the full migration chain from empty to head."""

    def test_upgrade_empty_to_head(self, api_root: Path) -> None:
        """Test upgrading from empty database to head."""
        # Reset to base with flag
        result = run_alembic_command(
            ["downgrade", "base"],
            api_root,
            extra_env={"ALLOW_DESTRUCTIVE_DOWNGRADE": "1"},
        )
        assert result.returncode == 0, f"Downgrade to base failed: {result.stderr}"

        # Upgrade to head
        result = run_alembic_command(["upgrade", "head"], api_root)
        assert result.returncode == 0, f"Empty to head upgrade failed: {result.stderr}"

    def test_alembic_check_no_drift(self, api_root: Path) -> None:
        """Test that alembic check reports no drift."""
        result = run_alembic_command(["check"], api_root)
        assert (
            "Target database is up to date" in result.stdout
            or "No errors" in result.stdout
            or "No new upgrade operations detected" in result.stdout
            or result.returncode == 0
        )

    def test_alembic_heads_single_head(self, api_root: Path) -> None:
        """Test that alembic heads returns exactly one head."""
        result = run_alembic_command(["heads"], api_root)
        assert result.returncode == 0, f"Alembic heads failed: {result.stderr}"
        head_lines = [line for line in result.stdout.split("\n") if line.strip()]
        assert len(head_lines) == 1, f"Expected 1 head, got {len(head_lines)}"


class TestEnumMigration:
    """Test the enum value sync migration (b4c5d6e7f8a9)."""

    def test_enum_values_added(self, api_root: Path) -> None:
        """Test that enum values are added correctly."""
        # Reset to before enum migration
        result = run_alembic_command(
            ["downgrade", "a2b3c4d5e6f7"],
            api_root,
            extra_env={"ALLOW_DESTRUCTIVE_DOWNGRADE": "1"},
        )
        # Downgrade may succeed or fail depending on whether head has changed, but let's upgrade
        result = run_alembic_command(["upgrade", "b4c5d6e7f8a9"], api_root)
        assert result.returncode == 0, f"Enum migration failed: {result.stderr}"

        # Check that new enum values exist
        enum_values = get_enum_values("plan_tier")
        new_values = ["resume_builder", "job_search", "complete", "corporate_annual", "corporate_lifetime"]
        for value in new_values:
            assert value in enum_values, f"Enum value {value} not found in plan_tier: {enum_values}"

        # Re-upgrade to head
        run_alembic_command(["upgrade", "head"], api_root)
