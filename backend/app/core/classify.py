"""Category classification: rules first, then an optional ML model (PRD FR-402, TRD TR-MOD-03).

The rules are the `CATS` patterns of the reference implementation (PRD Appendix C), checked in
the same order. The ML model (TRD 4.3) is trained in Phase 5; until then `model` is None and
text no rule recognises gets no category (FR-307: never guessed).
"""

import re
from typing import Final, Literal, Protocol

ClassSource = Literal["RULE", "ML", "NONE"]

CATEGORY_RULES: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("VALVE", re.compile(r"\bVALVE\b|\bGV\b|\bGLV\b|\bBV\b")),
    ("GASKET", re.compile(r"\bGASKET\b")),
    ("FLANGE", re.compile(r"\bFLANGE\b")),
    ("PIPE", re.compile(r"\bPIPE\b")),
    ("FASTENER", re.compile(r"\b(BOLT|STUD|NUT|SCREW)\b")),
    ("MOTOR", re.compile(r"\bMOTOR\b")),
)


class CategoryModel(Protocol):
    """A loaded category model: the most likely label (or `NONE`) and its probability."""

    def predict(self, norm_text: str) -> tuple[str, float]: ...


def classify(
    norm_text: str, model: CategoryModel | None, threshold: float
) -> tuple[str | None, ClassSource, float | None]:
    """(category, source, probability). The model is used only if no rule fires (TRD 4.3)."""
    for category, pattern in CATEGORY_RULES:
        if pattern.search(norm_text):
            return category, "RULE", None
    if model is None:
        return None, "NONE", None
    label, p = model.predict(norm_text)
    if label == "NONE" or p < threshold:
        return None, "NONE", p
    return label, "ML", p
