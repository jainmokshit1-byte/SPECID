"""TR-TST-12: core/ is pure (TRD TR-ARC-10, CLAUDE.md hard rule 1).

Parses every module under app/core and fails if it imports a service, API, DB or other app layer,
a database or web framework, or a network library.
"""

import ast
from pathlib import Path

CORE = Path(__file__).resolve().parents[2] / "app" / "core"
FORBIDDEN = (
    # TR-TST-12
    "app.services",
    "app.api",
    "app.db",
    "sqlalchemy",
    "psycopg",
    "fastapi",
    # the other app layers sit above core/
    "app.security",
    "app.eval",
    "app.schemas",
    "app.main",
    "app.settings",
    "app.cli",
    # I/O libraries (TR-ARC-10)
    "socket",
    "http",
    "urllib",
    "requests",
    "httpx",
    "subprocess",
    "starlette",
)


def imported_modules(source: str, module: str) -> set[str]:
    """Absolute names of everything `source` imports; `module` resolves relative imports."""
    names: set[str] = set()
    package = module.rsplit(".", 1)[0]
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")
                base = base[: len(base) - (node.level - 1)]
                prefix = ".".join(base + ([node.module] if node.module else []))
            else:
                prefix = node.module or ""
            names.add(prefix)
            names |= {f"{prefix}.{a.name}" for a in node.names}
    return names


def violations(source: str, module: str) -> list[str]:
    return sorted(
        n
        for n in imported_modules(source, module)
        if any(n == f or n.startswith(f + ".") for f in FORBIDDEN)
    )


def test_core_imports_nothing_forbidden() -> None:
    files = sorted(CORE.rglob("*.py"))
    assert files, "app/core has no modules"
    found = {}
    for f in files:
        module = "app." + ".".join(f.relative_to(CORE.parent).with_suffix("").parts[1:])
        bad = violations(f.read_text("utf-8"), module)
        if bad:
            found[str(f.relative_to(CORE.parent))] = bad
    assert not found, found


def test_checker_catches_planted_imports() -> None:
    planted = (
        "import sqlalchemy\n"
        "from fastapi import FastAPI\n"
        "from app.services.audit import record\n"
        "from ..db import models\n"
        "import socket\n"
        "from . import units\n"
        "import re\n"
    )
    assert violations(planted, "app.core.decide") == [
        "app.db",
        "app.db.models",
        "app.services.audit",
        "app.services.audit.record",
        "fastapi",
        "fastapi.FastAPI",
        "socket",
        "sqlalchemy",
    ]
