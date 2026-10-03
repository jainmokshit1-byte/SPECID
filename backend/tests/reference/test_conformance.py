"""core/ conforms to the verbatim PRD Appendix C reference, except allowlisted deviations.

The allowlist is DEVIATIONS below; each entry names the DEC that documents it (DEC-21, 24, 26).

Compared on every corpus pair: extraction (category, stated attributes, notes, residual), the
decision (verdict, route, reasons, every evidence row), the short text, text_sim, both
baselines and the CNMC. Any difference that is not explained by an entry of DEVIATIONS fails.
Adding an entry needs a DEC in docs/DECISIONS.md (checked below).
"""

import random
import re
import string
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests.coreenv import EQV, NOT, D, E, N
from tests.golden.test_golden import CASES
from tests.property.strategies import texts
from tests.property.test_properties import CL, GR, SIZES, _render
from tests.reference import specid_ref as R

REPO = Path(__file__).resolve().parents[3]
REF_FILE = Path(__file__).with_name("specid_ref.py")

# The only differences allowed between core/ and the reference: key -> (decision, summary).
DEVIATIONS = {
    "DEV-1": ("DEC-21", "short_desc leaves out missing parts (reference raises or writes None)"),
    "DEV-2": ("DEC-21", "NUT rule drops length_mm when either side is a nut (reference: A only)"),
    "DEV-3": ("DEC-21", "normaliser applies NFKC and drops non-printing characters (TR-MOD-01)"),
    "DEV-4": ("DEC-24", "normaliser repeats the rules to a fixed point (FR-201 idempotence)"),
    "DEV-5": ("DEC-26", "IDENTICAL needs MPN and maker on both sides, equal without case"),
}
REF_MAX_PASSES = 8  # the same cap as core/ (DEC-24)


def _prd() -> Path | None:
    for p in (REPO / "impdocs", Path("/impdocs")):
        f = p / "SIH26099_SpecID_Prototype_PRD.md"
        if f.exists():
            return f
    return None


def test_reference_is_appendix_c_verbatim() -> None:
    prd = _prd()
    if prd is None:
        pytest.skip("impdocs/ not mounted")
    doc = prd.read_text("utf-8")
    appendix = doc[doc.index("## Appendix C: Reference implementation") :]
    m = re.search(r"^```python\n(.*?)^```$", appendix, re.S | re.M)
    assert m is not None
    assert REF_FILE.read_text("utf-8") == m.group(1)


def test_every_deviation_is_logged_in_decisions() -> None:
    candidates = [REPO / "docs" / "DECISIONS.md", Path("/docs/DECISIONS.md")]
    log = next((p for p in candidates if p.exists()), None)
    if log is None:
        pytest.skip("docs/ not mounted")
    rows = log.read_text("utf-8").splitlines()
    for key, (dec, _) in DEVIATIONS.items():
        row = next(line for line in rows if f"| {dec} |" in line)
        assert f"**{key}**" in row, (key, dec)


# ---- allowlist predicates ----
def _dev3(text: str) -> bool:
    """DEV-3 applies only to input with a non-ASCII or a non-printing character (DEC-21).

    Printable-ASCII input (whitespace included) gets no tolerance: NFKC leaves it unchanged
    and there is nothing to remove, so core/ must match the reference exactly.
    """
    return not text.isascii() or any(not ch.isprintable() and not ch.isspace() for ch in text)


def _dev4(text: str) -> bool:
    """DEV-4 applies only when the reference normaliser itself is not idempotent on `text`."""
    once = R.normalise(text)
    return R.normalise(once) != once


def _ref_input(text: str) -> str:
    """The text the reference is run on: `text`, or under DEV-4 the reference's own fixed point."""
    if not _dev4(text):
        return text
    t = R.normalise(text)
    for _ in range(REF_MAX_PASSES - 1):
        nxt = R.normalise(t)
        if nxt == t:
            return t
        t = nxt
    raise AssertionError(f"reference fixed point not reached in {REF_MAX_PASSES} passes")


