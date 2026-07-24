# RoleCraft

Next.js frontend (repo root) + FastAPI backend (`apps/api`).

## Frontend

```bash
cp .env.local.example .env.local
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL` to your API (default `http://127.0.0.1:8000`).

## Backend (Stage 1)

See [`apps/api/README.md`](apps/api/README.md) for Neon Postgres setup, migrations, uvicorn, and Cloud Run deploy.

```bash
cd apps/api
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn main:app --reload --port 8000
```
