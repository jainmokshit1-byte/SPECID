"""PRD 13.3 property tests (TRD TR-TST-03) and PRD Appendix D sections 3 and 4.

T-P1 veto, T-P2 no conflict inside a cluster, T-P3 symmetry, T-P4 idempotent normaliser,
T-P5 short text <= 40 characters or none, T-C CNMC check digit.
"""

import random
import string
from itertools import combinations
from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from tests.coreenv import D, E, N, dictionary, spec
from tests.property.strategies import CATEGORIES, attrs_for, criticality, spec_pair, texts

POSITIVE = ("EQUIVALENT", "IDENTICAL")


# ---- T-P1 veto (FR-602, NFR-04) ----
@given(spec_pair(), criticality)
def test_t_p1_any_conflict_vetoes(pair: tuple[dict[str, Any], dict[str, Any]], crit: Any) -> None:
    a, b = spec(**pair[0]), spec(**pair[1])
    r = D(a, b, criticality=crit)
    if any(e.status == "CONFLICT" for e in r.evidence):
        assert r.verdict == "NOT_EQUIVALENT" and r.route == "NONE"
    if r.verdict in POSITIVE:
        assert all(e.status == "MATCH" for e in r.evidence if e.level == "core")
        assert not any(e.status == "CONFLICT" for e in r.evidence)
    if r.verdict == "NOT_EQUIVALENT":
        assert r.confidence == 0.0
    if r.verdict == "INSUFFICIENT_DATA":
        assert r.confidence is None and r.route == "REVIEW"


@given(texts, texts)
def test_t_p1_any_conflict_vetoes_on_text(x: str, y: str) -> None:
    r = D(E(x), E(y))
    if any(e.status == "CONFLICT" for e in r.evidence):
        assert r.verdict == "NOT_EQUIVALENT"


# ---- T-P3 symmetry (FR-611) ----
@given(spec_pair(), criticality)
def test_t_p3_decide_is_symmetric(pair: tuple[dict[str, Any], dict[str, Any]], crit: Any) -> None:
    a, b = spec(**pair[0]), spec(**pair[1])
    r, r2 = D(a, b, criticality=crit), D(b, a, criticality=(crit[1], crit[0]))
    assert (r.verdict, r.route) == (r2.verdict, r2.route)
    assert sorted(r.reasons) == sorted(r2.reasons)


@given(texts, texts)
def test_t_p3_decide_is_symmetric_on_text(x: str, y: str) -> None:
    a, b = E(x), E(y)
    r, r2 = D(a, b), D(b, a)
    assert (r.verdict, r.route) == (r2.verdict, r2.route)


# ---- T-P2 no cluster contains a NOT_EQUIVALENT pair (FR-701) ----
@given(st.lists(attrs_for("VALVE"), min_size=2, max_size=7), st.data())
def test_t_p2_no_conflict_inside_a_cluster(rows: list[dict[str, Any]], data: Any) -> None:
    from app.core.cluster import constrained_clusters

    recs = [spec("VALVE", attrs) for attrs in rows]
    verdict = {(i, j): D(recs[i], recs[j]).verdict for i, j in combinations(range(len(recs)), 2)}
    edges = [
        (i, j, data.draw(st.floats(0.5, 1.0))) for (i, j), v in verdict.items() if v in POSITIVE
    ]

    def conflict(i: int, j: int) -> bool:
        return verdict[(min(i, j), max(i, j))] == "NOT_EQUIVALENT"

    clusters = constrained_clusters(len(recs), edges, conflict)
    assert sorted(m for c in clusters for m in c) == list(range(len(recs)))
    for c in clusters:
        for i, j in combinations(sorted(c), 2):
            assert verdict[(i, j)] != "NOT_EQUIVALENT", (c, i, j)


# ---- T-P4 idempotent normaliser (FR-201, TR-MOD-01); pass cap never reached (DEC-24) ----
PRINTABLE_ASCII = st.text(alphabet=string.printable)
PRINTABLE_UNICODE = st.text(st.characters(exclude_categories=("Cc", "Cf", "Cs", "Co", "Cn")))


def _idempotent_below_cap(x: str) -> None:
    from app.core.normalise import MAX_PASSES, normalise_passes

    once, passes = normalise_passes(x, dictionary())
    assert passes < MAX_PASSES, (x, passes)
    assert N(once) == once


@given(st.text())
def test_t_p4_normaliser_is_idempotent(x: str) -> None:
    _idempotent_below_cap(x)


@given(texts)
def test_t_p4_normaliser_is_idempotent_on_vocabulary(x: str) -> None:
    _idempotent_below_cap(x)