def _dev1(ref_short: Any) -> bool:
    """DEV-1 applies when the reference fails on, or prints, a missing value."""
    return isinstance(ref_short, Exception) or "None" in ref_short or "?IN" in ref_short


def _dev2(ra: dict[str, Any], rb: dict[str, Any]) -> bool:
    """DEV-2 applies when only side B is a nut (the reference keys the NUT rule on side A)."""
    return ra["attrs"].get("fastener_type") != "NUT" and rb["attrs"].get("fastener_type") == "NUT"


def _drop_attr(reasons: list[str], attr: str) -> list[str]:
    out = []
    for r in reasons:
        head, sep, tail = r.partition(": ")
        if sep and head in ("conflict", "core attribute not verifiable"):
            names = [n for n in tail.split(", ") if n != attr]
            if names:
                out.append(f"{head}: {', '.join(names)}")
        else:
            out.append(r)
    return out


# ---- comparison ----
def _core_extraction(x: str) -> dict[str, Any]:
    s = E(x)
    return {
        "category": s.category,
        "attrs": {k: v for k, v in s.attrs.items() if v is not None},
        "notes": {k: m.note for k, m in s.meta.items() if m.note},
        "residual": list(s.residual),
    }


def _ref_extraction(x: str) -> dict[str, Any]:
    s = R.extract(x)
    return {
        "category": s["category"],
        "attrs": {k: v for k, v in s["attrs"].items() if v is not None},
        "notes": dict(s["notes"]),
        "residual": list(s["residual"]),
    }


def _rows_core(r: Any) -> list[tuple[Any, ...]]:
    return [
        (e.attr, e.level, e.a, e.b, e.status, e.rule, e.rule_text, e.note_a, e.note_b)
        for e in r.evidence
    ]


def _rows_ref(r: dict[str, Any]) -> list[tuple[Any, ...]]:
    keys = ("attr", "level", "a", "b", "status", "rule", "rule_text", "note_a", "note_b")
    return [tuple(e[k] for k in keys) for e in r["evidence"]]


def _short_ref(x: str) -> Any:
    try:
        return R.short_desc(R.extract(x))
    except Exception as exc:  # the reference raises on some missing values (DEV-1)
        return exc


def assert_conforms(x: str, y: str) -> None:
    if _dev3(x) or _dev3(y):
        return  # DEV-3
    xr, yr = _ref_input(x), _ref_input(y)  # DEV-4: the reference runs on its fixed point
    for t, tr in ((x, xr), (y, yr)):
        assert _core_extraction(t) == _ref_extraction(tr), t
        if R.extract(tr)["category"] is not None:
            from app.core.shortdesc import short_desc

            ref_short = _short_ref(tr)
            if not _dev1(ref_short):
                assert short_desc(E(t)) == ref_short, t

    ra, rb = R.extract(xr), R.extract(yr)
    ref, core = R.decide(ra, rb), D(E(x), E(y))
    assert (core.verdict, core.route) == (ref["verdict"], ref["route"]), (x, y)
    core_rows, ref_rows = _rows_core(core), _rows_ref(ref)
    core_reasons, ref_reasons = list(core.reasons), list(ref["reasons"])
    if _dev2(ra, rb):  # DEV-2
        ref_rows = [row for row in ref_rows if row[0] != "length_mm"]
        core_rows = [row for row in core_rows if row[0] != "length_mm"]
        ref_reasons, core_reasons = _drop_attr(ref_reasons, "length_mm"), _drop_attr(
            core_reasons, "length_mm"
        )
    assert core_rows == ref_rows, (x, y)
    assert core_reasons == ref_reasons, (x, y)

    from app.core.baselines import b1, b2
    from app.core.radar import text_sim

    sim = text_sim(N(x), N(y))
    assert sim == R.text_sim(xr, yr)
    for tau in (0.55, 0.85):
        assert b1(sim, tau) == R.baseline_b1(xr, yr, tau)
        # B2 compares the numeric tokens of the RAW texts (PRD 10.2b), so x and y, not xr, yr
        ref_b2 = R.text_sim(xr, yr) >= tau and R.numeric_tokens(x) == R.numeric_tokens(y)
        assert b2(sim, x, y, tau) == ref_b2


