"""Per-CPSE migration pack (PRD FR-907, TRD TR-MOD-26, TR-ALG-08).

For each CPSE and each ACTIVE CNMC holding ≥ 1 of its active crosswalk rows:
- survivor = the code with the largest annual value, then the most complete spec, then the
  lowest legacy code (deterministic): RETAIN;
- every other code: PHASE_OUT_WHEN_STOCK_ZERO when stock is on hand, else
  BLOCK_FOR_NEW_PROCUREMENT.
The recommended actions are written back to the crosswalk (audited). They are recommendations:
each CPSE applies them through its own master-data process.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import AppUser, Cpse
from app.services import audit

NOTE = (
    "Recommendations; apply through your own master-data process (for SAP typically a material "
    "status such as MARA-MSTAE; confirm with your SAP team)."
)
COLUMNS = [
    "cpse", "legacy_code", "legacy_short_text", "cnmc", "cnmc_short_desc_40", "relation",
    "survivor", "recommended_action", "uom", "uom_factor", "stock_known", "stock_qty",
    "annual_value", "note",
]  # fmt: skip


def pack(session: Session, actor: AppUser, cpse: Cpse) -> list[dict[str, Any]]:
    rows = session.execute(
        text("""
            SELECT x.id, x.legacy_code, m.short_text, x.cnmc, n.short_desc_40, x.relation, x.uom,
                   x.uom_factor, m.stock_qty, m.annual_value, s.spec_completeness
            FROM crosswalk x
            JOIN cnmc n ON n.cnmc = x.cnmc AND n.status = 'ACTIVE'
            JOIN material_record m ON m.id = x.record_id
            LEFT JOIN spec_record s ON s.record_id = m.id
            WHERE x.cpse_id = :c AND x.status = 'ACTIVE'
            ORDER BY x.cnmc, x.legacy_code
            """),
        {"c": cpse.id},
    ).all()
    by_cnmc: dict[str, list[Any]] = {}
    for r in rows:
        by_cnmc.setdefault(r[3], []).append(r)
    out: list[dict[str, Any]] = []
    changes: list[tuple[Any, str]] = []
    for cnmc, members in by_cnmc.items():
        survivor = max(
            members,
            key=lambda r: (float(r[9] or 0), float(r[10] or 0), [-ord(ch) for ch in r[1]] + [1]),
        )
        for r in members:
            stock = float(r[8]) if r[8] is not None else None
            if r is survivor:
                action = "RETAIN"
            elif stock and stock > 0:
                action = "PHASE_OUT_WHEN_STOCK_ZERO"
            else:
                action = "BLOCK_FOR_NEW_PROCUREMENT"
            changes.append((r[0], action))
            note = None
            if r[7] is None and r[6] is not None:
                note = "UoM factor needed"
            out.append(
                {"cpse": cpse.code, "legacy_code": r[1], "legacy_short_text": r[2], "cnmc": cnmc,
                 "cnmc_short_desc_40": r[4], "relation": r[5], "survivor": r is survivor,
                 "recommended_action": action, "uom": r[6],
                 "uom_factor": float(r[7]) if r[7] is not None else None,
                 "stock_known": r[8] is not None, "stock_qty": stock,
                 "annual_value": float(r[9]) if r[9] is not None else None, "note": note}
            )  # fmt: skip
    changed = 0
    for crosswalk_id, action in changes:
        changed += session.execute(
            text(
                "UPDATE crosswalk SET migration_action = :a WHERE id = :i"
                " AND migration_action IS DISTINCT FROM :a"
            ),
            {"a": action, "i": crosswalk_id},
        ).rowcount
    if changed:
        audit.record(
            session,
            actor_id=actor.id,
            action="MIGRATION_ACTIONS_SET",
            object_type="crosswalk",
            object_id=cpse.code,
            after={"cpse": cpse.code, "rows": len(out), "changed": changed},
        )
    return out
