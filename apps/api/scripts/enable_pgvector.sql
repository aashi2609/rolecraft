-- Run once on the target Postgres database if needed (Neon SQL Editor / psql).
-- Also executed as the first statement of alembic/versions/0001_initial.py.
-- On Neon, pgvector is available on all plans; CREATE EXTENSION is still required per database.
CREATE EXTENSION IF NOT EXISTS vector;
