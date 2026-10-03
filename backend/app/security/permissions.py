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
