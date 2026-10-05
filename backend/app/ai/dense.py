"""Meaning-search neighbours for the dense candidate channel (PRD FR-503; DEC-41).

Embeddings come from the provider (unit length); neighbours are the top-k by cosine inside each
category, computed in memory with numpy (thousands of records: milliseconds). The candidate
module filters them again by category and run mode; nothing here decides anything.
"""

from collections.abc import Sequence

import numpy as np


def neighbours(
    ids: Sequence[str],
    categories: Sequence[str | None],
    vectors: Sequence[Sequence[float]],
    k: int,
) -> dict[str, list[str]]:
    by_cat: dict[str, list[int]] = {}
    for i, c in enumerate(categories):
        if c is not None:
            by_cat.setdefault(c, []).append(i)
    out: dict[str, list[str]] = {}
    for members in by_cat.values():
        if len(members) < 2:
            continue
        m = np.asarray([vectors[i] for i in members], dtype=np.float32)
        sims = m @ m.T
        np.fill_diagonal(sims, -1.0)
        top = min(k, len(members) - 1)
        idx = np.argsort(-sims, axis=1, kind="stable")[:, :top]
        for row, i in enumerate(members):
            out[ids[i]] = [ids[members[j]] for j in idx[row]]
    return out
