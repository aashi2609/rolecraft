from pathlib import Path
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.config import get_settings
from routers import (
    admin,
    analytics,
    applications,
    auth,
    candidates,
    companies,
    jobs,
    messages,
    resumes,
)
from routers.notifications import (
    router_notifications,
    router_subscriptions,
    router_uploads,
)

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(title="RoleCraft API", version="1.0.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # Local/LAN frontends (Next "Network" URL like http://192.168.x.x:3000)
    allow_origin_regex=r"https?://("
    r"localhost|"
    r"127\.0\.0\.1|"
    r"\[::1\]|"
    r"192\.168\.\d{1,3}\.\d{1,3}|"
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
    r")(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    if isinstance(exc, RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}"},
    )


app.include_router(auth.router)
app.include_router(candidates.router)
app.include_router(resumes.router)
app.include_router(companies.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(messages.router)
app.include_router(analytics.router)
app.include_router(router_notifications)
app.include_router(router_subscriptions)
app.include_router(router_uploads)
app.include_router(admin.router)

uploads_dir = Path(__file__).parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(uploads_dir)), name="static")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "environment": settings.environment,
        "force_deterministic_resumes": settings.force_deterministic_resumes,
    }
