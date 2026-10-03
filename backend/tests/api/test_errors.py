"""TR-API-03: every error is RFC 7807 `application/problem+json`."""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.api import errors
from app.main import app as real_app
from app.services.errors import (
    Conflict,
    Forbidden,
    Invalid,
    NotFound,
    RateLimited,
    ServiceError,
    Unauthorized,
)

demo = FastAPI()
errors.install(demo)

CASES: list[tuple[type[ServiceError], int, str]] = [
    (Invalid, 400, "invalid"),
    (Unauthorized, 401, "unauthorized"),
    (Forbidden, 403, "forbidden"),
    (NotFound, 404, "not-found"),
    (Conflict, 409, "conflict"),
    (RateLimited, 429, "rate-limited"),
]


@demo.get("/raise/{i}")
def _raise(i: int) -> None:
    raise CASES[i][0]("explained here")


class Body(BaseModel):
    username: str
    password: str


@demo.post("/body")
def _body(b: Body) -> None:
    return None


@demo.get("/http")
def _http() -> None:
    raise HTTPException(status_code=403)


client = TestClient(demo)


def _is_problem(r, status: int) -> dict:  # type: ignore[no-untyped-def]
    assert r.status_code == status
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert {"type", "title", "status", "detail", "instance"} <= body.keys()
    assert body["status"] == status
    return body


@pytest.mark.parametrize("i", range(len(CASES)))
def test_service_errors_map_to_problem(i: int) -> None:
    _, status, slug = CASES[i]
    body = _is_problem(client.get(f"/raise/{i}"), status)
    assert body["type"] == f"https://specid.local/problems/{slug}"
    assert body["detail"] == "explained here"
    assert body["instance"] == f"/raise/{i}"


def test_rate_limited_sets_retry_after() -> None:
    r = client.get(f"/raise/{len(CASES) - 1}")
    assert r.headers["retry-after"] == "60"


def test_unauthorized_sets_www_authenticate() -> None:
    assert client.get("/raise/1").headers["www-authenticate"] == "Bearer"


def test_validation_errors_list_fields_without_echoing_input() -> None:
    body = _is_problem(client.post("/body", json={"password": "s3cret-value"}), 422)
    assert body["errors"][0]["loc"] == ["body", "username"]
    assert "s3cret-value" not in str(body)


def test_http_exception_and_unknown_route_are_problems() -> None:
    assert _is_problem(client.get("/http"), 403)["title"] == "Forbidden"
    with TestClient(real_app) as c:
        assert _is_problem(c.get("/api/v1/nope"), 404)["type"].endswith("/not-found")
