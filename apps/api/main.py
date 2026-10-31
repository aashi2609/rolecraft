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
from core.request_id import RequestIdMiddleware
from services.ai_client import AIServiceError
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
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

# In production, docs, redoc, and openapi_url are disabled. Debug is always False.
app = FastAPI(
    title="RoleCraft API",
    version="1.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
    debug=False,
)

# slowapi: same Limiter instance used by @limiter.limit route decorators
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_exception_handler(RateLimited, rate_limit_exceeded_handler)

# Request ID middleware
app.add_middleware(RequestIdMiddleware)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

# CORS configuration:
# In production: strict explicit allow_origins only from env, no regex, no wildcards, no cookies (allow_credentials=False).
# In development: allows localhost / LAN origins for convenient local testing.
if settings.is_production:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["http://localhost:3000"],
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


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or "unknown"


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Clean validation error response: preserves field-level errors but strips submitted inputs (e.g. passwords)."""
    clean_errors = []
    for err in exc.errors():
        e = dict(err)
        # Never echo back the raw submitted values (such as passwords, tokens, or PII)
        e.pop("input", None)
        if "ctx" in e and isinstance(e["ctx"], dict):
            e["ctx"] = {
                k: str(v) if isinstance(v, Exception) else v
                for k, v in e["ctx"].items()
            }
        clean_errors.append(e)

    req_id = _get_request_id(request)
    return JSONResponse(
        status_code=422,
        content={"detail": clean_errors, "request_id": req_id},
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Database integrity violation: maps to clean 409 Conflict without leaking SQL, table, or constraint names."""
    req_id = _get_request_id(request)
    logger.error(
        "Database integrity violation [request_id=%s] on %s %s: %s",
        req_id,
        request.method,
        request.url.path,
        exc,
    )
    return JSONResponse(
        status_code=409,
        content={
            "detail": "A conflict occurred with an existing resource.",
            "request_id": req_id,
        },
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """Database query / driver error: maps to clean 500 without leaking SQL text or connection metadata."""
    req_id = _get_request_id(request)
    logger.exception(
        "Database error [request_id=%s] on %s %s: %s",
        req_id,
        request.method,
        request.url.path,
        exc,
    )
    detail = "Internal database error" if not settings.is_production else "Internal server error"
    return JSONResponse(
        status_code=500,
        content={"detail": detail, "request_id": req_id},
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(AIServiceError)
async def ai_service_error_handler(request: Request, exc: AIServiceError):
    """Upstream AI / Groq failure: clean 502/503 response without provider bodies or API keys."""
    req_id = _get_request_id(request)
    logger.warning(
        "Upstream AI service failure [request_id=%s] on %s %s: %s",
        req_id,
        request.method,
        request.url.path,
        exc,
    )
    return JSONResponse(
        status_code=502,
        content={
            "detail": "AI service is currently unavailable. Please try again later.",
            "request_id": req_id,
        },
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    req_id = _get_request_id(request)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    req_id = _get_request_id(request)
    if isinstance(exc, (RateLimitExceeded, RateLimited)):
        return rate_limit_exceeded_handler(request, exc)
    if isinstance(exc, StarletteHTTPException):
        return await http_exception_handler(request, exc)
    if isinstance(exc, RequestValidationError):
        return await validation_exception_handler(request, exc)
    if isinstance(exc, IntegrityError):
        return await integrity_error_handler(request, exc)
    if isinstance(exc, SQLAlchemyError):
        return await sqlalchemy_error_handler(request, exc)
    if isinstance(exc, AIServiceError):
        return await ai_service_error_handler(request, exc)

    logger.exception(
        "Unhandled error [request_id=%s] on %s %s",
        req_id,
        request.method,
        request.url.path,
    )
    # In production, never leak internal traceback or exception messages to callers
    detail = "Internal server error" if settings.is_production else f"{type(exc).__name__}: {exc}"
    return JSONResponse(
        status_code=500,
        content={"detail": detail, "request_id": req_id},
        headers={"X-Request-ID": req_id},
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
