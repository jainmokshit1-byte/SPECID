"""DEC-41: classifier, verified AI reader (grounding check) and dense neighbours.
A fake provider stands in for Gemini, so no key and no network are needed."""

import csv
import io
from functools import lru_cache
from typing import Any

import pytest

from app.ai import reader
from app.ai.classifier import CATEGORY_WORDS, default_classifier
from app.ai.dense import neighbours
from app.ai.provider import AIError, Gemini, make_provider
from app.core.normalise import normalise
from app.eval.generator import GeneratorConfig, files, generate
from tests.coreenv import D, E, dictionary, templates


@lru_cache
def clf() -> Any:
    return default_classifier(dictionary())


def test_classifier_reads_items_without_a_category_word() -> None:
    """On the held-out test split, with the category word removed, the model names the
    category (or abstains); it is never used when a rule fires."""
    data = files(generate(GeneratorConfig(seed=7)))
    truth = list(csv.DictReader(io.StringIO(data["truth_entities.csv"].decode())))
    texts = {}
    for c in "ABC":
        for r in csv.DictReader(io.StringIO(data[f"cpse_{c}.csv"].decode())):
            texts[(f"CPSE-{c}", r["legacy_code"])] = r["long_text"] or r["short_text"]
    right = abstained = wrong = 0
    for t in truth:
        if t["split"] != "test":
            continue
        bare = CATEGORY_WORDS.sub(
            " ", normalise(texts[(t["cpse"], t["legacy_code"])], dictionary())
        )
        label, p = clf().predict(bare)
        if label == "NONE" or p < 0.8:
            abstained += 1
        elif label == t["category"]:
            right += 1
        else:
            wrong += 1
    answered = right + wrong
    assert answered > 300 and right / answered >= 0.97, (right, wrong, abstained)


@pytest.mark.parametrize("text", ["SAFETY GLOVES LEATHER SIZE M", "PRINTER PAPER A4 80 GSM"])
def test_classifier_does_not_force_other_items_into_a_category(text: str) -> None:
    label, p = clf().predict(normalise(text, dictionary()))
    assert label == "NONE" or p < 0.8


def test_classifier_recovers_a_valve_written_without_the_word() -> None:
    from app.core.extract import extract

    s = extract("25NB 300# WCB BW", dictionary=dictionary(), model=clf(), threshold=0.8)
    assert s.category == "VALVE" and s.class_source == "ML"
    assert s.attrs["size_dn"] == 25 and s.attrs["pressure_class"] == 300
    rule = extract("GATE VALVE 4IN CL150", dictionary=dictionary(), model=clf(), threshold=0.8)
    assert rule.class_source == "RULE"  # rules first, always


# ---- verified reader
class FakeAI:
    name = "fake"
    model = "fake"
    embed_model = "fake"

    def __init__(self, answer: Any) -> None:
        self.answer, self.prompts = answer, []

    def generate_json(self, prompt: str) -> Any:
        self.prompts.append(prompt)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer

    def embed(self, texts: Any) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


def spec_without(text: str, attr: str) -> Any:
    from dataclasses import replace

    s = E(text)
    return replace(s, attrs={**s.attrs, attr: None})


def test_reader_accepts_a_grounded_allowed_value_and_tags_it() -> None:
    text = "GATE VALVE 4IN CL150 WCB FLGD RF"
    s = spec_without(text, "pressure_class")
    ai = FakeAI({"items": [{"id": 0, "attributes": [
        {"name": "pressure_class", "value": 150, "span": "CL150"}]}]})  # fmt: skip
    [res] = reader.read_missing(ai, [(text, s)], templates(), dictionary())
    assert res.accepted == 1 and res.rejected == 0
    assert res.spec.attrs["pressure_class"] == 150
    assert res.spec.meta["pressure_class"].tier == "LLM"
    assert "CL150" in (res.spec.meta["pressure_class"].note or "")
    assert "pressure_class" in ai.prompts[0]


@pytest.mark.parametrize(
    ("value", "span", "why"),
    [
        (300, "CL300", "span not in the text (invented)"),
        (175, "CL150", "value outside the allowed list"),
        (300, "CL150", "the rules read the span as 150, not 300"),
        ("abc", "4IN", "wrong type"),
    ],
)
def test_reader_rejects_values_that_fail_the_grounding_check(
    value: Any, span: str, why: str
) -> None:
    text = "GATE VALVE 4IN CL150 WCB FLGD RF"
    s = spec_without(text, "pressure_class")
    ai = FakeAI({"items": [{"id": 0, "attributes": [
        {"name": "pressure_class", "value": value, "span": span}]}]})  # fmt: skip
    [res] = reader.read_missing(ai, [(text, s)], templates(), dictionary())
    assert res.accepted == 0 and res.rejected == 1, why
    assert res.spec.attrs["pressure_class"] is None


def test_reader_never_overwrites_a_value_the_rules_read() -> None:
    text = "GATE VALVE 4IN CL150 WCB FLGD RF"
    s = spec_without(text, "pressure_class")
    ai = FakeAI({"items": [{"id": 0, "attributes": [
        {"name": "size_dn", "value": 150, "span": "4IN"}]}]})  # fmt: skip
    [res] = reader.read_missing(ai, [(text, s)], templates(), dictionary())
    assert res.spec.attrs["size_dn"] == 100 and res.accepted == 0


def test_reader_failure_leaves_specs_unchanged() -> None:
    text = "GATE VALVE 4IN CL150 WCB FLGD RF"
    s = spec_without(text, "pressure_class")
    [res] = reader.read_missing(FakeAI(AIError("down")), [(text, s)], templates(), dictionary())
    assert res.spec == s and res.accepted == res.rejected == 0


def test_an_ai_read_value_can_never_merge_different_items() -> None:
    """Safety: with a grounded value the pair is decided by the same rules; CL150 vs CL300
    stays a veto whatever the AI said about another attribute."""
    text = "GATE VALVE 4IN CL150 WCB FLGD RF"
    s = spec_without(text, "pressure_class")
    ai = FakeAI({"items": [{"id": 0, "attributes": [
        {"name": "pressure_class", "value": 150, "span": "CL150"}]}]})  # fmt: skip
    [res] = reader.read_missing(ai, [(text, s)], templates(), dictionary())
    other = E("GATE VALVE 4IN CL300 WCB FLGD RF")
    assert D(res.spec, other).verdict == "NOT_EQUIVALENT"


# ---- dense neighbours and provider config
def test_dense_neighbours_stay_inside_the_category() -> None:
    ids = ["a", "b", "c", "d"]
    cats = ["VALVE", "VALVE", "PIPE", "VALVE"]
    vecs = [[1, 0], [0.9, 0.1], [1, 0], [0, 1]]
    got = neighbours(ids, cats, vecs, k=1)
    assert got["a"] == ["b"] and got["b"] == ["a"] and "c" not in got
    assert got["d"] in (["a"], ["b"])


def test_provider_is_off_without_a_key() -> None:
    class S:
        ai_provider = "gemini"
        gemini_api_key = ""
        gemini_model = "m"
        gemini_embed_model = "e"

    assert make_provider(S()) is None
    with pytest.raises(AIError):
        Gemini("PASTE_YOUR_KEY_HERE", "m", "e")
