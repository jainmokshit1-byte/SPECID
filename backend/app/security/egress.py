"""Egress guard (PRD 9.13.7, SF-7, FR-1461-1463; TRD TR-SEC-05, Appendix D T-S5).

Defence in depth for the air-gap claim: refuse every outbound connection and name lookup except
loopback, UNIX sockets and explicitly allowed hosts (the database, the local model server), and
count each refusal. The counter is a `multiprocessing.Value` shared with the job worker, so the
footer shows one number for the whole system.

Scope, stated plainly: libraries that open sockets in C (libpq inside psycopg) bypass this guard.
The real guarantee is the `internal: true` Compose network (no route to the internet); the guard
catches Python-level attempts and makes them visible.
"""

import ipaddress
import multiprocessing
import socket
from collections.abc import Callable, Iterable
from multiprocessing.sharedctypes import Synchronized
from typing import Any

# One "spawn" context for the guard counter and the job pool (see services/jobs.py).
MP_CONTEXT = multiprocessing.get_context("spawn")
blocked_counter: "Synchronized[int]" = MP_CONTEXT.Value("i", 0)  # type: ignore[assignment]


def _is_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class EgressGuard:
    def __init__(
        self,
        allowed: Iterable[str] = (),
        counter: "Synchronized[int] | None" = None,
    ) -> None:
        self.counter = counter if counter is not None else MP_CONTEXT.Value("i", 0)
        self.allowed = {a.lower() for a in allowed if a} | {"localhost"}
        self.installed = False
        self._orig: tuple[Callable[..., Any], Callable[..., Any], Callable[..., Any]] | None = None

    @property
    def blocked(self) -> int:
        return int(self.counter.value)

    def _resolve_allowed(self) -> None:
        """Add the addresses of allowed host names, looked up before the guard is installed."""
        for name in list(self.allowed):
            try:
                for info in socket.getaddrinfo(name, None):
                    self.allowed.add(str(info[4][0]).lower())
            except OSError:
                continue

    def check(self, host: object) -> None:
        if not isinstance(host, str):
            return  # None, bytes and AF_UNIX paths are not network hosts
        if _is_loopback(host) or host.lower() in self.allowed:
            return
        with self.counter.get_lock():
            self.counter.value += 1
        raise PermissionError(f"egress blocked: {host}")

    def install(self) -> None:
        if self.installed:
            return
        self._resolve_allowed()
        guard = self
        orig_connect, orig_connect_ex = socket.socket.connect, socket.socket.connect_ex
        orig_getaddrinfo = socket.getaddrinfo
        self._orig = (orig_connect, orig_connect_ex, orig_getaddrinfo)

        def connect(sock: socket.socket, address: Any) -> Any:
            if isinstance(address, tuple):
                guard.check(address[0])
            return orig_connect(sock, address)

        def connect_ex(sock: socket.socket, address: Any) -> Any:
            if isinstance(address, tuple):
                guard.check(address[0])
            return orig_connect_ex(sock, address)

        def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
            guard.check(host)
            return orig_getaddrinfo(host, *args, **kwargs)

        socket.socket.connect = connect  # type: ignore[method-assign,assignment]
        socket.socket.connect_ex = connect_ex  # type: ignore[method-assign,assignment]
        socket.getaddrinfo = getaddrinfo  # type: ignore[assignment]
        self.installed = True

    def uninstall(self) -> None:
        if not self.installed or self._orig is None:
            return
        orig_connect, orig_connect_ex, orig_getaddrinfo = self._orig
        socket.socket.connect = orig_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = orig_connect_ex  # type: ignore[method-assign]
        socket.getaddrinfo = orig_getaddrinfo
        self.installed = False


_guard: EgressGuard | None = None


def install_guard(
    allowed: Iterable[str], counter: "Synchronized[int] | None" = None
) -> EgressGuard:
    """Install the process-wide guard (called at API start and in every job worker)."""
    global _guard
    if _guard is None or not _guard.installed:
        _guard = EgressGuard(allowed, counter if counter is not None else blocked_counter)
        _guard.install()
    return _guard


def current_guard() -> EgressGuard | None:
    return _guard


def guard_installed() -> bool:
    return _guard is not None and _guard.installed


def blocked_attempts() -> int:
    return int(blocked_counter.value)
