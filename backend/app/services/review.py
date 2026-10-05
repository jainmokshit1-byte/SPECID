"""Maker-checker review and multi-CPSE consent (TRD TR-MOD-24, TR-MOD-32, Appendix F.3,
TR-ALG-11; PRD FR-801-807, FR-1501-1504).

State machine of `review_task` (one per cluster, created by the run):

    OPEN --maker proposes--> MADE --checker confirms--> DONE
                                                     | AWAITING_CONSENT --last answer--> DONE
                              MADE --checker overturns (comment)--> OPEN

- The maker and the checker are different people: 403 here, a CHECK constraint in the database.
- On confirming an APPROVE, the maker's and the checker's CPSEs consent implicitly. With
  `CONSENT_MODE=ALL_PARTICIPANTS`, a cluster that has records of any other CPSE waits for a
  steward (CHECKER) of that CPSE; the code is issued in the transaction of the last answer, for
  the CPSEs that consented (≥ 2 records), or the cluster is rejected.
- Every step writes an audit event in the same transaction.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import AppUser, Cluster, ReviewConsent, ReviewDecision, ReviewTask
from app.services import audit, notices, registry
from app.services.errors import Conflict, Forbidden, Invalid, NotFound

Proposal = Literal["APPROVE", "REJECT", "SPLIT", "NEEDS_INFO"]
Check = Literal["CONFIRM", "OVERTURN"]
MIN_REASON = 5


def _task(session: Session, cluster_id: uuid.UUID, lock: bool = False) -> ReviewTask:
    stmt = select(ReviewTask).where(ReviewTask.cluster_id == cluster_id)
    if lock:
        stmt = stmt.with_for_update()  # no double issuance (2.3b)
    task = session.scalar(stmt)
    if task is None:
        raise NotFound("No review task for this cluster.")
    return task


def _touch(task: ReviewTask) -> None:
    task.updated_at = datetime.now(UTC)


def consent_rows(session: Session, task_id: uuid.UUID) -> dict[uuid.UUID, ReviewConsent]:
    rows = session.scalars(select(ReviewConsent).where(ReviewConsent.task_id == task_id))
    return {r.cpse_id: r for r in rows}


def propose(
    session: Session,
    maker: AppUser,
    cluster_id: uuid.UUID,
    decision: Proposal,
    comment: str | None,
    split_groups: list[list[uuid.UUID]] | None = None,
) -> ReviewTask:
    task = _task(session, cluster_id, lock=True)
    if task.state != "OPEN":
        raise Conflict(f"This cluster is not waiting for a proposal (it is {task.state}).")
    comment = (comment or "").strip() or None
    if decision in ("REJECT", "NEEDS_INFO") and (comment is None or len(comment) < MIN_REASON):
        raise Invalid("Say why (at least 5 characters).", title="Comment required")
    if decision == "SPLIT" and not split_groups:
        raise Invalid("A split needs the groups of records.", title="Groups required")
    task.state, task.made_by, task.proposed_decision, task.checked_by = (
        "MADE",
        maker.id,
        decision,
        None,
    )
    _touch(task)
    session.add(
        ReviewDecision(
            task_id=task.id,
            actor_id=maker.id,
            actor_role="MAKER",
            decision=decision,
            comment=comment,
            split_groups=[[str(r) for r in g] for g in split_groups] if split_groups else None,
        )
    )
    audit.record(
        session,
        actor_id=maker.id,
        action="REVIEW_PROPOSED",
        object_type="review_task",
        object_id=str(task.id),
        after={"cluster": str(cluster_id), "decision": decision, "comment": comment},
    )
    return task


def check(
    session: Session,
    checker: AppUser,
    cluster_id: uuid.UUID,
    action: Check,
    comment: str | None,
    *,
    consent_mode: str,
) -> dict[str, Any]:
    """Confirm or overturn the maker's proposal. Returns {state, cnmc, waiting_for}."""
    task = _task(session, cluster_id, lock=True)
    if task.state != "MADE":
        raise Conflict(f"This cluster has no proposal waiting for a check (it is {task.state}).")
    if task.made_by == checker.id:
        raise Forbidden(
            "You made this proposal; another checker must confirm it.", title="Maker ≠ checker"
        )
    comment = (comment or "").strip() or None
    if action == "OVERTURN":
        if comment is None or len(comment) < MIN_REASON:
            raise Invalid(
                "Say why you overturn it (at least 5 characters).", title="Comment required"
            )
        session.add(ReviewDecision(task_id=task.id, actor_id=checker.id, actor_role="CHECKER",
                                   decision="OVERTURN", comment=comment))  # fmt: skip
        audit.record(
            session,
            actor_id=checker.id,
            action="REVIEW_OVERTURNED",
            object_type="review_task",
            object_id=str(task.id),
            after={"cluster": str(cluster_id), "comment": comment,
                   "proposal": task.proposed_decision},
        )  # fmt: skip
        task.state, task.made_by, task.proposed_decision = "OPEN", None, None
        _touch(task)
        return {"state": "OPEN", "cnmc": None, "waiting_for": []}

    task.checked_by = checker.id
    _touch(task)
    session.add(ReviewDecision(task_id=task.id, actor_id=checker.id, actor_role="CHECKER",
                               decision="CONFIRM", comment=comment))  # fmt: skip
    audit.record(
        session,
        actor_id=checker.id,
        action="REVIEW_CONFIRMED",
        object_type="review_task",
        object_id=str(task.id),
        after={"cluster": str(cluster_id), "proposal": task.proposed_decision},
    )
    cluster = session.get(Cluster, cluster_id)
    assert cluster is not None
    if task.proposed_decision != "APPROVE":
        if task.proposed_decision in ("REJECT", "SPLIT"):
            cluster.status = "REJECTED" if task.proposed_decision == "REJECT" else "SPLIT"
        task.state = "DONE"  # NEEDS_INFO: the cluster stays PROPOSED until the value is supplied
        return {"state": "DONE", "cnmc": None, "waiting_for": []}

    members = registry.members_of(session, cluster_id)
    cpses = registry.participants(members)
    have = consent_rows(session, task.id)
    maker = session.get(AppUser, task.made_by) if task.made_by else None
    for user, via in ((maker, "MAKER_PROPOSAL"), (checker, "CHECKER_CONFIRMATION")):
        if user is not None and user.cpse_id in cpses and user.cpse_id not in have:
            row = ReviewConsent(task_id=task.id, cpse_id=user.cpse_id, user_id=user.id,
                                decision="CONSENT", via=via)  # fmt: skip
            session.add(row)
            have[user.cpse_id] = row
    session.flush()
    missing = [code for cid, code in cpses.items() if cid not in have]
    if consent_mode == "ALL_PARTICIPANTS" and missing:
        task.state = "AWAITING_CONSENT"
        audit.record(
            session,
            actor_id=checker.id,
            action="CONSENT_REQUESTED",
            object_type="review_task",
            object_id=str(task.id),
            after={"cluster": str(cluster_id), "waiting_for": sorted(missing)},
        )
        return {"state": "AWAITING_CONSENT", "cnmc": None, "waiting_for": sorted(missing)}
    code = registry.issue(session, checker, task, members, consent_mode=consent_mode,
                          relation=_relation(session, cluster_id))  # fmt: skip
    return {"state": "DONE", "cnmc": code, "waiting_for": []}


