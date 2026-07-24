# RoleCraft

RoleCraft is an AI-powered platform for resume writing and job matching, designed to connect candidates with the right opportunities using advanced vector search and automated resume optimization.

## 🏗️ Architecture

The project is built as a full-stack web application with the following stack:

### Frontend
- **Framework:** Next.js (React)
- **Styling:** Tailwind CSS (or similar, depending on configuration)
- **State Management:** React Context (`UserContext` connected to backend APIs)

### Backend (`apps/api`)
- **Framework:** FastAPI (Python 3.11/3.12)
- **Database:** PostgreSQL on [Neon](https://neon.tech) (Serverless Postgres)
- **ORM:** async SQLAlchemy 2.0
- **Vector Database:** `pgvector` extension for embeddings
- **Migrations:** Alembic
- **Authentication:** JWT (python-jose, bcrypt)
- **Storage:** Local / Google Cloud Storage

---

## 🚀 Setup Instructions

### Frontend Setup

```bash
# From the project root
cp .env.local.example .env.local
npm install
npm run dev
```
> Set `NEXT_PUBLIC_API_URL` to your API (default `http://127.0.0.1:8000`).

### Backend Setup (Stage 1)

See [`apps/api/README.md`](apps/api/README.md) for full details on Neon Postgres setup, migrations, and Cloud Run deploy.

```bash
cd apps/api
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Set DATABASE_URL in .env to your Neon pooled connection string

alembic upgrade head
uvicorn main:app --reload --port 8000
```

---

## 🗺️ Project Pipeline & Task Tracker

Based on our development roadmap, here is the current progress of the project:

### Stage 0: Design the UI first
- [x] Onboarding form UI
- [x] Personal details page
- [x] Resume download page
- [x] Candidate dashboard
- [x] Pricing page
- [x] Checkout page
- [x] Company dashboard UI
- [x] Reusable components
- [x] Stub all actions

### Stage 0b: Fill the missing frontend gaps
- [x] Job browse page
- [x] Job detail page
- [x] Apply flow
- [x] Candidate inbox
- [x] Resumes management
- [x] Saved jobs page
- [x] Public company profile
- [x] Checkout auth gate
- [x] Settings pages
- [x] Notifications
- [x] Forgot password
- [x] Empty states
- [x] Legal pages

### Stage 1: Connect a real backend
- [x] Set up the database (Neon Postgres + Alembic)
- [x] Set up login/signup (JWT Auth)
- [x] Replace stubbed forms (Wiring API endpoints to frontend Context)
- [ ] Deploy staging version (Cloud Run)

### Stage 2: Build the resume-writing AI
- [ ] Resume writing agent
- [ ] ATS score checker
- [ ] Auto-fix loop
- [ ] Multiple job types
- [ ] Download as PDF
- [ ] Handle messy data

### Stage 3: Build the job-matching AI
- [ ] Job posting data ingestion
- [ ] Resume fingerprinting (`pgvector`)
- [ ] Find likely matches
- [ ] AI double-checks shortlist
- [ ] Show results
- [ ] Scale performance

### Stage 4: Get production ready
- [ ] Test under load
- [ ] Add monitoring
- [ ] Security check
- [ ] Control AI costs
- [ ] Final UI polish
- [ ] Go live