# ---- corpora ----
APPENDIX_D_EXTRA = [
    ("VALVE GATE 4IN CL150 WCB FLANGED RF API 600", "VALVE GATE 4IN CL150 WCB FLANGED RF"),
    ("VALVE GATE 4IN CL150 WCB FLANGED RF NACE", "VALVE GATE 4IN CL150 WCB FLANGED RF"),
    ("PUMP BOLT M16X80 8.8", "BOLT M16X80 8.8"),
    ("PIPE 6IN SCH40 A106B", "PIPE SMLS 6IN SCH40 A106 GRB"),
    ("BOLT HEX M16X80 8.8", "BOLT HEX M16X80 8.8 ZN"),
    ("VALVE GATE 4IN CL150 WCB FLANGED RF API 6D", "VALVE GATE 4IN CL150 WCB FLANGED RF"),
    ("HEX NUT M20 A194 2H", "BOLT HEX M20X80 8.8"),  # DEV-2 both ways
    ("BOLT HEX M20X80 8.8", "HEX NUT M20 A194 2H"),
    ("NUT M20X120 2H", "STUD M20X90 B7"),
    ("STUD M20X90 B7", "NUT M20X120 2H"),
]
GOLDEN_PAIRS = [(p.values[1]["a"], p.values[1]["b"]) for p in CASES]


@pytest.mark.parametrize(("x", "y"), GOLDEN_PAIRS + NOT + EQV + APPENDIX_D_EXTRA)
def test_core_conforms_on_appendix_d_texts(x: str, y: str) -> None:
    assert_conforms(x, y)
    assert_conforms(y, x)


def test_core_conforms_on_the_appendix_d_renders() -> None:
    rng = random.Random(7)
    for _ in range(1500):
        i, d = rng.choice(SIZES)
        e = {"i": i, "d": d, "c": rng.choice(CL), "g": rng.choice(GR)}
        n = {"i": rng.choice(SIZES)[0], "d": d, "c": rng.choice(CL), "g": rng.choice(GR)}
        n["d"] = dict(SIZES)[n["i"]]
        st_ = rng.randrange(3)
        assert_conforms(_render(e, st_), _render(n, st_))


@given(texts, texts)
def test_core_conforms_on_generated_text(x: str, y: str) -> None:
    assert_conforms(x, y)


@given(st.text(), st.text())
def test_core_conforms_on_any_text(x: str, y: str) -> None:
    assert_conforms(x, y)


PRINTABLE_ASCII = st.text(alphabet=string.printable)


@given(PRINTABLE_ASCII, PRINTABLE_ASCII)
def test_core_conforms_on_printable_ascii(x: str, y: str) -> None:
    assert not _dev3(x) and not _dev3(y)  # no DEV-3 tolerance on printable ASCII
    assert_conforms(x, y)


def test_ascii_input_gets_no_dev3_tolerance(monkeypatch: pytest.MonkeyPatch) -> None:
    """A planted core/ difference fails on ASCII input; DEV-3 tolerates it only on non-ASCII."""
    real_e = E

    def drifted(text: str, mpn: str | None = None, maker: str | None = None) -> Any:
        s = real_e(text, mpn, maker)
        return replace(s, residual=(*s.residual, "DRIFT"))

    monkeypatch.setattr(sys.modules[__name__], "E", drifted)
    ascii_text = "VALVE GATE 4IN CL150 WCB FLANGED RF"
    with pytest.raises(AssertionError):
        assert_conforms(ascii_text, ascii_text)
    assert_conforms(ascii_text + " É", ascii_text)  # non-ASCII input: DEV-3 applies

    ascii_inputs = [t for pair in GOLDEN_PAIRS for t in pair] + ['4" PIPE', "A\tB\nC\x0bD"]
    assert not any(_dev3(t) for t in ascii_inputs)
    for t in ("VALVE ＧATE", "GATE\x00VALVE", "GATE​VALVE"):
        assert _dev3(t), t


