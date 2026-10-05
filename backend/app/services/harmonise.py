"""Harmonisation run (TRD TR-MOD-23, sequence 2.3a; PRD FR-505-507, FR-601-611, FR-701-703).

One run reads the records of its batches and takes them through:

    read -> candidates -> decide -> cluster -> done

- read: extract a spec for every record and refresh `spec_record`;
- candidates: `core.candidates.generate` (blocking, BM25, part number; dense when available);
- decide: `core.decide.decide` for every candidate pair, plus text similarity, Look-alike class
  and the two text baselines, stored as `pair_decision` (MISSING_BOTH rows are not stored);
- cluster: `core.cluster` joins EQUIVALENT / IDENTICAL pairs but never across a conflict.

Progress is written to `run.stats` in short separate transactions, so the API (another process)
sees it; the results are written in one transaction per stage and removed again if the run is
cancelled or fails. `execute` is called by the job worker (`services/jobs.py`) and by tests.
"""

import time
import uuid
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.ai import dense as dense_ai
from app.ai import reader as ai_reader
from app.ai.provider import AIError, make_provider
from app.core.baselines import b1, b2
from app.core.candidates import (
    CandidateConfig,
    CandRecord,
    block_attr,
    channel_counts,
    generate,
)
from app.core.cluster import cluster_priority, cluster_with_blocked, cohesion
from app.core.decide import decide
from app.core.normalise import normalise
from app.core.radar import lookalike_class, text_sim
from app.core.templates import Template
from app.core.types import Decision, Dictionary, Spec
from app.db.copy import copy_rows
from app.db.models import AppUser, Run, UploadBatch
from app.schemas.jsonb import Evidence, RunConfig, RunStats
from app.security import egress
from app.services import audit
from app.services.errors import Conflict, Invalid, NotFound
from app.services.specs import RecordText, build_spec, record_text, spec_row, store_specs
from app.settings import Settings

log = structlog.get_logger()

PAIR_BATCH = 1000  # cancellation is checked, and progress written, every 1,000 pairs
ACTIVE = ("QUEUED", "RUNNING", "CANCELLING")
LOOKALIKE_HI, LOOKALIKE_LO = 0.85, 0.75  # S13 defaults (PRD 9.13.1)
BASELINE_TAU = 0.85  # B1 / B2 threshold until the evaluation tunes it on validation (DEC-37)


class RunCancelled(Exception):
    pass


# ---------------------------------------------------------------- creating a run
def default_config(
    settings: Settings,
    templates: Mapping[str, Template],
    dictionary: Dictionary,
    mode: str,
    options: Mapping[str, Any] | None = None,
) -> RunConfig:
    """The stored run configuration: defaults, then the caller's options (validated)."""
    o = dict(options or {})
    unknown = set(o) - {"bm25_k", "block_cap", "dense_enabled", "dense_k", "lookalike_min_sim",
                        "hidden_twin_max_sim", "tau_b1", "tau_b2", "seed"}  # fmt: skip
    if unknown:
        raise Invalid(f"Unknown run option(s): {', '.join(sorted(unknown))}.", title="Bad options")
    cfg = {
        "mode": mode,
        "seed": 0,
        "bm25_k": CandidateConfig.bm25_k,
        "dense_enabled": settings.ai_provider != "off",  # meaning search needs embeddings
        "dense_k": CandidateConfig.dense_k,
        "block_cap": CandidateConfig.block_cap,
        "classifier_threshold": settings.classifier_threshold,
        "lookalike_min_sim": LOOKALIKE_HI,
        "hidden_twin_max_sim": LOOKALIKE_LO,
        "tau_b1": BASELINE_TAU,
        "tau_b2": BASELINE_TAU,
        "templates": {t.id: t.version for t in templates.values()},
        "dictionary_version": dictionary.version,
        "uom_table_version": dictionary.uom_version,
        "embedding_model": settings.gemini_embed_model if settings.ai_provider != "off" else "none",
        "classifier_model": "rules + char-ngram-lr-v1" if settings.classifier_enabled else "rules",
        "git_commit": settings.git_commit,
        **o,
    }
    return RunConfig.model_validate(cfg)


