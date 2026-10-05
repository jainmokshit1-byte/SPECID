"""Category classifier (PRD FR-402, TRD 4.3): character n-grams + logistic regression.

Used only when no category rule fires (`core.classify`), and it abstains below the threshold,
so a description like `25NB 300# WCB BW` (no category word) can still be read as a valve.

Trained at start-up on the synthetic train split, with each text also shown without its
category word, so the model learns the attributes (sizes, classes, materials, threads) rather
than the word itself. A small set of other items teaches it to answer NONE. Runs inside the app:
no download, no key, works offline.
"""

import random
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.core.normalise import normalise
from app.core.types import Dictionary
from app.eval.generator import GeneratorConfig, generate

MODEL_NAME = "char-ngram-lr-v1"
CATEGORY_WORDS = re.compile(
    r"\b(VALVE|VALVES|GV|GLV|BV|CV|FLANGE|FLANGES|PIPE|PIPES|BOLT|BOLTS|STUD|STUDS|NUT|NUTS|"
    r"SCREW|MOTOR|MOTORS|GASKET)\b"
)
OTHER_ITEMS = [
    "SAFETY GLOVES LEATHER SIZE L", "PRINTER PAPER A4 75 GSM", "CABLE 3C 4 SQMM ARMOURED",
    "LUBRICATING OIL ISO VG 68 20 L", "WELDING ELECTRODE E7018 3.15 MM", "PAINT EPOXY GREY 4 L",
    "LED LAMP 20 W 230 V", "HELMET SAFETY YELLOW", "BEARING 6205 2RS", "V BELT B 52",
    "FILTER CARTRIDGE 10 MICRON", "PRESSURE GAUGE 0-10 BAR 100 MM DIAL", "O RING NITRILE 50X3",
    "HOSE RUBBER 1 IN 10 M", "TRANSFORMER OIL 210 L DRUM", "CONTACTOR 32 A 3 POLE",
    "GRATING 25X5 MS GALVANISED", "PLATE MS 10 MM IS 2062", "ANGLE 50X50X6 MS", "BEAM ISMB 200",
]  # fmt: skip


class CategoryClassifier:
    """Implements `core.classify.CategoryModel`."""

    name = MODEL_NAME

    def __init__(self, pipeline: Pipeline) -> None:
        self.pipeline = pipeline

    def predict(self, norm_text: str) -> tuple[str, float]:
        probs = self.pipeline.predict_proba([norm_text])[0]
        i = int(probs.argmax())
        return str(self.pipeline.classes_[i]), float(probs[i])


def training_data(dictionary: Dictionary, seed: int = 7) -> tuple[list[str], list[str]]:
    gen = generate(GeneratorConfig(seed=seed))
    split = {(t["cpse"], t["legacy_code"]): t for t in gen.truth_entities}
    texts, labels = [], []
    for cpse, rows in gen.records.items():
        for r in rows:
            t = split[(f"CPSE-{cpse}", r["legacy_code"])]
            if t["split"] != "train":
                continue
            norm = normalise(r["long_text"] or r["short_text"], dictionary)
            texts.append(norm)
            labels.append(t["category"])
            bare = CATEGORY_WORDS.sub(" ", norm).strip()
            if bare and bare != norm:
                texts.append(bare)
                labels.append(t["category"])
    rng = random.Random(seed)
    for item in OTHER_ITEMS:
        for _ in range(6):  # a few noisy copies so NONE has weight
            words = item.split()
            rng.shuffle(words)
            texts.append(normalise(" ".join(words), dictionary))
            labels.append("NONE")
    return texts, labels


def train(dictionary: Dictionary, seed: int = 7) -> CategoryClassifier:
    texts, labels = training_data(dictionary, seed)
    pipe = Pipeline(
        [
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2)),
            ("lr", LogisticRegression(max_iter=1000, C=4.0)),
        ]
    )
    pipe.fit(texts, labels)
    return CategoryClassifier(pipe)


_cache: dict[int, CategoryClassifier] = {}


def default_classifier(dictionary: Dictionary) -> CategoryClassifier:
    """Trained once per process and dictionary version (a few seconds at start-up)."""
    if dictionary.version not in _cache:
        _cache[dictionary.version] = train(dictionary)
    return _cache[dictionary.version]