def test_dev1_short_desc_leaves_out_missing_values() -> None:
    from app.core.shortdesc import short_desc

    assert isinstance(_short_ref("MOTOR 100KW 4P"), Exception)  # reference: None.replace
    assert short_desc(E("MOTOR 100KW 4P")) == "MOTOR 100KW 4P"
    assert "None" in _short_ref("VALVE GATE 4IN WCB FLANGED RF")  # reference: CLNone
    assert short_desc(E("VALVE GATE 4IN WCB FLANGED RF")) == "VLV GATE 4IN A216-WCB FLGD RF"


def test_dev2_nut_rule_is_symmetric() -> None:
    a, b = E("BOLT HEX M20X80 8.8"), E("HEX NUT M20 A194 2H")
    r, r2 = D(a, b), D(b, a)
    assert [e.attr for e in r.evidence] == [e.attr for e in r2.evidence]
    assert "length_mm" not in [e.attr for e in r.evidence]
    assert sorted(r.reasons) == sorted(r2.reasons)


def test_cnmc_conforms() -> None:
    from app.core.cnmc import cnmc_valid, new_cnmc

    rng = random.Random(3)
    for _ in range(2000):
        seq = rng.randrange(10**10)
        assert new_cnmc(seq) == R.new_cnmc(seq)
        c = R.new_cnmc(seq)
        bad = c[:-1] + str((int(c[-1]) + 1) % 10)
        assert cnmc_valid(c) and not cnmc_valid(bad) and not R.cnmc_valid(bad)


