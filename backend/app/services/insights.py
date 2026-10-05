"""Dashboard, Look-alike Guard and money views (PRD FR-1201, FR-1203, FR-1401-1403, SF-10;
TRD TR-MOD-28; docs/SOLUTION.md Pillars 3, 6, 10).

Every figure is computed from stored data of one run and carries the run id, the synthetic
flag and the time it was computed (never a typed-in number). Money figures are **gaps**, not
promised savings: what the same item costs across CPSEs, and the stock one CPSE holds while
another one buys.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.errors import NotFound

IDLE_DAYS = 365


def resolve_run(session: Session, run_id: uuid.UUID | None) -> uuid.UUID | None:
    if run_id is not None:
        found = session.scalar(text("SELECT id FROM run WHERE id = :r"), {"r": run_id})
        if found is None:
            raise NotFound("No such run.")
        return run_id
    rid: uuid.UUID | None = session.scalar(
        text("SELECT id FROM run WHERE status = 'DONE' ORDER BY started_at DESC LIMIT 1")
    )
    return rid


def _synthetic(session: Session, run_id: uuid.UUID) -> bool:
    return bool(
        session.scalar(
            text(
                "SELECT bool_or(b.is_synthetic) FROM run r JOIN upload_batch b"
                " ON b.id = ANY(r.batch_ids) WHERE r.id = :r"
            ),
            {"r": run_id},
        )
    )


# ---------------------------------------------------------------- dashboard
def dashboard(session: Session, run_id: uuid.UUID | None) -> dict[str, Any]:
    rid = resolve_run(session, run_id)
    if rid is None:
        return {"run_id": None, "empty": True}
    p = {"r": rid}
    run = session.execute(
        text("SELECT batch_ids, stats, mode, started_at FROM run WHERE id = :r"), p
    ).one()
    per_cpse = session.execute(
        text("""
            WITH recs AS (
              SELECT m.id, m.cpse_id, m.annual_value FROM material_record m
              WHERE m.batch_id = ANY(:b)
            )
            SELECT c.code,
                   count(r.id) AS records,
                   coalesce(sum(r.annual_value), 0) AS spend,
                   (SELECT (b.quality->>'health_score')::int FROM upload_batch b
                     WHERE b.cpse_id = c.id AND b.id = ANY(:b) AND b.quality IS NOT NULL
                     ORDER BY b.created_at DESC LIMIT 1) AS health
            FROM cpse c JOIN recs r ON r.cpse_id = c.id
            GROUP BY c.id, c.code ORDER BY c.code
            """),
        {"b": list(run.batch_ids)},
    ).all()
    in_groups = dict(
        session.execute(
            text("""
                SELECT c.code, count(DISTINCT cm.record_id) FROM cluster cl
                JOIN cluster_member cm ON cm.cluster_id = cl.id
                JOIN material_record m ON m.id = cm.record_id JOIN cpse c ON c.id = m.cpse_id
                WHERE cl.run_id = :r GROUP BY c.code
                """),
            p,
        ).all()
    )
    within = dict(
        session.execute(
            text("""
                SELECT code, sum(n - 1) FROM (
                  SELECT c.code, cl.id, count(*) AS n FROM cluster cl
                  JOIN cluster_member cm ON cm.cluster_id = cl.id
                  JOIN material_record m ON m.id = cm.record_id JOIN cpse c ON c.id = m.cpse_id
                  WHERE cl.run_id = :r GROUP BY c.code, cl.id HAVING count(*) > 1
                ) t GROUP BY code
                """),
            p,
        ).all()
    )
    groups = session.execute(
        text("""
            SELECT count(*) AS groups,
                   count(*) FILTER (WHERE n_cpse >= 2) AS cross_cpse,
                   count(*) FILTER (WHERE n_cpse >= 3) AS three_plus
            FROM (SELECT cl.id, count(DISTINCT m.cpse_id) AS n_cpse FROM cluster cl
                  JOIN cluster_member cm ON cm.cluster_id = cl.id
                  JOIN material_record m ON m.id = cm.record_id
                  WHERE cl.run_id = :r GROUP BY cl.id) g
            """),
        p,
    ).one()
    backlog = dict(
        session.execute(
            text(
                "SELECT t.state, count(*) FROM review_task t JOIN cluster c ON c.id = t.cluster_id"
                " WHERE c.run_id = :r GROUP BY t.state"
            ),
            p,
        ).all()
    )
    issued = session.scalar(
        text(
            "SELECT count(*) FROM cnmc n JOIN cluster c ON c.id = n.source_cluster"
            " WHERE c.run_id = :r"
        ),
        p,
    )
    by_category = session.execute(
        text("""
            SELECT cl.category, count(DISTINCT cl.id), count(cm.record_id)
            FROM cluster cl JOIN cluster_member cm ON cm.cluster_id = cl.id
            WHERE cl.run_id = :r GROUP BY cl.category ORDER BY 3 DESC
            """),
        p,
    ).all()
    top = session.execute(
        text("""
            SELECT cl.id, cl.category, cl.priority, t.state,
                   (SELECT min(m.short_text) FROM cluster_member cm JOIN material_record m
                      ON m.id = cm.record_id WHERE cm.cluster_id = cl.id),
                   (SELECT array_agg(DISTINCT c.code ORDER BY c.code) FROM cluster_member cm
                      JOIN material_record m ON m.id = cm.record_id JOIN cpse c ON c.id = m.cpse_id
                      WHERE cm.cluster_id = cl.id),
                   (SELECT coalesce(sum(m.annual_value), 0) FROM cluster_member cm
                      JOIN material_record m ON m.id = cm.record_id WHERE cm.cluster_id = cl.id)
            FROM cluster cl JOIN review_task t ON t.cluster_id = cl.id
            WHERE cl.run_id = :r ORDER BY cl.priority DESC NULLS LAST LIMIT 10
            """),
        p,
    ).all()
    money = money_summary(session, rid)
    stats = run.stats or {}
    return {
        "run_id": rid,
        "is_synthetic": _synthetic(session, rid),
        "computed_at": datetime.now(UTC),
        "mode": run.mode,
        "run_started_at": run.started_at,
        "per_cpse": [
            {"cpse": code, "records": int(n), "annual_spend": float(spend),
             "health_score": health, "in_groups": int(in_groups.get(code, 0)),
             "internal_duplicates": int(within.get(code, 0) or 0)}
            for code, n, spend, health in per_cpse
        ],  # fmt: skip
        "groups": {"total": groups.groups, "cross_cpse": groups.cross_cpse,
                   "three_plus": groups.three_plus},  # fmt: skip
        "verdicts": stats.get("verdicts", {}),
        "records": stats.get("records"),
        "candidate_pairs": stats.get("candidate_pairs"),
        "backlog": {k: int(v) for k, v in backlog.items()},
        "issued": int(issued or 0),
        "by_category": [
            {"category": c, "groups": int(g), "records": int(r)} for c, g, r in by_category
        ],
        "top_groups": [
            {"id": i, "category": c, "priority": float(pr) if pr is not None else None, "state": st,
             "sample_text": s, "cpses": list(cp or []), "annual_spend": float(v)}
            for i, c, pr, st, s, cp, v in top
        ],  # fmt: skip
        "money": money,
    }


# ---------------------------------------------------------------- money
def _prices_sql() -> str:
    """Per (group, CPSE): average unit price and quantity bought in the last 12 months of data,
    stock on hand and stock that did not move (idle: no purchase in the last 12 months)."""
    return """
        WITH asof AS (SELECT max(po_date) AS d FROM procurement_line),
        lines AS (
          SELECT cm.cluster_id, m.cpse_id, m.id AS record_id, p.qty, p.unit_price, p.po_date
          FROM cluster cl JOIN cluster_member cm ON cm.cluster_id = cl.id
          JOIN material_record m ON m.id = cm.record_id
          JOIN procurement_line p ON p.record_id = m.id, asof
          WHERE cl.run_id = :r AND p.po_date > asof.d - interval '12 months'
            AND p.unit_price IS NOT NULL
        ),
        per AS (
          SELECT cluster_id, cpse_id, sum(qty) AS qty,
                 sum(qty * unit_price) / nullif(sum(qty), 0) AS avg_price
          FROM lines GROUP BY cluster_id, cpse_id
        )
        SELECT per.cluster_id, c.code, per.qty, per.avg_price
        FROM per JOIN cpse c ON c.id = per.cpse_id
    """


def money_summary(session: Session, run_id: uuid.UUID, limit: int = 10) -> dict[str, Any]:
    rows = session.execute(text(_prices_sql()), {"r": run_id}).all()
    by_group: dict[uuid.UUID, list[tuple[str, float, float]]] = {}
    for cid, code, qty, price in rows:
        if price is not None and qty:
            by_group.setdefault(cid, []).append((code, float(qty), float(price)))
    gaps = []
    for cid, parts in by_group.items():
        if len({p[0] for p in parts}) < 2:
            continue  # a price gap needs at least two CPSEs buying the same item
        low = min(p[2] for p in parts)
        gap = sum(q * (price - low) for _, q, price in parts)
        gaps.append((cid, parts, low, gap))
    gaps.sort(key=lambda g: -g[3])
    meta = _group_meta(session, [g[0] for g in gaps[:limit]])
    idle = stock_sharing(session, run_id, limit)
    return {
        "groups_with_prices": len(gaps),
        "total_price_gap": round(sum(g[3] for g in gaps)),
        "pooled_annual_spend": round(sum(q * pr for _, parts, _, _ in gaps for _, q, pr in parts)),
        "top_price_gaps": [
            {"cluster_id": cid, **meta.get(cid, {}), "lowest_price": round(low, 2),
             "price_gap": round(gap),
             "by_cpse": [{"cpse": c, "annual_qty": q, "avg_price": round(pr, 2)}
                         for c, q, pr in sorted(parts)]}
            for cid, parts, low, gap in gaps[:limit]
        ],  # fmt: skip
        "stock_sharing": idle,
        "note": "Gaps between CPSE prices for the same item and idle stock; not savings achieved.",
    }


def stock_sharing(session: Session, run_id: uuid.UUID, limit: int = 10) -> dict[str, Any]:
    """Groups where one CPSE holds stock it has not used for 12 months while another CPSE of
    the same group keeps buying: transfer before buying."""
    rows = session.execute(
        text("""
            WITH asof AS (SELECT max(po_date) AS d FROM procurement_line),
            rec AS (
              SELECT cm.cluster_id, m.id, c.code AS cpse, m.legacy_code, m.stock_qty,
                     (SELECT max(p.po_date) FROM procurement_line p
                       WHERE p.record_id = m.id) AS last_po,
                     (SELECT coalesce(sum(p.qty), 0) FROM procurement_line p, asof
                       WHERE p.record_id = m.id
                         AND p.po_date > asof.d - interval '12 months') AS qty_12m,
                     (SELECT avg(p.unit_price) FROM procurement_line p
                       WHERE p.record_id = m.id) AS price
              FROM cluster cl JOIN cluster_member cm ON cm.cluster_id = cl.id
              JOIN material_record m ON m.id = cm.record_id JOIN cpse c ON c.id = m.cpse_id
              WHERE cl.run_id = :r
            )
            SELECT h.cluster_id, h.cpse, h.legacy_code, h.stock_qty, b.cpse, b.legacy_code,
                   b.qty_12m, b.price
            FROM rec h JOIN rec b ON b.cluster_id = h.cluster_id AND b.cpse <> h.cpse, asof
            WHERE h.stock_qty > 0
              AND (h.last_po IS NULL OR h.last_po <= asof.d - interval '12 months')
              AND b.qty_12m > 0
            ORDER BY least(h.stock_qty, b.qty_12m) * coalesce(b.price, 0) DESC
            """),
        {"r": run_id},
    ).all()
    seen: set[tuple[Any, str]] = set()
    picks = []
    for cid, h_cpse, h_code, stock, b_cpse, b_code, qty, price in rows:
        if (cid, h_cpse) in seen:
            continue
        seen.add((cid, h_cpse))
        transfer = min(float(stock), float(qty))
        picks.append(
            {"cluster_id": cid, "holder": h_cpse, "holder_code": h_code, "idle_stock": float(stock),
             "buyer": b_cpse, "buyer_code": b_code, "buyer_annual_qty": float(qty),
             "transferable": transfer,
             "value_at_buyer_price": round(transfer * float(price or 0))}
        )  # fmt: skip
    meta = _group_meta(session, [p["cluster_id"] for p in picks[:limit]])
    return {
        "suggestions": len(picks),
        "total_value": round(sum(p["value_at_buyer_price"] for p in picks)),
        "top": [{**p, **meta.get(p["cluster_id"], {})} for p in picks[:limit]],
    }


def _group_meta(session: Session, ids: list[Any]) -> dict[Any, dict[str, Any]]:
    if not ids:
        return {}
    rows = session.execute(
        text("""
            SELECT cl.id, cl.category, t.state,
                   (SELECT min(m.short_text) FROM cluster_member cm JOIN material_record m
                      ON m.id = cm.record_id WHERE cm.cluster_id = cl.id),
                   (SELECT n.cnmc FROM cnmc n WHERE n.source_cluster = cl.id LIMIT 1)
            FROM cluster cl LEFT JOIN review_task t ON t.cluster_id = cl.id
            WHERE cl.id = ANY(:ids)
            """),
        {"ids": ids},
    ).all()
    return {
        r[0]: {"category": r[1], "state": r[2], "sample_text": r[3], "cnmc": r[4]} for r in rows
    }


# ---------------------------------------------------------------- Look-alike Guard
def lookalikes(session: Session, run_id: uuid.UUID | None, kind: str, limit: int) -> dict[str, Any]:
    """LOOKALIKE_VETOED (text says same, specification says no) or HIDDEN_TWIN (worded
    differently, same specification), with the decisive attribute and its rule."""
    rid = resolve_run(session, run_id)
    if rid is None:
        return {"run_id": None, "total": 0, "items": [], "histogram": []}
    cls = "LOOKALIKE_VETOED" if kind == "vetoed" else "HIDDEN_TWIN"
    order = "p.text_sim DESC" if kind == "vetoed" else "p.text_sim ASC"
    p = {"r": rid, "cls": cls, "limit": limit}
    total = session.scalar(
        text("SELECT count(*) FROM pair_decision p WHERE p.run_id = :r AND p.lookalike = :cls"), p
    )
    rows = session.execute(
        text(f"""
            SELECT p.id, p.verdict, p.text_sim, p.evidence, ca.code, a.legacy_code,
                   coalesce(nullif(a.long_text, ''), a.short_text), cb.code, b.legacy_code,
                   coalesce(nullif(b.long_text, ''), b.short_text), sa.category
            FROM pair_decision p
            JOIN material_record a ON a.id = p.rec_a JOIN cpse ca ON ca.id = a.cpse_id
            JOIN material_record b ON b.id = p.rec_b JOIN cpse cb ON cb.id = b.cpse_id
            LEFT JOIN spec_record sa ON sa.record_id = p.rec_a
            WHERE p.run_id = :r AND p.lookalike = :cls
            ORDER BY {order}, p.id LIMIT :limit
            """),  # noqa: S608
        p,
    ).all()
    items = []
    for pid, verdict, sim, evidence, ca, la, ta, cb, lb, tb, cat in rows:
        decisive = [e for e in evidence if e["status"] == "CONFLICT"]
        items.append(
            {"pair_id": pid, "verdict": verdict, "text_sim": float(sim), "category": cat,
             "a": {"cpse": ca, "legacy_code": la, "text": ta},
             "b": {"cpse": cb, "legacy_code": lb, "text": tb},
             "decisive": decisive}
        )  # fmt: skip
    histogram = session.execute(
        text("""
            SELECT width_bucket(p.text_sim::float, 0, 1.0000001, 10) AS bucket,
                   count(*) FILTER (WHERE p.verdict IN ('EQUIVALENT','IDENTICAL')),
                   count(*) FILTER (WHERE p.verdict = 'NOT_EQUIVALENT'),
                   count(*) FILTER (WHERE p.verdict = 'INSUFFICIENT_DATA')
            FROM pair_decision p WHERE p.run_id = :r GROUP BY 1 ORDER BY 1
            """),
        {"r": rid},
    ).all()
    by_attr = session.execute(
        text("""
            SELECT e->>'attr', count(*) FROM pair_decision p,
                   jsonb_array_elements(p.evidence) e
            WHERE p.run_id = :r AND p.lookalike = 'LOOKALIKE_VETOED' AND e->>'status' = 'CONFLICT'
            GROUP BY 1 ORDER BY 2 DESC
            """),
        {"r": rid},
    ).all()
    cfg = session.scalar(text("SELECT config FROM run WHERE id = :r"), {"r": rid}) or {}
    return {
        "run_id": rid,
        "kind": kind,
        "total": int(total or 0),
        "thresholds": {"lookalike_min_sim": cfg.get("lookalike_min_sim"),
                       "hidden_twin_max_sim": cfg.get("hidden_twin_max_sim")},  # fmt: skip
        "items": items,
        "histogram": [
            {"from": round((b - 1) / 10, 1), "to": round(b / 10, 1), "same": s, "different": d,
             "unknown": u}
            for b, s, d, u in histogram
        ],  # fmt: skip
        "decisive_attributes": [{"attr": a, "pairs": int(n)} for a, n in by_attr],
    }
