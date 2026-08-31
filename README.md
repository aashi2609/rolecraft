# RoleCraft

RoleCraft is an AI-powered platform for resume writing and job matching, designed to connect candidates with the right opportunities using advanced vector search and automated resume optimization.

## 🏗️ Architecture

The project is built as a full-stack web application with the following stack:

### Frontend
- **Framework:** Next.js 16 (React 19)
- **Language:** TypeScript
- **Styling:** Tailwind CSS v4
- **State Management:** React Context (`UserContext` connected to backend APIs)
- **Payment:** Mock implementation (ready for Stripe/Razorpay integration)

### Backend (`apps/api`)
- **Framework:** FastAPI (Python 3.11/3.12)
- **Database:** PostgreSQL on [Neon](https://neon.tech) (Serverless Postgres)
- **ORM:** async SQLAlchemy 2.0
- **Vector Database:** `pgvector` extension for embeddings
- **Migrations:** Alembic
- **Authentication:** JWT (python-jose, bcrypt)
- **Storage:** Local / Google Cloud Storage
- **AI Services:** Gemini API with deterministic fallback

---

## 📊 Current Status

**Overall Completion:**
- **Backend:** 92% complete
- **Frontend:** 88% complete
- **AI Features:** 45% complete
- **Production Readiness:** 25% complete

### ✅ Completed Features

#### Backend (FastAPI)
- ✅ Authentication system (signup, signin, forgot-password)
- ✅ User management with role-based access (candidate/company)
- ✅ Subscription & plan management with role-based validation
- ✅ Payment processing framework (mock implementation)
- ✅ Candidate profile CRUD (education, experience, projects, certifications, skills)
- ✅ Company profile management
- ✅ Job posting CRUD with status management
- ✅ Application workflow with status tracking
- ✅ Messages/threads system
- ✅ Notifications system
- ✅ File uploads (photos, documents, logos)
- ✅ Database migrations (Alembic)
- ✅ Resume generation with AI service (Gemini)
- ✅ Enhanced AI error handling with deterministic fallback
- ✅ Resume PDF generation
- ✅ Fitment service (basic job-candidate matching with embeddings)

#### Frontend (Next.js)
- ✅ Complete candidate UI flow (dashboard, onboarding, profile, jobs, applications, messages, settings)
- ✅ Complete company UI flow (dashboard, jobs, candidates, applications, messages, settings)
- ✅ Public pages (landing, pricing, checkout, company profiles)
- ✅ Authentication pages (signin, signup, forgot-password)
- ✅ UserContext with API integration
- ✅ Reusable UI components
- ✅ Plan-based feature gating
- ✅ Job search with filters
- ✅ Resume generation flow
- ✅ Pricing pages with backend integration
- ✅ Checkout flow with payment processing framework
- ✅ Settings pages with subscription management

### ⏳ In Progress / TODO

See [`ARCHITECTURE_PLAN.md`](ARCHITECTURE_PLAN.md) for detailed implementation roadmap.

**High Priority:**
- Replace mock data with real API calls in candidate search
- Implement real-time application status updates
- Enhanced error handling for API failures
- Deploy staging environment

**Medium Priority:**
- Advanced candidate search API
- Analytics endpoints for dashboards
- AI double-check for shortlists
- Enhanced embedding strategy

**Lower Priority:**
- Production deployment
- Monitoring and analytics
- Security hardening
- Performance optimization

---

## 🚀 Setup Instructions

### Prerequisites
- Node.js 18+ and npm
- Python 3.13 (required - pydantic-core and other native dependencies require prebuilt wheels)
- PostgreSQL database (Neon recommended)
- Gemini API key (optional, for AI features)

### Frontend Setup

```bash
# From the project root
cp .env.local.example .env.local
npm install
npm run dev
```

> Set `NEXT_PUBLIC_API_URL` to your API (default `http://127.0.0.1:8000`).

### Backend Setup

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
# Set GEMINI_API_KEY for AI features (optional)

alembic upgrade head
uvicorn main:app --reload --port 8000
```

### Environment Variables

**Frontend (`.env.local`):**
```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

**Backend (`.env`):**
```bash
DATABASE_URL=postgresql+asyncpg://user:password@host/database
JWT_SECRET=your-secret-key
GEMINI_API_KEY=your-gemini-api-key  # Optional
GCS_BUCKET_NAME=rolecraft-uploads   # For GCS storage
STORAGE_BACKEND=local               # or 'gcs'
```

---

## 📖 Documentation

- [`ARCHITECTURE_PLAN.md`](ARCHITECTURE_PLAN.md) - Comprehensive implementation roadmap
- [`FIXES_SUMMARY.md`](FIXES_SUMMARY.md) - Recent fixes and integration details
- [`apps/api/README.md`](apps/api/README.md) - Backend-specific documentation
- [`AGENTS.md`](AGENTS.md) - Development guidelines for AI agents

---

## 🧪 Testing

### Backend Tests
```bash
cd apps/api
pytest
```

### Frontend Tests
```bash
npm test
```

### E2E Tests
```bash
npm run test:e2e
```

---

## 🚢 Deployment

### Backend (Cloud Run)
```bash
cd apps/api
gcloud run deploy
```

### Frontend (Vercel/Netlify)
Follow platform-specific deployment instructions.

---

## 🗺️ Development Roadmap

The project follows a phased implementation approach:

**Phase 1:** Complete Stage 1 Integration (2-3 weeks)
**Phase 2:** Payment & Subscription Enhancement (2 weeks)
**Phase 3:** Advanced AI Features (3-4 weeks)
**Phase 4:** Production Readiness (4-5 weeks)
**Phase 5:** Advanced Features (3-4 weeks)

See [`ARCHITECTURE_PLAN.md`](ARCHITECTURE_PLAN.md) for detailed timeline and implementation steps.

---

## 🛡️ Code Quality Standards

### Backend (Python/FastAPI)
- PEP 8 compliance
- Type hints for all functions
- Maximum function length: 50 lines
- Maximum file length: 500 lines
- Test coverage minimum: 80%

### Frontend (Next.js/React)
- TypeScript strict mode
- ESLint rules compliance
- Maximum component length: 300 lines
- Functional components with hooks
- Test coverage minimum: 70%

---

## 🛡️ Security & Known Vulnerabilities

All frontend dependencies have been audited and high-severity CVEs have been resolved.

**Upload Validation Security Fix (Aug 2026):**
- Implemented comprehensive file upload validation in `upload_limits.py` with:
  - Content-type verification against allowed MIME types
  - Magic-byte verification for PNG/JPEG/WEBP/PDF files
  - Content-Length fast-path rejection for oversized files
  - Bounded 64KB chunked reads with abort-on-oversize
  - Filename/path sanitization against path traversal attacks
  - Fixed NameError crash in upload validation path

For backend dependencies, we actively monitor and patch vulnerabilities. The following vulnerabilities currently remain unpatched either because no fix is available upstream or because upgrading would introduce breaking changes:

- **`python-jose` (3.4.0)**: PYSEC-2025-185 - No upstream fix available yet.
- **`ecdsa` (0.19.2)**: PYSEC-2026-1325 - Transitive dependency of `python-jose`, no fix available.
- **`pyasn1` (0.4.8)**: 5 CVEs - Transitive dependency of `python-jose`, which strictly pins `pyasn1<0.5.0`. Cannot bump to fix version 0.6.4 without breaking `python-jose`.
- **`weasyprint` (68.0)**: PYSEC-2026-3412 - No fix available upstream yet.
- **`starlette` (0.46.2)**: 9 CVEs - Pinned by `fastapi` 0.115.14. Upgrading `fastapi` to a version that supports a patched `starlette` (1.0+) introduces significant breaking changes and is deferred to a future maintenance window.

---

## 📄 License

[Add your license information here]

---

## 👥 Team

[Add team information here]

---

## 🙏 Acknowledgments

- Built with [Next.js](https://nextjs.org/)
- Backend powered by [FastAPI](https://fastapi.tiangolo.com/)
- Database hosted on [Neon](https://neon.tech/)
- AI features powered by [Google Gemini](https://ai.google.dev/)
