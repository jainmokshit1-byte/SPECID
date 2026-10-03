"""Roles and the permission matrix (PRD section 2, Backend Schema 5.2; TRD TR-SEC-03).

Encoded once. Routers depend on `require(Action.X)` and the API tests are generated from this
table, so a change here changes both.
"""

from enum import StrEnum


class Role(StrEnum):
    MAKER = "MAKER"
    CHECKER = "CHECKER"
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"
    INTEGRATOR = "INTEGRATOR"


ROLES: tuple[str, ...] = tuple(r.value for r in Role)

# Users who act for one CPSE (consent for own CPSE, own-CPSE procurement; FR-1501, FR-104).
CPSE_SCOPED_ROLES: frozenset[str] = frozenset({Role.MAKER, Role.CHECKER})


class Action(StrEnum):
    """Rows of the PRD section 2 permission matrix (plus API-37 consent)."""

    UPLOAD_BATCHES = "upload, map, ingest batches"
    START_RUNS = "start harmonisation / evaluation runs"
    VIEW_CLUSTERS = "view clusters, pairs, evidence cards"
    PROPOSE_REVIEW = "propose review decision"
    CONFIRM_REVIEW = "confirm / overturn a proposal"
    CONSENT = "consent / decline for own CPSE"  # API-37, SF-11
    VIEW_REGISTRY = "view registry and crosswalk"
    SEARCH_BEFORE_CREATE = "search-before-create"
    EDIT_TEMPLATES = "edit templates, dictionaries, thresholds"
    VIEW_AUDIT = "view audit log / verify chain"
    MANAGE_USERS = "manage users"
    VIEW_GUARD = "view Look-alike Guard, baselines, air-gap status"
    SUPPLY_ATTRIBUTE = "supply a missing attribute"  # P1
    PREVIEW_RULEBOOK = "preview a rulebook change"  # P0 since DEC-06b
    UNMERGE = "unmerge a record from a CNMC"  # P1


M, C, A, AU, INT = Role.MAKER, Role.CHECKER, Role.ADMIN, Role.AUDITOR, Role.INTEGRATOR

PERMISSIONS: dict[Action, frozenset[Role]] = {
    Action.UPLOAD_BATCHES: frozenset({M, C, A}),
    Action.START_RUNS: frozenset({M, C, A}),
    Action.VIEW_CLUSTERS: frozenset({M, C, A, AU}),
    Action.PROPOSE_REVIEW: frozenset({M}),
    Action.CONFIRM_REVIEW: frozenset({C}),
    Action.CONSENT: frozenset({C}),
    Action.VIEW_REGISTRY: frozenset({M, C, A, AU, INT}),
    Action.SEARCH_BEFORE_CREATE: frozenset({M, C, A, INT}),
    Action.EDIT_TEMPLATES: frozenset({A}),
    Action.VIEW_AUDIT: frozenset({A, AU}),
    Action.MANAGE_USERS: frozenset({A}),
    Action.VIEW_GUARD: frozenset({M, C, A, AU}),
    Action.SUPPLY_ATTRIBUTE: frozenset({M, C}),
    Action.PREVIEW_RULEBOOK: frozenset({A}),
    Action.UNMERGE: frozenset({C}),
}


def allowed(role: str, action: Action) -> bool:
    return role in PERMISSIONS[action]
