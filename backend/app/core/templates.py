"""Category templates and dictionaries from YAML (PRD FR-401, Appendix A; TRD TR-MOD-05).

`Template` is the single template model: the template JSONB contract (`app.schemas.jsonb`)
reuses it. Invalid files raise `TemplateError` naming the file and line, which aborts API
startup (PRD 6.5).
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.core.types import Dictionary

DICTIONARY_FILES = frozenset({"dictionary.yaml", "uom.yaml"})


class Template(BaseModel):
    """A category template YAML document (PRD Appendix A, TRD TR-MOD-05)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    version: int = Field(ge=1)
    category: str
    critical_default: bool
    core: list[str]
    extended: list[str] = []
    tolerant: list[str] = []
    make: list[str] = []
    value_domains: dict[str, list[str | int]] = {}
    aliases: dict[str, dict[str, str]] = {}
    rule_text: dict[str, str] = {}
    rules: list[str] = []
    implied: list[dict[str, Any]] = []
    substitutes: list[dict[str, Any]] = []  # P1
    class_path: list[str] | None = None
    unspsc: str | None = None

    @model_validator(mode="after")
    def _keys_are_attributes(self) -> "Template":
        attrs = set(self.core) | set(self.extended) | set(self.tolerant) | set(self.make)
        for name, keys in (
            ("rule_text", self.rule_text),
            ("value_domains", self.value_domains),
            ("aliases", self.aliases),
        ):
            unknown = set(keys) - attrs
            if unknown:
                raise ValueError(f"{name} keys are not attributes of the template: {unknown}")
        return self


class TemplateError(ValueError):
    """An invalid template or dictionary file: `<file>:<line>: <problem>`."""

    def __init__(self, source: str, line: int, problem: str) -> None:
        super().__init__(f"{source}:{line}: {problem}")
        self.source, self.line, self.problem = source, line, problem


def _key_line(node: yaml.Node, key: str) -> int | None:
    if isinstance(node, yaml.MappingNode):
        for k, _ in node.value:
            if k.value == key:
                return int(k.start_mark.line) + 1
    return None


def _line_of(root: yaml.Node, loc: tuple[int | str, ...], message: str) -> int:
    """The line of the YAML node a validation error points at (deepest node found)."""
    node, line = root, int(root.start_mark.line) + 1
    if not loc and isinstance(root, yaml.MappingNode):  # model-level error: the key it names
        named = [k for k, _ in root.value if str(k.value) in message]
        return int(named[0].start_mark.line) + 1 if named else line
    for part in loc:
        if isinstance(node, yaml.MappingNode):
            pair = next(((k, v) for k, v in node.value if k.value == str(part)), None)
            if pair is None:
                break
            line, node = int(pair[0].start_mark.line) + 1, pair[1]
        elif isinstance(node, yaml.SequenceNode) and isinstance(part, int):
            if part >= len(node.value):
                break
            node = node.value[part]
            line = int(node.start_mark.line) + 1
        else:
            break
    return line


def _load_yaml(text: str, source: str) -> tuple[Any, yaml.Node | None]:
    try:
        return yaml.safe_load(text), yaml.compose(text, Loader=yaml.SafeLoader)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        raise TemplateError(source, int(mark.line) + 1 if mark else 1, str(exc)) from exc


def parse_template(text: str, source: str = "<template>") -> Template:
    """Validate one template YAML document (also used for DRAFT versions edited as text)."""
    data, root = _load_yaml(text, source)
    if not isinstance(data, dict) or root is None:
        raise TemplateError(source, 1, "a template must be a YAML mapping")
    try:
        return Template.model_validate(data)
    except ValidationError as exc:
        err = exc.errors()[0]
        loc = tuple(err["loc"])
        where = ".".join(str(p) for p in loc) or "template"
        raise TemplateError(
            source, _line_of(root, loc, err["msg"]), f"{where}: {err['msg']}"
        ) from exc