@given(PRINTABLE_ASCII)
def test_t_p4_normaliser_is_idempotent_on_printable_ascii(x: str) -> None:
    _idempotent_below_cap(x)


@given(PRINTABLE_UNICODE)
def test_t_p4_normaliser_is_idempotent_on_printable_unicode(x: str) -> None:
    _idempotent_below_cap(x)


@given(st.lists(st.sampled_from(sorted(set(string.printable) | {"1/2", "#", "GR.", "ADE"}))))
def test_t_p4_normaliser_is_idempotent_on_rule_fragments(parts: list[str]) -> None:
    _idempotent_below_cap(" ".join(parts) if len(parts) % 2 else "".join(parts))


# ---- T-P5 short text <= 40 characters or none (FR-901) ----
@given(st.sampled_from(CATEGORIES).flatmap(lambda c: st.tuples(st.just(c), attrs_for(c))))
def test_t_p5_short_desc_fits_or_is_none(cat_attrs: tuple[str, dict[str, Any]]) -> None:
    from app.core.shortdesc import short_desc

    s = short_desc(spec(*cat_attrs))
    assert s is None or (0 < len(s) <= 40)


@given(texts)
def test_t_p5_short_desc_fits_or_is_none_on_text(x: str) -> None:
    from app.core.shortdesc import short_desc

    a = E(x)
    if a.category is not None:
        s = short_desc(a)
        assert s is None or (0 < len(s) <= 40)


# ---- PRD Appendix D section 3: hard negatives never EQUIVALENT (smoke test, seed 7) ----
SIZES = [(2, "DN50"), (3, "DN80"), (4, "DN100"), (6, "DN150"), (8, "DN200")]
CL = [150, 300, 600]
GR = [("A216 WCB", "WCB"), ("A351 CF8M", "CF8M")]


def _render(e: dict[str, Any], st_: int) -> str:
    full, short = e["g"]
    s = [
        f"VALVE GATE {e['i']}IN CL{e['c']} {full} FLGD RF",
        f"GV {e['d'][2:]}NB {e['c']}# {short} RF FLANGED",
        f"GATE VALVE, {e['i']} INCH, CLASS {e['c']}, ASTM {full}, RAISED FACE FLANGED",
    ][st_]
    return s[:40] if st_ < 2 else s


def test_appendix_d_hard_negatives_never_equivalent() -> None:
    rng = random.Random(7)
    viol = 0
    for _ in range(1500):
        i, d = rng.choice(SIZES)
        e = {"i": i, "d": d, "c": rng.choice(CL), "g": rng.choice(GR)}
        n = dict(e)
        f = rng.choice("icg")
        if f == "i":
            n["i"], n["d"] = rng.choice([s for s in SIZES if s[0] != i])
        elif f == "c":
            n["c"] = rng.choice([c for c in CL if c != e["c"]])
        else:
            n["g"] = rng.choice([g for g in GR if g != e["g"]])
        st_ = rng.randrange(3)
        r = D(E(_render(e, st_)), E(_render(n, st_)))
        viol += r.verdict in POSITIVE
    assert viol == 0, viol


# ---- T-C CNMC check digit (FR-902; PRD Appendix D section 4) ----
def _cnmc_errors_detected(seq: int) -> None:
    from app.core.cnmc import cnmc_valid, new_cnmc

    c = new_cnmc(seq)
    assert cnmc_valid(c)
    body, chk = c[4:14], c[14]
    for p in range(10):
        for dgt in "0123456789":
            if dgt != body[p]:  # every single-digit error caught
                assert not cnmc_valid("NMC-" + body[:p] + dgt + body[p + 1 :] + chk)
    for p in range(9):
        if body[p] != body[p + 1] and {body[p], body[p + 1]} != {"0", "9"}:
            swapped = body[:p] + body[p + 1] + body[p] + body[p + 2 :]
            assert not cnmc_valid("NMC-" + swapped + chk)  # adjacent swaps caught (except 09/90)


def test_t_c_appendix_d_cnmc() -> None:
    from app.core.cnmc import new_cnmc

    rng = random.Random(1)
    for _ in range(500):
        _cnmc_errors_detected(rng.randrange(10**10))
    assert new_cnmc(1234567) == "NMC-00012345674"  # PRD 9.8 example


@given(st.integers(0, 10**10 - 1))
def test_t_c_cnmc_property(seq: int) -> None:
    _cnmc_errors_detected(seq)


def test_t_c_rejects_malformed_codes() -> None:
    from app.core.cnmc import cnmc_valid

    for bad in ("", "NMC-0001234567", "NMC-000123456745", "nmc-00012345674", "XMC-00012345674"):
        assert not cnmc_valid(bad)
