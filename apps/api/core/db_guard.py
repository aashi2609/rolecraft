"""Database isolation safety guard.

Prevents migration test runs and pytest test suites from accidentally
connecting to the primary production database.
"""

from __future__ import annotations

import os
from sqlalchemy.engine.url import make_url

# ── Primary Neon endpoint denylist ─────────────────────────────────────
# These endpoint IDs are known production databases that must never be
# used for testing or migration runs without explicit ALLOW_PRIMARY_MIGRATIONS=1
# Can be overridden via PRIMARY_ENDPOINT_ID environment variable
_DEFAULT_PRIMARY_ENDPOINT = "ep-fragrant-salad-aybt4nuh"
PRIMARY_ENDPOINT_DENYLIST = {
    os.getenv("PRIMARY_ENDPOINT_ID", _DEFAULT_PRIMARY_ENDPOINT),
}
PRIMARY_DB_NAME = "neondb"


def extract_db_identity(url_str: str) -> tuple[str, str, int | None, str]:
    """Extract (endpoint_or_normalized_host, database_name, port, host_type) from a DB URL."""
    if not url_str or not url_str.strip():
        return ("", "", None, "empty")
    
    url = make_url(url_str.strip())
    host = (url.host or "").lower().strip()
    db_name = (url.database or "").strip()
    port = url.port

    # If this is a Neon host, strip "-pooler" to get the root endpoint ID
    # e.g., 'ep-fragrant-salad-aybt4nuh-pooler.c-5.us-east-2.aws.neon.tech' -> 'ep-fragrant-salad-aybt4nuh'
    if "neon.tech" in host:
        endpoint_id = host.split(".")[0]
        if endpoint_id.endswith("-pooler"):
            endpoint_id = endpoint_id[:-7]  # remove '-pooler'
        return (endpoint_id, db_name, port, "neon")

    # Localhost / local IP normalization
    if host in ("localhost", "127.0.0.1", "::1", ""):
        return ("localhost", db_name, port or 5432, "local")

    return (host, db_name, port, "standard")


def is_same_database(url1_str: str, url2_str: str) -> bool:
    """Check if two connection strings resolve to the exact same database.
    
    Handles:
    - Neon pooled vs direct URLs (ep-*-pooler vs ep-*)
    - localhost vs 127.0.0.1
    - Exact URL matches
    """
    if not url1_str or not url2_str:
        return False
    if url1_str.strip() == url2_str.strip():
        return True

    id1 = extract_db_identity(url1_str)
    id2 = extract_db_identity(url2_str)

    # If either failed to parse or is empty
    if not id1[0] or not id2[0] or not id1[1] or not id2[1]:
        return False

    # For Neon: match on root endpoint ID + database name
    if id1[3] == "neon" and id2[3] == "neon":
        return id1[0] == id2[0] and id1[1] == id2[1]

    # For Localhost: match on local host + port + db name
    if id1[3] == "local" and id2[3] == "local":
        return id1[1] == id2[1] and id1[2] == id2[2]

    # Standard host: match on normalized host + db name
    return id1[0] == id2[0] and id1[1] == id2[1] and id1[2] == id2[2]


def is_primary_endpoint(endpoint_id: str) -> bool:
    """Check if an endpoint ID is in the primary denylist."""
    return endpoint_id in PRIMARY_ENDPOINT_DENYLIST


def enforce_isolated_test_database(
    test_db_url: str | None, primary_db_url: str | None = None
) -> None:
    """Enforce that test_db_url is set and does not resolve to the primary database.

    Primary identity comes from ``PRIMARY_ENDPOINT_DENYLIST`` (fixed endpoint IDs),
    NOT from ``settings.database_url`` — that value is often rewritten to the test
    URL before this runs.

    Raises RuntimeError if test_db_url is missing, its Neon endpoint is denylisted,
    or (when ``primary_db_url`` is provided) it resolves to the same database.
    """
    if not test_db_url or not test_db_url.strip():
        raise RuntimeError(
            "FATAL: TEST_DATABASE_URL is not set or empty. "
            "Testing requires an isolated database (e.g., local Postgres or a Neon branch). "
            "Refusing to execute against default database."
        )

    # Authoritative check: fixed denylist of production Neon endpoint IDs
    t_info = extract_db_identity(test_db_url)
    if t_info[3] == "neon" and is_primary_endpoint(t_info[0]):
        raise RuntimeError(
            f"FATAL: TEST_DATABASE_URL endpoint '{t_info[0]}' is in the primary denylist. "
            "Refusing to run tests or migrations against a production database. "
            "Use a Neon *branch* (different endpoint) or local Postgres."
        )

    # Optional secondary check against a pre-override primary URL snapshot
    if primary_db_url and primary_db_url.strip():
        if is_same_database(test_db_url, primary_db_url):
            p_info = extract_db_identity(primary_db_url)
            raise RuntimeError(
                f"FATAL: TEST_DATABASE_URL resolves to the primary database! "
                f"Primary endpoint/host='{p_info[0]}', db='{p_info[1]}' vs "
                f"Test endpoint/host='{t_info[0]}', db='{t_info[1]}'. "
                "Refusing to run tests or migrations against the primary database."
            )
