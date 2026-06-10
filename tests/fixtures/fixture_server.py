"""Pytest fixtures providing real loopback servers for timeout integration tests.

These let a test drive a genuine curl_cffi timeout through the stack instead of feeding
a hand-picked exception class to a mocked session — the only way to confirm the code
catches the exception curl_cffi actually raises.
"""

import socket
import threading
from typing import Iterator, List

import pytest


@pytest.fixture
def hanging_url() -> Iterator[str]:
    """Yield a URL whose server accepts the TCP connection but never sends a response.

    A request to it connects fine but then times out reading, so the caller sees the
    real curl_cffi timeout exception. Bound on an ephemeral loopback port; torn down
    after the test.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    accepted: List[socket.socket] = []  # hold connections open so the peer isn't reset

    def accept_and_hang() -> None:
        while True:
            try:
                connection, _ = server.accept()
            except OSError:
                return
            accepted.append(connection)

    worker = threading.Thread(target=accept_and_hang, daemon=True)
    worker.start()
    host, port = server.getsockname()
    try:
        yield f"http://{host}:{port}/"
    finally:
        server.close()
        for connection in accepted:
            connection.close()
        worker.join(timeout=1)
