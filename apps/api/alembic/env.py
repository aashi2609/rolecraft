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
