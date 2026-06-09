from __future__ import annotations

import re
import threading
from contextlib import contextmanager
from queue import Empty, Queue
from typing import Any, Dict, Iterator, List, NamedTuple, Optional, Union
from urllib.parse import urljoin

import chardet
import curl_cffi.requests
from curl_cffi.requests import BrowserTypeLiteral
from curl_cffi.requests.exceptions import HTTPError, TooManyRedirects
from typing_extensions import Self

from fundus.logging import create_logger
from fundus.utils.events import __EVENTS__

logger = create_logger(__name__)

_default_header = {"user-agent": "Fundus/2.0 (contact: github.com/flairnlp/fundus)"}
_charset_re = re.compile(rb"charset\s*=\s*[\"']?\s*([^\"'\s;>]+)", re.IGNORECASE)


class CrashThread(BaseException):
    """Is raised to end a thread without relying on the thread ending naturally"""

    pass


class _RequestTask(NamedTuple):
    url: str
    kwargs: Any
    result_queue: Queue[Union[curl_cffi.requests.Response, Exception]]


def _detect_encoding_from_html(response: bytes) -> Optional[str]:
    """Extract the charset declared in an HTML meta tag, scanning only the first 2048 bytes."""
    if match := _charset_re.search(response[:2048]):
        return match.group(1).decode("ascii", errors="replace")
    return None


def _detect_encoding_from_bytes(response: bytes) -> str:
    """Detect the character encoding of an HTML response.

    Checks the HTML meta charset tag first, then falls back to chardet,
    then to UTF-8 if neither yields a result.

    Args:
        response: Raw response bytes to detect encoding for.

    Returns:
        Detected encoding string, guaranteed non-empty.
    """
    if encoding := _detect_encoding_from_html(response):
        logger.debug(f"Detected encoding from HTML: {encoding!r}")
    elif encoding := chardet.detect(response)["encoding"]:
        logger.debug(f"Detected encoding from chardet: {encoding!r}")
    else:
        logger.debug("Unable to detect encoding from response. Defaulting to <utf-8>")
    # see https://github.com/flairNLP/fundus/issues/446
    return encoding or "utf-8"


class InterruptableSession(curl_cffi.requests.Session[curl_cffi.requests.Response]):
    """Extends curl_cffi Session with interruptable requests via a persistent daemon thread.

    The daemon thread owns the curl handle for the lifetime of the session, enabling
    connection reuse across requests. get_with_interrupt() submits work to the daemon
    thread and polls for a stop event every second, raising CrashThread if interrupted.
    """

    def __init__(self, **kwargs: Any) -> None:
        # use_thread_local_curl=True gives the worker thread its own curl handle, separate
        # from the caller thread's handle closed in close(). Prevents close() from touching
        # a handle that may still be in use by the worker.
        kwargs.pop("use_thread_local_curl", None)
        super().__init__(use_thread_local_curl=True, **kwargs)
        self._closed = False
        self._task_queue: Queue[Optional[_RequestTask]] = Queue()
        self._worker_thread = threading.Thread(target=self._worker_loop, name=f"session-worker-{id(self)}", daemon=True)
        self._worker_thread.start()

    @staticmethod
    def _log_response(response: curl_cffi.requests.Response) -> None:
        history: List[curl_cffi.requests.Response] = object.__getattribute__(response, "_history")
        method = getattr(getattr(response, "request", None), "method", "GET")
        if history:
            hops = f"{history[0].url} → " + " → ".join(
                f"{r.status_code} {next_r.url}" for r, next_r in zip(history, history[1:] + [response])
            )
            chain = f"{method} {hops} → {response.status_code}"
        else:
            chain = f"{method} {response.url} -> {response.status_code}"
        logger.debug(f"{chain} ({response.elapsed}s)")

    def _follow_redirects(self, url: str, **kwargs: Any) -> curl_cffi.requests.Response:
        """Follow redirects manually, building a response history."""
        history: List[curl_cffi.requests.Response] = []
        current = url

        for _ in range(self.max_redirects):
            response: curl_cffi.requests.Response = self.get(current, **kwargs, allow_redirects=False)

            if not (300 <= response.status_code <= 399):
                object.__setattr__(response, "_history", history)
                return response

            location = response.headers.get("location")
            if not location:
                raise HTTPError(f"Redirect {response.status_code} from {current!r} missing Location header")

            history.append(response)
            current = urljoin(str(response.url), location)

        raise TooManyRedirects(f"Exceeded {self.max_redirects} maximum redirects following {url!r}")

    def _worker_loop(self) -> None:
        while True:
            task = self._task_queue.get()
            if task is None:
                return
            try:
                task.result_queue.put(self._follow_redirects(task.url, **task.kwargs))
            except Exception as error:
                task.result_queue.put(error)

    def get_with_interrupt(self, url: str, **kwargs: Any) -> curl_cffi.requests.Response:
        """Interruptable GET request.

        Submits the request to the persistent daemon thread and polls every second
        for a stop event. Raises CrashThread if interrupted. When impersonating a
        browser, kwargs are dropped so curl_cffi can apply the full browser
        fingerprint unmodified.
        """
        if self._closed:
            raise RuntimeError("Session is closed")
        request_kwargs: Dict[str, Any] = {} if self.impersonate else kwargs
        response_queue: Queue[Union[curl_cffi.requests.Response, Exception]] = Queue()
        self._task_queue.put(_RequestTask(url, request_kwargs, response_queue))

        while True:
            try:
                response = response_queue.get(timeout=1)
            except Empty:
                if __EVENTS__.is_event_set("stop"):
                    logger.debug(f"Interrupt request for {url!r}")
                    raise CrashThread(f"Request to {url} was interrupted by stop event")
            else:
                if isinstance(response, Exception):
                    raise response
                self._log_response(response)
                response.raise_for_status()
                return response

    def close(self) -> None:
        """Signal the worker thread to exit and close this thread's curl handle.

        Sending the sentinel is non-blocking — the daemon thread exits asynchronously
        after finishing any in-flight request. Safe to call while a request is in flight.
        """
        self._closed = True
        self._task_queue.put(None)
        super().close()