def create_run(
    session: Session,
    actor: AppUser,
    *,
    batch_ids: Sequence[uuid.UUID],
    mode: str,
    options: Mapping[str, Any] | None,
    settings: Settings,
    templates: Mapping[str, Template],
    dictionary: Dictionary,
) -> Run:
    ids = list(dict.fromkeys(batch_ids))
    if not ids:
        raise Invalid("Choose at least one ingested batch.", title="No batches")
    batches = list(session.scalars(select(UploadBatch).where(UploadBatch.id.in_(ids))))
    if len(batches) != len(ids):
        raise NotFound("One of the batches does not exist.")
    pending = [b.filename for b in batches if b.status != "INGESTED"]
    if pending:
        raise Conflict(f"Ingest these files first: {', '.join(pending)}.")
    if mode == "CROSS_CPSE" and len({b.cpse_id for b in batches}) < 2:
        raise Invalid("A cross-CPSE run needs batches from at least two CPSEs.", title="One CPSE")
    cfg = default_config(settings, templates, dictionary, mode, options)
    run = Run(
        batch_ids=ids,
        mode=mode,
        config=cfg.model_dump(mode="json"),
        status="QUEUED",
        stats=RunStats(progress={"stage": "queued", "done": 0, "total": 0}).model_dump(
            mode="json", exclude_none=True
        ),
        started_by=actor.id,
    )
    session.add(run)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="RUN_STARTED",
        object_type="run",
        object_id=str(run.id),
        after={"mode": mode, "batches": [str(i) for i in ids], "options": dict(options or {})},
    )
    return run


def request_cancel(session: Session, actor: AppUser, run: Run) -> Run:
    if run.status not in ACTIVE:
        raise Conflict(f"This run is already {run.status.lower()}.")
    run.status = "CANCELLED" if run.status == "QUEUED" else "CANCELLING"
    if run.status == "CANCELLED":
        run.finished_at = datetime.now(UTC)
    audit.record(
        session,
        actor_id=actor.id,
        action="RUN_CANCEL_REQUESTED",
        object_type="run",
        object_id=str(run.id),
        after={"status": run.status},
    )
    return run


# ---------------------------------------------------------------- helpers for the worker
@dataclass
class Rec:
    id: uuid.UUID
    cpse: str
    legacy_code: str
    short_text: str
    text: str
    norm: str
    mpn: str | None
    maker: str | None
    criticality: bool | None
    annual_value: float | None
    spec: Spec


class _Control:
    """Progress and cancellation through short, separate transactions."""

    def __init__(self, factory: sessionmaker[Session], run_id: uuid.UUID) -> None:
        self.factory, self.run_id = factory, run_id
        self.stats: dict[str, Any] = {}
        self.timings: dict[str, int] = {}

    def update(self, stage: str, done: int, total: int, **extra: Any) -> None:
        self.stats.update(extra)
        self.stats["progress"] = {"stage": stage, "done": done, "total": total}
        self.stats["timings_ms"] = dict(self.timings)
        payload = RunStats.model_validate(self.stats).model_dump(mode="json", exclude_none=True)
        with self.factory() as s:
            s.execute(
                text("UPDATE run SET stats = CAST(:s AS jsonb) WHERE id = :i"),
                {"s": _json(payload), "i": self.run_id},
            )
            s.commit()

    def check_cancel(self) -> None:
        with self.factory() as s:
            status = s.scalar(select(Run.status).where(Run.id == self.run_id))
        if status in ("CANCELLING", "CANCELLED"):
            raise RunCancelled


def _json(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, default=str)


