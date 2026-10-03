"""PRD Appendix D sections 2, 5, 6, 7 ported to pytest against core/ (DEC-22).

Translation only: dataclass attributes for dict keys, explicit dictionary and templates. The
expected values are the ones in Appendix D. Section 3 (property smoke) and 4 (CNMC) are in
tests/property; section 1 is the golden set; section 8 (egress guard, T-S5) is Phase 5.
"""

import copy

from tests.coreenv import EQV, NOT, D, E, N, V, template_yaml, templates


# ---- section 2: route, flag and IDENTICAL checks (FR-604, FR-605, FR-606) ----
def test_extended_attribute_on_one_side_flags_the_pair() -> None:
    r = V("VALVE GATE 4IN CL150 WCB FLANGED RF API 600", "VALVE GATE 4IN CL150 WCB FLANGED RF")
    assert r.verdict == "EQUIVALENT" and r.route == "REVIEW"
    assert any("design_standard unverified" in x for x in r.reasons)


def test_residual_token_guard_flags_nace() -> None:
    r = V("VALVE GATE 4IN CL150 WCB FLANGED RF NACE", "VALVE GATE 4IN CL150 WCB FLANGED RF")
    assert r.verdict == "EQUIVALENT" and r.route == "REVIEW" and any("NACE" in x for x in r.reasons)


def test_non_critical_class_is_auto_eligible() -> None:
    r = V("NUT HEX M20 2H", "HEX NUT M20 A194 2H")
    assert r.route == "AUTO_ELIGIBLE"


def test_same_mpn_and_maker_is_identical() -> None:
    a = E("PUMP BOLT M16X80 8.8", mpn="X-1", maker="ACME")
    b = E("BOLT M16X80 8.8", mpn="X-1", maker="Acme")
    assert D(a, b).verdict == "IDENTICAL"


# ---- section 5: 40-character short descriptions (FR-901) ----
SHORT = {
    "VALVE GATE 4IN CL150 A216 WCB FLGD RF": "VLV GATE 4IN CL150 A216-WCB FLGD RF",
    "PIPE SMLS 6IN SCH40 A106 GR.B": "PIPE SMLS 6IN SCH40 A106-B",
    "FLANGE WN 4IN CL150 RF A105": "FLG WN 4IN CL150 RF A105",
    "BOLT HEX M16X80 GR8.8 ZN": "BOLT HEX M16X80 8.8 ZN",
    "MOTOR AC SQ 100KW 1500RPM 4P": "MOTOR AC IND 100KW 4P",
    "GASKET SPIRAL WND 4IN CL150 SS316/GRAF": "GASKET SPW 4IN CL150 SS316 GRAPH",
}


def test_short_descriptions_fit_40_characters() -> None:
    from app.core.shortdesc import short_desc

    for text, expected in SHORT.items():
        s = short_desc(E(text))
        assert s and len(s) <= 40
        assert s == expected  # the outputs printed in PRD Appendix D and table 9.9


# ---- section 6: constrained clustering (FR-701) ----
def test_cluster_never_joins_a_conflicting_pair() -> None:
    from app.core.cluster import constrained_clusters

    recs = [
        E("VALVE GATE 4IN CL150 WCB FLANGED RF API 600"),
        E("VALVE GATE 4IN CL150 WCB FLANGED RF"),
        E("VALVE GATE 4IN CL150 WCB FLANGED RF API 6D"),
    ]

    def conflict(i: int, j: int) -> bool:
        return D(recs[i], recs[j]).verdict == "NOT_EQUIVALENT"

    edges = [(0, 1, 0.9), (1, 2, 0.8)]
    assert all(D(recs[i], recs[j]).verdict == "EQUIVALENT" for i, j, _ in edges)
    assert conflict(0, 2)
    clusters = constrained_clusters(3, edges, conflict)
    assert clusters != [[0, 1, 2]]
    assert clusters == [[0, 1], [2]]  # printed in PRD Appendix D


# ---- section 7: signature features ----
def test_t_s6_evidence_cites_rules_and_conversions() -> None:
    r = V(*EQV[0])
    rows = {e.attr: e for e in r.evidence}
    assert rows["size_dn"].note_a == "4 IN = DN100" and rows["size_dn"].note_b == "100 NB = DN100"
    assert (
        rows["body_material"].note_b == "WCB -> A216-WCB" and rows["body_material"].note_a is None
    )
    assert all(e.rule.startswith("VALVE.") and e.rule_text for e in r.evidence)


def test_t_s6_rule_text_equals_template_yaml() -> None:
    defaults = {
        "core": "Must match",
        "ext": "Conflict vetoes; a value stated on one side only flags the pair",
    }  # level defaults of the reference `rule()` (PRD Appendix C)
    for a, b in NOT + EQV:
        r = V(a, b)
        doc = template_yaml()[E(a).category]
        for e in r.evidence:
            assert e.rule == f"{doc['category']}.{e.attr}"
            assert e.rule_text == doc.get("rule_text", {}).get(e.attr, defaults[e.level])


