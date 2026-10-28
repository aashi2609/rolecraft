import pytest
from core.db_guard import is_same_database, enforce_isolated_test_database, extract_db_identity, is_primary_endpoint

# Mark these tests to skip the database guard
pytestmark = pytest.mark.skip_db_guard

PRIMARY_POOLED = "postgresql+asyncpg://neondb_owner:npg_secret@ep-fragrant-salad-aybt4nuh-pooler.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"
PRIMARY_DIRECT = "postgresql+asyncpg://neondb_owner:npg_secret@ep-fragrant-salad-aybt4nuh.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"
BRANCH_URL = "postgresql+asyncpg://neondb_owner:npg_secret@ep-cool-breeze-12345678-pooler.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require"
DIFFERENT_DB_NAME = "postgresql+asyncpg://neondb_owner:npg_secret@ep-fragrant-salad-aybt4nuh-pooler.c-5.us-east-2.aws.neon.tech/test_branch_db?sslmode=require"
LOCAL_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/test_rolecraft"


def test_extract_db_identity_neon():
    eid1, db1, port1, type1 = extract_db_identity(PRIMARY_POOLED)
    eid2, db2, port2, type2 = extract_db_identity(PRIMARY_DIRECT)
    
    assert eid1 == "ep-fragrant-salad-aybt4nuh"
    assert eid2 == "ep-fragrant-salad-aybt4nuh"
    assert db1 == "neondb"
    assert db2 == "neondb"
    assert type1 == "neon"
    assert type2 == "neon"


def test_is_same_database_direct_vs_pooled():
    # Direct (non-pooler) must match pooled form of primary Neon DB
    assert is_same_database(PRIMARY_DIRECT, PRIMARY_POOLED) is True
    assert is_same_database(PRIMARY_POOLED, PRIMARY_DIRECT) is True


def test_is_same_database_different_neon_branch():
    # Different Neon endpoint is recognized as a different DB
    assert is_same_database(BRANCH_URL, PRIMARY_POOLED) is False


def test_is_same_database_different_db_name():
    # Different database on same cluster
    assert is_same_database(DIFFERENT_DB_NAME, PRIMARY_POOLED) is False


def test_is_same_database_local_vs_neon():
    assert is_same_database(LOCAL_URL, PRIMARY_POOLED) is False


def test_enforce_guard_refuses_direct_primary_url():
    # Feeding the direct (non-pooler) form of the primary URL MUST be refused (denylist).
    with pytest.raises(RuntimeError, match="primary denylist|resolves to the primary"):
        enforce_isolated_test_database(PRIMARY_DIRECT, PRIMARY_POOLED)


def test_enforce_guard_refuses_identical_primary_url():
    with pytest.raises(RuntimeError, match="primary denylist|resolves to the primary"):
        enforce_isolated_test_database(PRIMARY_POOLED, PRIMARY_POOLED)


def test_enforce_guard_blocks_same_endpoint_different_db_name():
    """rolecraft_empty on the primary endpoint must be refused — use a Neon branch."""
    with pytest.raises(RuntimeError, match="primary denylist"):
        enforce_isolated_test_database(DIFFERENT_DB_NAME, PRIMARY_POOLED)


def test_enforce_guard_refuses_empty_url():
    with pytest.raises(RuntimeError, match="FATAL: TEST_DATABASE_URL is not set or empty"):
        enforce_isolated_test_database("", PRIMARY_POOLED)
    with pytest.raises(RuntimeError, match="FATAL: TEST_DATABASE_URL is not set or empty"):
        enforce_isolated_test_database(None, PRIMARY_POOLED)


def test_enforce_guard_permits_isolated_databases():
    # Should not raise
    enforce_isolated_test_database(LOCAL_URL, PRIMARY_POOLED)
    enforce_isolated_test_database(BRANCH_URL, PRIMARY_POOLED)


def test_primary_endpoint_denylist_blocks_pooled():
    """Test that the primary endpoint denylist blocks pooled URLs."""
    with pytest.raises(RuntimeError, match="FATAL: TEST_DATABASE_URL endpoint.*is in the primary denylist"):
        enforce_isolated_test_database(PRIMARY_POOLED, PRIMARY_POOLED)


def test_primary_endpoint_denylist_blocks_direct():
    """Test that the primary endpoint denylist blocks direct URLs."""
    with pytest.raises(RuntimeError, match="FATAL: TEST_DATABASE_URL endpoint.*is in the primary denylist"):
        enforce_isolated_test_database(PRIMARY_DIRECT, PRIMARY_POOLED)


def test_is_primary_endpoint():
    """Test the is_primary_endpoint function."""
    assert is_primary_endpoint("ep-fragrant-salad-aybt4nuh") is True
    assert is_primary_endpoint("ep-cool-breeze-12345678") is False
    assert is_primary_endpoint("ep-fragrant-salad-aybt4nuh-pooler") is False  # normalized version
