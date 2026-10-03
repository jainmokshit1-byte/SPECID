"""Command line for the pure engine (Implementation Plan Phase 4). SYNTHETIC DATA only.

  python -m app.cli generate --seed 7 --out data/synthetic/seed-7
  python -m app.cli decide --file data/synthetic/seed-7
  python -m app.cli decide --a "VALVE GATE 4IN CL150 A216 WCB FLGD RF" --b "GV 100NB 150# WCB RF"
  python -m app.cli extract --text "PIPE SMLS 6IN SCH40 A106 GR.B"

Templates and dictionaries come from TEMPLATE_DIR (default: ./templates, ../templates or
/app/templates). Every number printed is computed from the files; nothing is hard-coded.
"""

import argparse
import csv
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from app.core.decide import decide
from app.core.extract import extract
from app.core.normalise import normalise
from app.core.radar import lookalike_class, text_sim
from app.core.shortdesc import long_desc, short_desc
from app.core.templates import load_dictionary, load_templates
from app.core.types import Decision, Dictionary, Spec
from app.eval.generator import HONESTY, GeneratorConfig, generate, write

VERDICTS = ("IDENTICAL", "EQUIVALENT", "INSUFFICIENT_DATA", "NOT_EQUIVALENT")
ROUTES = ("AUTO_ELIGIBLE", "REVIEW", "NONE")
BANNER = "SYNTHETIC DATA · " + HONESTY


def _template_dir() -> Path:
    if os.environ.get("TEMPLATE_DIR"):
        return Path(os.environ["TEMPLATE_DIR"])
    for p in (Path("templates"), Path("../templates"), Path("/app/templates")):
        if (p / "valve.yaml").exists():
            return p
    raise SystemExit("templates not found: set TEMPLATE_DIR")


def _engine() -> tuple[dict[str, Any], Dictionary]:
    d = _template_dir()
    return load_templates(d), load_dictionary(d)


def _spec(
    text: str, dictionary: Dictionary, mpn: str | None = None, maker: str | None = None
) -> Spec:
    return extract(
        text, mpn or None, maker or None, dictionary=dictionary, model=None, threshold=0.8
    )


def _table(rows: list[list[str]]) -> str:
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    lines = [
        "  ".join(
            c.ljust(w) if i == 0 else c.rjust(w)
            for i, (c, w) in enumerate(zip(r, widths, strict=True))
        )
        for r in rows
    ]
    lines.insert(1, "  ".join("-" * w for w in widths))
    return "\n".join(lines)


def cmd_generate(args: argparse.Namespace) -> None:
    cfg = GeneratorConfig(seed=args.seed, n_entities=args.n_entities)
    t0 = time.perf_counter()
    manifest = write(generate(cfg), args.out)
    elapsed = time.perf_counter() - t0
    c = manifest["counts"]
    size = (
        sum(f["bytes"] for f in manifest["files"].values())
        + (Path(args.out) / "manifest.json").stat().st_size
    )
    print(BANNER)
    print(f"seed {cfg.seed}, n_entities {cfg.n_entities} -> {args.out}")
    print(f"records {c['records']} {c['records_per_cpse']}")
    print(
        f"entities {c['entities']}; truth pairs: EQUIVALENT {c['pairs_equivalent']}, "
        f"NOT_EQUIVALENT_HARD {c['pairs_not_equivalent_hard']}"
    )
    print(
        f"files {len(manifest['files']) + 1}, {size:,} bytes on disk; generated in {elapsed:.2f} s"
    )
    for name, f in manifest["files"].items():
        print(f"  {name:20s} {f['bytes']:>9,} B  sha256 {f['sha256']}")


def _records(folder: Path) -> dict[str, dict[str, str]]:
    out = {}
    for path in sorted(folder.glob("cpse_*.csv")):
        cpse = "CPSE-" + path.stem.split("_")[1]
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                out[f"{cpse}:{row['legacy_code']}"] = row
    return out


def _criticality(row: dict[str, str]) -> bool | None:
    value = row.get("criticality", "").strip().upper()
    return {"Y": True, "YES": True, "TRUE": True, "N": False, "NO": False, "FALSE": False}.get(
        value
    )