def answer_consent(
    session: Session,
    steward: AppUser,
    cluster_id: uuid.UUID,
    decision: Literal["CONSENT", "DECLINE"],
    reason: str | None,
    *,
    consent_mode: str,
) -> dict[str, Any]:
    """A steward (CHECKER) answers for their own CPSE (sequence 2.3 b2)."""
    task = _task(session, cluster_id, lock=True)
    members = registry.members_of(session, cluster_id)
    cpses = registry.participants(members)
    if steward.cpse_id not in cpses:
        raise Forbidden("Your CPSE has no record in this cluster.", title="Not a participant")
    have = consent_rows(session, task.id)
    if steward.cpse_id in have:
        raise Conflict(f"{cpses[steward.cpse_id]} has already answered for this cluster.")
    if task.state != "AWAITING_CONSENT":
        raise Conflict(f"This cluster is not waiting for consent (it is {task.state}).")
    reason = (reason or "").strip() or None
    if decision == "DECLINE" and (reason is None or len(reason) < MIN_REASON):
        raise Invalid(
            "Give the reason for declining (at least 5 characters).", title="Reason required"
        )
    row = ReviewConsent(task_id=task.id, cpse_id=steward.cpse_id, user_id=steward.id,
                        decision=decision, via="STEWARD", reason=reason)  # fmt: skip
    session.add(row)
    session.flush()
    have[steward.cpse_id] = row
    event = audit.record(
        session,
        actor_id=steward.id,
        action="CONSENT_GIVEN" if decision == "CONSENT" else "CONSENT_DECLINED",
        object_type="review_consent",
        object_id=str(task.id),
        after={"cluster": str(cluster_id), "cpse": cpses[steward.cpse_id], "reason": reason},
    )
    if decision == "DECLINE":
        mine = [m for m in members if m.cpse_id == steward.cpse_id]
        notices.create(
            session,
            cpse_id=steward.cpse_id,
            kind="CONSENT_DECLINED",
            object_type="review_task",
            object_id=str(task.id),
            summary=f"{cpses[steward.cpse_id]} declined; its {len(mine)} code(s) stay unmapped.",
            delta=[{"legacy_code": m.legacy_code, "cnmc": None, "reason": reason} for m in mine],
            audit_event_id=event.id,
        )
    missing = [code for cid, code in cpses.items() if cid not in have]
    if missing:
        return {"state": "AWAITING_CONSENT", "cnmc": None, "waiting_for": sorted(missing)}

    consenting = {cid for cid, r in have.items() if r.decision == "CONSENT"}
    kept = [m for m in members if m.cpse_id in consenting]
    cluster = session.get(Cluster, cluster_id)
    assert cluster is not None
    if len(kept) < 2:  # nothing left to unify
        cluster.status = "REJECTED"
        task.state = "DONE"
        _touch(task)
        return {"state": "DONE", "cnmc": None, "waiting_for": []}
    code = registry.issue(session, steward, task, kept, consent_mode=consent_mode,
                          relation=_relation(session, cluster_id))  # fmt: skip
    _touch(task)
    return {"state": "DONE", "cnmc": code, "waiting_for": []}


