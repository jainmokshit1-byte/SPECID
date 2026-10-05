"""National-code issuance and registry reads (TRD TR-MOD-25, sequence 2.3b; PRD FR-901-906).

`issue()` runs inside the caller's transaction (the checker's confirmation or the last consent):
next CNMC from `cnmc_seq` with its Luhn digit, canonical spec, 40-character short text and long
text from the members' specs, class path, variants, base UoM, one crosswalk row per member,
cluster APPROVED, audit event, and a change notice for every CPSE whose codes joined. The partial
unique index `crosswalk_active_uq` is the last guard against mapping a legacy code twice.
"""

import uuid
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.cnmc import new_cnmc
from app.core.shortdesc import long_desc, short_desc
from app.core.types import Spec
from app.db.models import AppUser, Cluster, Cnmc, Cpse, Crosswalk, ReviewTask
from app.services import audit, notices
from app.services.errors import Conflict, NotFound

# Class path: group -> category -> subtype (PRD FR-402). The subtype attribute per category.
GROUP = {
    "VALVE": "PIPING", "PIPE": "PIPING", "FLANGE": "PIPING", "GASKET": "PIPING",
    "FASTENER": "FASTENERS", "MOTOR": "ELECTRICAL",
}  # fmt: skip
SUBTYPE_ATTR = {
    "VALVE": "valve_type", "PIPE": "process", "FLANGE": "flange_type",
    "FASTENER": "fastener_type", "MOTOR": "motor_type", "GASKET": "gasket_type",
}  # fmt: skip


@dataclass(frozen=True)
class Member:
    record_id: uuid.UUID
    cpse_id: uuid.UUID
    cpse_code: str
    legacy_code: str
    short_text: str
    long_text: str | None
    uom: str | None
    manufacturer: str | None
    mpn: str | None
    annual_value: Decimal | None
    stock_qty: Decimal | None
    category: str | None
    attrs: dict[str, Any]
    spec_completeness: Decimal | None


def members_of(session: Session, cluster_id: uuid.UUID) -> list[Member]:
    rows = session.execute(
        text("""
            SELECT m.id, m.cpse_id, c.code, m.legacy_code, m.short_text, m.long_text,
                   m.uom_canonical, m.manufacturer, m.mpn, m.annual_value, m.stock_qty,
                   s.category, COALESCE(s.attrs, '{}'::jsonb), s.spec_completeness
            FROM cluster_member cm
            JOIN material_record m ON m.id = cm.record_id
            JOIN cpse c ON c.id = m.cpse_id
            LEFT JOIN spec_record s ON s.record_id = m.id
            WHERE cm.cluster_id = :c
            ORDER BY c.code, m.legacy_code
            """),
        {"c": cluster_id},
    ).all()
    return [Member(*r) for r in rows]


def participants(members: Sequence[Member]) -> dict[uuid.UUID, str]:
    """Participating CPSEs (TR-ALG-11): the distinct CPSEs of the cluster's members."""
    return {m.cpse_id: m.cpse_code for m in members}


def canonical_spec(members: Sequence[Member]) -> dict[str, Any]:
    """Union of the members' attributes; per attribute the most common known value (PRD 9.8).
    Members are EQUIVALENT, so core values agree; the vote matters only for tolerant ones."""
    keys: list[str] = []
    for m in members:
        keys.extend(k for k in m.attrs if k not in keys)
    out: dict[str, Any] = {}
    for k in keys:
        values = [m.attrs.get(k) for m in members if m.attrs.get(k) is not None]
        out[k] = Counter(map(_hashable, values)).most_common(1)[0][0] if values else None
    return out


def _hashable(v: Any) -> Any:
    return tuple(v) if isinstance(v, list) else v


def base_uom(members: Sequence[Member]) -> str | None:
    """Most frequent canonical UoM among members; ties go to EA (TR-ALG-06)."""
    counts = Counter(m.uom for m in members if m.uom)
    if not counts:
        return None
    top = max(counts.values())
    best = sorted(u for u, n in counts.items() if n == top)
    return "EA" if "EA" in best else best[0]


