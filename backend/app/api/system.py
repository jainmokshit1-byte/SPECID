"""API-32 `GET /system/airgap` (PRD SF-7, FR-1462): the air-gap status for the footer."""

from typing import Any

from fastapi import APIRouter, Depends

from app.db.models import AppUser
from app.security import egress
from app.security.rbac import current_user
from app.settings import Settings, get_settings

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/airgap")
def airgap(
    _: AppUser = Depends(current_user), settings: Settings = Depends(get_settings)
) -> dict[str, Any]:
    guard = egress.current_guard()
    return {
        "mode": "OFFLINE" if settings.offline else "ONLINE",
        "egress_guard": {
            "enabled": settings.egress_guard_enabled,
            "installed": egress.guard_installed(),
        },
        "blocked_egress_attempts": egress.blocked_attempts(),
        "allowed_hosts": sorted(guard.allowed) if guard else [],
        "scope": (
            "Counts outbound connections attempted by Python code. The network guarantee is the "
            "Docker network with no route to the internet."
        ),
    }
