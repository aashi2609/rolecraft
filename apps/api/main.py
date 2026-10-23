from pathlib import Path
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.config import get_settings
from core.rate_limit import RateLimited, limiter, rate_limit_exceeded_handler
from routers import (
    admin,
    analytics,
    applications,
    auth,
    candidates,
    companies,
    files,
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

# slowapi: same Limiter instance used by @limiter.limit route decorators
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_exception_handler(RateLimited, rate_limit_exceeded_handler)

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
    if isinstance(exc, (RateLimitExceeded, RateLimited)):
        return rate_limit_exceeded_handler(request, exc)
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
app.include_router(files.router)

# Ensure local uploads directory exists (used by local storage backend).
uploads_dir = Path(__file__).parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
# NOTE: No StaticFiles mount — files are served only through the
# authenticated GET /files/{file_id} endpoint. Company logos use the
# unauthenticated GET /files/logo/{file_id} endpoint.


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "environment": settings.environment,
        "force_deterministic_resumes": settings.force_deterministic_resumes,
        "rate_limit_enabled": settings.rate_limit_enabled,
        "rate_limit_storage": settings.rate_limit_storage_uri.split("://", 1)[0],
        "trusted_proxy": settings.trusted_proxy,
    }
