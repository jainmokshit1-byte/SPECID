"""Seeded evaluation (PRD 10.2, 10.2b, FR-1101-1106, FR-1411-1413, FR-1441-1443; SF-2, SF-5).

Everything happens in memory on a freshly generated synthetic set, so a seed always gives the
same numbers and the demo data is never touched:

    generate(seed) -> specs (rules + classifier) -> candidates (mode BOTH) -> decide every pair

Metrics are over candidate pairs; *positive* = EQUIVALENT or IDENTICAL. Baselines B1 (text only)
and B2 (text + numbers) get their thresholds tuned on the validation split to maximise F1; all
three methods are then scored once on the test split, on the same pairs. False merges on hard
negatives are reported as k of n with a 95% upper bound (rule of three when k = 0, Wilson
otherwise), never as "0%".
"""

import math
import time
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from app.core.baselines import b1, b2
from app.core.candidates import CandidateConfig, CandRecord, block_attr
from app.core.candidates import generate as candidates
from app.core.decide import decide
from app.core.extract import extract
from app.core.normalise import normalise
from app.core.radar import text_sim
from app.core.templates import Template
from app.core.types import Dictionary
from app.eval.generator import HONESTY, GeneratorConfig, generate

POSITIVE = ("EQUIVALENT", "IDENTICAL")
TAU_GRID = [round(0.50 + 0.01 * i, 2) for i in range(50)]  # 0.50 .. 0.99
Z = 1.96


def wilson_upper(k: int, n: int) -> float | None:
    if n == 0:
        return None
    if k == 0:
        return round(3 / n, 6)  # rule of three
    p = k / n
    centre = (p + Z * Z / (2 * n)) / (1 + Z * Z / n)
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / (1 + Z * Z / n)
    return round(centre + half, 6)


@dataclass
class Pair:
    a: str
    b: str
    truth: str  # SAME, HARD (near-miss neighbour), OTHER (any other different pair)
    split: str | None
    category: str | None
    verdict: str
    sim: float
    numbers_equal: bool
    justified_abstain: bool


def _scores(pairs: list[Pair], positive: Any) -> dict[str, Any]:
    tp = sum(1 for p in pairs if p.truth == "SAME" and positive(p) is True)
    fp = sum(1 for p in pairs if p.truth != "SAME" and positive(p) is True)
    fn = sum(1 for p in pairs if p.truth == "SAME" and positive(p) is False)
    abstain = sum(1 for p in pairs if p.truth == "SAME" and positive(p) is None)
    hard = [p for p in pairs if p.truth == "HARD"]
    k = sum(1 for p in hard if positive(p) is True)
    decided = sum(1 for p in pairs if positive(p) is not None)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "abstain": abstain,
        "precision": round(tp / (tp + fp), 4) if tp + fp else None,
        "recall_strict": round(tp / (tp + fn + abstain), 4) if tp + fn + abstain else None,
        "recall_decided": round(tp / (tp + fn), 4) if tp + fn else None,
        "coverage": round(decided / len(pairs), 4) if pairs else None,
        "false_merges": k,
        "hard_negatives": len(hard),
        "false_merge_upper_95": wilson_upper(k, len(hard)),
    }


def _f1(pairs: list[Pair], positive: Any) -> float:
    s = _scores(pairs, positive)
    p, r = s["precision"] or 0, s["recall_strict"] or 0
    return 2 * p * r / (p + r) if p + r else 0.0


def _specid(p: Pair) -> bool | None:
    if p.verdict in POSITIVE:
        return True
    return None if p.verdict == "INSUFFICIENT_DATA" else False