class SessionHandler:
    """Manages one InterruptableSession per thread via a thread-id registry.

    Each thread gets its own session instance backed by a persistent daemon thread,
    enabling connection reuse within a thread. Sessions are created lazily on first use.
    If get_session() is called with a different impersonate profile than the existing
    session, the old session is closed and replaced.
    """

    DEFAULT_SESSION_KWARGS: Dict[str, Any] = {"timeout": 30}

    def __init__(self) -> None:
        self._session_kwargs: Dict[str, Any] = dict(self.DEFAULT_SESSION_KWARGS)
        self._context_lock = threading.RLock()
        self._sessions: Dict[int, InterruptableSession] = {}

    def get_session(self, impersonate: Optional[BrowserTypeLiteral] = None) -> InterruptableSession:
        """Return the session for the current thread, creating it lazily if needed.

        If the existing session was created with a different impersonate profile,
        it is closed and replaced with a fresh one matching the requested profile.
        """
        tid = threading.get_ident()
        session = self._sessions.get(tid)

        if session is not None and session.impersonate != impersonate:
            logger.debug(f"Replacing session in thread-{tid} (impersonate={session.impersonate!r} → {impersonate!r})")
            session.close()
            session = None
        if session is None:
            session = InterruptableSession(
                impersonate=impersonate,
                default_encoding=_detect_encoding_from_bytes,
                **self._session_kwargs,
            )
            self._sessions[tid] = session
        return session

    def close_sessions(self) -> None:
        """Closes and removes all open sessions."""
        sessions, self._sessions = self._sessions, {}
        for tid, session in sessions.items():
            logger.debug(f"Close session in thread-{tid} (impersonate={session.impersonate!r})")
            session.close()

    @contextmanager
    def context(self, **kwargs: Any) -> Iterator[Self]:
        """Context manager for temporarily overriding session kwargs.

        Merges kwargs with the defaults for the duration of the block, then
        restores the previous state on exit. Only one context may be active at a time.

        Args:
            **kwargs: Any curl_cffi Session kwargs to override (e.g. timeout=10, verify=False).

        Raises:
            AssertionError: If a context is already active.
        """
        if not self._context_lock.acquire(blocking=False):
            raise AssertionError(
                "Tried to open a session context while another is already active. "
                "Exit the existing context before opening a new one."
            )

        prev_kwargs = self._session_kwargs
        prev_sessions = self._sessions
        self._session_kwargs = {**self.DEFAULT_SESSION_KWARGS, **kwargs}
        self._sessions = {}

        try:
            yield self
        finally:
            self.close_sessions()
            self._session_kwargs = prev_kwargs
            self._sessions = prev_sessions
            self._context_lock.release()


session_handler = SessionHandler()
