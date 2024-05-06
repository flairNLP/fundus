import threading
from contextlib import contextmanager
from typing import Iterator, Optional

import requests.adapters
from typing_extensions import Self

from fundus.logging import create_logger

logger = create_logger(__name__)

_default_header = {"user-agent": "Fundus"}


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

    def __init__(self, pool_connections: int = 50, pool_maxsize: int = 1):
        self.session: Optional[requests.Session] = None
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize
        self.lock = threading.Lock()

    def _session_factory(self) -> requests.Session:
        """Builds a new Session

        This returns a new client session build from pre-defined configurations:
        - pool_connections: <self.pool_connections>
        - pool_maxsize: <self.pool_maxsize>
        - hooks: (1) Hook to raise an `HTTPError` if one occurred. (2) Hook to log the request responses.

        Returns:
            A new requests.Session
        """

        logger.debug("Creating new session")
        session = requests.Session()

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
            requests.adapters.HTTPAdapter(pool_connections=self.pool_connections, pool_maxsize=self.pool_maxsize),
        )
        session.mount(
            "https://",
            requests.adapters.HTTPAdapter(pool_connections=self.pool_connections, pool_maxsize=self.pool_maxsize),
        )

        return session

    def get_session(self) -> requests.Session:
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

    @contextmanager
    def context(self, pool_connections: int, pool_maxsize: int) -> Iterator[Self]:
        """Context manager to temporarily overwrite parameter and build a new session.

        Args:
            pool_connections: see requests.Session documentation.
            pool_maxsize: see requests.Session documentation.

        Returns:
            SessionHandler: The session handler instance.
        """
        previous_pool_connections = self.pool_connections
        previous_pool_maxsize = self.pool_maxsize

        self.close_current_session()

        try:
            self.pool_connections = pool_connections
            self.pool_maxsize = pool_maxsize
            yield self
        finally:
            self.pool_connections = previous_pool_connections
            self.pool_maxsize = previous_pool_maxsize


session_handler = SessionHandler()
