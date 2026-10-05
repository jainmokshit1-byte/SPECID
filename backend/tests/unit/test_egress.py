"""FR-1461-1463, TR-SEC-05, T-S5 (PRD Appendix D section 8): the egress guard blocks and counts."""

import socket
import threading

import pytest

from app.security.egress import MP_CONTEXT, EgressGuard
from tests.unit.egress_child import attempt_outbound


@pytest.fixture
def guard():  # type: ignore[no-untyped-def]
    g = EgressGuard(allowed={"db"})
    g.install()
    try:
        yield g
    finally:
        g.uninstall()


def test_outbound_connections_and_lookups_are_blocked_and_counted(guard: EgressGuard) -> None:
    with pytest.raises(PermissionError):
        socket.create_connection(("203.0.113.1", 80), timeout=1)  # TEST-NET-3: never routable
    with pytest.raises(PermissionError):
        socket.getaddrinfo("example.com", 80)
    assert guard.blocked == 2


def test_loopback_and_unix_sockets_are_allowed(guard: EgressGuard, tmp_path) -> None:  # type: ignore[no-untyped-def]
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    threading.Thread(target=lambda: srv.accept()[0].close(), daemon=True).start()
    socket.create_connection(("127.0.0.1", srv.getsockname()[1]), timeout=1).close()
    socket.getaddrinfo("localhost", 80)
    srv.close()
    path = str(tmp_path / "s.sock")
    unix = socket.socket(socket.AF_UNIX)
    unix.bind(path)
    unix.listen(1)
    threading.Thread(target=lambda: unix.accept()[0].close(), daemon=True).start()
    c = socket.socket(socket.AF_UNIX)
    c.connect(path)
    c.close()
    unix.close()
    assert guard.blocked == 0


def test_allowed_hosts_pass(guard: EgressGuard) -> None:
    guard.check("db")
    guard.check("DB")
    assert guard.blocked == 0
    with pytest.raises(PermissionError):
        guard.check("db.example.org")
    assert guard.blocked == 1


def test_uninstall_restores_the_socket_functions() -> None:
    before = (socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo)
    g = EgressGuard()
    g.install()
    assert socket.getaddrinfo is not before[2]
    g.uninstall()
    assert (socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo) == before
    assert not g.installed


def test_the_counter_is_shared_with_a_worker_process() -> None:
    """The job worker (spawned) adds to the same counter the API reports."""
    counter = MP_CONTEXT.Value("i", 0)
    proc = MP_CONTEXT.Process(target=attempt_outbound, args=(counter,))
    proc.start()
    proc.join(timeout=60)
    assert proc.exitcode == 0
    assert counter.value == 1