def cmd_decide_file(args: argparse.Namespace) -> None:
    folder = Path(args.file)
    templates, dictionary = _engine()
    t0 = time.perf_counter()
    records = _records(folder)
    specs = {
        k: _spec(r["long_text"] or r["short_text"], dictionary, r["mpn"], r["manufacturer"])
        for k, r in records.items()
    }
    with (folder / "truth_pairs.csv").open(encoding="utf-8", newline="") as f:
        pairs = list(csv.DictReader(f))
    table: Counter[tuple[str, str]] = Counter()
    routes: Counter[tuple[str, str]] = Counter()
    looks: Counter[str] = Counter()
    rows_total = rows_without_rule = 0
    for p in pairs:
        ka, kb = f"{p['cpse_a']}:{p['legacy_code_a']}", f"{p['cpse_b']}:{p['legacy_code_b']}"
        ra, rb = records[ka], records[kb]
        d: Decision = decide(specs[ka], specs[kb], templates, (_criticality(ra), _criticality(rb)))
        table[(p["label"], d.verdict)] += 1
        routes[(d.verdict, d.route)] += 1
        rows_total += len(d.evidence)
        rows_without_rule += sum(1 for e in d.evidence if not (e.rule and e.rule_text))
        ta, tb = (normalise(r["long_text"] or r["short_text"], dictionary) for r in (ra, rb))
        cls = lookalike_class(text_sim(ta, tb), d.verdict)
        if cls:
            looks[cls] += 1
    elapsed = time.perf_counter() - t0

    labels = sorted({p["label"] for p in pairs})
    print(BANNER)
    print(
        f"{folder}: {len(records)} records, {len(pairs)} truth pairs decided in {elapsed:.2f} s\n"
    )
    print("Verdict mix by truth label (rows: truth; columns: SpecID verdict)")
    head = ["truth \\ verdict", *VERDICTS, "total"]
    body = [
        [
            lab,
            *(str(table[(lab, v)]) for v in VERDICTS),
            str(sum(table[(lab, v)] for v in VERDICTS)),
        ]
        for lab in labels
    ]
    total = [
        "all",
        *(str(sum(table[(lab, v)] for lab in labels)) for v in VERDICTS),
        str(len(pairs)),
    ]
    print(_table([head, *body, total]))
    print("\nRoutes by verdict")
    print(
        _table(
            [
                ["verdict \\ route", *ROUTES],
                *[[v, *(str(routes[(v, r)]) for r in ROUTES)] for v in VERDICTS],
            ]
        )
    )
    print(
        f"\nEvidence rows: {rows_total}; rows without a rule ID or rule text: {rows_without_rule}"
    )
    print(
        f"Look-alike Guard (hi 0.85, lo 0.75): LOOKALIKE_VETOED {looks['LOOKALIKE_VETOED']}, "
        f"HIDDEN_TWIN {looks['HIDDEN_TWIN']}"
    )
    print("Truth pairs only (no candidate generation until Phase 5); not an evaluation result.")


def _card(d: Decision) -> str:
    rows = [["attribute", "level", "a", "b", "status", "rule", "note a", "note b"]]
    for e in d.evidence:
        rows.append(
            [e.attr, e.level, str(e.a), str(e.b), e.status, e.rule, e.note_a or "", e.note_b or ""]
        )
    conf = "none" if d.confidence is None else f"{d.confidence:.2f}"
    out = [
        f"verdict {d.verdict} · route {d.route} · confidence (heuristic) {conf}"
        f" · template v{d.template_version}",
        "reasons: " + ("; ".join(d.reasons) or "none"),
    ]
    if d.evidence:
        out += ["", _table(rows), "", "rule texts:"]
        out += [f"  {e.rule}: {e.rule_text}" for e in d.evidence]
    return "\n".join(out)


def cmd_decide_pair(args: argparse.Namespace) -> None:
    templates, dictionary = _engine()
    a = _spec(args.a, dictionary, args.mpn_a, args.maker_a)
    b = _spec(args.b, dictionary, args.mpn_b, args.maker_b)
    d = decide(a, b, templates)
    sim = text_sim(normalise(args.a, dictionary), normalise(args.b, dictionary))
    print(BANNER)
    print(f"A: {args.a}\n   -> {normalise(args.a, dictionary)}")
    print(f"B: {args.b}\n   -> {normalise(args.b, dictionary)}")
    print(f"category A {a.category} ({a.class_source}), B {b.category} ({b.class_source})\n")
    print(_card(d))
    print(f"\ntext_sim {sim:.2f} · look-alike class {lookalike_class(sim, d.verdict) or 'none'}")


def cmd_extract(args: argparse.Namespace) -> None:
    _, dictionary = _engine()
    s = _spec(args.text, dictionary)
    print(f"normalised: {normalise(args.text, dictionary)}")
    print(f"category:   {s.category} ({s.class_source})")
    for k, v in s.attrs.items():
        if v is not None or k in s.meta:
            note = s.meta[k].note if k in s.meta and s.meta[k].note else ""
            print(f"  {k:16s} {v!s:12s} {note}")
    print(f"residual:   {' '.join(s.residual) or '-'}")
    if s.category:
        print(f"short:      {short_desc(s)}\nlong:       {long_desc(s)}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="command", required=True)
    g = sub.add_parser("generate", help="write a seeded synthetic dataset (PRD 10.1)")
    g.add_argument("--seed", type=int, default=7)
    g.add_argument("--n-entities", type=int, default=GeneratorConfig.n_entities)
    g.add_argument("--out", required=True)
    g.set_defaults(func=cmd_generate)
    d = sub.add_parser("decide", help="decide the truth pairs of a dataset, or one pair")
    d.add_argument("--file", help="dataset folder (cpse_*.csv + truth_pairs.csv)")
    d.add_argument("--a")
    d.add_argument("--b")
    for side in ("a", "b"):
        d.add_argument(f"--mpn-{side}")
        d.add_argument(f"--maker-{side}")
    d.set_defaults(func=lambda a: cmd_decide_file(a) if a.file else cmd_decide_pair(a))
    e = sub.add_parser("extract", help="show the extracted spec of one text")
    e.add_argument("--text", required=True)
    e.set_defaults(func=cmd_extract)
    args = p.parse_args(argv)
    if args.command == "decide" and not args.file and not (args.a and args.b):
        p.error("decide needs --file DIR, or --a TEXT and --b TEXT")
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
