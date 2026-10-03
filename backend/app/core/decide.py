"""The decision: veto -> unknown-state -> route (PRD 9.5, FR-601-609, FR-611; TRD TR-MOD-06).

Pure and symmetric. No score, model or advisor input exists here, so nothing can override a
veto (FR-602, NFR-04). This is the reference `decide` (PRD Appendix C) with the item
criticality of TRD TR-ALG-02 and the symmetric NUT rule (DEC-21 DEV-2).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, Final

from app.core.confidence import p_rule
from app.core.templates import Template
from app.core.types import Decision, EvidenceRow, Level, Route, Spec, Status, Verdict

# level defaults of the reference `rule()`; per-attribute texts come from the template YAML
DEFAULT_RULE_TEXT: Final[dict[Level, str]] = {
    "core": "Must match",
    "ext": "Conflict vetoes; a value stated on one side only flags the pair",
}
MATERIAL_ATTRS: Final = frozenset({"material", "body_material", "winding_material"})
POWER_TOLERANCE: Final = 0.01  # power_kw equal within 1% (PRD 9.3)
RPM_TOLERANCE: Final = 0.05  # rpm equal within 5%
# residual words that matter even without a digit (FR-303)
WATCH: Final = frozenset(
    {"NACE", "LTCS", "CRYO", "CRYOGENIC", "BELLOWS", "SOUR", "HIC", "ATEX", "IECEX", "FIRESAFE",
     "FIREPROOF", "EPOXY", "LINED"}
)  # fmt: skip


def family(code: str) -> str:
    """Material family of PRD Appendix B.3 (CS, 316, 304, ...)."""
    if code.startswith("A182-F"):
        return code[6:]
    if code.startswith("SS"):
        return code[2:]
    if code == "A351-CF8M":
        return "316"
    if code == "A351-CF8":
        return "304"
    if code.startswith(("A216", "A105", "A106", "A53")):
        return "CS"
    return code


def _generic(code: str) -> bool:
    return code.endswith("?") or code.startswith("SS")


def compare(name: str, x: Any, y: Any) -> Status:
    """Attribute status of PRD 9.5."""
    if x is None and y is None:
        return "MISSING_BOTH"
    if x is None or y is None:
        return "MISSING_ONE"
    if x == y:
        return "MATCH"
    if name in MATERIAL_ATTRS:
        if family(x) != family(y):
            return "CONFLICT"
        # same family: one generic and one specific is PARTIAL; two specific codes conflict
        return "PARTIAL" if _generic(x) != _generic(y) else "CONFLICT"
    if name == "end_connection":
        if x.startswith("FLANGED") and y.startswith("FLANGED") and "?" in (x[-1], y[-1]):
            return "PARTIAL"
        return "CONFLICT"
    if name == "power_kw":
        return "MATCH" if abs(x - y) <= POWER_TOLERANCE * max(x, y) else "CONFLICT"
    if name == "rpm":
        return "MATCH" if abs(x - y) <= RPM_TOLERANCE * max(x, y) else "CONFLICT"
    return "CONFLICT"


def _make_key(value: str | None) -> str:
    return (value or "").strip().upper()


def same_make(a: Spec, b: Spec) -> bool:
    """IDENTICAL test of PRD 9.5 / FR-604 (DEC-26 DEV-5).

    MPN and manufacturer must both be present on both sides and equal, compared without case
    after trimming. Used only after the veto and the unknown-state have passed, so a failed test
    only means EQUIVALENT instead of IDENTICAL.
    """
    mpn_a, mpn_b = _make_key(a.mpn), _make_key(b.mpn)
    maker_a, maker_b = _make_key(a.maker), _make_key(b.maker)
    return bool(mpn_a and maker_a) and mpn_a == mpn_b and maker_a == maker_b


def _note(spec: Spec, attr: str) -> str | None:
    meta = spec.meta.get(attr)
    return meta.note if meta else None


def _technical(residual: Sequence[str]) -> set[str]:
    return {x for x in residual if any(c.isdigit() for c in x) or x in WATCH}


def decide(
    a: Spec,
    b: Spec,
    templates: Mapping[str, Template],
    criticality: tuple[bool | None, bool | None] = (None, None),
) -> Decision:
    """Verdict, route, reasons and evidence for one pair. `templates` may be a DRAFT set."""
    if a.category is None or b.category is None:
        return Decision("INSUFFICIENT_DATA", "REVIEW", ("category not recognised",), (), None, None)
    if a.category != b.category:
        return Decision("NOT_EQUIVALENT", "NONE", ("category differs",), (), 0.0, None)
    t = templates[a.category]
    nut = "NUT" in (a.attrs.get("fastener_type"), b.attrs.get("fastener_type"))  # DEV-2
    core = [c for c in t.core if not (nut and c == "length_mm")]

    evidence: list[EvidenceRow] = []
    conflicts: list[str] = []
    missing: list[str] = []
    flags: list[str] = []
    levels: tuple[tuple[Level, list[str]], ...] = (("core", core), ("ext", t.extended))
    for level, names in levels:
        for n in names:
            x, y = a.attrs.get(n), b.attrs.get(n)
            s = compare(n, x, y)
            evidence.append(
                EvidenceRow(
                    attr=n,
                    level=level,
                    a=x,
                    b=y,
                    status=s,
                    rule=f"{a.category}.{n}",
                    rule_text=t.rule_text.get(n, DEFAULT_RULE_TEXT[level]),
                    note_a=_note(a, n),
                    note_b=_note(b, n),
                )
            )
            if s == "CONFLICT":
                conflicts.append(n)
            elif level == "core" and s in ("MISSING_ONE", "MISSING_BOTH", "PARTIAL"):
                missing.append(n)
            elif level == "ext" and s in ("MISSING_ONE", "PARTIAL"):
                flags.append(n + " unverified")
    diff = _technical(a.residual) ^ _technical(b.residual)
    if diff:
        flags.append("unexplained tokens: " + " ".join(sorted(diff)))
    ev = tuple(evidence)

    verdict: Verdict
    route: Route
    reasons: tuple[str, ...]
    if conflicts:  # hard veto, no override
        verdict, route, reasons = "NOT_EQUIVALENT", "NONE", ("conflict: " + ", ".join(conflicts),)
    elif missing:  # unknown-state: ask for the attribute
        verdict, route = "INSUFFICIENT_DATA", "REVIEW"
        reasons = ("core attribute not verifiable: " + ", ".join(missing),)
    else:
        # item criticality overrides the template default; either side critical -> critical
        if any(t.critical_default if c is None else c for c in criticality):
            flags.append("critical class: maker-checker")
        verdict = "IDENTICAL" if same_make(a, b) else "EQUIVALENT"
        route = "REVIEW" if flags else "AUTO_ELIGIBLE"
        reasons = tuple(flags)
    d = Decision(verdict, route, reasons, ev, None, t.version)
    return replace(d, confidence=p_rule(d))


@dataclass(frozen=True)
class Transition:
    """A stored pair whose (verdict, route) would change under a draft rulebook."""

    pair: int
    old: Verdict
    new: Verdict
    old_route: Route
    new_route: Route


def impact_preview(
    pairs: Sequence[tuple[Spec, Spec]],
    templates: Mapping[str, Template],
    draft: Mapping[str, Template],
) -> list[Transition]:
    """Rulebook impact preview (PRD 9.13.6, SF-6): the pairs that change under `draft`."""
    out = []
    for i, (a, b) in enumerate(pairs):
        old, new = decide(a, b, templates), decide(a, b, draft)
        if (old.verdict, old.route) != (new.verdict, new.route):
            out.append(Transition(i, old.verdict, new.verdict, old.route, new.route))
    return out