def _load_records(
    session: Session,
    batch_ids: Sequence[uuid.UUID],
    dictionary: Dictionary,
    threshold: float,
    model: Any = None,
) -> list[Rec]:
    rows = session.execute(
        text("""
            SELECT m.id, c.code, m.legacy_code, m.short_text, m.long_text, m.mpn, m.manufacturer,
                   m.criticality, m.annual_value
            FROM material_record m
            JOIN upload_batch b ON b.id = m.batch_id
            JOIN cpse c ON c.id = m.cpse_id
            WHERE m.batch_id = ANY(:ids)
            ORDER BY b.created_at DESC, m.legacy_code
            """),
        {"ids": list(batch_ids)},
    ).all()
    seen: set[tuple[str, str]] = set()
    out: list[Rec] = []
    for rid, cpse, code, short, long, mpn, maker, crit, value in rows:
        if (cpse, code) in seen:  # a newer batch of the same CPSE replaces the older record
            continue
        seen.add((cpse, code))
        rt = RecordText(rid, record_text(short, long), mpn, maker)
        spec = build_spec(rt, dictionary, threshold, model)
        out.append(
            Rec(
                rid, cpse, code, short, rt.text, normalise(rt.text, dictionary), mpn, maker,
                {"Y": True, "N": False}.get(crit or ""),
                float(value) if value is not None else None, spec,
            )
        )  # fmt: skip
    return out


def _evidence(decision: Decision) -> list[dict[str, Any]]:
    """Stored evidence rows: MISSING_BOTH rows are omitted (TRD TR-DAT-05)."""
    rows = [
        {
            "attr": e.attr, "level": e.level, "a": e.a, "b": e.b, "status": e.status,
            "rule": e.rule, "rule_text": e.rule_text, "note_a": e.note_a, "note_b": e.note_b,
        }
        for e in decision.evidence
        if e.status != "MISSING_BOTH"
    ]  # fmt: skip
    return Evidence.model_validate(rows).model_dump(mode="json")


def _dec(value: float | None, places: int = 4) -> Decimal | None:
    return None if value is None else Decimal(str(round(value, places)))


def _clear_results(session: Session, run_id: uuid.UUID) -> None:
    for table in ("blocked_edge", "cluster", "pair_decision"):  # cluster cascades its members
        session.execute(text(f"DELETE FROM {table} WHERE run_id = :r"), {"r": run_id})  # noqa: S608


# ---------------------------------------------------------------- the run
def execute(
    factory: sessionmaker[Session],
    run_id: uuid.UUID,
    *,
    templates: Mapping[str, Template],
    dictionary: Dictionary,
    settings: Settings,
    dense: Callable[[Sequence[Rec]], Mapping[str, Sequence[str]]] | None = None,
    classifier: Any = None,
    provider: Any = None,
) -> None:
    """Run one harmonisation to DONE, or CANCELLED / FAILED (never raises for those)."""
    provider = provider if provider is not None else make_provider(settings)
    ctl = _Control(factory, run_id)
    with factory() as s:
        run = s.get(Run, run_id)
        if run is None or run.status not in ("QUEUED", "RUNNING"):
            return  # cancelled while queued, or gone
        run.status = "RUNNING"
        started_by, batch_ids = run.started_by, list(run.batch_ids)
        cfg = RunConfig.model_validate(run.config)
        s.commit()
    t_run = time.perf_counter()
    try:
        with factory() as work:
            _pipeline(work, ctl, cfg, batch_ids, templates, dictionary, settings, dense,
                      classifier, provider)  # fmt: skip
            work.commit()
        _finish(factory, run_id, started_by, "DONE", None, ctl, t_run)
    except RunCancelled:
        with factory() as s:
            _clear_results(s, run_id)
            s.commit()
        _finish(factory, run_id, started_by, "CANCELLED", None, ctl, t_run)
    except Exception as exc:  # the run fails; the API and the logs say why
        log.error("run_failed", run_id=str(run_id), error=repr(exc))
        with factory() as s:
            _clear_results(s, run_id)
            s.commit()
        _finish(factory, run_id, started_by, "FAILED", f"{type(exc).__name__}: {exc}", ctl, t_run)


