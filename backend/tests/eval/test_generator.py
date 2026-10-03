"""FR-1101 (PRD 10.1; TRD TR-TST-07): seeded synthetic generator v0."""

import csv
import hashlib
import io
import json
from functools import lru_cache
from itertools import combinations

from app.core.normalise import MAX_PASSES, normalise_passes
from app.eval.generator import CORE, Generated, GeneratorConfig, files, generate
from tests.coreenv import D, E, dictionary


@lru_cache
def seed7() -> tuple[Generated, dict[str, bytes]]:
    gen = generate(GeneratorConfig())  # seed 7, n_entities 1200 (DEC-09)
    return gen, files(gen)


def _rows(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8"))))


def test_defaults_follow_prd_10_1_and_dec_09() -> None:
    cfg = GeneratorConfig()
    assert (cfg.seed, cfg.n_entities, cfg.hard_negative_share) == (7, 1200, 0.30)
    assert dict(cfg.category_mix) == {
        "VALVE": 0.25,
        "PIPE": 0.25,
        "FLANGE": 0.20,
        "FASTENER": 0.20,
        "MOTOR": 0.10,
    }
    assert (cfg.within_dup_rate, cfg.drop_ext_rate, cfg.drop_core_rate) == (0.10, 0.30, 0.05)
    assert (cfg.typo_rate, cfg.make_rate, cfg.presence) == (0.02, 0.40, (0.4, 0.4, 0.2))


def test_about_3000_records() -> None:
    gen, _ = seed7()
    n = sum(len(r) for r in gen.records.values())
    assert 2_700 <= n <= 3_300, n  # DEC-09: about 3,000 records


def test_same_seed_gives_identical_files() -> None:
    _, first = seed7()
    again = files(generate(GeneratorConfig()))
    assert first == again
    manifest = json.loads(first["manifest.json"])
    for name, meta in manifest["files"].items():
        assert hashlib.sha256(first[name]).hexdigest() == meta["sha256"]
        assert len(first[name]) == meta["bytes"]
    assert files(generate(GeneratorConfig(seed=8)))["truth_pairs.csv"] != first["truth_pairs.csv"]


def test_manifest_and_files_are_flagged_synthetic() -> None:
    _, data = seed7()
    manifest = json.loads(data["manifest.json"])
    assert manifest["synthetic"] is True and "optimistic by construction" in manifest["honesty"]
    assert manifest["config"]["seed"] == 7 and "timestamp" not in data["manifest.json"].decode()
    for name in ("cpse_A.csv", "cpse_B.csv", "cpse_C.csv"):
        for row in _rows(data[name]):
            assert row["manufacturer"] in ("",) or row["manufacturer"].startswith("SYNTH-MAKER-")
            assert row["mpn"] == "" or row["mpn"].startswith("SX-")
            assert len(row["short_text"]) <= 40


def test_truth_files_are_consistent() -> None:
    _, data = seed7()
    truth = _rows(data["truth_entities.csv"])
    records = {f"CPSE-{c}:{r['legacy_code']}" for c in "ABC" for r in _rows(data[f"cpse_{c}.csv"])}
    assert {f"{t['cpse']}:{t['legacy_code']}" for t in truth} == records
    entity = {f"{t['cpse']}:{t['legacy_code']}": t for t in truth}
    by_entity: dict[str, dict[str, str]] = {t["entity_id"]: t for t in truth}

    def core_key(t: dict[str, str]) -> str:
        attrs = json.loads(t["attrs"])
        return json.dumps([t["category"], *(attrs[a] for a in CORE[t["category"]])])

    core_keys = {core_key(t) for t in by_entity.values()}
    assert len(core_keys) == len(by_entity)  # entities are unique on their core attributes
    splits = {t["split"] for t in truth}
    assert splits == {"train", "validation", "test"}
    labels = set()
    for p in _rows(data["truth_pairs.csv"]):
        a = entity[f"{p['cpse_a']}:{p['legacy_code_a']}"]
        b = entity[f"{p['cpse_b']}:{p['legacy_code_b']}"]
        labels.add(p["label"])
        if p["label"] == "EQUIVALENT":
            assert a["entity_id"] == b["entity_id"]
        else:  # a hard negative differs in exactly one core attribute
            assert p["label"] == "NOT_EQUIVALENT_HARD" and a["category"] == b["category"]
            assert a["split"] == b["split"]
            xa, xb = json.loads(a["attrs"]), json.loads(b["attrs"])
            assert sum(xa[k] != xb[k] for k in CORE[a["category"]]) == 1
    assert labels == {"EQUIVALENT", "NOT_EQUIVALENT_HARD"}


def test_every_pair_of_an_entity_is_listed() -> None:
    _, data = seed7()
    truth = _rows(data["truth_entities.csv"])
    members: dict[str, list[str]] = {}
    for t in truth:
        members.setdefault(t["entity_id"], []).append(f"{t['cpse']}:{t['legacy_code']}")
    expected = sum(len(list(combinations(m, 2))) for m in members.values())
    pairs = [p for p in _rows(data["truth_pairs.csv"]) if p["label"] == "EQUIVALENT"]
    assert len(pairs) == expected


def test_normalise_cap_never_reached_on_seed_7_output() -> None:
    """DEC-24: the pass cap is never reached on the generator's texts."""
    _, data = seed7()
    texts = [
        r[col]
        for c in "ABC"
        for r in _rows(data[f"cpse_{c}.csv"])
        for col in ("short_text", "long_text")
    ]
    passes = [normalise_passes(t, dictionary())[1] for t in texts if t]
    assert len(passes) > 3_000 and max(passes) < MAX_PASSES


def test_truth_attributes_are_canonical() -> None:
    """A schedule is stored the way the rules compare it (PRD B.2: STD = SCH40 up to DN250),
    so a hard negative can never be a renamed copy of its base entity."""
    from app.core.units import schedule_for

    _, data = seed7()
    for t in _rows(data["truth_entities.csv"]):
        if t["category"] == "PIPE":
            a = json.loads(t["attrs"])
            assert schedule_for(a["schedule"], a["size_dn"])[0] == a["schedule"], t


def test_hard_negatives_with_clean_text_are_never_merged() -> None:
    """With canonical truth and the veto, a hard-negative pair whose texts carry the differing
    attribute (nothing dropped) is never EQUIVALENT or IDENTICAL (FR-602 on generator data)."""
    _, data = seed7()
    truth = {f"{t['cpse']}:{t['legacy_code']}": t for t in _rows(data["truth_entities.csv"])}
    text = {
        f"CPSE-{c}:{r['legacy_code']}": r["long_text"] or r["short_text"]
        for c in "ABC"
        for r in _rows(data[f"cpse_{c}.csv"])
    }
    checked = 0
    for p in _rows(data["truth_pairs.csv"]):
        if p["label"] != "NOT_EQUIVALENT_HARD":
            continue
        ka, kb = f"{p['cpse_a']}:{p['legacy_code_a']}", f"{p['cpse_b']}:{p['legacy_code_b']}"
        if truth[ka]["dropped_core"] or truth[kb]["dropped_core"]:
            continue
        checked += 1
        assert D(E(text[ka]), E(text[kb])).verdict not in ("EQUIVALENT", "IDENTICAL"), (ka, kb)
    assert checked > 500  # sanity: the check really ran on hundreds of pairs
