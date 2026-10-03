"""SpecID FastAPI application.

Startup order (TRD 2.2): guard -> settings -> DB -> templates -> models -> registry index.
Phase 2 adds migrations (TR-DAT-01); the other steps arrive in their phases.
"""

import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, errors, health, users
from app.db.migrate import upgrade_head
from app.settings import get_settings

API_PREFIX = "/api/v1"


def configure_logging(level: str) -> None:
    """Structured JSON logs to stdout (TRD TR-OPS-09, NFR-11)."""
    logging.basicConfig(format="%(message)s", level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()  # fails fast on missing or short JWT_SECRET (TR-SEC-02)
    configure_logging(settings.log_level)
    structlog.get_logger().info(
        "startup",
        git_commit=settings.git_commit,
        consent_mode=settings.consent_mode,
        offline=settings.offline,
    )
    upgrade_head(settings.database_url)  # TR-DAT-01: migrations before templates load
    structlog.get_logger().info("migrations_applied")
    yield


app = FastAPI(
    title="SpecID API",
    version=health.APP_VERSION,
    openapi_url=f"{API_PREFIX}/openapi.json",
    docs_url=None,  # default Swagger UI loads assets from a CDN (TRD TR-API-01, TD-08)
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().cors_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Bind the nginx-generated X-Request-ID to every log line (TR-OPS-09, TR-SEC-12)."""
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex
    structlog.contextvars.bind_contextvars(request_id=rid)
    try:
        response = await call_next(request)
        structlog.get_logger().info(
            "request", method=request.method, path=request.url.path, status=response.status_code
        )
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        structlog.contextvars.clear_contextvars()


errors.install(app)
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