def _finish(
    factory: sessionmaker[Session], run_id: uuid.UUID, actor: uuid.UUID | None, status: str,
    error: str | None, ctl: _Control, t_run: float,
) -> None:  # fmt: skip
    ctl.timings["total"] = int((time.perf_counter() - t_run) * 1000)
    ctl.stats["blocked_egress"] = egress.blocked_attempts()
    stage = ctl.stats.get("progress", {}).get("stage", "queued") if status != "DONE" else "done"
    done = ctl.stats.get("progress", {}).get("done", 0)
    total = ctl.stats.get("progress", {}).get("total", 0)
    if status == "DONE":
        done = total = max(total, 1)
    ctl.stats["progress"] = {"stage": stage, "done": done, "total": total}
    ctl.stats["timings_ms"] = dict(ctl.timings)
    payload = RunStats.model_validate(ctl.stats).model_dump(mode="json", exclude_none=True)
    with factory() as s:
        s.execute(
            text(
                "UPDATE run SET status = :st, error = :e, stats = CAST(:s AS jsonb),"
                " finished_at = now() WHERE id = :i"
            ),
            {"st": status, "e": error, "s": _json(payload), "i": run_id},
        )
        audit.record(
            s,
            actor_id=actor,
            action=f"RUN_{status}",
            object_type="run",
            object_id=str(run_id),
            after={"status": status, "error": error, "verdicts": ctl.stats.get("verdicts")},
        )
        s.commit()


def _pipeline(
    work: Session, ctl: _Control, cfg: RunConfig, batch_ids: Sequence[uuid.UUID],
    templates: Mapping[str, Template], dictionary: Dictionary, settings: Settings,
    dense_fn: Callable[[Sequence[Rec]], Mapping[str, Sequence[str]]] | None,
    classifier: Any = None,
    provider: Any = None,
) -> None:  # fmt: skip
    _clear_results(work, ctl.run_id)

    # 1 read ------------------------------------------------------------------------------
    t0 = time.perf_counter()
    ctl.update("read", 0, 0)
    recs = _load_records(work, batch_ids, dictionary, cfg.classifier_threshold, classifier)
    ctl.update("read", 0, len(recs), records=len(recs),
               ai_provider=provider.name if provider is not None else "off")  # fmt: skip
    if provider is not None:
        _ai_read(recs, provider, templates, dictionary, settings, ctl)
    done = 0
    for i in range(0, len(recs), 1000):
        chunk = recs[i : i + 1000]
        store_specs(
            work.connection(),
            [
                spec_row(RecordText(r.id, r.text, r.mpn, r.maker), r.spec, templates, dictionary)
                for r in chunk
            ],
        )
        done += len(chunk)
        ctl.update("read", done, len(recs))
        ctl.check_cancel()
    unclassified = sum(1 for r in recs if r.spec.category is None)
    ctl.timings["read"] = int((time.perf_counter() - t0) * 1000)
    ctl.update(
        "candidates", 0, 0, specs_parsed=len(recs) - unclassified, unclassified=unclassified,
        classified_by_ml=sum(1 for r in recs if r.spec.class_source == "ML"),
    )  # fmt: skip
    work.commit()

    # 2 candidates ------------------------------------------------------------------------
    t0 = time.perf_counter()
    cand_records = [
        CandRecord(
            str(r.id), r.cpse, r.spec.category,
            r.spec.attrs.get(block_attr(r.spec.category)), r.norm, r.mpn, r.maker,
        )
        for r in recs
    ]  # fmt: skip
    dense = None
    if cfg.dense_enabled:
        if dense_fn is not None:
            dense = dense_fn(recs)
        elif provider is not None:
            dense = _dense(recs, provider, cfg.dense_k, ctl)
    pairs = generate(
        cand_records,
        CandidateConfig(
            mode=cfg.mode, bm25_k=cfg.bm25_k, dense_k=cfg.dense_k, block_cap=cfg.block_cap
        ),
        dense,
    )
    ctl.timings["candidates"] = int((time.perf_counter() - t0) * 1000)
    ctl.update("decide", 0, len(pairs), candidate_pairs=len(pairs), channels=channel_counts(pairs))
    ctl.check_cancel()

    # 3 decide ----------------------------------------------------------------------------
    t0 = time.perf_counter()
    by_id = {str(r.id): r for r in recs}
    ordered = sorted(pairs.items())
    verdicts: Counter[str] = Counter()
    stored: list[tuple[uuid.UUID, uuid.UUID, str, float, int, int]] = []  # for clustering
    rows: list[tuple[Any, ...]] = []
    decisions: dict[tuple[str, str], Decision] = {}
    for n, ((ia, ib), mask) in enumerate(ordered, 1):
        a, b = by_id[ia], by_id[ib]
        d = decide(a.spec, b.spec, templates, (a.criticality, b.criticality))
        route = d.route
        if route == "AUTO_ELIGIBLE" and not settings.auto_eligible_enabled:
            route = "REVIEW"  # DEC-09: auto-eligibility stays OFF
        sim = text_sim(a.norm, b.norm)
        look = lookalike_class(sim, d.verdict, cfg.lookalike_min_sim, cfg.hidden_twin_max_sim)
        base = {
            "b1": b1(sim, cfg.tau_b1 or BASELINE_TAU),
            "b2": b2(sim, a.text, b.text, cfg.tau_b2 or BASELINE_TAU),
            "tau1": cfg.tau_b1 or BASELINE_TAU,
            "tau2": cfg.tau_b2 or BASELINE_TAU,
        }
        decisions[(ia, ib)] = d
        verdicts[d.verdict] += 1
        rows.append(
            (
                uuid.uuid4(), ctl.run_id, a.id, b.id, d.verdict, route, _dec(d.confidence, 2),
                _dec(sim), base, look, mask, list(d.reasons), _evidence(d), None,
                d.template_version,
            )
        )  # fmt: skip
        if d.verdict in ("IDENTICAL", "EQUIVALENT"):
            flags = sum(1 for r in d.reasons)
            stored.append((a.id, b.id, d.verdict, d.confidence or 0.5, flags, mask))
        if n % PAIR_BATCH == 0 or n == len(ordered):
            ctl.update("decide", n, len(ordered))
            ctl.check_cancel()
    copy_rows(
        work.connection(), "pair_decision",
        ["id", "run_id", "rec_a", "rec_b", "verdict", "route", "p_equiv", "text_sim", "baseline",
         "lookalike", "channels", "reasons", "evidence", "model_version", "template_version"],
        rows,
    )  # fmt: skip
    ctl.timings["decide"] = int((time.perf_counter() - t0) * 1000)
    ctl.update("cluster", 0, 0, verdicts=dict(verdicts))
    work.commit()

    # 4 cluster ---------------------------------------------------------------------------
    t0 = time.perf_counter()
    _cluster(work, ctl, recs, stored, decisions, templates)
    ctl.timings["cluster"] = int((time.perf_counter() - t0) * 1000)


