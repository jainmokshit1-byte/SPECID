"""Candidate generation (PRD FR-501-505, TRD TR-MOD-22, TR-ALG-01).

Which pairs are worth deciding? Comparing every record with every other is quadratic, so a pair
becomes a candidate only through one of four channels (bit values in the result):

- B (1) blocking: same category and same size. The pressure class is deliberately NOT part of the
  key, so CL150 vs CL300 near-misses become candidates and are vetoed visibly (TD-03, FR-501).
- L (2) lexical: BM25 top-k neighbours (inside the category) for records without a usable block,
  and for records in an oversized block.
- D (4) dense: nearest neighbours by meaning. The caller computes them (pgvector) and passes them
  in `dense`; this module only filters them (same category, mode).
- M (8) exact manufacturer + part number.

Pure and deterministic: ties are broken by record id. Records without a category get no
candidates (they appear in the quality report). Nothing here decides anything.
"""

import re
from collections import defaultdict
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from typing import Literal

from rank_bm25 import BM25Okapi

CHANNEL_B, CHANNEL_L, CHANNEL_D, CHANNEL_M = 1, 2, 4, 8
CHANNEL_LETTERS = {CHANNEL_B: "B", CHANNEL_L: "L", CHANNEL_D: "D", CHANNEL_M: "M"}
MPN_GROUP_CAP = 200  # a part number shared by more records than this is not an identity

Mode = Literal["CROSS_CPSE", "WITHIN_CPSE", "BOTH"]

# The attribute that plays the role of "size" per category (DEC-36): DN where there is one,
# thread for fasteners, power for motors. Anything else falls back to size_dn.
BLOCK_ATTR: dict[str, str] = {"FASTENER": "thread", "MOTOR": "power_kw"}
DEFAULT_BLOCK_ATTR = "size_dn"

_TOKEN = re.compile(r"[A-Z0-9][A-Z0-9.\-]*")


@dataclass(frozen=True)
class CandRecord:
    id: str
    cpse: str
    category: str | None
    block: Hashable | None  # the category's size value; None when unknown
    norm_text: str
    mpn: str | None = None
    maker: str | None = None


@dataclass(frozen=True)
class CandidateConfig:
    mode: Mode = "CROSS_CPSE"
    bm25_k: int = 200  # PRD FR-502 says 20; 200 measured on seed-7 (DEC-36)
    dense_k: int = 20
    block_cap: int = 2000


def block_attr(category: str | None) -> str:
    return BLOCK_ATTR.get(category or "", DEFAULT_BLOCK_ATTR)


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.upper())


def _allowed(a: CandRecord, b: CandRecord, mode: Mode) -> bool:
    same = a.cpse == b.cpse
    return mode == "BOTH" or (mode == "WITHIN_CPSE" and same) or (mode == "CROSS_CPSE" and not same)


def _add(out: dict[tuple[str, str], int], a: CandRecord, b: CandRecord, bit: int) -> None:
    if a.id == b.id:
        return
    key = (a.id, b.id) if a.id < b.id else (b.id, a.id)
    out[key] = out.get(key, 0) | bit


def generate(
    records: Sequence[CandRecord],
    cfg: CandidateConfig,
    dense: Mapping[str, Sequence[str]] | None = None,
) -> dict[tuple[str, str], int]:
    """{(id_a, id_b) with id_a < id_b: channel bitmask}, mode filter applied."""
    out: dict[tuple[str, str], int] = {}
    by_id = {r.id: r for r in records}
    by_cat: dict[str, list[CandRecord]] = defaultdict(list)
    for r in sorted(records, key=lambda r: r.id):
        if r.category is not None:
            by_cat[r.category].append(r)

    for recs in by_cat.values():
        blocks: dict[Hashable, list[CandRecord]] = defaultdict(list)
        unblocked: list[CandRecord] = []
        for r in recs:
            if r.block is None:
                unblocked.append(r)
            else:
                blocks[r.block].append(r)
        for members in blocks.values():  # channel B
            if len(members) > cfg.block_cap:
                unblocked.extend(members)  # oversized: lexical channel instead
                continue
            for a, b in combinations(members, 2):
                if _allowed(a, b, cfg.mode):
                    _add(out, a, b, CHANNEL_B)
        if unblocked:  # channel L
            _lexical(recs, unblocked, cfg, out)

    mpn_groups: dict[tuple[str, str], list[CandRecord]] = defaultdict(list)
    for r in sorted(records, key=lambda r: r.id):  # channel M
        if (r.mpn or "").strip() and (r.maker or "").strip():
            mpn_groups[(r.maker.strip().upper(), r.mpn.strip().upper())].append(r)  # type: ignore[union-attr]
    for members in mpn_groups.values():
        if 1 < len(members) <= MPN_GROUP_CAP:
            for a, b in combinations(members, 2):
                if _allowed(a, b, cfg.mode):
                    _add(out, a, b, CHANNEL_M)

    for rid, neighbours in (dense or {}).items():  # channel D
        a = by_id.get(rid)
        if a is None or a.category is None:
            continue
        kept = 0
        for nid in neighbours:
            b = by_id.get(nid)
            if b is None or b.category != a.category or not _allowed(a, b, cfg.mode):
                continue
            _add(out, a, b, CHANNEL_D)
            kept += 1
            if kept >= cfg.dense_k:
                break
    return out


def _lexical(
    corpus: Sequence[CandRecord],
    queries: Sequence[CandRecord],
    cfg: CandidateConfig,
    out: dict[tuple[str, str], int],
) -> None:
    """BM25 over the category's texts; each query takes its top-k allowed neighbours."""
    if len(corpus) < 2:
        return
    index = BM25Okapi([tokens(r.norm_text) or ["_"] for r in corpus])
    for q in queries:
        scores = index.get_scores(tokens(q.norm_text) or ["_"])
        ranked = sorted(
            (i for i, r in enumerate(corpus) if r.id != q.id and _allowed(q, r, cfg.mode)),
            key=lambda i: (-float(scores[i]), corpus[i].id),
        )
        for i in ranked[: cfg.bm25_k]:
            _add(out, q, corpus[i], CHANNEL_L)


def channel_counts(pairs: Mapping[tuple[str, str], int]) -> dict[str, int]:
    """Pairs reached per channel (a pair found by two channels counts for both)."""
    return {
        letter: sum(1 for mask in pairs.values() if mask & bit)
        for bit, letter in CHANNEL_LETTERS.items()
    }
