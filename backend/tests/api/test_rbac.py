"""TRD TR-SEC-03 / TR-TST-05: every endpoint declares its roles; one test per endpoint per role,
generated from the permission matrix (app.security.permissions.PERMISSIONS)."""

import uuid

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, RouteContext, iter_route_contexts
from fastapi.testclient import TestClient

from app.main import app
from app.security.permissions import PERMISSIONS, ROLES, Action
from app.security.rbac import current_user
from tests.api.conftest import DEMO, audit_actions, login

PUBLIC = {("GET", "/api/v1/health"), ("POST", "/api/v1/auth/login")}
SIGNED_IN = "any signed-in user"

# Which matrix row each endpoint implements. A new endpoint fails test_every_route_is_listed
# until it is added here with its row.
ENDPOINTS: dict[tuple[str, str], Action | str] = {
    ("GET", "/api/v1/me"): SIGNED_IN,
    ("POST", "/api/v1/me/password"): SIGNED_IN,
    ("GET", "/api/v1/users"): Action.MANAGE_USERS,
    ("POST", "/api/v1/users"): Action.MANAGE_USERS,
    ("POST", "/api/v1/users/{user_id}/reset-password"): Action.MANAGE_USERS,
    ("POST", "/api/v1/users/{user_id}/disable"): Action.MANAGE_USERS,
    ("GET", "/api/v1/audit"): Action.VIEW_AUDIT,
    ("GET", "/api/v1/audit/verify"): Action.VIEW_AUDIT,
}
ROLE_USER = {role: name for name, (role, _) in DEMO.items()}


def _routes() -> list[RouteContext]:
    """API routes with their effective (prefixed) paths; FastAPI 0.142 nests included routers."""
    return [c for c in iter_route_contexts(app.routes) if isinstance(c.original_route, APIRoute)]


def _keys(route: RouteContext) -> list[tuple[str, str]]:
    return [(m, str(route.path)) for m in sorted(route.methods or ())]


def _calls(d: Dependant) -> list[object]:
    out: list[object] = []
    for sub in d.dependencies:
        out.append(sub.call)
        out.extend(_calls(sub))
    return out


def _declared(route: RouteContext) -> frozenset[str] | str | None:
    calls = _calls(route.dependant)
    for c in calls:
        roles = getattr(c, "allowed_roles", None)
        if roles is not None:
            return frozenset(roles)
    return SIGNED_IN if current_user in calls else None


def test_every_route_is_listed_and_protected() -> None:
    seen = set()
    for route in _routes():
        for key in _keys(route):
            seen.add(key)
            if key in PUBLIC:
                assert _declared(route) is None, f"{key} is public but has an auth dependency"
                continue
            assert key in ENDPOINTS, f"{key} has no row in ENDPOINTS (permission matrix)"
            expected = ENDPOINTS[key]
            want = expected if expected == SIGNED_IN else frozenset(PERMISSIONS[Action(expected)])
            assert _declared(route) == want, f"{key} declares {_declared(route)}, matrix {want}"
    assert set(ENDPOINTS) <= seen, f"listed but missing: {set(ENDPOINTS) - seen}"


def test_matrix_rows_from_prd_section_2() -> None:
    assert PERMISSIONS[Action.MANAGE_USERS] == {"ADMIN"}
    assert PERMISSIONS[Action.VIEW_AUDIT] == {"ADMIN", "AUDITOR"}
    assert PERMISSIONS[Action.PROPOSE_REVIEW] == {"MAKER"}
    assert PERMISSIONS[Action.CONFIRM_REVIEW] == {"CHECKER"}
    assert "ADMIN" not in PERMISSIONS[Action.PROPOSE_REVIEW] | PERMISSIONS[Action.CONFIRM_REVIEW]
    assert PERMISSIONS[Action.VIEW_REGISTRY] == set(ROLES)


def _url(path: str) -> str:
    return path.replace("{user_id}", str(uuid.uuid4()))


CASES = [(method, path, role) for (method, path), action in ENDPOINTS.items() for role in ROLES]


@pytest.mark.parametrize(("method", "path", "role"), CASES)
def test_endpoint_per_role(
    client: TestClient, ids: dict[str, uuid.UUID], method: str, path: str, role: str
) -> None:
    action = ENDPOINTS[(method, path)]
    may = action == SIGNED_IN or role in PERMISSIONS[Action(action)]
    r = client.request(method, _url(path), headers=login(client, ROLE_USER[role]), json={})
    if may:
        assert r.status_code not in (401, 403), r.text
    else:
        assert r.status_code == 403, r.text
        assert r.headers["content-type"].startswith("application/problem+json")


@pytest.mark.parametrize(("method", "path"), list(ENDPOINTS))
def test_endpoint_without_token_is_401(
    client: TestClient, ids: dict[str, uuid.UUID], method: str, path: str
) -> None:
    assert client.request(method, _url(path), json={}).status_code == 401


def test_maker_calling_admin_endpoint_gets_403(
    client: TestClient, ids: dict[str, uuid.UUID]
) -> None:
    """Done-when (Phase 3)."""
    r = client.get("/api/v1/users", headers=login(client, "meera"))
    assert r.status_code == 403
    body = r.json()
    assert body["type"] == "https://specid.local/problems/forbidden"
    assert body["detail"] == "The MAKER role cannot do this."
    assert audit_actions() == ["LOGIN_SUCCEEDED"]  # a refusal changes nothing