def evaluate(
    *,
    seed: int,
    n_entities: int,
    hard_negative_share: float,
    templates: Mapping[str, Template],
    dictionary: Dictionary,
    classifier: Any = None,
    threshold: float = 0.8,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    cfg = GeneratorConfig(seed=seed, n_entities=n_entities, hard_negative_share=hard_negative_share)
    gen = generate(cfg)
    truth = {f"{t['cpse']}:{t['legacy_code']}": t for t in gen.truth_entities}
    neighbour = {t["entity_id"]: t["neighbour_of"] for t in gen.truth_entities if t["neighbour_of"]}
    recs, specs, norms, raws = [], {}, {}, {}
    for cpse, rows in gen.records.items():
        for r in rows:
            key = f"CPSE-{cpse}:{r['legacy_code']}"
            text_ = r["long_text"] or r["short_text"]
            s = extract(
                text_,
                r["mpn"] or None,
                r["manufacturer"] or None,
                dictionary=dictionary,
                model=classifier,
                threshold=threshold,
            )
            specs[key], raws[key], norms[key] = s, text_, normalise(text_, dictionary)
            recs.append(
                CandRecord(
                    key,
                    f"CPSE-{cpse}",
                    s.category,
                    s.attrs.get(block_attr(s.category)),
                    norms[key],
                    r["mpn"] or None,
                    r["manufacturer"] or None,
                )
            )
    t_read = time.perf_counter()
    cand = candidates(recs, CandidateConfig(mode="BOTH"))
    t_cand = time.perf_counter()
    pairs: list[Pair] = []
    for a, b in cand:
        ta, tb = truth[a], truth[b]
        ea, eb = ta["entity_id"], tb["entity_id"]
        kind = (
            "SAME"
            if ea == eb
            else "HARD" if neighbour.get(ea) == eb or neighbour.get(eb) == ea else "OTHER"
        )
        d = decide(specs[a], specs[b], templates)
        sim = text_sim(norms[a], norms[b])
        pairs.append(
            Pair(
                a,
                b,
                kind,
                ta["split"] if ta["split"] == tb["split"] else None,
                specs[a].category,
                d.verdict,
                sim,
                b2(1.0, raws[a], raws[b], 0.0),
                bool(ta["dropped_core"] or tb["dropped_core"]),
            )
        )
    t_dec = time.perf_counter()

    val = [p for p in pairs if p.split == "validation"]
    test = [p for p in pairs if p.split == "test"]
    tau1 = max(TAU_GRID, key=lambda t: (_f1(val, lambda p: b1(p.sim, t)), -t))
    tau2 = max(TAU_GRID, key=lambda t: (_f1(val, lambda p: p.numbers_equal and p.sim >= t), -t))

    def m_b1(p: Pair) -> bool:
        return b1(p.sim, tau1)

    def m_b2(p: Pair) -> bool:
        return p.numbers_equal and p.sim >= tau2

    truth_same = Counter()
    for t in gen.truth_entities:
        truth_same[t["entity_id"]] += 1
    all_same = sum(n * (n - 1) // 2 for n in truth_same.values())
    reached_same = sum(1 for p in pairs if p.truth == "SAME")
    n = len(recs)
    hard_truth_test = sum(
        1
        for p in gen.truth_pairs
        if p["label"] == "NOT_EQUIVALENT_HARD"
        and truth[f"{p['cpse_a']}:{p['legacy_code_a']}"]["split"] == "test"
    )
    specid = _scores(test, _specid)
    abst = [p for p in test if p.truth == "SAME" and p.verdict == "INSUFFICIENT_DATA"]
    disagree = {
        "b1_merged_specid_vetoed": sum(
            1 for p in test if m_b1(p) and p.verdict == "NOT_EQUIVALENT"
        ),
        "of_which_truly_different": sum(
            1 for p in test if m_b1(p) and p.verdict == "NOT_EQUIVALENT" and p.truth != "SAME"
        ),
        "b1_wrong_merges_specid_asked": sum(
            1 for p in test if m_b1(p) and p.truth != "SAME" and p.verdict == "INSUFFICIENT_DATA"
        ),
        "specid_found_b1_missed": sum(
            1 for p in test if _specid(p) is True and not m_b1(p) and p.truth == "SAME"
        ),
        "specid_found_b2_missed": sum(
            1 for p in test if _specid(p) is True and not m_b2(p) and p.truth == "SAME"
        ),
        "specid_abstained_b1_decided": sum(1 for p in test if p.verdict == "INSUFFICIENT_DATA"),
        "b1_right_where_specid_abstained": sum(
            1 for p in test if p.verdict == "INSUFFICIENT_DATA" and m_b1(p) == (p.truth == "SAME")
        ),
    }
    per_category = {}
    for cat in sorted({p.category or "UNRECOGNISED" for p in test}):
        sub = [p for p in test if (p.category or "UNRECOGNISED") == cat]
        per_category[cat] = _scores(sub, _specid)
    return {
        "honesty": HONESTY,
        "config": {
            **asdict(cfg),
            "tau_b1": tau1,
            "tau_b2": tau2,
            "mode": "BOTH",
            "classifier": getattr(classifier, "name", None),
        },
        "dataset": {
            "records": n,
            "entities": len(truth_same),
            "candidate_pairs": len(pairs),
            "test_pairs": len(test),
            "validation_pairs": len(val),
            "classified_by_ml": sum(1 for s in specs.values() if s.class_source == "ML"),
            "unclassified": sum(1 for s in specs.values() if s.category is None),
        },
        "blocking": {
            "pair_completeness": round(reached_same / all_same, 4) if all_same else None,
            "reduction_ratio": round(1 - len(pairs) / (n * (n - 1) / 2), 6) if n > 1 else None,
            "hard_negatives_in_test": hard_truth_test,
            "hard_negatives_not_reached": hard_truth_test - specid["hard_negatives"],
        },
        "methods": {
            "specid": specid,
            "b1": {**_scores(test, m_b1), "tau": tau1},
            "b2": {**_scores(test, m_b2), "tau": tau2},
        },
        "abstentions": {
            "total": len(abst),
            "justified": sum(1 for p in abst if p.justified_abstain),
            "rate": round(len(abst) / max(1, sum(1 for p in test if p.truth == "SAME")), 4),
        },
        "disagreements": disagree,
        "per_category": per_category,
        "verdicts_test": dict(Counter(p.verdict for p in test)),
        "timings_ms": {
            "read": int((t_read - t0) * 1000),
            "candidates": int((t_cand - t_read) * 1000),
            "decide": int((t_dec - t_cand) * 1000),
            "total": int((time.perf_counter() - t0) * 1000),
        },
    }
