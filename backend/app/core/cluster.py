"""Constrained clustering (PRD 9.7, FR-701-703, TRD TR-MOD-07, TR-ALG-03).

Groups are joined along EQUIVALENT / IDENTICAL edges, highest score first, and never when any
pair across the two groups would be NOT_EQUIVALENT. `conflict` is memoised by the caller.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

SIZE_CAP = 200  # TR-ALG-03: larger merges are refused and logged as a blocked edge


@dataclass(frozen=True)
class BlockedEdge:
    """An edge that was not followed, so the reviewer sees "why not merged" (FR-703)."""

    i: int
    j: int
    score: float
    reason: Literal["conflict", "size cap"]


def cluster_with_blocked(
    n: int,
    edges: Sequence[tuple[int, int, float]],
    conflict: Callable[[int, int], bool],
    size_cap: int = SIZE_CAP,
) -> tuple[list[list[int]], list[BlockedEdge]]:
    parent = list(range(n))
    members: dict[int, set[int]] = {i: {i} for i in range(n)}
    blocked: list[BlockedEdge] = []

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j, score in sorted(edges, key=lambda e: (-e[2], e[0], e[1])):
        ri, rj = find(i), find(j)
        if ri == rj:
            continue
        if len(members[ri]) + len(members[rj]) > size_cap:
            blocked.append(BlockedEdge(i, j, score, "size cap"))
        elif any(conflict(x, y) for x in members[ri] for y in members[rj]):
            blocked.append(BlockedEdge(i, j, score, "conflict"))
        else:
            parent[rj] = ri
            members[ri] |= members.pop(rj)
    return sorted(sorted(m) for m in members.values()), blocked


def constrained_clusters(
    n: int,
    edges: Sequence[tuple[int, int, float]],
    conflict: Callable[[int, int], bool],
    size_cap: int = SIZE_CAP,
) -> list[list[int]]:
    """The clusters only (reference `constrained_clusters`)."""
    return cluster_with_blocked(n, edges, conflict, size_cap)[0]


def cluster_priority(annual_values: Sequence[float | None], n_flags: int) -> float:
    """(sum of annual_value, or 1) x (1 + 0.5 x number of flags in its pairs) (FR-702)."""
    total = sum(v for v in annual_values if v is not None)
    return (total or 1.0) * (1 + 0.5 * n_flags)


def cohesion(confidences: Sequence[float]) -> float | None:
    """Mean confidence of the cluster's edges (FR-702)."""
    return sum(confidences) / len(confidences) if confidences else None