def _ai_read(
    recs: list[Rec], provider: Any, templates: Mapping[str, Template], dictionary: Dictionary,
    settings: Settings, ctl: _Control,
) -> None:  # fmt: skip
    """Verified AI reader on records with a category and a key attribute still unknown."""
    todo = [i for i, r in enumerate(recs) if ai_reader.missing_core(r.spec, templates)]
    todo = todo[: settings.ai_reader_max_records]
    if not todo:
        return
    results = ai_reader.read_missing(
        provider, [(recs[i].text, recs[i].spec) for i in todo], templates, dictionary
    )
    accepted = rejected = 0
    for i, res in zip(todo, results, strict=True):
        recs[i].spec = res.spec
        accepted += res.accepted
        rejected += res.rejected
    ctl.update("read", len(recs), len(recs), ai_records_asked=len(todo),
               ai_values_accepted=accepted, ai_values_rejected=rejected)  # fmt: skip


def _dense(recs: list[Rec], provider: Any, k: int, ctl: _Control) -> dict[str, list[str]] | None:
    """Meaning-search neighbours from the provider's embeddings; None when it fails."""
    try:
        vectors = provider.embed([r.norm for r in recs])
    except AIError as exc:
        log.warning("dense_channel_failed", error=str(exc))
        return None
    found = dense_ai.neighbours(
        [str(r.id) for r in recs], [r.spec.category for r in recs], vectors, k
    )
    ctl.stats["dense_pairs"] = sum(len(v) for v in found.values())
    return found