def test_t_s6_decision_records_template_version() -> None:
    r = V(*EQV[0])
    assert r.template_version == templates()["VALVE"].version


def test_t_s1_baselines_on_the_12_hand_built_pairs() -> None:
    from app.core.baselines import b1, b2
    from app.core.radar import text_sim

    def sim(a: str, b: str) -> float:
        return text_sim(N(a), N(b))

    fp1 = sum(b1(sim(a, b), 0.85) for a, b in NOT)
    tp1 = sum(b1(sim(a, b), 0.85) for a, b in EQV)
    fp2 = sum(b2(sim(a, b), a, b, 0.55) for a, b in NOT)
    tp2 = sum(b2(sim(a, b), a, b, 0.55) for a, b in EQV)
    assert (fp1, tp1, fp2, tp2) == (6, 2, 0, 2)


def test_t_s2_lookalike_guard_on_the_12_pairs() -> None:
    from app.core.radar import lookalike_class, text_sim

    cls = [lookalike_class(text_sim(N(a), N(b)), V(a, b).verdict, 0.85, 0.75) for a, b in NOT + EQV]
    assert cls.count("LOOKALIKE_VETOED") == 6 and cls.count("HIDDEN_TWIN") == 2


def test_t_s2_classes_only_for_their_verdicts() -> None:
    from app.core.radar import lookalike_class

    for sim in (0.0, 0.5, 0.75, 0.8, 0.85, 1.0):
        for verdict in ("IDENTICAL", "EQUIVALENT", "NOT_EQUIVALENT", "INSUFFICIENT_DATA"):
            c = lookalike_class(sim, verdict, 0.85, 0.75)
            if c == "LOOKALIKE_VETOED":
                assert verdict == "NOT_EQUIVALENT" and sim >= 0.85
            elif c == "HIDDEN_TWIN":
                assert verdict in ("EQUIVALENT", "IDENTICAL") and sim <= 0.75
            else:
                assert c is None
                assert not (verdict == "NOT_EQUIVALENT" and sim >= 0.85)
                assert not (verdict in ("EQUIVALENT", "IDENTICAL") and sim <= 0.75)


def test_t_s3_supplying_a_missing_attribute() -> None:
    from app.core.extract import supply_attribute

    a = E("VALVE GATE 4IN CL150 WCB FLANGED")
    b = E("VALVE GATE 4IN CL150 WCB FLANGED RF")
    assert D(a, b).verdict == "INSUFFICIENT_DATA"
    a2 = supply_attribute(a, "end_connection", "FLANGED-RF", "datasheet D-123")
    r2 = D(a2, b)
    assert r2.verdict == "EQUIVALENT"
    assert [e.note_a for e in r2.evidence if e.attr == "end_connection"] == [
        "supplied by user: datasheet D-123"
    ]
    assert a2.meta["end_connection"].tier == "USER"
    # a supplied value can still conflict: it never overrides the veto
    assert (
        D(supply_attribute(a, "end_connection", "FLANGED-FF", "x"), b).verdict == "NOT_EQUIVALENT"
    )


def test_t_s3_source_note_is_mandatory() -> None:
    import pytest
    from app.core.extract import supply_attribute

    a = E("VALVE GATE 4IN CL150 WCB FLANGED")
    for empty in ("", "   "):
        with pytest.raises(ValueError):
            supply_attribute(a, "end_connection", "FLANGED-RF", empty)


def test_t_s4_impact_preview() -> None:
    from app.core.decide import decide, impact_preview

    t = templates()
    pairs = [
        (
            E("VALVE GATE 4IN CL150 WCB FLANGED RF API 600"),
            E("VALVE GATE 4IN CL150 WCB FLANGED RF"),
        ),
        (E("PIPE 6IN SCH40 A106B"), E("PIPE SMLS 6IN SCH40 A106 GRB")),
        (E("BOLT HEX M16X80 8.8"), E("BOLT HEX M16X80 8.8 ZN")),
    ]
    valve = t["VALVE"]
    draft = {
        **t,
        "VALVE": valve.model_copy(
            update={
                "core": [*valve.core, "design_standard"],
                "extended": [x for x in valve.extended if x != "design_standard"],
            }
        ),
    }
    ch = impact_preview(pairs, t, draft)
    assert len(ch) == 1 and (ch[0].old, ch[0].new) == ("EQUIVALENT", "INSUFFICIENT_DATA")
    assert ch[0].pair == 0
    assert impact_preview(pairs, t, t) == []  # unchanged template: no transitions
    # passing the templates explicitly gives the same verdict as the active set
    assert decide(*pairs[0], copy.deepcopy(t)).verdict == D(*pairs[0]).verdict


def test_normalised_text_is_what_text_sim_sees() -> None:
    # TRD TR-MOD-10: token-set ratio / 100 on NORMALISED text
    from app.core.radar import text_sim

    assert text_sim(N("150# VALVE"), N("CL150 VALVE")) == 1.0
    assert 0.0 <= text_sim(N("GATE VALVE"), N("BOLT")) < 1.0
