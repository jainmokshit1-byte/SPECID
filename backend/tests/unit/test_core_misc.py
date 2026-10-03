"""FR-701-703, FR-901-902 (TRD TR-MOD-07-09): clusters, CNMC and descriptions beyond Appendix D."""

import pytest

from app.core.cluster import (
    BlockedEdge,
    cluster_priority,
    cluster_with_blocked,
    cohesion,
    constrained_clusters,
)
from app.core.cnmc import cnmc_valid, new_cnmc
from app.core.shortdesc import long_desc, short_desc
from tests.coreenv import E, spec


# ---- clustering ----
def test_blocked_edges_say_why_not_merged() -> None:
    def conflict(i: int, j: int) -> bool:
        return {i, j} == {0, 2}

    clusters, blocked = cluster_with_blocked(3, [(0, 1, 0.9), (1, 2, 0.8)], conflict)
    assert clusters == [[0, 1], [2]]
    assert blocked == [BlockedEdge(1, 2, 0.8, "conflict")]


def test_ties_are_broken_by_index_for_determinism() -> None:
    def conflict(i: int, j: int) -> bool:
        return {i, j} == {1, 2}

    # equal scores: (0, 1) is taken before (0, 2) whatever the input order
    for edges in ([(0, 2, 0.9), (0, 1, 0.9)], [(0, 1, 0.9), (0, 2, 0.9)]):
        assert constrained_clusters(3, edges, conflict) == [[0, 1], [2]]


def test_size_cap_refuses_large_merges() -> None:
    edges = [(i, i + 1, 1.0) for i in range(5)]
    clusters, blocked = cluster_with_blocked(6, edges, lambda i, j: False, size_cap=3)
    assert max(len(c) for c in clusters) <= 3
    assert blocked and all(b.reason == "size cap" for b in blocked)


def test_priority_and_cohesion() -> None:
    assert cluster_priority([1000.0, None, 500.0], n_flags=2) == 3000.0
    assert cluster_priority([None, None], n_flags=0) == 1.0  # no value -> 1
    assert cohesion([0.98, 0.88]) == pytest.approx(0.93)
    assert cohesion([]) is None


# ---- CNMC ----
def test_cnmc_range() -> None:
    assert new_cnmc(0) == "NMC-00000000000" and cnmc_valid(new_cnmc(10**10 - 1))
    for bad in (-1, 10**10):
        with pytest.raises(ValueError):
            new_cnmc(bad)
    assert not cnmc_valid("NMC-٠٠٠٠٠٠٠٠٠٠٠")


# ---- descriptions (PRD 9.9) ----
def test_short_text_never_truncates() -> None:
    attrs = {"valve_type": "BUTTERFLY", "size_dn": 600, "pressure_class": 2500}
    long = spec("VALVE", {**attrs, "body_material": "A351-CF8M", "end_connection": "FLANGED-RTJ"})
    assert short_desc(long) is None  # 44 characters: flagged for manual abbreviation
    assert short_desc(long, limit=50) == "VLV BUTTERFLY 24IN CL2500 A351-CF8M FLGD RTJ"


def test_long_descriptions() -> None:
    assert long_desc(E("VALVE GATE 4IN CL150 A216 WCB FLGD RF")) == (
        "GATE VALVE, 4 IN (DN100), CLASS 150, ASTM A216 WCB, FLANGED RAISED FACE"
    )  # the PRD 9.9 example
    assert long_desc(E("PIPE SMLS 6IN SCH40 A106 GR.B BE")) == (
        "PIPE, SEAMLESS, 6 IN (DN150), SCH 40, ASTM A106 B, BEVELLED END"
    )
    assert long_desc(E("FLANGE WN 4IN CL150 RF A105")) == (
        "WELD NECK FLANGE, 4 IN (DN100), CLASS 150, RAISED FACE, ASTM A105"
    )
    assert long_desc(E("BOLT HEX M16X80 GR8.8 ZN")) == "HEX BOLT, M16 X 80 MM, GRADE 8.8, ZINC"
    assert long_desc(E("MOTOR AC SQ 100KW 1500RPM 4P 415V IP55")) == (
        "AC INDUCTION MOTOR, 100 KW, 4 POLE, 1500 RPM, 415 V, IP55"
    )
    assert long_desc(E("GASKET SPIRAL WND 4IN CL150 SS316/GRAF")) == (
        "SPIRAL WOUND GASKET, 4 IN (DN100), CLASS 150, SS316, GRAPHITE FILLER"
    )
    assert long_desc(E("FLANGE WN CL150 RF")) == "WELD NECK FLANGE, CLASS 150, RAISED FACE"


