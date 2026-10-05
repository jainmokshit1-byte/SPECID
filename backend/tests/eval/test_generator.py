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


# ---- v1: purchase history and stock (DEC-33) ----
V0_SHA256 = {  # data/synthetic/seed-7/manifest.json of generator v0.1.0
    "truth_entities.csv": "73f63871253934724aaec56323a3c25d3bd890f57e8b0fa62d47a030c4e46b7e",
    "truth_pairs.csv": "69b7f86542072449eaa3a3a7c0f8d2e0e8a625e34528a9de39ba11ceb2a51d6e",
}


def test_v1_keeps_v0_codes_texts_and_truth() -> None:
    """The history pass uses its own random stream: truth files stay byte-identical to v0."""
    _, data = seed7()
    for name, sha in V0_SHA256.items():
        assert hashlib.sha256(data[name]).hexdigest() == sha, name


def test_procurement_files_match_records() -> None:
    import datetime as dt

    gen, data = seed7()
    as_of = dt.date.fromisoformat(gen.config.as_of)
    manifest = json.loads(data["manifest.json"])
    total = 0
    for c in "ABC":
        records = {r["legacy_code"]: r for r in _rows(data[f"cpse_{c}.csv"])}
        lines = _rows(data[f"procurement_{c}.csv"])
        total += len(lines)
        recent: dict[str, float] = {}
        for ln in lines:
            rec = records[ln["legacy_code"]]  # every line belongs to a record of that CPSE
            age = (as_of - dt.date.fromisoformat(ln["po_date"])).days
            assert 0 <= age < gen.config.history_months * 30
            assert float(ln["qty"]) > 0 and float(ln["unit_price"]) > 0
            assert ln["currency"] == "INR" and ln["uom"] == rec["uom"]
            assert ln["vendor"].startswith(f"SYNTH-VENDOR-{c}")
            if age < 365:
                recent[ln["legacy_code"]] = recent.get(ln["legacy_code"], 0.0) + float(
                    ln["qty"]
                ) * float(ln["unit_price"])
        assert {ln["legacy_code"] for ln in lines} == set(records)  # every record was bought
        for code, rec in records.items():
            assert abs(float(rec["annual_value"]) - round(recent.get(code, 0.0))) <= 1
            assert float(rec["stock_qty"]) >= 0
    assert manifest["counts"]["procurement_lines"] == total


def test_same_item_costs_differently_across_cpses() -> None:
    """Price spread exists for shared entities, and CPSE-B pays more than CPSE-A on average."""
    gen, data = seed7()
    truth = {
        (t["cpse"], t["legacy_code"]): t["entity_id"] for t in _rows(data["truth_entities.csv"])
    }
    price: dict[tuple[str, str], list[float]] = {}
    for c in "ABC":
        for ln in _rows(data[f"procurement_{c}.csv"]):
            ent = truth[(f"CPSE-{c}", ln["legacy_code"])]
            price.setdefault((ent, c), []).append(float(ln["unit_price"]))
    mean = {k: sum(v) / len(v) for k, v in price.items()}
    shared = {e for e, c in mean if c == "A"} & {e for e, c in mean if c == "B"}
    assert len(shared) > 100
    ratios = sorted(mean[(e, "B")] / mean[(e, "A")] for e in shared)
    assert ratios[len(ratios) // 2] > 1.05  # median: B pays more
    assert max(ratios) / min(ratios) > 1.2  # and the spread varies per item


def test_idle_stock_exists_for_transfer_suggestions() -> None:
    """Some records hold stock without any purchase in the last 12 months (stock sharing)."""
    import datetime as dt

    gen, data = seed7()
    as_of = dt.date.fromisoformat(gen.config.as_of)
    idle = 0
    for c in "ABC":
        bought = {
            ln["legacy_code"]
            for ln in _rows(data[f"procurement_{c}.csv"])
            if (as_of - dt.date.fromisoformat(ln["po_date"])).days < 365
        }
        idle += sum(
            1
            for r in _rows(data[f"cpse_{c}.csv"])
            if float(r["stock_qty"]) > 0 and r["legacy_code"] not in bought
        )
    assert idle > 100
