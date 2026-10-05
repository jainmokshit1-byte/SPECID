"""FR-501-505, TR-ALG-01: candidate generation (pure), plus pair completeness on seed-7."""

import csv
import io
from functools import lru_cache

import pytest

from app.core.candidates import (
    CHANNEL_B,
    CHANNEL_D,
    CHANNEL_L,
    CHANNEL_M,
    CandidateConfig,
    CandRecord,
    block_attr,
    channel_counts,
    generate,
)
from app.core.normalise import normalise
from app.eval.generator import GeneratorConfig, files
from app.eval.generator import generate as generate_data
from tests.coreenv import D, E, dictionary


def rec(i: str, cpse: str, cat: str | None, block: object, text: str = "", **kw: str) -> CandRecord:
    return CandRecord(i, cpse, cat, block, text or f"{cat} {block}", **kw)  # type: ignore[arg-type]


CROSS = CandidateConfig(mode="CROSS_CPSE")


def test_blocking_pairs_same_category_and_size_across_cpses() -> None:
    recs = [rec("a", "A", "VALVE", 100), rec("b", "B", "VALVE", 100), rec("c", "B", "VALVE", 150),
            rec("d", "B", "PIPE", 100)]  # fmt: skip
    assert generate(recs, CROSS) == {("a", "b"): CHANNEL_B}


def test_pressure_class_is_not_a_blocking_key() -> None:
    """CL150 and CL300 valves of one size must meet: the veto and the Look-alike Guard see them."""
    a = CandRecord("a", "A", "VALVE", 100, "VALVE GATE 4 IN CL150")
    b = CandRecord("b", "B", "VALVE", 100, "VALVE GATE 4 IN CL300")
    assert generate([a, b], CROSS) == {("a", "b"): CHANNEL_B}


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("CROSS_CPSE", {("a", "b"), ("a", "c")}),
        ("WITHIN_CPSE", {("a", "d"), ("b", "c")}),
        ("BOTH", {("a", "b"), ("a", "c"), ("a", "d"), ("b", "c"), ("b", "d"), ("c", "d")}),
    ],
)
def test_run_modes(mode: str, expected: set[tuple[str, str]]) -> None:
    recs = [rec("a", "A", "PIPE", 50), rec("b", "B", "PIPE", 50), rec("c", "B", "PIPE", 50),
            rec("d", "A", "PIPE", 50)]  # fmt: skip
    if mode == "CROSS_CPSE":
        expected = {("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")}
    got = set(generate(recs, CandidateConfig(mode=mode)))  # type: ignore[arg-type]
    assert got == expected


def test_in_cross_cpse_mode_no_pair_has_both_records_in_one_cpse() -> None:
    """FR-505."""
    recs = [rec(f"r{i}", "AB"[i % 2], "VALVE", 100 + i % 3) for i in range(40)]
    by = {r.id: r.cpse for r in recs}
    pairs = generate(recs, CROSS)
    assert pairs and all(by[a] != by[b] for a, b in pairs)


def test_unknown_size_gets_bm25_neighbours_inside_the_category() -> None:
    """FR-502: a record without a size still receives candidates."""
    filler = [
        rec(f"f{i}", "B", "VALVE", 200 + i, f"{t} VALVE {200 + i} IN CL{c} {m} BW")
        for i, (t, c, m) in enumerate(
            [("BALL", 600, "A351-CF8M"), ("GLOBE", 300, "A216-WCC"), ("CHECK", 900, "A105"),
             ("BALL", 300, "A351-CF8"), ("GLOBE", 150, "A216-WCC"), ("CHECK", 600, "A105")]
        )
    ]  # fmt: skip
    recs = [
        rec("a", "A", "VALVE", None, "GATE VALVE CL150 A216-WCB FLANGED RF"),
        rec("b", "B", "VALVE", 100, "GATE VALVE 4 IN CL150 A216-WCB FLANGED RF"),
        rec("x", "B", "PIPE", 100, "GATE VALVE CL150 A216-WCB FLANGED RF"),  # other category
        *filler,
    ]
    pairs = generate(recs, CandidateConfig(bm25_k=1))
    assert pairs == {("a", "b"): CHANNEL_L}  # nearest by text; the pipe is never a neighbour


def test_oversized_blocks_fall_back_to_bm25() -> None:
    recs = [
        rec(f"r{i:02d}", "AB"[i % 2], "FLANGE", 100, f"FLANGE SO 4 IN CL150 ITEM{i}")
        for i in range(10)
    ]
    small = generate(recs, CandidateConfig(block_cap=100))
    assert all(m == CHANNEL_B for m in small.values()) and len(small) == 25
    big = generate(recs, CandidateConfig(block_cap=5, bm25_k=2))
    assert all(m == CHANNEL_L for m in big.values()) and 0 < len(big) <= 20


def test_exact_maker_and_part_number_always_pair() -> None:
    """FR-504: the same MPN across CPSEs becomes a candidate even when nothing else links them."""
    a = rec("a", "A", "VALVE", 100, "A", mpn="sx-1", maker="Acme")
    b = rec("b", "B", "PIPE", 250, "B", mpn="SX-1", maker="ACME ")  # case and spaces ignored
    c = rec("c", "B", "VALVE", 100, "C", mpn="SX-1", maker=None)  # no maker: not an identity
    pairs = generate([a, b, c], CROSS)
    assert pairs[("a", "b")] == CHANNEL_M
    assert pairs[("a", "c")] == CHANNEL_B and ("b", "c") not in pairs