def load_templates(directory: str | Path) -> dict[str, Template]:
    """Every template YAML in `directory`, keyed by category."""
    files = sorted(p for p in Path(directory).glob("*.yaml") if p.name not in DICTIONARY_FILES)
    if not files:
        raise TemplateError(str(directory), 0, "no template YAML files")
    out: dict[str, Template] = {}
    for path in files:
        text = path.read_text("utf-8")
        template = parse_template(text, str(path))
        if template.category in out:
            root = yaml.compose(text, Loader=yaml.SafeLoader)
            line = _key_line(root, "category") or 1
            raise TemplateError(str(path), line, f"duplicate category {template.category}")
        out[template.category] = template
    return out


def _str_map(value: Any, source: str, line: int, name: str) -> Mapping[str, str]:
    if not isinstance(value, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    ):
        raise TemplateError(source, line, f"{name} must map text to text")
    return dict(value)


def _words(value: Any, source: str, line: int, name: str) -> frozenset[str]:
    if not isinstance(value, list) or not all(
        isinstance(w, str) and w.isalpha() and w.isupper() for w in value
    ):
        raise TemplateError(source, line, f"{name} must be a list of upper-case words")
    return frozenset(value)


def _spelling(doc: dict[str, Any], root: yaml.Node, source: str) -> tuple[frozenset[str], ...]:
    """SPELLING (DEC-34): optional; vocabulary and protected words must not overlap."""
    spelling = doc.get("SPELLING")
    line = _key_line(root, "SPELLING") or 1
    if spelling is None:
        return frozenset(), frozenset()
    if not isinstance(spelling, dict) or set(spelling) - {"vocabulary", "protected"}:
        raise TemplateError(source, line, "SPELLING has only vocabulary and protected")
    vocab = _words(spelling.get("vocabulary", []), source, line, "SPELLING.vocabulary")
    protected = _words(spelling.get("protected", []), source, line, "SPELLING.protected")
    if vocab & protected:
        raise TemplateError(
            source, line, f"SPELLING word(s) in both lists: {sorted(vocab & protected)}"
        )
    return vocab, protected


def load_dictionary(directory: str | Path) -> Dictionary:
    """Expansions and spelling list (dictionary.yaml ABBREVIATION, SPELLING) and UoM aliases
    (uom.yaml), PRD 9.2 / TRD I / DEC-34."""
    paths = {name: Path(directory) / name for name in ("dictionary.yaml", "uom.yaml")}
    docs: dict[str, tuple[Any, yaml.Node]] = {}
    for name, path in paths.items():
        data, root = _load_yaml(path.read_text("utf-8"), str(path))
        if not isinstance(data, dict) or root is None:
            raise TemplateError(str(path), 1, "a dictionary file must be a YAML mapping")
        docs[name] = (data, root)
    (doc, droot), (uom, uroot) = docs["dictionary.yaml"], docs["uom.yaml"]
    d_src, u_src = str(paths["dictionary.yaml"]), str(paths["uom.yaml"])
    version = doc.get("version")
    if not isinstance(version, int) or version < 1:
        raise TemplateError(d_src, _key_line(droot, "version") or 1, "version must be >= 1")
    ambiguous = uom.get("ambiguous", [])
    if not isinstance(ambiguous, list) or not all(isinstance(a, str) for a in ambiguous):
        raise TemplateError(u_src, _key_line(uroot, "ambiguous") or 1, "ambiguous must be text")
    spelling, protected = _spelling(doc, droot, d_src)
    return Dictionary(
        version=version,
        spelling=spelling,
        spelling_protected=protected,
        abbreviations=_str_map(
            doc.get("ABBREVIATION"), d_src, _key_line(droot, "ABBREVIATION") or 1, "ABBREVIATION"
        ),
        uom_aliases=_str_map(
            uom.get("aliases"), u_src, _key_line(uroot, "aliases") or 1, "aliases"
        ),
        uom_ambiguous=frozenset(ambiguous),
    )
