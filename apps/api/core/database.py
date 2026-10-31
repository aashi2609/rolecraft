from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import get_settings

settings = get_settings()

# Query keys libpq/Neon put in the URL that asyncpg does not accept as-is.
_ASYNCPG_STRIP_QUERY_KEYS = frozenset({"sslmode", "ssl", "channel_binding"})


def asyncpg_engine_kwargs(database_url: str) -> tuple[str, dict[str, Any]]:
    """Normalize a DATABASE_URL for asyncpg + Neon.

    Neon requires TLS. asyncpg expects SSL via connect_args (not libpq's
    ``sslmode=`` query param). Prefer Neon's pooled host (``*-pooler.*``).
    """
    url = make_url(database_url)
    if url.drivername in ("postgresql", "postgres"):
        url = url.set(drivername="postgresql+asyncpg")
    query = dict(url.query)
    connect_args: dict[str, Any] = {}

    ssl_hint = query.get("sslmode") or query.get("ssl")
    host = (url.host or "").lower()
    needs_ssl = bool(ssl_hint) or host.endswith("neon.tech") or "-pooler." in host

    for key in _ASYNCPG_STRIP_QUERY_KEYS:
        query.pop(key, None)

    if needs_ssl:
        # asyncpg: True / SSLContext / "require" — prefer explicit require for Neon.
        connect_args["ssl"] = "require"

    # PgBouncer / Neon pooler and dynamic migrations require disabling prepared statement cache
    if "-pooler." in host or "pytest" in sys.modules or os.getenv("TEST_DATABASE_URL"):
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_cache_size"] = 0

    clean_url = url.set(query=query)
    return clean_url.render_as_string(hide_password=False), connect_args


import os
import sys
from sqlalchemy.pool import NullPool

_is_test = bool(os.getenv("TEST_DATABASE_URL")) or "pytest" in sys.modules

_db_url, _connect_args = asyncpg_engine_kwargs(settings.database_url)

_engine_kwargs: dict[str, Any] = {
    "echo": False,
    "connect_args": _connect_args,
}
if _is_test:
    _engine_kwargs["poolclass"] = NullPool
else:
    # Neon scale-to-zero can drop idle connections; ping before checkout.
    _engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(_db_url, **_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
