from __future__ import annotations

import random
import re
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
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
    """Raised to terminate a thread without waiting for it to exit naturally."""

    pass


class _RequestTask(NamedTuple):
    """A unit of work handed to the session worker thread: the URL, request kwargs, and a queue for the result."""

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
    5xx responses are retried in place with interruptable exponential backoff (see
    get_with_interrupt); an exhausted retry surfaces as a normal HTTPError.
    """

    def __init__(
        self,
        *,
        max_retries: int = 3,
        retry_backoff_base: float = 1.0,
        retry_backoff_cap: float = 30.0,
        **kwargs: Any,
    ) -> None:
        """Start the persistent worker thread; forwards kwargs to curl_cffi.Session.

        use_thread_local_curl is forced on so the worker thread gets its own curl handle,
        separate from the caller thread's handle that close() tears down; otherwise close()
        could touch a handle still in use by the worker.

        Args:
            max_retries (int): Number of additional attempts for 5xx responses (0 disables retrying).
            retry_backoff_base (float): Base for the full-jitter exponential backoff between retries (seconds).
            retry_backoff_cap (float): Upper bound on a single backoff wait, including Retry-After (seconds).
        """
        kwargs.pop("use_thread_local_curl", None)
        super().__init__(use_thread_local_curl=True, **kwargs)
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base
        self.retry_backoff_cap = retry_backoff_cap
        self._closed = False
        self._task_queue: Queue[Optional[_RequestTask]] = Queue()
        self._worker_thread = threading.Thread(target=self._worker_loop, name=f"session-worker-{id(self)}", daemon=True)
        self._worker_thread.start()

    @staticmethod
    def _log_response(response: curl_cffi.requests.Response) -> None:
        """Debug-log the request method, any redirect chain, the final status, and elapsed time."""
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
        """Pull tasks off the queue and run each request, returning the response or the raised error; exit on the None sentinel."""
        while True:
            task = self._task_queue.get()
            if task is None:
                return
            try:
                task.result_queue.put(self._follow_redirects(task.url, **task.kwargs))
            except Exception as error:
                task.result_queue.put(error)

    @staticmethod
    def _parse_retry_after(value: str) -> Optional[float]:
        """Parse a Retry-After header (delta-seconds or HTTP-date) into seconds from now, or None if unparseable."""
        value = value.strip()
        if value.isdigit():
            return float(value)
        try:
            # Raises TypeError (py<3.10) or ValueError (py>=3.10) on unparseable input.
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return max(0.0, (parsed - datetime.now(timezone.utc)).total_seconds())

    def _retry_backoff(self, response: curl_cffi.requests.Response, attempt: int) -> float:
        """Seconds to wait before retrying: a valid Retry-After (capped) if present, else full-jitter exponential backoff."""
        retry_after = response.headers.get("retry-after")
        if retry_after is not None and (parsed := self._parse_retry_after(retry_after)) is not None:
            return min(parsed, self.retry_backoff_cap)
        window = min(self.retry_backoff_cap, self.retry_backoff_base * 2**attempt)
        return random.uniform(0.0, window)

    @staticmethod
    def _sleep_with_interrupt(seconds: float, url: str) -> None:
        """Sleep up to `seconds`, waking every second to honor the stop event (raises CrashThread if set)."""
        deadline = time.monotonic() + seconds
        while (remaining := deadline - time.monotonic()) > 0:
            if __EVENTS__.is_event_set("stop"):
                logger.debug(f"Interrupt backoff before retrying {url!r}")
                raise CrashThread(f"Backoff before retrying {url} was interrupted by stop event")
            time.sleep(min(1.0, remaining))

    def _submit_and_wait(self, url: str, request_kwargs: Dict[str, Any]) -> curl_cffi.requests.Response:
        """Submit one request to the worker thread and block until a result, polling the stop event each second.

        Raises any exception the worker raised, or CrashThread if the stop event fires while waiting.
        """
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
                return response

    def get_with_interrupt(self, url: str, **kwargs: Any) -> curl_cffi.requests.Response:
        """Interruptable GET request with in-place 5xx retry.

        Submits the request to the persistent daemon thread and polls every second
        for a stop event. Raises CrashThread if interrupted. When impersonating a
        browser, kwargs are dropped so curl_cffi can apply the full browser
        fingerprint unmodified.

        A 5xx response is retried up to max_retries times with interruptable
        exponential backoff (honoring Retry-After); once retries are exhausted the
        status surfaces as a normal HTTPError via raise_for_status.
        """
        if self._closed:
            raise RuntimeError("Session is closed")
        request_kwargs: Dict[str, Any] = {} if self.impersonate else kwargs

        # Hand-rolled rather than curl_cffi's retry=/RetryStrategy: that only retries transport
        # exceptions (not 5xx), ignores Retry-After, and sleeps with a blocking time.sleep that the
        # stop event can't interrupt.
        for attempt in range(self.max_retries + 1):
            response = self._submit_and_wait(url, request_kwargs)
            self._log_response(response)
            if response.status_code >= 500 and attempt < self.max_retries:
                backoff = self._retry_backoff(response, attempt)
                logger.debug(
                    f"Server error {response.status_code} for {url!r}; "
                    f"retry {attempt + 1}/{self.max_retries} in {backoff:.2f}s"
                )
                self._sleep_with_interrupt(backoff, url)
                continue
            response.raise_for_status()
            return response

        # Unreachable: the loop either returns or raises on its final iteration.
        raise AssertionError("retry loop exited without returning")

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

    DEFAULT_SESSION_KWARGS: Dict[str, Any] = {
        "timeout": 30,
        "max_retries": 3,
        "retry_backoff_base": 1.0,
        "retry_backoff_cap": 30.0,
    }

    def __init__(self) -> None:
        """Initialize the per-thread session registry with the default session kwargs."""
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
