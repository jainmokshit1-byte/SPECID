"""Hosted demo mode (DEC-42): one-click sign-in for the demo roles, and demo data prepared on
the first start so the public link never opens on an empty app.

Only active with `DEMO_MODE=true`. The data is synthetic (generator seed 7) and flagged as such
everywhere. Bootstrap = what a team would click: three CPSE files with purchase history,
ingest, one cross-CPSE run, three national codes through maker -> checker -> consent, and one
evaluation. It runs in a background thread; `/health` reports `demo_status`.
"""

import threading
import uuid
from typing import Any

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db.models import AppUser, Cpse, EvalRun, Run, UploadBatch
from app.db.session import get_session_factory
from app.eval.generator import GeneratorConfig, files, generate
from app.security import auth
from app.services import audit, harmonise, ingest, review
from app.services.errors import NotFound
from app.services.users import LoginResult

log = structlog.get_logger()
DEMO_USERS = ("meera", "arjun", "kavya", "admin", "auditor", "erp")
STATUS: dict[str, Any] = {"state": "off"}


def demo_login(session: Session, username: str, secret: str, expire_min: int) -> LoginResult:
    """Sign in a demo user without a password (demo mode only; audited like any login)."""
    if username not in DEMO_USERS:
        raise NotFound("Not a demo user.")
    user = session.scalar(select(AppUser).where(func.lower(AppUser.username) == username))
    if user is None or not user.is_active:
        raise NotFound("The demo users are not ready yet. Try again in a minute.")
    audit.record(
        session,
        actor_id=user.id,
        action="LOGIN_SUCCEEDED",
        object_type="app_user",
        object_id=str(user.id),
        after={"username": user.username, "via": "demo"},
    )
    token, exp = auth.create_token(secret, user.id, user.role, user.cpse_id, expire_min)
    return LoginResult(user=user, access_token=token, expires_at=exp)


def start_bootstrap(app_state: Any, settings: Any) -> None:
    STATUS["state"] = "preparing"
    threading.Thread(target=_bootstrap_safe, args=(app_state, settings), daemon=True).start()


def _bootstrap_safe(app_state: Any, settings: Any) -> None:
    try:
        if settings.classifier_enabled and getattr(app_state, "classifier", None) is None:
            from app.ai.classifier import default_classifier

            app_state.classifier = default_classifier(app_state.dictionary)
        bootstrap(app_state, settings)
        STATUS["state"] = "ready"
    except Exception as exc:  # the app keeps working; the status says why
        log.error("demo_bootstrap_failed", error=repr(exc))
        STATUS.update(state="failed", error=f"{type(exc).__name__}: {exc}")


def bootstrap(app_state: Any, settings: Any, n_entities: int | None = None) -> None:
    factory = get_session_factory()
    with factory() as s:
        from app.db.seed import SeedSettings, seed

        seed(s.connection(), SeedSettings())  # type: ignore[call-arg]
        s.execute(
            text("UPDATE app_user SET must_change_password = false" " WHERE username = ANY(:u)"),
            {"u": list(DEMO_USERS)},
        )
        s.commit()
        if s.scalar(select(func.count()).select_from(UploadBatch)):
            return  # already prepared (a restart keeps the data)
        admin = s.scalar(select(AppUser).where(AppUser.username == "admin"))
        assert admin is not None
        data = files(
            generate(GeneratorConfig(seed=7, n_entities=n_entities or settings.demo_entities))
        )
        batch_ids = []
        for c in "ABC":
            cpse = s.scalar(select(Cpse).where(Cpse.code == f"CPSE-{c}"))
            assert cpse is not None
            up = ingest.create_batch(
                s,
                admin,
                cpse=cpse,
                filename=f"cpse_{c}.csv",
                data=data[f"cpse_{c}.csv"],
                is_synthetic=True,
                dictionary=app_state.dictionary,
                upload_dir=settings.upload_dir,
            )
            ingest.save_mapping(s, admin, up.batch, up.suggested, settings.upload_dir)
            ingest.ingest_batch(
                s,
                admin,
                up.batch,
                dictionary=app_state.dictionary,
                templates=app_state.templates,
                threshold=settings.classifier_threshold,
                upload_dir=settings.upload_dir,
                model=getattr(app_state, "classifier", None),
            )
            ingest.ingest_procurement(
                s,
                admin,
                up.batch,
                filename=f"procurement_{c}.csv",
                data=data[f"procurement_{c}.csv"],
            )
            batch_ids.append(up.batch.id)
            s.commit()
        meera = s.scalar(select(AppUser).where(AppUser.username == "meera"))
        assert meera is not None
        run = harmonise.create_run(
            s,
            meera,
            batch_ids=batch_ids,
            mode="CROSS_CPSE",
            options={},
            settings=settings,
            templates=app_state.templates,
            dictionary=app_state.dictionary,
        )
        s.commit()
        run_id = run.id
    harmonise.execute(
        factory,
        run_id,
        templates=app_state.templates,
        dictionary=app_state.dictionary,
        settings=settings,
        classifier=getattr(app_state, "classifier", None),
    )
    _issue_examples(factory, run_id, settings)
    _evaluation(factory, app_state, n_entities or settings.demo_entities)


def _issue_examples(factory: Any, run_id: uuid.UUID, settings: Any, n: int = 3) -> None:
    """Three national codes through the full governance flow, so the registry is not empty."""
    with factory() as s:
        users = {u.username: u for u in s.scalars(select(AppUser))}
        run = s.get(Run, run_id)
        if run is None or run.status != "DONE":
            return
        _, items = review.queue(
            s,
            users["meera"],
            run_id=run_id,
            stage="to_propose",
            category=None,
            critical=None,
            limit=200,
            offset=0,
        )
        three = [i for i in items if len(i["cpses"]) == 3][:n]
        for item in three:
            cid = item["id"]
            review.propose(s, users["meera"], cid, "APPROVE", None)
            review.check(
                s, users["arjun"], cid, "CONFIRM", None, consent_mode=settings.consent_mode
            )
            out = review.answer_consent(
                s, users["kavya"], cid, "CONSENT", None, consent_mode=settings.consent_mode
            )
            log.info("demo_code_issued", cnmc=out["cnmc"])
        s.commit()


def _evaluation(factory: Any, app_state: Any, n_entities: int) -> None:
    from app.eval.runner import evaluate

    with factory() as s:
        admin = s.scalar(select(AppUser).where(AppUser.username == "admin"))
        assert admin is not None
        cfg = {"seed": 7, "n_entities": n_entities, "hard_negative_share": 0.5}
        e = EvalRun(kind="SYNTHETIC", seed=7, config=cfg, status="RUNNING", created_by=admin.id)
        s.add(e)
        s.commit()
        e.metrics = evaluate(
            templates=app_state.templates,
            dictionary=app_state.dictionary,
            classifier=getattr(app_state, "classifier", None),
            **cfg,
        )
        e.status = "DONE"
        s.commit()