def _relation(session: Session, cluster_id: uuid.UUID) -> str:
    """IDENTICAL when every decided pair inside the cluster is IDENTICAL, else EQUIVALENT."""
    verdicts = set(
        session.execute(
            text("""
                SELECT DISTINCT p.verdict FROM pair_decision p
                JOIN cluster c ON c.run_id = p.run_id AND c.id = :c
                JOIN cluster_member a ON a.cluster_id = c.id AND a.record_id = p.rec_a
                JOIN cluster_member b ON b.cluster_id = c.id AND b.record_id = p.rec_b
                """),
            {"c": cluster_id},
        ).scalars()
    )
    return "IDENTICAL" if verdicts == {"IDENTICAL"} else "EQUIVALENT"


# ---------------------------------------------------------------- reads
STAGES = {
    "to_propose": "t.state = 'OPEN'",
    "to_check": "t.state = 'MADE'",
    "awaiting_consent": "t.state = 'AWAITING_CONSENT'",
    "done": "t.state = 'DONE'",
}


def queue(
    session: Session,
    user: AppUser,
    *,
    run_id: uuid.UUID | None,
    stage: str | None,
    category: str | None,
    critical: bool | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """S5 review queue: clusters with their task state, sorted by priority (FR-801)."""
    if run_id is None:  # the newest finished run
        run_id = session.scalar(
            text("SELECT id FROM run WHERE status = 'DONE' ORDER BY started_at DESC LIMIT 1")
        )
        if run_id is None:
            return 0, []
    where = ["c.run_id = :run"]
    args: dict[str, Any] = {"run": run_id, "limit": limit, "offset": offset, "me": user.id}
    if stage:
        if stage not in STAGES:
            raise Invalid(f"Unknown stage {stage}.")
        where.append(STAGES[stage])
        if stage == "to_check":
            where.append("t.made_by IS DISTINCT FROM :me")
    if category:
        where.append("c.category = :category")
        args["category"] = category
    if critical is not None:
        where.append("c.is_critical = :critical")
        args["critical"] = critical
    w = " AND ".join(where)
    frm = "FROM cluster c JOIN review_task t ON t.cluster_id = c.id"
    total = session.scalar(text(f"SELECT count(*) {frm} WHERE {w}"), args) or 0  # noqa: S608
    rows = session.execute(
        text(f"""
            SELECT c.id, c.category, c.priority, c.cohesion, c.flags_count, c.is_critical, c.status,
                   t.state, t.proposed_decision, mk.username,
                   (SELECT count(*) FROM cluster_member m WHERE m.cluster_id = c.id),
                   (SELECT array_agg(DISTINCT p.code ORDER BY p.code) FROM cluster_member m
                      JOIN material_record r ON r.id = m.record_id JOIN cpse p ON p.id = r.cpse_id
                      WHERE m.cluster_id = c.id),
                   (SELECT min(r.short_text) FROM cluster_member m
                      JOIN material_record r ON r.id = m.record_id WHERE m.cluster_id = c.id),
                   t.updated_at
            {frm} LEFT JOIN app_user mk ON mk.id = t.made_by
            WHERE {w}
            ORDER BY c.priority DESC NULLS LAST, c.id LIMIT :limit OFFSET :offset
            """),  # noqa: S608
        args,
    ).all()
    items = [
        {"id": r[0], "category": r[1], "priority": float(r[2]) if r[2] is not None else None,
         "cohesion": float(r[3]) if r[3] is not None else None, "flags": r[4], "critical": r[5],
         "status": r[6], "state": r[7], "proposed": r[8], "made_by": r[9], "members": r[10],
         "cpses": list(r[11] or []), "sample_text": r[12], "updated_at": r[13]}
        for r in rows
    ]  # fmt: skip
    return int(total), items


def consent_queue(session: Session, steward: AppUser) -> list[dict[str, Any]]:
    """S18: tasks AWAITING_CONSENT that include the steward's CPSE and lack its answer."""
    rows = session.execute(
        text("""
            SELECT c.id, c.category, t.updated_at, mk.username, ck.username,
                   (SELECT count(*) FROM cluster_member m WHERE m.cluster_id = c.id),
                   (SELECT array_agg(r.legacy_code ORDER BY r.legacy_code) FROM cluster_member m
                      JOIN material_record r ON r.id = m.record_id
                      WHERE m.cluster_id = c.id AND r.cpse_id = :cpse),
                   (SELECT min(r.short_text) FROM cluster_member m
                      JOIN material_record r ON r.id = m.record_id WHERE m.cluster_id = c.id)
            FROM review_task t JOIN cluster c ON c.id = t.cluster_id
            LEFT JOIN app_user mk ON mk.id = t.made_by LEFT JOIN app_user ck ON ck.id = t.checked_by
            WHERE t.state = 'AWAITING_CONSENT'
              AND EXISTS (SELECT 1 FROM cluster_member m
                          JOIN material_record r ON r.id = m.record_id
                          WHERE m.cluster_id = c.id AND r.cpse_id = :cpse)
              AND NOT EXISTS (SELECT 1 FROM review_consent rc
                              WHERE rc.task_id = t.id AND rc.cpse_id = :cpse)
            ORDER BY t.updated_at, c.id
            """),
        {"cpse": steward.cpse_id},
    ).all()
    return [
        {"cluster_id": r[0], "category": r[1], "waiting_since": r[2], "proposed_by": r[3],
         "confirmed_by": r[4], "members": r[5], "my_codes": list(r[6] or []), "sample_text": r[7]}
        for r in rows
    ]  # fmt: skip


def cluster_detail(session: Session, user: AppUser, cluster_id: uuid.UUID) -> dict[str, Any]:
    cluster = session.get(Cluster, cluster_id)
    if cluster is None:
        raise NotFound("No such cluster.")
    task = _task(session, cluster_id)
    members = registry.members_of(session, cluster_id)
    cpses = registry.participants(members)
    consents = consent_rows(session, task.id)
    names = dict(session.execute(text("SELECT id, username FROM app_user")).all())
    pairs = session.execute(
        text("""
            SELECT p.id, p.rec_a, p.rec_b, p.verdict, p.route, p.p_equiv, p.text_sim, p.lookalike,
                   p.reasons, p.evidence
            FROM pair_decision p
            JOIN cluster_member a ON a.cluster_id = :c AND a.record_id = p.rec_a
            JOIN cluster_member b ON b.cluster_id = :c AND b.record_id = p.rec_b
            WHERE p.run_id = :run ORDER BY p.text_sim NULLS LAST
            """),
        {"c": cluster_id, "run": cluster.run_id},
    ).all()
    blocked = session.execute(
        text("""
            SELECT be.rec_a, be.rec_b, be.blocking_a, be.blocking_b, be.reason FROM blocked_edge be
            WHERE be.run_id = :run AND (be.rec_a IN (SELECT record_id FROM cluster_member
                  WHERE cluster_id = :c) OR be.rec_b IN (SELECT record_id FROM cluster_member
                  WHERE cluster_id = :c))
            """),
        {"c": cluster_id, "run": cluster.run_id},
    ).all()
    decisions = session.execute(
        text("""
            SELECT d.created_at, u.username, d.actor_role, d.decision, d.comment
            FROM review_decision d JOIN app_user u ON u.id = d.actor_id
            WHERE d.task_id = :t ORDER BY d.created_at
            """),
        {"t": task.id},
    ).all()
    issued = session.scalar(
        text("SELECT cnmc FROM cnmc WHERE source_cluster = :c ORDER BY issued_at DESC LIMIT 1"),
        {"c": cluster_id},
    )
    mapped = dict(
        session.execute(
            text("SELECT record_id, cnmc FROM crosswalk WHERE status = 'ACTIVE'"
                 " AND record_id = ANY(:ids)"),
            {"ids": [m.record_id for m in members]},
        ).all()
    )  # fmt: skip
    can = _abilities(user, task, cpses, consents)
    return {
        "id": cluster.id,
        "run_id": cluster.run_id,
        "category": cluster.category,
        "status": cluster.status,
        "priority": float(cluster.priority) if cluster.priority is not None else None,
        "cohesion": float(cluster.cohesion) if cluster.cohesion is not None else None,
        "flags": cluster.flags_count,
        "critical": cluster.is_critical,
        "task": {
            "id": task.id,
            "state": task.state,
            "proposed": task.proposed_decision,
            "made_by": names.get(task.made_by),
            "checked_by": names.get(task.checked_by),
        },
        "members": [
            {"record_id": m.record_id, "cpse": m.cpse_code, "legacy_code": m.legacy_code,
             "short_text": m.short_text, "long_text": m.long_text, "uom": m.uom,
             "manufacturer": m.manufacturer, "mpn": m.mpn,
             "annual_value": float(m.annual_value) if m.annual_value is not None else None,
             "stock_qty": float(m.stock_qty) if m.stock_qty is not None else None,
             "category": m.category, "attrs": m.attrs, "mapped_to": mapped.get(m.record_id)}
            for m in members
        ],  # fmt: skip
        "pairs": [
            {"id": r[0], "rec_a": r[1], "rec_b": r[2], "verdict": r[3], "route": r[4],
             "p_equiv": float(r[5]) if r[5] is not None else None,
             "text_sim": float(r[6]) if r[6] is not None else None, "lookalike": r[7],
             "reasons": list(r[8]), "evidence": r[9]}
            for r in pairs
        ],  # fmt: skip
        "blocked": [
            {"rec_a": r[0], "rec_b": r[1], "blocking_a": r[2], "blocking_b": r[3], "reason": r[4]}
            for r in blocked
        ],
        "consents": [
            {"cpse": code,
             "decision": consents[cid].decision if cid in consents else None,
             "via": consents[cid].via if cid in consents else None,
             "reason": consents[cid].reason if cid in consents else None,
             "by": names.get(consents[cid].user_id) if cid in consents else None}
            for cid, code in sorted(cpses.items(), key=lambda kv: kv[1])
        ],  # fmt: skip
        "decisions": [
            {"at": r[0], "by": r[1], "role": r[2], "decision": r[3], "comment": r[4]}
            for r in decisions
        ],
        "proposal": registry.proposal(members),
        "cnmc": issued,
        "can": can,
    }


def _abilities(
    user: AppUser, task: ReviewTask, cpses: dict[uuid.UUID, str], consents: dict[uuid.UUID, Any]
) -> dict[str, bool | str]:
    """What the signed-in user may do here, so the screen never offers a button the API refuses."""
    return {
        "propose": user.role == "MAKER" and task.state == "OPEN",
        "check": user.role == "CHECKER" and task.state == "MADE" and task.made_by != user.id,
        "waiting_for_other_checker": user.role == "CHECKER" and task.state == "MADE"
        and task.made_by == user.id,
        "consent": user.role == "CHECKER" and task.state == "AWAITING_CONSENT"
        and user.cpse_id in cpses and user.cpse_id not in consents,
    }  # fmt: skip
