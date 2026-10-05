"""DEC-34: spelling repair before the rules (DEV-6), face phrases, size-dependent schedules
without a size are unknown (DEV-7). A repair may only turn an unreadable word into a readable
one; it must never create a merge between two different specifications."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.core.normalise import repair_spelling, spelling_repairs
from tests.coreenv import D, E, N, dictionary


@pytest.mark.parametrize(
    ("raw", "fixed"),
    [
        ("LFANGE SO 1/2IN CL150 RF A182 F316", "FLANGE"),  # neighbour swap
        ("PIEP ERW 3/4IN SCH40 A53 GR.B", "PIPE"),  # 4 letters: swap only
        ("GATE VALVE, 10 INCH, CLSAS 300", "CLASS"),
        ("MOTOR AC INDUCTINO 15KW 4P", "INDUCTION"),
        ("GATE VALEV 4IN CL150", "VALVE"),
        ("GATE VALVEE 4IN CL150", "VALVE"),  # one letter added
        ("GATE VALE 4IN", None),  # 4 letters, not a neighbour swap: left alone
        ("FLANGE SEAMLES", "SEAMLESS"),  # one letter removed
    ],
)
def test_misspelt_engineering_words_are_repaired(raw: str, fixed: str | None) -> None:
    text, repairs = repair_spelling(raw.upper(), dictionary())
    if fixed is None:
        assert repairs == () and text == raw.upper()
    else:
        assert any(r.endswith(f"-> {fixed}") for r in repairs), repairs
        assert fixed in text.split() or fixed in text.replace(",", " ").split()


@pytest.mark.parametrize(
    "word",
    ["STUB", "CLASP", "GLOVE", "CHOCK", "PLATE", "ROUND", "VALUE", "WELDER", "GRATE"],
)
def test_protected_real_words_are_never_repaired(word: str) -> None:
    assert repair_spelling(f"{word} 4IN CL150", dictionary()) == (f"{word} 4IN CL150", ())


def test_ambiguous_words_are_left_alone() -> None:
    """FLANGD is one edit from both FLANGE and FLANGED: no repair."""
    assert repair_spelling("FLANGD 4IN", dictionary()) == ("FLANGD 4IN", ())


@pytest.mark.parametrize("word", ["GATE", "GLOBE", "CHECK", "BALL", "FLANGE", "CLASS", "RF"])
def test_correct_words_and_short_words_never_change(word: str) -> None:
    assert repair_spelling(f"{word} X", dictionary())[1] == ()


def test_numbers_are_never_repaired() -> None:
    """Pressure classes, sizes and grades carry digits: never touched (CL150 is not CL1500)."""
    text = "VALVE CL1500 A105 M20X80 10.9 F316 CF8M"
    assert repair_spelling(text, dictionary()) == (text, ())


def test_spec_records_the_repairs_for_the_evidence_card() -> None:
    s = E("LFANGE SO 1/2IN CL150 RF A182 F316")
    assert s.category == "FLANGE" and s.attrs["flange_type"] == "SO"
    assert s.repairs == ("LFANGE -> FLANGE",)
    assert spelling_repairs("GATE VALVE 4IN CL150", dictionary()) == ()


def test_repaired_typos_turn_abstentions_into_matches() -> None:
    a = E("FLANGE SO 1/2IN CL150 RF A182 F316")
    b = E("LFANGE SO 1/2IN CL150 RF A182 F316")
    assert D(a, b).verdict == "EQUIVALENT"


def test_motor_typo_is_no_longer_a_false_veto() -> None:
    a = E("MOTOR AC IND 15KW 4P 1475RPM 415V")
    b = E("AC INDUCTINO MOTOR, 15 KW, 4 POLE, 1475 RPM, 415 V")
    assert D(a, b).verdict == "EQUIVALENT"


@pytest.mark.parametrize(
    ("text", "face"),
    [
        ("WN FLANGE 4IN CL150 RAISED FACE A105", "RF"),
        ("BLIND FLANGE 2IN CL300 FLAT FACE A105", "FF"),
        ("WN FLANGE 4IN CL600 RING TYPE JOINT A105", "RTJ"),
    ],
)
def test_face_phrases_are_read(text: str, face: str) -> None:
    assert E(text).attrs["face"] == face


def test_valve_face_phrase_gives_a_specific_end_connection() -> None:
    assert (
        E("GATE VALVE, 4 INCH, CLASS 150, ASTM A216 WCB, RAISED FACE FLANGED").attrs[
            "end_connection"
        ]
        == "FLANGED-RF"
    )


def test_face_conflict_still_vetoes() -> None:
    """Reading the phrase must keep RF vs FF a veto (FLANGE.face is core)."""
    a = E("BLIND FLANGE 2IN CL300 FLAT FACE A105")
    b = E("BLIND FLANGE 2IN CL300 RAISED FACE A105")
    assert D(a, b).verdict == "NOT_EQUIVALENT"


def test_std_without_size_is_unknown_not_a_conflict() -> None:
    no_size = E("PIPE SMLS STD A106 GR.B")
    assert no_size.attrs["schedule"] is None
    assert no_size.meta["schedule"].note == "STD without a size is not resolvable"
    r = D(no_size, E("PIPE SMLS 4IN SCH40 A106 GR.B"))
    assert r.verdict == "INSUFFICIENT_DATA"  # was NOT_EQUIVALENT (false veto, Phase 4 finding a)


def test_std_with_a_size_still_resolves_and_still_vetoes_when_different() -> None:
    assert E("PIPE SMLS 4IN STD A106 GR.B").attrs["schedule"] == "40"
    a, b = E("PIPE SMLS 4IN STD A106 GR.B"), E("PIPE SMLS 4IN SCH80 A106 GR.B")
    assert D(a, b).verdict == "NOT_EQUIVALENT"


WORDS = st.sampled_from(sorted(dictionary().spelling))


@given(WORDS, st.integers(min_value=0, max_value=20))
def test_a_neighbour_swap_never_maps_to_a_different_vocabulary_word(word: str, i: int) -> None:
    """Swapping two neighbouring letters of a vocabulary word repairs back to that word, or
    leaves the text alone; it never lands on another vocabulary word."""
    if len(word) < 4:
        return
    i %= len(word) - 1
    typo = word[:i] + word[i + 1] + word[i] + word[i + 2 :]
    text, repairs = repair_spelling(typo, dictionary())
    assert text in (word, typo)


@given(st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ./-#,", max_size=60))
def test_normalise_stays_idempotent_with_repairs(text: str) -> None:
    once = N(text)
    assert N(once) == once
