"""RFC 7807 `application/problem+json` for every error (TRD TR-API-03).

One place maps typed service exceptions, HTTP errors and validation errors to problem documents
with `type`, `title`, `status`, `detail`, `instance` and, for validation, `errors[]`.
"""

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.errors import RateLimited, ServiceError

PROBLEM_BASE = "https://specid.local/problems/"
PROBLEM_JSON = "application/problem+json"

_SLUGS = {401: "unauthorized", 403: "forbidden", 404: "not-found", 405: "method-not-allowed"}


def problem(
    request: Request,
    status: int,
    slug: str,
    title: str,
    detail: str = "",
    errors: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": PROBLEM_BASE + slug,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
    }
    if errors is not None:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON, headers=headers)


async def _service_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ServiceError)
    headers = {"Retry-After": str(exc.retry_after)} if isinstance(exc, RateLimited) else None
    if exc.status == 401:
        headers = {"WWW-Authenticate": "Bearer"}
    return problem(request, exc.status, exc.slug, exc.title, exc.detail, headers=headers)


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    status = exc.status_code
    phrase = HTTPStatus(status).phrase if status in HTTPStatus._value2member_map_ else "Error"
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail != phrase else ""
    slug = _SLUGS.get(status, phrase.lower().replace(" ", "-"))
    return problem(request, status, slug, phrase, detail, headers=exc.headers)


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = [
        {"loc": [str(p) for p in e.get("loc", ())], "msg": e.get("msg", ""), "type": e.get("type")}
        for e in exc.errors()
    ]
    return problem(
        request, 422, "validation", "Validation failed", "Check the highlighted fields.", errors
    )


def install(app: FastAPI) -> None:
    app.add_exception_handler(ServiceError, _service_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
