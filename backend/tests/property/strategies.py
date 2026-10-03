"""Hypothesis strategies over template value domains (TRD TR-TST-03).

Values come from the template YAML `value_domains` where a template defines them; the other
attributes use small domains from PRD Appendix B (B.1 sizes, B.3 materials) and section 10.1.
Domains are kept small on purpose so that MATCH, PARTIAL and CONFLICT all occur often.
"""

from typing import Any

from hypothesis import strategies as st

from tests.coreenv import EQV, NOT, template_yaml

# attributes that no template YAML gives a value domain for (PRD B.1, B.3, 10.1)
EXTRA_DOMAINS: dict[str, dict[str, list[Any]]] = {
    "VALVE": {
        "size_dn": [50, 100],
        "body_material": ["A216-WCB", "A351-CF8M", "A182-F316", "SS316"],
        "end_connection": ["FLANGED-RF", "FLANGED-FF", "FLANGED-?", "BW"],
        "design_standard": ["API-600", "API-6D"],
        "trim": ["8", "12"],
    },
    "PIPE": {
        "size_dn": [100, 150],
        "schedule": ["40", "80", "STD"],
        "material": ["A106-B", "A106-?", "A53-B"],
        "end_finish": ["PE", "BE"],
    },
    "FLANGE": {
        "size_dn": [50, 100],
        "pressure_class": [150, 300],
        "material": ["A105", "A182-F316", "SS316", "A351-CF8M"],
    },
    "FASTENER": {
        "thread": ["M16", "M20"],
        "length_mm": [80, 90],
        "head": ["HEX"],
        "coating": ["ZINC", "HDG"],
    },
    "MOTOR": {
        "motor_type": ["AC-IND", "AC"],
        "power_kw": [93.0, 93.2, 100.0, 110.0],
        "poles": [4, 6],
        "rpm": [1450, 1480, 1000],
        "voltage": [415, 690],
        "ip": ["IP55"],
        "mounting": ["B3", "B5"],
    },
    "GASKET": {
        "size_dn": [50, 100],
        "pressure_class": [150, 300],
        "winding_material": ["SS316", "A182-F316", "SS304"],
    },
}
RESIDUAL = ["NACE", "LTCS", "X1", "PAINTED", "BELLOWS", "42"]


def domains(category: str) -> dict[str, list[Any]]:
    doc = template_yaml()[category]
    out: dict[str, list[Any]] = {}
    for attr in [*doc["core"], *doc.get("extended", [])]:
        yaml_values = doc.get("value_domains", {}).get(attr, [])
        values = list(dict.fromkeys([*yaml_values, *EXTRA_DOMAINS[category].get(attr, [])]))
        assert values, f"no domain for {category}.{attr}"
        out[attr] = values
    return out


CATEGORIES = sorted(EXTRA_DOMAINS)


@st.composite
def attrs_for(draw: Any, category: str) -> dict[str, Any]:
    return {
        attr: draw(st.one_of(st.none(), st.sampled_from(values)))
        for attr, values in domains(category).items()
    }


@st.composite
def spec_kwargs(draw: Any, category: str | None) -> dict[str, Any]:
    """Keyword arguments for tests.coreenv.spec()."""
    return {
        "category": category,
        "attrs": draw(attrs_for(category)) if category else {},
        "residual": draw(st.lists(st.sampled_from(RESIDUAL), max_size=2, unique=True)),
        "mpn": draw(st.sampled_from([None, "X-1", "X-2"])),
        "maker": draw(st.sampled_from([None, "ACME", "acme", "BETA"])),
    }


@st.composite
def spec_pair(draw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Mostly same-category pairs; sometimes different or unrecognised categories."""
    ca = draw(st.sampled_from(CATEGORIES))
    cb = draw(st.sampled_from([ca, ca, ca, ca, *CATEGORIES, None]))
    ca = draw(st.sampled_from([ca] * 9 + [None]))
    return draw(spec_kwargs(ca)), draw(spec_kwargs(cb))


criticality = st.tuples(*[st.sampled_from([None, True, False])] * 2)

# free text from the vocabulary of the Appendix D strings plus near-miss tokens
_VOCAB = sorted(
    {tok for a, b in NOT + EQV for tok in (a + " " + b).replace(",", " ").split()}
    | {"NACE", "API", "600", "6D", "STD", "XS", "NUT", "8IN", "CL300", "SCH80", "HP", "RPM"}
    | {"6P", "PE", "BE", "IP55", "B3", "415V", "125HP", "DN100", "1/2", "IN", "#", '"', "/"}
)
texts = st.lists(st.sampled_from(_VOCAB), min_size=1, max_size=10).map(" ".join)