def test_dev4_applies_only_where_the_reference_is_not_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DEV-4 excuses nothing on idempotent ASCII input; where it applies, core/ is still exact."""
    assert _dev4("1/2 #") and _dev4("GR.ADE B")
    assert _ref_input("1/2 #") == "1 CL2" and _ref_input("GR.ADE B") == "GRB"
    golden = [t for pair in GOLDEN_PAIRS for t in pair]
    assert not any(_dev4(t) for t in golden)  # the golden texts never need DEV-4
    assert_conforms("PIPE 6IN SCH40 A106 GR.ADE B", "PIPE 6IN SCH40 A106B")  # DEV-4, exact
    assert_conforms("VALVE 1/2 # GATE", "VALVE GATE 1/2 IN CL2")

    real_e = E

    def drifted(text: str, mpn: str | None = None, maker: str | None = None) -> Any:
        s = real_e(text, mpn, maker)
        return replace(s, residual=(*s.residual, "DRIFT"))

    monkeypatch.setattr(sys.modules[__name__], "E", drifted)
    idempotent = "VALVE GATE 4IN CL150 WCB FLANGED RF"
    assert not _dev4(idempotent) and not _dev3(idempotent)
    with pytest.raises(AssertionError):
        assert_conforms(idempotent, idempotent)  # a planted difference is not excused
    with pytest.raises(AssertionError):
        assert_conforms("PIPE 6IN SCH40 A106 GR.ADE B", "PIPE 6IN SCH40 A106B")  # nor under DEV-4


def _key(value: str | None) -> str:
    return (value or "").strip().upper()


def _dev5(make_a: tuple[str | None, str | None], make_b: tuple[str | None, str | None]) -> bool:
    """DEV-5 applies only when (a) a manufacturer is missing or empty on either side, or (b) the
    MPNs or the manufacturers differ only in case (after the same trim as core/)."""
    (mpn_a, maker_a), (mpn_b, maker_b) = make_a, make_b
    if not _key(maker_a) or not _key(maker_b):
        return True
    return any(x != y and _key(x) == _key(y) for x, y in ((mpn_a, mpn_b), (maker_a, maker_b)))


def assert_make_conforms(x: str, y: str, make_a: Any, make_b: Any) -> None:
    """Under DEV-5 only IDENTICAL vs EQUIVALENT may differ, and only as PRD 9.5 says."""
    ref = R.decide(R.extract(x, *make_a), R.extract(y, *make_b))
    core = D(E(x, *make_a), E(y, *make_b))
    assert (core.route, list(core.reasons)) == (ref["route"], ref["reasons"]), (x, y)
    if _dev5(make_a, make_b) and ref["verdict"] in ("IDENTICAL", "EQUIVALENT"):
        (mpn_a, maker_a), (mpn_b, maker_b) = make_a, make_b
        prd = bool(_key(mpn_a) and _key(maker_a)) and (_key(mpn_a), _key(maker_a)) == (
            _key(mpn_b),
            _key(maker_b),
        )
        assert core.verdict == ("IDENTICAL" if prd else "EQUIVALENT"), (x, y, make_a, make_b)
    else:
        assert core.verdict == ref["verdict"], (x, y, make_a, make_b)


MAKES = [
    (("X-1", "ACME"), ("X-1", "ACME")),  # exact: no DEV-5
    (("X-1", "ACME"), ("X-1", "acme")),  # DEV-5 (b)
    (("x-1", "ACME"), ("X-1", "ACME")),  # DEV-5 (b): the reference compares MPNs with case
    (("X-1", "ACME"), ("X-1", None)),  # DEV-5 (a)
    (("X-1", None), ("X-1", None)),  # DEV-5 (a): the reference calls this IDENTICAL
    (("X-1", ""), ("X-1", "")),  # DEV-5 (a)
    ((None, "ACME"), (None, "ACME")),
    (("X-1", "ACME"), ("X-2", "ACME")),
    (("X-1", "ACME"), ("X-1", "BETA")),
]
MAKE_TEXTS = [
    ("VALVE GATE 4IN CL150 WCB FLANGED RF", "GV 100NB 150# WCB RF FLANGED"),
    ("NUT HEX M20 2H", "HEX NUT M20 A194 2H"),
    ("VALVE GATE 4IN CL150 WCB FLANGED RF", "VALVE GATE 4IN CL300 WCB FLANGED RF"),  # veto
    ("VALVE GATE 4IN CL150 WCB FLANGED", "VALVE GATE 4IN CL150 WCB FLANGED RF"),  # unknown
]


@pytest.mark.parametrize(("make_a", "make_b"), MAKES)
def test_identical_conforms_on_mpn_and_maker(make_a: Any, make_b: Any) -> None:
    """The text corpora carry no MPN or maker; IDENTICAL vs EQUIVALENT is checked here."""
    for x, y in MAKE_TEXTS:
        assert_make_conforms(x, y, make_a, make_b)
        assert_make_conforms(y, x, make_b, make_a)


def test_dev5_scope_and_planted_differences(monkeypatch: pytest.MonkeyPatch) -> None:
    assert not _dev5(("X-1", "ACME"), ("X-1", "ACME"))
    assert not _dev5(("X-1", "ACME"), ("X-2", "BETA"))
    assert _dev5(("X-1", "ACME"), ("X-1", None)) and _dev5(("X-1", "ACME"), ("x-1", "ACME"))
    real_d = D

    def drifted_verdict(a: Any, b: Any, **kw: Any) -> Any:
        r = real_d(a, b, **kw)
        return replace(r, verdict="EQUIVALENT") if r.verdict == "IDENTICAL" else r

    def drifted_route(a: Any, b: Any, **kw: Any) -> Any:
        return replace(real_d(a, b, **kw), route="AUTO_ELIGIBLE")

    x, y = MAKE_TEXTS[0]
    monkeypatch.setattr(sys.modules[__name__], "D", drifted_verdict)
    with pytest.raises(AssertionError):  # outside DEV-5 a verdict change is not excused
        assert_make_conforms(x, y, ("X-1", "ACME"), ("X-1", "ACME"))
    monkeypatch.setattr(sys.modules[__name__], "D", drifted_route)
    with pytest.raises(AssertionError):  # inside DEV-5 the route must still match
        assert_make_conforms(x, y, ("X-1", "ACME"), ("X-1", None))
