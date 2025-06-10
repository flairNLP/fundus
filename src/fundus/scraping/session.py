import socket
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Optional, Union

import requests.adapters

from fundus.logging import create_logger
from fundus.utils.events import __EVENTS__

logger = create_logger(__name__)

_default_header = {"user-agent": "Fundus"}


class InterruptableSession(requests.Session):
    def __init__(self, timeout: Optional[int] = None):
        super().__init__()
        self.timeout = timeout

    def get_with_interrupt(self, *args, **kwargs) -> requests.Response:
        """Interruptable request.

        This function hands over the request to another thread and checks every second
        for an interrupt event. If there was an interrupt event, this function raises
        a requests.exceptions.Timeout error.

        Args:
            *args: requests.Session.get(*) arguments.
            **kwargs: requests.Session.get(**) keyword arguments.

        Returns:
            The response.
        """

        def _req():
            try:
                response_queue.put(self.get(*args, **kwargs, timeout=self.timeout))
            except Exception as error:
                response_queue.put(error)

        if args:
            url = args[0]
        else:
            url = kwargs.get("url")

        response_queue: Queue[Union[requests.Response, Exception]] = Queue()
        thread = threading.Thread(target=_req, daemon=True)
        thread.start()

        while True:
            try:
                response = response_queue.get(timeout=1)
            except Empty:
                if __EVENTS__.is_event_set("stop"):
                    logger.debug(f"Interrupt request for {url!r}")
                    response_queue.task_done()
                    exit(1)
            else:
                if isinstance(response, Exception):
                    raise response
                return response


@dataclass
class CONFIG:
    POOL_CONNECTIONS: int = 50
    POOL_MAXSIZE: int = 1
    TIMEOUT: Optional[int] = 30


class SessionHandler:
    """Object for handling project global request.Session

    The session life cycle consists of three steps which can be repeated indefinitely:
    Build, Supply, Teardown.
    Initially there is no session build within the session handler. When a session is requested
    with get_session() either a new one is created with _session_factory() or the session handler's
    existing one returned. Every subsequent call to get_session() will return the same
    response.Session object. If close_current_session() is called, the current session will be
    tear-downed and the next call to get_session() will build a new session.
    """

    CONFIG: CONFIG = CONFIG()

    def __init__(self):
        self.session: Optional[InterruptableSession] = None
        self.lock = threading.Lock()

    def _session_factory(self) -> InterruptableSession:
        """Builds a new Session

        This returns a new client session build from pre-defined configurations:
        - pool_connections: <self.pool_connections>
        - pool_maxsize: <self.pool_maxsize>
        - hooks: (1) Hook to raise an `HTTPError` if one occurred. (2) Hook to log the request responses.

        Returns:
            A new requests.Session
        """

        logger.debug("Creating new session")
        session = InterruptableSession(timeout=self.CONFIG.TIMEOUT)

        def _response_log(response: requests.Response, *args, **kwargs) -> None:
            history = response.history
            previous_status_codes = [f"({response.status_code})" for response in history] if history else []
            status_code_chain = " -> ".join(previous_status_codes + [f"({response.status_code})"])
            logger.debug(
                f"{status_code_chain} <{response.request.method} {response.url!r}> "
                f"took {response.elapsed.total_seconds()} second(s)"
            )

        # hooks
        response_hooks = [lambda response, *args, **kwargs: response.raise_for_status(), _response_log]
        session.hooks["response"].extend(response_hooks)

        # adapters
        session.mount(
            "http://",
            requests.adapters.HTTPAdapter(
                pool_connections=self.CONFIG.POOL_CONNECTIONS, pool_maxsize=self.CONFIG.POOL_MAXSIZE
            ),
        )
        session.mount(
            "https://",
            requests.adapters.HTTPAdapter(
                pool_connections=self.CONFIG.POOL_CONNECTIONS, pool_maxsize=self.CONFIG.POOL_MAXSIZE
            ),
        )

        return session

    def get_session(self) -> InterruptableSession:
        """Requests the current build session

        If called for the first time or after close_current_session was called,
        this function will build a new session. Every subsequent call will return
        the same session object until the session is closed with close_current_session().

        Returns:
            requests.Session: The current build session
        """

        with self.lock:
            if not self.session:
                self.session = self._session_factory()
            return self.session

    def close_current_session(self) -> None:
        """Tears down the current build session

        Returns:
            None
        """
        if self.session is not None:
            session = self.get_session()
            logger.debug(f"Close session {session}")
            session.close()
            self.session = None

    @classmethod
    @contextmanager
    def context(cls, **kwargs):
        """Context manager to temporarily overwrite session parameters.

        Returns:
            SessionHandler: The session handler instance.
        """

        cls.CONFIG = CONFIG(**kwargs)

        try:
            yield cls
        finally:
            cls.CONFIG = CONFIG()


@contextmanager
def socket_timeout(timeout: Optional[int] = None):
    """Temporarily sets the socket timeout within this context."""
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        yield
    finally:
        socket.setdefaulttimeout(old_timeout)


session_handler = SessionHandler()
