"""Background execution of runs (TRD TR-MOD-30, TR-ARC-03).

One worker process (`ProcessPoolExecutor(max_workers=1)`, "spawn") runs one harmonisation at a
time; later runs wait in the pool's queue and show as QUEUED. The worker installs the egress
guard with the counter shared with the API and opens its own database engine, templates and
dictionary. Tests set `INLINE` to run the job in the calling thread.
"""

import uuid
from concurrent.futures import Future, ProcessPoolExecutor
from multiprocessing.sharedctypes import Synchronized
from typing import Any

import structlog
from sqlalchemy import text

from app.security.egress import MP_CONTEXT, blocked_counter

log = structlog.get_logger()

INLINE = False  # tests: run the job synchronously in the caller (same process, same database)
_pool: ProcessPoolExecutor | None = None
_worker: dict[str, Any] = {}


# ---- in the worker process ---------------------------------------------------------------
def worker_init(counter: "Synchronized[int]") -> None:
    """Runs once in the spawned worker: guard, logging, engine, templates (own copies)."""
    from app.core.templates import load_dictionary, load_templates
    from app.db.session import get_session_factory
    from app.main import configure_logging
    from app.security import egress
    from app.settings import get_settings

    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.egress_guard_enabled:
        egress.install_guard([settings.db_host, settings.ollama_host], counter)
    _worker.update(
        settings=settings,
        factory=get_session_factory(),
        templates=load_templates(settings.template_dir),
        dictionary=load_dictionary(settings.template_dir),
    )


def run_job(run_id: str) -> None:
    from app.services import harmonise

    harmonise.execute(
        _worker["factory"],
        uuid.UUID(run_id),
        templates=_worker["templates"],
        dictionary=_worker["dictionary"],
        settings=_worker["settings"],
    )


# ---- in the API process ------------------------------------------------------------------
def _executor() -> ProcessPoolExecutor:
    global _pool
    if _pool is None:
        _pool = ProcessPoolExecutor(
            max_workers=1,
            mp_context=MP_CONTEXT,
            initializer=worker_init,
            initargs=(blocked_counter,),
        )
    return _pool


def submit(run_id: uuid.UUID, templates: Any = None, dictionary: Any = None) -> Future[None] | None:
    """Queue a run. With `INLINE` it runs now, in this process, with the app's templates."""
    if INLINE:
        from app.db.session import get_session_factory
        from app.services import harmonise
        from app.settings import get_settings

        harmonise.execute(
            get_session_factory(),
            run_id,
            templates=templates,
            dictionary=dictionary,
            settings=get_settings(),
        )
        return None
    future = _executor().submit(run_job, str(run_id))
    future.add_done_callback(
        lambda f: f.exception() and log.error("job_crashed", error=repr(f.exception()))
    )
    return future


def shutdown() -> None:
    global _pool
    if _pool is not None:
        _pool.shutdown(wait=False, cancel_futures=True)
        _pool = None


def recover_interrupted(session: Any) -> int:
    """After a restart no job is running: mark runs left active as failed or cancelled."""
    rows = session.execute(
        text(
            "UPDATE run SET"
            " status = CASE WHEN status = 'CANCELLING' THEN 'CANCELLED' ELSE 'FAILED' END,"
            " error = CASE WHEN status = 'CANCELLING' THEN NULL"
            " ELSE 'interrupted by a restart of the server' END, finished_at = now()"
            " WHERE status IN ('QUEUED','RUNNING','CANCELLING') RETURNING id"
        )
    ).all()
    return len(rows)
