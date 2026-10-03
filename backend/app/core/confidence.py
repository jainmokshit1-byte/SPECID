"""Heuristic confidence `p_rule` (PRD 9.6, FR-607, TRD TR-MOD-12).

Shown as "confidence (heuristic)", not a probability. It never changes a verdict or a route.
"""

from app.core.types import Decision

FLOOR = 0.50


def p_rule(decision: Decision) -> float | None:
    """0.98 - 0.10 x extended flags - 0.15 x residual flag, floor 0.50; NOT_EQUIVALENT 0.00."""
    if decision.verdict == "NOT_EQUIVALENT":
        return 0.0
    if decision.verdict == "INSUFFICIENT_DATA":
        return None
    ext_flags = sum(1 for r in decision.reasons if r.endswith(" unverified"))
    residual = any(r.startswith("unexplained tokens") for r in decision.reasons)
    return max(FLOOR, round(0.98 - 0.10 * ext_flags - 0.15 * residual, 2))
