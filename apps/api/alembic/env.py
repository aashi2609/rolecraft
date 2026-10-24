import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

import models  # noqa: F401 — register all models
from alembic import context
from core.config import get_settings
from core.database import Base, asyncpg_engine_kwargs

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
settings = get_settings()

import os
from sqlalchemy.engine.url import make_url

# ── 3A Safety Guard: Prevent running migration tests against primary DB ──
_is_test_migration = os.getenv("TEST_MIGRATIONS", "").lower() in ("1", "true", "yes")
_test_db_url = os.getenv("TEST_DATABASE_URL", "").strip()

if _is_test_migration:
    if not _test_db_url:
        raise RuntimeError(
            "FATAL: TEST_MIGRATIONS is enabled but TEST_DATABASE_URL is not set. "
            "Refusing to execute migrations against default database."
        )
    _primary_url = make_url(settings.database_url)
    _target_url = make_url(_test_db_url)
    if (_primary_url.host and _target_url.host and _primary_url.host.lower() == _target_url.host.lower() and _primary_url.database == _target_url.database) or settings.database_url.strip() == _test_db_url:
        raise RuntimeError(
            f"FATAL: TEST_DATABASE_URL matches primary database host/db ({_primary_url.host}/{_primary_url.database}). "
            "Refusing to run migration testing against the primary database."
        )
    _db_url, _connect_args = asyncpg_engine_kwargs(_test_db_url)
else:
    _db_url, _connect_args = asyncpg_engine_kwargs(settings.database_url)

# escape % for ConfigParser interpolation
config.set_main_option("sqlalchemy.url", _db_url.replace("%", "%%"))


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    # Prefer Neon's direct (non-pooler) host for DDL when possible; pooled works
    # for most Alembic upgrades but session-level features are limited on PgBouncer.
    section = dict(config.get_section(config.config_ini_section, {}) or {})
    section["sqlalchemy.url"] = _db_url
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=_connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
