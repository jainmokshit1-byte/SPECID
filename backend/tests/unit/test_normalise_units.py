"""FR-201, FR-202, FR-205 (TRD TR-MOD-01, TR-MOD-02): normaliser rules and unit tables."""

import pytest
import yaml

from app.core.normalise import normalise
from app.core.types import Dictionary
from app.core.units import (
    DN_NPS,
    NPS_DN,
    hp_to_kw,
    nb_to_dn,
    nps_to_dn,
    pressure_class,
    schedule_for,
    uom_canonical,
)
from tests.coreenv import TEMPLATE_DIR

_DOC = yaml.safe_load((TEMPLATE_DIR / "dictionary.yaml").read_text("utf-8"))
_UOM = yaml.safe_load((TEMPLATE_DIR / "uom.yaml").read_text("utf-8"))
DICT = Dictionary(
    version=_DOC["version"],
    abbreviations=_DOC["ABBREVIATION"],
    uom_aliases=_UOM["aliases"],
    uom_ambiguous=frozenset(_UOM["ambiguous"]),
)


# PRD 9.2: one row per rule, the examples of the table
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("gate valve", "GATE VALVE"),  # 1
        ('4"', "4 IN"),  # 2
        ("VALVE (GATE), 4; CL150", "VALVE GATE 4 CL150"),  # 2: strip , ; ( )
        ("SS316/GRAF", "SS316 GRAPHITE"),  # 3 (+ 9)
        ("1/2 IN", "1/2 IN"),  # 3: fractions keep their slash
        ("4INCH", "4 IN"),  # 4
        ("4 INCHES", "4 IN"),
        ("4IN", "4 IN"),
        ("DN100", "100 NB"),  # 5
        ("100NB", "100 NB"),
        ("150#", "CL150"),  # 6
        ("CLASS 150", "CL150"),
        ("CL 150", "CL150"),
        ("SCH 40", "SCH40"),  # 7
        ("SCHEDULE 40", "SCH40"),
        ("SCH.40", "SCH40"),
        ("SCH STD", "SCHSTD"),
        ("SCH XS", "SCHXS"),
        ("GR.B", "GRB"),  # 8
        ("GRADE B", "GRB"),
        ("GR B", "GRB"),
        ("GR8.8", "GR8.8"),
        ("FLGD RF", "FLANGED RF"),  # 9
        ("SMLS", "SEAMLESS"),
        ("SPIRAL WND", "SPIRAL WOUND"),
        ("HEX HD", "HEX HEAD"),
        ("FLG", "FLANGE"),
        ("  GATE \t VALVE \n ", "GATE VALVE"),  # 10
    ],
)
def test_normaliser_rules_of_prd_9_2(raw: str, expected: str) -> None:
    assert normalise(raw, DICT) == expected


def test_expansions_come_from_the_dictionary() -> None:
    assert normalise("FLGD", Dictionary(version=2)) == "FLGD"
    assert normalise("BRS", Dictionary(version=2, abbreviations={"BRS": "BRASS"})) == "BRASS"
    assert normalise("FLGDX", DICT) == "FLGDX"  # whole words only


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("４ＩＮ", "4 IN"),  # full-width 4IN (NFKC)
        ("GATE​VALVE", "GATEVALVE"),  # zero-width space is non-printing
        ("GATE\x00VALVE", "GATEVALVE"),
        ("GATE VALVE", "GATE VALVE"),  # no-break space is whitespace
        ("ＣＬＡＳＳ 150", "CL150"),  # full-width CLASS (NFKC)
    ],
)
def test_nfkc_and_non_printing_characters(raw: str, expected: str) -> None:
    assert normalise(raw, DICT) == expected


def test_normaliser_is_idempotent_on_examples() -> None:
    for raw in ('4" GV 150# SS316/GRAF', "PIPE SCH 40 A106 GRADE B SMLS"):
        once = normalise(raw, DICT)
        assert normalise(once, DICT) == once


# PRD Appendix B.1
def test_nps_to_dn_table_b1() -> None:
    expected = [15, 20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200, 250, 300, 350, 400, 450, 500]
    nps = "1/2 3/4 1 1-1/4 1-1/2 2 2-1/2 3 4 5 6 8 10 12 14 16 18 20".split()
    assert [nps_to_dn(n) for n in nps] == expected
    assert nps_to_dn("24") == 600 and len(NPS_DN) == 19
    assert DN_NPS[100] == "4"


@pytest.mark.parametrize("nps", ["7", "9", "1/4", "30", ""])
def test_non_standard_sizes_stay_unknown(nps: str) -> None:
    assert nps_to_dn(nps) is None


def test_nb_must_be_a_table_dn() -> None:
    assert nb_to_dn(100) == 100 and nb_to_dn(175) is None


def test_pressure_classes_b2() -> None:
    assert [pressure_class(c) for c in (150, 300, 600, 900, 1500, 2500)] == [
        150,
        300,
        600,
        900,
        1500,
        2500,
    ]
    assert pressure_class(400) is None


# PRD Appendix B.2 (SME to verify)
@pytest.mark.parametrize(
    ("raw", "dn", "value", "note"),
    [
        ("STD", 150, "40", "STD = SCH40 (DN150 <= 250)"),
        ("STD", 250, "40", "STD = SCH40 (DN250 <= 250)"),
        ("STD", 300, "STD", None),  # NPS 12: not SCH40
        ("STD", None, "STD", None),
        ("XS", 200, "80", "XS = SCH80 (DN200 <= 200)"),
        ("XS", 250, "XS", None),
        ("XXS", 100, "XXS", None),
        ("40", 100, "40", None),
    ],
)
def test_std_and_xs_limits(raw: str, dn: int | None, value: str, note: str | None) -> None:
    assert schedule_for(raw, dn) == (value, note)


def test_hp_to_kw() -> None:
    assert hp_to_kw(125) == 93.2  # 125 x 0.7457 = 93.21
    assert hp_to_kw(1) == 0.7


# TRD Appendix I (templates/uom.yaml)
def test_uom_aliases_of_appendix_i() -> None:
    groups = {
        "EA": ["EA", "NO", "NOS", "NO.", "PC", "PCS", "EACH", "NUMBER", "UNIT"],
        "M": ["M", "MTR", "MTRS", "METRE", "METER", "METRES", "METERS"],
        "KG": ["KG", "KGS", "KILOGRAM"],
        "L": ["L", "LTR", "LITRE", "LITER"],
        "SET": ["SET", "SETS"],
        "PR": ["PR", "PAIR"],
    }
    for canonical, aliases in groups.items():
        for alias in aliases:
            assert uom_canonical(alias, DICT) == (canonical, False), alias
    assert uom_canonical(" pcs ", DICT) == ("EA", False)


def test_ambiguous_and_unknown_uom() -> None:
    assert uom_canonical("MT", DICT) == (None, True)  # metre or metric tonne: never mapped
    assert uom_canonical("BAG", DICT) == (None, False)