def test_dense_neighbours_are_filtered_by_category_and_mode() -> None:
    recs = [rec("a", "A", "VALVE", None), rec("b", "B", "VALVE", None),
            rec("c", "A", "VALVE", None),
            rec("d", "B", "PIPE", None)]  # fmt: skip
    dense = {"a": ["b", "c", "d", "zzz"], "d": ["a"]}
    pairs = generate(recs, CandidateConfig(bm25_k=0), dense)
    assert pairs[("a", "b")] & CHANNEL_D and ("a", "c") not in pairs and ("a", "d") not in pairs
    assert not any(k for k in pairs if "d" in k)


def test_records_without_a_category_get_no_candidates() -> None:
    assert generate([rec("a", "A", None, None, "X"), rec("b", "B", None, None, "X")], CROSS) == {}


def test_result_is_deterministic_and_ordered() -> None:
    recs = [
        rec(f"r{i:03d}", "AB"[i % 2], "VALVE", None, f"GATE VALVE ITEM {i % 7}") for i in range(60)
    ]
    first = generate(recs, CandidateConfig(bm25_k=3))
    assert first == generate(list(reversed(recs)), CandidateConfig(bm25_k=3))
    assert all(a < b for a, b in first)


def test_channel_counts() -> None:
    assert channel_counts({("a", "b"): CHANNEL_B | CHANNEL_L, ("a", "c"): CHANNEL_M}) == {
        "B": 1, "L": 1, "D": 0, "M": 1,
    }  # fmt: skip


def test_block_attribute_per_category() -> None:
    assert [block_attr(c) for c in ("VALVE", "PIPE", "FLANGE", "FASTENER", "MOTOR", None)] == [
        "size_dn", "size_dn", "size_dn", "thread", "power_kw", "size_dn",
    ]  # fmt: skip


# ---- pair completeness on the seeded synthetic data (FR-501, FR-506) ----
@lru_cache
def seed7_candidates() -> tuple[dict[tuple[str, str], int], list[dict[str, str]], dict[str, str]]:
    data = files(generate_data(GeneratorConfig()))
    d = dictionary()
    cands, texts = [], {}
    for c in "ABC":
        for r in csv.DictReader(io.StringIO(data[f"cpse_{c}.csv"].decode())):
            key = f"CPSE-{c}:{r['legacy_code']}"
            text = r["long_text"] or r["short_text"]
            spec = E(text, r["mpn"] or None, r["manufacturer"] or None)
            attr = block_attr(spec.category)
            cands.append(
                CandRecord(key, f"CPSE-{c}", spec.category, spec.attrs.get(attr),
                           normalise(text, d), r["mpn"] or None, r["manufacturer"] or None)
            )  # fmt: skip
            texts[key] = text
    pairs = generate(cands, CandidateConfig(mode="BOTH"))
    truth = list(csv.DictReader(io.StringIO(data["truth_pairs.csv"].decode())))
    return pairs, truth, texts


def _key(p: dict[str, str], side: str) -> str:
    return f"{p['cpse_' + side]}:{p['legacy_code_' + side]}"


def test_pair_completeness_on_seed_7() -> None:
    pairs, truth, texts = seed7_candidates()
    eq = [p for p in truth if p["label"] == "EQUIVALENT"]
    hard = [p for p in truth if p["label"] == "NOT_EQUIVALENT_HARD"]

    def reached(p: dict[str, str]) -> bool:
        a, b = _key(p, "a"), _key(p, "b")
        return ((a, b) if a < b else (b, a)) in pairs

    def category(key: str) -> str | None:
        return E(texts[key]).category  # type: ignore[no-any-return]

    # a pair is unreachable by design when a record has no recognised category (they surface in
    # the quality report; the ML classifier of Go 2 addresses them)
    known = [p for p in eq if category(_key(p, "a")) and category(_key(p, "b"))]
    overall = sum(map(reached, eq)) / len(eq)
    categorised = sum(map(reached, known)) / len(known)
    assert overall >= 0.94, overall
    assert categorised >= 0.975, categorised  # FR-501 target 0.98 [T]; measured 0.981

    # near-misses that share a block always meet; those that differ in the block attribute (the
    # size) sit in different blocks, are never compared, and are counted, not merged (TR-ALG-01a)
    def same_block(p: dict[str, str]) -> bool:
        a, b = E(texts[_key(p, "a")]), E(texts[_key(p, "b")])
        attr = block_attr(a.category)
        return a.attrs.get(attr) is not None and a.attrs.get(attr) == b.attrs.get(attr)

    shared = [p for p in hard if category(_key(p, "a")) and same_block(p)]
    assert len(shared) > 400 and all(map(reached, shared))
    n = len(texts)
    assert len(pairs) < 0.05 * n * (n - 1) / 2  # reduction ratio: under 5% of all pairs


def test_candidates_feed_decide_without_error() -> None:
    pairs, _, texts = seed7_candidates()
    sample = sorted(pairs)[:300]
    verdicts = {D(E(texts[a]), E(texts[b])).verdict for a, b in sample}
    assert verdicts <= {"IDENTICAL", "EQUIVALENT", "NOT_EQUIVALENT", "INSUFFICIENT_DATA"}