def _cluster(
    work: Session, ctl: _Control, recs: Sequence[Rec],
    edges_in: Sequence[tuple[uuid.UUID, uuid.UUID, str, float, int, int]],
    decisions: Mapping[tuple[str, str], Decision], templates: Mapping[str, Template],
) -> None:  # fmt: skip
    conn = work.connection()
    index = {r.id: i for i, r in enumerate(recs)}
    nodes = sorted({x for e in edges_in for x in (e[0], e[1])}, key=lambda u: index[u])
    local = {u: i for i, u in enumerate(nodes)}
    edges = [(local[a], local[b], score) for a, b, _, score, _, _ in edges_in]
    by_uuid = {r.id: r for r in recs}
    memo: dict[tuple[int, int], bool] = {}

    def conflict(i: int, j: int) -> bool:
        key = (i, j) if i < j else (j, i)
        if key not in memo:
            a, b = by_uuid[nodes[key[0]]], by_uuid[nodes[key[1]]]
            known = decisions.get((str(min(a.id, b.id)), str(max(a.id, b.id))))
            d = known or decide(a.spec, b.spec, templates, (a.criticality, b.criticality))
            memo[key] = d.verdict == "NOT_EQUIVALENT"
        return memo[key]

    groups, blocked = cluster_with_blocked(len(nodes), edges, conflict)
    edge_info: dict[tuple[int, int], tuple[float, int]] = {}
    for a, b, _, score, flags, _ in edges_in:
        edge_info[(min(local[a], local[b]), max(local[a], local[b]))] = (score, flags)
    group_of = {i: g for g, members in enumerate(groups) for i in members}

    cluster_rows: list[tuple[Any, ...]] = []
    member_rows: list[tuple[Any, ...]] = []
    for members in groups:
        if len(members) < 2:
            continue
        mset = set(members)
        inner = [info for (i, j), info in edge_info.items() if i in mset and j in mset]
        recs_in = [by_uuid[nodes[i]] for i in members]
        category = recs_in[0].spec.category
        t = templates.get(category or "")
        critical = any(
            (r.criticality if r.criticality is not None else bool(t and t.critical_default))
            for r in recs_in
        )
        flags = sum(f for _, f in inner)
        cid = uuid.uuid4()
        cluster_rows.append(
            (cid, ctl.run_id, category, "PROPOSED", _dec(cohesion([s for s, _ in inner]), 3), True,
             critical, flags, _dec(cluster_priority([r.annual_value for r in recs_in], flags), 2))
        )  # fmt: skip
        member_rows.extend((cid, r.id) for r in recs_in)
    copy_rows(
        conn, "cluster",
        ["id", "run_id", "category", "status", "cohesion", "needs_review", "is_critical",
         "flags_count", "priority"],
        cluster_rows,
    )  # fmt: skip
    copy_rows(conn, "cluster_member", ["cluster_id", "record_id"], member_rows)
    # one review task per cluster, OPEN for a maker (sequence 2.3a step 6)
    copy_rows(conn, "review_task", ["cluster_id", "state"], [(r[0], "OPEN") for r in cluster_rows])

    blocked_rows = []
    for b in blocked:
        ra, rb = by_uuid[nodes[b.i]], by_uuid[nodes[b.j]]
        pair = (ra.id, rb.id)
        if b.reason == "conflict":  # name one conflicting pair across the two final clusters
            side_i = [m for m in groups[group_of[b.i]]]
            side_j = [m for m in groups[group_of[b.j]]]
            found = next(((x, y) for x in side_i for y in side_j if conflict(x, y)), None)
            if found:
                pair = (by_uuid[nodes[found[0]]].id, by_uuid[nodes[found[1]]].id)
        lo, hi = sorted((ra.id, rb.id))
        blocked_rows.append((ctl.run_id, lo, hi, pair[0], pair[1], b.reason))
    copy_rows(
        conn, "blocked_edge",
        ["run_id", "rec_a", "rec_b", "blocking_a", "blocking_b", "reason"], blocked_rows,
    )  # fmt: skip
    ctl.stats["clusters"] = len(cluster_rows)
    ctl.stats["blocked_edges"] = len(blocked_rows)
    ctl.update("cluster", 1, 1)
