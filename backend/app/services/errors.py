"""Typed service exceptions (TRD section 13: services raise typed exceptions; one handler maps
them to RFC 7807, TR-API-03). Services never import FastAPI."""


class ServiceError(Exception):
    """Base class. `title` is short and safe to show; `detail` explains this occurrence."""

    status: int = 400
    slug: str = "invalid"
    default_title: str = "Invalid request"

    def __init__(self, detail: str = "", title: str | None = None) -> None:
        super().__init__(detail or title or self.default_title)
        self.title = title or self.default_title
        self.detail = detail


class Invalid(ServiceError):
    status, slug, default_title = 400, "invalid", "Invalid request"


class Unauthorized(ServiceError):
    status, slug, default_title = 401, "unauthorized", "Not signed in"


class Forbidden(ServiceError):
    status, slug, default_title = 403, "forbidden", "No access"


class NotFound(ServiceError):
    status, slug, default_title = 404, "not-found", "Not found"


class Conflict(ServiceError):
    status, slug, default_title = 409, "conflict", "Conflict"


class RateLimited(ServiceError):
    status, slug, default_title = 429, "rate-limited", "Too many attempts"

    def __init__(self, detail: str = "", retry_after: int = 60) -> None:
        super().__init__(detail)
        self.retry_after = retry_after
