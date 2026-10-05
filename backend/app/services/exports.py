"""Exports: crosswalk (CSV, JSON, SAP-style) and files built from rows (TRD TR-MOD-31, FR-905).

CSV formula-injection guard (TR-SEC-10): a cell starting with `=`, `+`, `-`, `@`, tab or CR is
prefixed with `'`. CSV files are UTF-8 with a BOM so Excel opens them correctly.
"""

import csv
import io
import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import AppUser
from app.services import audit

DANGEROUS = ("=", "+", "-", "@", "\t", "\r")
CROSSWALK_COLUMNS = [
    "cnmc", "cnmc_short_desc_40", "category", "cpse", "legacy_code", "legacy_short_text",
    "relation", "uom", "uom_factor", "migration_action", "status",
]  # fmt: skip
# SAP-style: one row per legacy material, semicolon-separated, SAP-like field names.
# Confirm the target fields with each CPSE's SAP team (TRD Appendix H.2).
SAP_COLUMNS = [
    "MATNR",
    "ZZ_CNMC",
    "MAKTX_NATIONAL",
    "MEINS",
    "UMREZ",
    "MSTAE_RECOMMENDED",
    "WERKS_NOTE",
]
SAP_STATUS = {
    "RETAIN": "",
    "BLOCK_FOR_NEW_PROCUREMENT": "BLOCK",
    "PHASE_OUT_WHEN_STOCK_ZERO": "PHASE_OUT",
}


def safe_cell(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(DANGEROUS):
        return "'" + value
    return value


def to_csv(rows: Sequence[dict[str, Any]], columns: Sequence[str], delimiter: str = ",",
           preamble: str | None = None) -> bytes:  # fmt: skip
    buf = io.StringIO()
    if preamble:
        buf.write(f"# {preamble}\n")
    w = csv.DictWriter(buf, fieldnames=list(columns), delimiter=delimiter, lineterminator="\r\n",
                       extrasaction="ignore")  # fmt: skip
    w.writeheader()
    for r in rows:
        w.writerow({k: safe_cell("" if r.get(k) is None else r.get(k)) for k in columns})
    return ("﻿" + buf.getvalue()).encode("utf-8")


def crosswalk_rows(
    session: Session, *, cnmc: str | None = None, cpse: str | None = None
) -> list[dict[str, Any]]:
    where = ["x.status = 'ACTIVE'"]
    args: dict[str, Any] = {}
    if cnmc:
        where.append("x.cnmc = :cnmc")
        args["cnmc"] = cnmc
    if cpse:
        where.append("c.code = :cpse")
        args["cpse"] = cpse
    rows = session.execute(
        text(f"""
            SELECT x.cnmc, n.short_desc_40, n.category, c.code, x.legacy_code, m.short_text,
                   x.relation, x.uom, x.uom_factor, x.migration_action, x.status
            FROM crosswalk x JOIN cnmc n ON n.cnmc = x.cnmc JOIN cpse c ON c.id = x.cpse_id
            JOIN material_record m ON m.id = x.record_id
            WHERE {" AND ".join(where)} ORDER BY x.cnmc, c.code, x.legacy_code
            """),  # noqa: S608
        args,
    ).all()
    return [
        dict(zip(CROSSWALK_COLUMNS, [*r[:8], float(r[8]) if r[8] is not None else None, *r[9:]],
                 strict=True))
        for r in rows
    ]  # fmt: skip


def crosswalk_file(rows: Sequence[dict[str, Any]], fmt: str) -> tuple[bytes, str, str]:
    """(content, media type, extension) for csv, json or sap_csv."""
    if fmt == "json":
        body = json.dumps({"rows": list(rows)}, ensure_ascii=False, indent=1, default=str)
        return body.encode("utf-8"), "application/json", "json"
    if fmt == "sap_csv":
        sap = [
            {"MATNR": r["legacy_code"], "ZZ_CNMC": r["cnmc"],
             "MAKTX_NATIONAL": r["cnmc_short_desc_40"], "MEINS": r["uom"], "UMREZ": r["uom_factor"],
             "MSTAE_RECOMMENDED": SAP_STATUS.get(r["migration_action"] or "", ""),
             "WERKS_NOTE": r["cpse"]}
            for r in rows
        ]  # fmt: skip
        return to_csv(sap, SAP_COLUMNS, ";"), "text/csv", "csv"
    return to_csv(rows, CROSSWALK_COLUMNS), "text/csv", "csv"


def record_download(session: Session, actor: AppUser, what: str, **after: Any) -> None:
    audit.record(
        session,
        actor_id=actor.id,
        action="EXPORT_DOWNLOADED",
        object_type="export",
        object_id=what,
        after=after or None,
    )