def proposal(members: Sequence[Member]) -> dict[str, Any]:
    """What the national code would look like: shown to the reviewer before issuance."""
    category = next((m.category for m in members if m.category), None)
    attrs = canonical_spec(members)
    spec = Spec(category, attrs, {}, ())
    subtype = attrs.get(SUBTYPE_ATTR.get(category or "", ""), None)
    return {
        "category": category,
        "canonical_spec": attrs,
        "short_desc_40": short_desc(spec) if category else None,
        "long_desc": long_desc(spec) if category else None,
        "class_path": [p for p in (GROUP.get(category or ""), category, subtype) if p],
        "base_uom": base_uom(members),
        "variants": sorted(
            {(m.manufacturer, m.mpn) for m in members if m.manufacturer or m.mpn},
            key=lambda v: (v[0] or "", v[1] or ""),
        ),
    }


def issue(
    session: Session,
    actor: AppUser,
    task: ReviewTask,
    members: Sequence[Member],
    *,
    consent_mode: str,
    relation: str,
) -> str:
    """Issue one CNMC for `members` (≥ 2) inside the caller's transaction; returns the code."""
    cluster = session.get(Cluster, task.cluster_id)
    if cluster is None:
        raise NotFound("No such cluster.")
    mapped = session.execute(
        text(
            "SELECT cw.legacy_code, cw.cnmc FROM crosswalk cw"
            " WHERE cw.status = 'ACTIVE' AND cw.record_id = ANY(:ids)"
        ),
        {"ids": [m.record_id for m in members]},
    ).first()
    if mapped:
        raise Conflict(
            f"Legacy code {mapped[0]} is already mapped to {mapped[1]}."
            " Open it, or unmerge it first."
        )
    seq = session.execute(text("SELECT nextval('cnmc_seq')")).scalar_one()
    code = new_cnmc(int(seq))
    p = proposal(members)
    completeness = [float(m.spec_completeness) for m in members if m.spec_completeness is not None]
    row = Cnmc(
        cnmc=code,
        template_id=(p["category"] or "").lower() or None,
        template_version=None,
        category=p["category"] or "UNKNOWN",
        class_path=p["class_path"] or None,
        unspsc=None,  # filled only from a verified table (FR-405); empty in v1
        hsn=None,
        canonical_spec=p["canonical_spec"],
        spec_completeness=Decimal(str(max(completeness))) if completeness else None,
        variants=[{"manufacturer": a, "mpn": b} for a, b in p["variants"]],
        base_uom=p["base_uom"],
        short_desc_40=p["short_desc_40"],
        long_desc=p["long_desc"],
        status="ACTIVE",
        source_cluster=cluster.id,
        issued_by=actor.id,
    )
    session.add(row)
    session.flush()
    for m in members:
        same = m.uom is not None and m.uom == p["base_uom"]
        session.add(
            Crosswalk(
                cnmc=code,
                record_id=m.record_id,
                cpse_id=m.cpse_id,
                legacy_code=m.legacy_code,
                relation=relation,
                uom=m.uom,
                uom_factor=(
                    Decimal(1) if same else None
                ),  # a different UoM needs a factor: never guessed
                cluster_id=cluster.id,
                approver_id=actor.id,
            )
        )
    cluster.status = "APPROVED"
    task.state = "DONE"
    session.flush()
    cpses = participants(members)
    event = audit.record(
        session,
        actor_id=actor.id,
        action="CNMC_ISSUED",
        object_type="cnmc",
        object_id=code,
        after={
            "cluster": str(cluster.id),
            "members": len(members),
            "cpses": sorted(cpses.values()),
            "short_desc_40": p["short_desc_40"],
            "consent_mode": consent_mode,
        },
    )
    for cpse_id in cpses:
        mine = [m for m in members if m.cpse_id == cpse_id]
        notices.create(
            session,
            cpse_id=cpse_id,
            kind="CNMC_ISSUED",
            object_type="cnmc",
            object_id=code,
            summary=f"{code} issued; {len(mine)} of your codes now map to it.",
            delta=[
                {"legacy_code": m.legacy_code, "cnmc": code, "relation": relation,
                 "short_desc_40": p["short_desc_40"]}
                for m in mine
            ],  # fmt: skip
            audit_event_id=event.id,
        )
    return code


