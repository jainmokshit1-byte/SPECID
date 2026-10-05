"""FR-401 (TRD TR-MOD-05): templates and dictionaries load from YAML; errors name file and line."""

import shutil
from pathlib import Path

import pytest

from app.core.templates import (
    TemplateError,
    load_dictionary,
    load_templates,
    parse_template,
)
from tests.coreenv import TEMPLATE_DIR, template_yaml


def test_loads_the_six_appendix_a_templates_by_category() -> None:
    t = load_templates(TEMPLATE_DIR)
    assert sorted(t) == ["FASTENER", "FLANGE", "GASKET", "MOTOR", "PIPE", "VALVE"]
    for category, template in t.items():
        doc = template_yaml()[category]
        assert template.core == doc["core"] and template.extended == doc.get("extended", [])
        assert template.critical_default is doc["critical_default"]
        assert template.rule_text == doc.get("rule_text", {})
        assert template.version == 1
    assert t["FASTENER"].critical_default is False


def test_loads_the_versioned_dictionary() -> None:
    d = load_dictionary(TEMPLATE_DIR)
    assert d.version == 2  # v2: face phrases and SPELLING (DEC-34)
    assert dict(d.abbreviations) == {
        "SMLS": "SEAMLESS",
        "FLGD": "FLANGED",
        "WND": "WOUND",
        "GRAF": "GRAPHITE",
        "HD": "HEAD",
        "FLG": "FLANGE",
        "RAISED FACE": "RF",
        "FLAT FACE": "FF",
        "RING TYPE JOINT": "RTJ",
        "RING JOINT": "RTJ",
    }
    assert {"FLANGE", "CLASS", "INDUCTION"} <= d.spelling
    assert "STUB" in d.spelling_protected and not d.spelling & d.spelling_protected
    assert d.uom_aliases["PCS"] == "EA" and "MT" in d.uom_ambiguous


@pytest.fixture
def copy_dir(tmp_path: Path) -> Path:
    for f in TEMPLATE_DIR.glob("*.yaml"):
        shutil.copy(f, tmp_path / f.name)
    return tmp_path


def _line(text: str, needle: str) -> int:
    return next(i for i, line in enumerate(text.splitlines(), 1) if needle in line)


def _edit(path: Path, old: str, new: str) -> str:
    text = path.read_text("utf-8")
    assert old in text
    text = text.replace(old, new, 1)
    path.write_text(text, "utf-8")
    return text


def test_yaml_syntax_error_names_file_and_line(copy_dir: Path) -> None:
    text = _edit(copy_dir / "valve.yaml", "core: [valve_type,", "core: [valve_type,: ][")
    with pytest.raises(TemplateError) as exc:
        load_templates(copy_dir)
    assert exc.value.source.endswith("valve.yaml")
    assert exc.value.line == _line(text, "core: [valve_type,")


def test_wrong_type_points_at_its_line(copy_dir: Path) -> None:
    text = _edit(copy_dir / "flange.yaml", "critical_default: true", "critical_default: maybe")
    with pytest.raises(TemplateError, match=r"flange\.yaml:\d+: critical_default") as exc:
        load_templates(copy_dir)
    assert exc.value.line == _line(text, "critical_default: maybe")


def test_rule_text_key_must_be_an_attribute(copy_dir: Path) -> None:
    text = _edit(copy_dir / "motor.yaml", '  rpm: "Equal within 5%"', '  colour: "Equal within 5%"')
    with pytest.raises(TemplateError, match="rule_text keys are not attributes") as exc:
        load_templates(copy_dir)
    assert exc.value.line == _line(text, "rule_text:")


def test_unknown_field_is_rejected(copy_dir: Path) -> None:
    _edit(copy_dir / "pipe.yaml", "category: PIPE", "category: PIPE\nweight_kg: 3")
    with pytest.raises(TemplateError, match=r"pipe\.yaml:\d+: weight_kg"):
        load_templates(copy_dir)


def test_duplicate_category_is_rejected(copy_dir: Path) -> None:
    shutil.copy(copy_dir / "valve.yaml", copy_dir / "valve2.yaml")
    with pytest.raises(TemplateError, match="duplicate category VALVE"):
        load_templates(copy_dir)


def test_empty_directory_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(TemplateError, match="no template YAML"):
        load_templates(tmp_path)


def test_dictionary_errors_name_the_file(copy_dir: Path) -> None:
    _edit(copy_dir / "dictionary.yaml", "version: 2", "version: 0")
    with pytest.raises(TemplateError, match=r"dictionary\.yaml:\d+: version"):
        load_dictionary(copy_dir)


def test_spelling_lists_are_validated(copy_dir: Path) -> None:
    _edit(copy_dir / "dictionary.yaml", "protected: [STUB,", "protected: [FLANGE, STUB,")
    with pytest.raises(TemplateError, match=r"dictionary\.yaml:\d+: SPELLING word\(s\) in both"):
        load_dictionary(copy_dir)


def test_a_draft_can_be_validated_from_text() -> None:
    text = (TEMPLATE_DIR / "valve.yaml").read_text("utf-8").replace("version: 1", "version: 2")
    draft = parse_template(text, "draft")
    assert draft.version == 2 and draft.category == "VALVE"
    with pytest.raises(TemplateError, match="must be a YAML mapping"):
        parse_template("- just\n- a list\n", "draft")
