from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import get_settings
from routers import auth, candidates, resumes, companies, jobs, applications, messages
from routers.notifications import router_notifications, router_subscriptions, router_uploads

settings = get_settings()

app = FastAPI(title="RoleCraft API", version="1.0.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(candidates.router)
app.include_router(resumes.router)
app.include_router(companies.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(messages.router)
app.include_router(router_notifications)
app.include_router(router_subscriptions)
app.include_router(router_uploads)

uploads_dir = Path(__file__).parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(uploads_dir)), name="static")


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.environment}
