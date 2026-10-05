"""Run in a spawned process by test_egress.py: attempt one outbound connection."""

from multiprocessing.sharedctypes import Synchronized

from app.security.egress import EgressGuard


def attempt_outbound(counter: "Synchronized[int]") -> None:
    import socket

    guard = EgressGuard(allowed={"db"}, counter=counter)
    guard.install()
    try:
        socket.create_connection(("203.0.113.9", 80), timeout=1)
    except PermissionError:
        pass
    finally:
        guard.uninstall()