# ---------------------------------------------------------------- reads
def list_cnmc(
    session: Session,
    *,
    q: str | None,
    category: str | None,
    cpse: str | None,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    where = ["1=1"]
    args: dict[str, Any] = {"limit": limit, "offset": offset}
    if q:
        where.append(
            "(n.cnmc ILIKE :q OR n.short_desc_40 ILIKE :q OR n.long_desc ILIKE :q OR EXISTS ("
            " SELECT 1 FROM crosswalk x WHERE x.cnmc = n.cnmc AND x.legacy_code ILIKE :q))"
        )
        args["q"] = f"%{q.strip()}%"
    if category:
        where.append("n.category = :category")
        args["category"] = category
    if status:
        where.append("n.status = :status")
        args["status"] = status
    if cpse:
        where.append(
            "EXISTS (SELECT 1 FROM crosswalk x JOIN cpse c ON c.id = x.cpse_id"
            " WHERE x.cnmc = n.cnmc AND x.status = 'ACTIVE' AND c.code = :cpse)"
        )
        args["cpse"] = cpse
    w = " AND ".join(where)
    total = session.scalar(text(f"SELECT count(*) FROM cnmc n WHERE {w}"), args) or 0  # noqa: S608
    rows = session.execute(
        text(f"""
            SELECT n.cnmc, n.category, n.short_desc_40, n.status, n.issued_at,
                   (SELECT count(*) FROM crosswalk x WHERE x.cnmc = n.cnmc AND x.status = 'ACTIVE'),
                   (SELECT array_agg(DISTINCT c.code ORDER BY c.code) FROM crosswalk x
                      JOIN cpse c ON c.id = x.cpse_id WHERE x.cnmc = n.cnmc AND x.status = 'ACTIVE')
            FROM cnmc n WHERE {w}
            ORDER BY n.issued_at DESC, n.cnmc DESC LIMIT :limit OFFSET :offset
            """),  # noqa: S608
        args,
    ).all()
    items = [
        {"cnmc": r[0], "category": r[1], "short_desc_40": r[2], "status": r[3], "issued_at": r[4],
         "codes": r[5], "cpses": list(r[6] or [])}
        for r in rows
    ]  # fmt: skip
    return int(total), items


def get_cnmc(session: Session, code: str) -> dict[str, Any]:
    n = session.get(Cnmc, code)
    if n is None:
        raise NotFound(f"No national code {code}.")
    crosswalk = session.execute(
        text("""
            SELECT c.code, x.legacy_code, m.short_text, x.relation, x.status, x.uom, x.uom_factor,
                   x.migration_action, m.annual_value, m.stock_qty, x.approved_at
            FROM crosswalk x JOIN cpse c ON c.id = x.cpse_id
            JOIN material_record m ON m.id = x.record_id
            WHERE x.cnmc = :n ORDER BY c.code, x.legacy_code
            """),
        {"n": code},
    ).all()
    history = session.execute(
        text("""
            SELECT e.ts, e.action, u.username, e.after FROM audit_event e
            LEFT JOIN app_user u ON u.id = e.actor_id
            WHERE (e.object_type = 'cnmc' AND e.object_id = :n)
               OR (e.object_type IN ('review_task', 'review_consent') AND e.object_id IN (
                     SELECT t.id::text FROM review_task t WHERE t.cluster_id = :cl))
            ORDER BY e.id
            """),
        {"n": code, "cl": n.source_cluster},
    ).all()
    issuer = (
        session.scalar(select(AppUser.username).where(AppUser.id == n.issued_by))
        if n.issued_by
        else None
    )
    return {
        "cnmc": n.cnmc,
        "category": n.category,
        "class_path": list(n.class_path or []),
        "unspsc": n.unspsc,
        "hsn": n.hsn,
        "canonical_spec": n.canonical_spec,
        "spec_completeness": (
            float(n.spec_completeness) if n.spec_completeness is not None else None
        ),
        "variants": n.variants,
        "base_uom": n.base_uom,
        "short_desc_40": n.short_desc_40,
        "long_desc": n.long_desc,
        "status": n.status,
        "source_cluster": n.source_cluster,
        "issued_by": issuer,
        "issued_at": n.issued_at,
        "crosswalk": [
            {"cpse": r[0], "legacy_code": r[1], "short_text": r[2], "relation": r[3],
             "status": r[4], "uom": r[5], "uom_factor": float(r[6]) if r[6] is not None else None,
             "migration_action": r[7], "annual_value": float(r[8]) if r[8] is not None else None,
             "stock_qty": float(r[9]) if r[9] is not None else None, "approved_at": r[10]}
            for r in crosswalk
        ],  # fmt: skip
        "history": [{"ts": r[0], "action": r[1], "actor": r[2], "after": r[3]} for r in history],
    }


def cpse_by_code(session: Session, code: str) -> Cpse:
    cpse = session.scalar(select(Cpse).where(Cpse.code == code))
    if cpse is None:
        raise NotFound(f"No CPSE with code {code}.")
    return cpse
