import threading
import time
from queue import Queue
from threading import Thread
from typing import Union
from unittest.mock import MagicMock, patch

import curl_cffi
import pytest
from curl_cffi.requests.exceptions import HTTPError, TooManyRedirects

from fundus.scraping.session import (
    CrashThread,
    InterruptableSession,
    SessionHandler,
    _RequestTask,
)
from fundus.utils.events import __EVENTS__
from tests.exceptions import Success


def _mock_response(status_code: int = 200) -> MagicMock:
    """Build a mock curl_cffi response that satisfies InterruptableSession._log_response."""
    response = MagicMock()
    response._history = []  # object.__getattribute__ reads directly from __dict__
    response.status_code = status_code
    response.url = "https://example.com"
    response.elapsed = 0.01
    response.request = None
    response.raise_for_status = MagicMock()
    return response


class TestContext:
    def test_config_override(self):
        session_handler = SessionHandler()
        prev = session_handler._session_kwargs

        with session_handler.context(timeout=-9999):
            assert session_handler._session_kwargs != prev
            assert session_handler._session_kwargs["timeout"] == -9999

        assert session_handler._session_kwargs == prev

    def test_new_session(self):
        session_handler = SessionHandler()

        prev = session_handler.get_session()

        with session_handler.context():
            assert session_handler.get_session() != prev

        assert session_handler.get_session() == prev

    def test_nested_context(self):
        session_handler = SessionHandler()

        with session_handler.context(timeout=1):
            with session_handler.context(timeout=2):
                assert session_handler.get_session().timeout == 2

            assert session_handler.get_session().timeout == 1

        assert session_handler.get_session().timeout == SessionHandler.DEFAULT_SESSION_KWARGS["timeout"]

    def test_thread_safety(self):
        session_handler = SessionHandler()

        def set_context(timeout: int = 100):
            with pytest.raises(Success):
                with session_handler.context(timeout=timeout):
                    assert session_handler.get_session().timeout == timeout
                    raise Success

        def set_context_fail():
            with pytest.raises(AssertionError):
                set_context()

        prev = session_handler.get_session()

        # 1. test if we can open a context in another thread
        thread = Thread(target=set_context, args=(11,))
        thread.start()
        thread.join()

        # 2. test if previous context where restored correctly
        assert session_handler.get_session() == prev

        # 3. open new context
        with session_handler.context(timeout=12):
            # 4. the thread should raise an AssertionError
            thread = Thread(target=set_context_fail)
            thread.start()
            thread.join()

            # 5. test if the session handler still resets
            assert session_handler.get_session().timeout == 12

        # 6. test if the context is closed properly
        thread = Thread(target=set_context, args=(13,))
        thread.start()
        thread.join()

    def test_context_resets_other_threads_sessions(self):
        """Other threads get a fresh session inside a context, not their pre-context session."""
        session_handler = SessionHandler()
        pre_context_session = None
        inside_context_session = None
        ready = threading.Event()
        entered = threading.Event()
        sampled = threading.Event()

        def worker():
            nonlocal pre_context_session, inside_context_session
            pre_context_session = session_handler.get_session()
            ready.set()
            assert entered.wait(5)
            inside_context_session = session_handler.get_session()
            sampled.set()

        t = Thread(target=worker)
        t.start()
        assert ready.wait(5)

        with session_handler.context(timeout=9999):
            entered.set()
            assert sampled.wait(5)

        t.join()

        assert inside_context_session is not None
        assert inside_context_session is not pre_context_session
        assert inside_context_session.timeout == 9999

    def test_context_restores_other_threads_sessions(self):
        """After the context exits, other threads get back their original session."""
        session_handler = SessionHandler()
        pre_context_session = None
        post_context_session = None
        entered = threading.Event()
        exited = threading.Event()

        def worker():
            nonlocal pre_context_session, post_context_session
            pre_context_session = session_handler.get_session()
            entered.set()
            assert exited.wait(5)
            post_context_session = session_handler.get_session()

        t = Thread(target=worker)
        t.start()
        assert entered.wait(5)

        with session_handler.context(timeout=9999):
            pass

        exited.set()
        t.join()

        assert post_context_session is pre_context_session


class TestInterruptableSession:
    def test_worker_thread_starts_on_init(self):
        session = InterruptableSession()
        assert session._worker_thread.is_alive()
        session.close()

    def test_worker_thread_is_daemon(self):
        session = InterruptableSession()
        assert session._worker_thread.daemon
        session.close()

    def test_worker_thread_exits_after_close(self):
        session = InterruptableSession()
        session.close()
        session._worker_thread.join(timeout=2)
        assert not session._worker_thread.is_alive()

    def test_close_is_nonblocking(self):
        """close() returns immediately even when a request is in flight."""
        session = InterruptableSession()
        inside_request = threading.Event()
        allow_return = threading.Event()

        def slow_follow_redirects(url, **kwargs):
            inside_request.set()
            allow_return.wait(timeout=5)

        with patch.object(session, "_follow_redirects", side_effect=slow_follow_redirects):
            result_queue: Queue[Union[curl_cffi.requests.Response, Exception]] = Queue()
            session._task_queue.put(_RequestTask("http://example.com", {}, result_queue))
            assert inside_request.wait(5)

            start = time.monotonic()
            session.close()
            assert time.monotonic() - start < 1.0

        allow_return.set()
        session._worker_thread.join(timeout=2)

    def test_request_runs_on_worker_thread(self):
        """_follow_redirects executes on the worker thread, not the caller thread."""
        session = InterruptableSession()
        caller_thread_id = threading.current_thread().ident
        captured_thread_id = None

        def capture_thread(url, **kwargs):
            nonlocal captured_thread_id
            captured_thread_id = threading.current_thread().ident
            return _mock_response()

        with patch.object(session, "_follow_redirects", side_effect=capture_thread):
            session.get_with_interrupt("http://example.com")

        assert captured_thread_id is not None
        assert captured_thread_id != caller_thread_id
        assert captured_thread_id == session._worker_thread.ident
        session.close()

    def test_same_worker_thread_handles_all_requests(self):
        """All requests go through the same persistent worker thread, enabling connection reuse."""
        session = InterruptableSession()
        captured_thread_ids = []

        def capture_thread(url, **kwargs):
            captured_thread_ids.append(threading.current_thread().ident)
            return _mock_response()

        with patch.object(session, "_follow_redirects", side_effect=capture_thread):
            for _ in range(3):
                session.get_with_interrupt("http://example.com")

        assert len(set(captured_thread_ids)) == 1
        assert captured_thread_ids[0] == session._worker_thread.ident
        session.close()

    def test_response_returned_to_caller(self):
        session = InterruptableSession()
        mock = _mock_response(status_code=200)

        with patch.object(session, "_follow_redirects", return_value=mock):
            response = session.get_with_interrupt("http://example.com")

        assert response is mock
        session.close()

    def test_exception_propagates_to_caller(self):
        """Exceptions raised in the worker thread are re-raised in the caller thread."""
        session = InterruptableSession()

        with patch.object(session, "_follow_redirects", side_effect=ConnectionError("unreachable")):
            with pytest.raises(ConnectionError, match="unreachable"):
                session.get_with_interrupt("http://example.com")

        session.close()

    def test_crash_thread_on_stop_event(self):
        """CrashThread is raised in the caller when the stop event fires while polling."""
        session = InterruptableSession()
        inside_request = threading.Event()
        allow_return = threading.Event()

        def slow_follow_redirects(url, **kwargs):
            inside_request.set()
            allow_return.wait(timeout=5)

        def set_stop():
            assert inside_request.wait(5)
            __EVENTS__.set_event("stop", "test-stop-event")

        stopper = Thread(target=set_stop, daemon=True)

        with patch.object(session, "_follow_redirects", side_effect=slow_follow_redirects):
            stopper.start()
            with __EVENTS__.context("test-stop-event"):
                with pytest.raises(CrashThread):
                    session.get_with_interrupt("http://example.com")

        stopper.join(timeout=2)
        allow_return.set()
        session.close()

    def test_use_thread_local_curl_always_true(self):
        """use_thread_local_curl=True is enforced regardless of what kwargs pass."""
        session = InterruptableSession(use_thread_local_curl=False)
        assert session._use_thread_local_curl is True
        session.close()

    def test_kwargs_forwarded_to_curl_session(self):
        session = InterruptableSession(timeout=42, verify=False)
        assert session.timeout == 42
        assert session.verify is False
        session.close()

    def test_impersonate_drops_kwargs_before_dispatch(self):
        """When impersonating, get_with_interrupt strips caller kwargs so curl_cffi's fingerprint is unmodified."""
        session = InterruptableSession(impersonate="chrome")
        final = _mock_response()
        captured_kwargs = []

        def capturing_follow(url, **kwargs):
            captured_kwargs.append(kwargs)
            return final

        with patch.object(session, "_follow_redirects", side_effect=capturing_follow):
            session.get_with_interrupt("http://example.com", headers={"x-custom": "value"})

        assert captured_kwargs[0] == {}
        session.close()

    def test_no_impersonate_forwards_kwargs(self):
        session = InterruptableSession()
        final = _mock_response()
        captured_kwargs = []

        def capturing_follow(url, **kwargs):
            captured_kwargs.append(kwargs)
            return final

        with patch.object(session, "_follow_redirects", side_effect=capturing_follow):
            session.get_with_interrupt("http://example.com", headers={"x-custom": "value"})

        assert captured_kwargs[0] == {"headers": {"x-custom": "value"}}
        session.close()

    def test_raise_for_status_propagates(self):
        session = InterruptableSession()
        mock = _mock_response(status_code=404)
        mock.raise_for_status.side_effect = HTTPError("404")

        with patch.object(session, "_follow_redirects", return_value=mock):
            with pytest.raises(HTTPError):
                session.get_with_interrupt("http://example.com")

        session.close()


def _redirect_response(status_code: int, location: str) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.headers = MagicMock()
    response.headers.get = MagicMock(return_value=location)
    response.url = "http://example.com"
    return response


class TestFollowRedirects:
    def test_no_redirect_returns_response_with_empty_history(self):
        session = InterruptableSession()
        final = _mock_response()

        with patch.object(session, "get", return_value=final):
            result = session._follow_redirects("http://example.com", headers={"x": "y"})

        assert result is final
        assert object.__getattribute__(result, "_history") == []
        session.close()

    def test_redirect_chain_builds_history(self):
        session = InterruptableSession()
        r1 = _redirect_response(301, "http://example.com/step2")
        r2 = _redirect_response(302, "http://example.com/final")
        final = _mock_response()

        with patch.object(session, "get", side_effect=[r1, r2, final]):
            result = session._follow_redirects("http://example.com")

        assert result is final
        assert object.__getattribute__(result, "_history") == [r1, r2]
        session.close()

    def test_redirect_chain_follows_location_urls(self):
        session = InterruptableSession()
        r1 = _redirect_response(301, "http://example.com/step2")
        final = _mock_response()
        captured_urls = []

        def capturing_get(url, **kwargs):
            captured_urls.append(url)
            return r1 if url == "http://example.com" else final

        with patch.object(session, "get", side_effect=capturing_get):
            session._follow_redirects("http://example.com")

        assert captured_urls == ["http://example.com", "http://example.com/step2"]
        session.close()

    def test_missing_location_header_raises_http_error(self):
        session = InterruptableSession()
        redirect = MagicMock()
        redirect.status_code = 301
        redirect.headers = MagicMock()
        redirect.headers.get = MagicMock(return_value=None)
        redirect.url = "http://example.com"

        with patch.object(session, "get", return_value=redirect):
            with pytest.raises(HTTPError):
                session._follow_redirects("http://example.com")

        session.close()

    def test_too_many_redirects_raises(self):
        session = InterruptableSession()
        redirect = _redirect_response(301, "http://example.com/loop")

        with patch.object(session, "get", return_value=redirect):
            with pytest.raises(TooManyRedirects):
                session._follow_redirects("http://example.com")

        session.close()

    def test_kwargs_passed_through(self):
        session = InterruptableSession()
        final = _mock_response()
        captured_kwargs = []

        def capturing_get(url, **kwargs):
            captured_kwargs.append(kwargs)
            return final

        with patch.object(session, "get", side_effect=capturing_get):
            session._follow_redirects("http://example.com", headers={"x-custom": "value"})

        assert captured_kwargs[0].get("headers") == {"x-custom": "value"}
        session.close()


class TestSessionHandlerExtra:
    def test_get_session_returns_same_instance(self):
        session_handler = SessionHandler()
        assert session_handler.get_session() is session_handler.get_session()

    def test_get_session_respects_impersonate(self):
        session_handler = SessionHandler()
        session = session_handler.get_session(impersonate="chrome")
        assert session.impersonate == "chrome"

    def test_close_sessions_is_noop_when_no_sessions(self):
        session_handler = SessionHandler()
        session_handler.close_sessions()  # must not raise

    def test_close_sessions_closes_all_sessions(self):
        session_handler = SessionHandler()
        results = {}
        barrier = threading.Barrier(2)

        def worker(name):
            s = session_handler.get_session()
            results[name] = s
            barrier.wait()

        t = threading.Thread(target=worker, args=("other",))
        t.start()
        worker("main")
        t.join()

        mocks = {name: patch.object(s, "close") for name, s in results.items()}
        with mocks["main"] as m_main, mocks["other"] as m_other:
            session_handler.close_sessions()

        m_main.assert_called_once()
        m_other.assert_called_once()
        assert session_handler._sessions == {}

    def test_get_session_replaces_session_on_impersonate_mismatch(self):
        session_handler = SessionHandler()
        first = session_handler.get_session(impersonate=None)
        second = session_handler.get_session(impersonate="chrome")
        assert first is not second
        assert second.impersonate == "chrome"

    def test_context_restores_session_on_exception(self):
        session_handler = SessionHandler()
        prev = session_handler.get_session()

        with pytest.raises(RuntimeError):
            with session_handler.context(timeout=5):
                raise RuntimeError("boom")

        assert session_handler.get_session() is prev


class TestGetWithInterruptClosed:
    def test_raises_after_close(self):
        session = InterruptableSession()
        session.close()
        with pytest.raises(RuntimeError, match="closed"):
            session.get_with_interrupt("http://example.com")

    def test_does_not_raise_before_close(self):
        session = InterruptableSession()
        mock = _mock_response()
        with patch.object(session, "_follow_redirects", return_value=mock):
            session.get_with_interrupt("http://example.com")  # must not raise
        session.close()


class TestEncoding:
    def test_charset_detected_from_meta_tag(self):
        from fundus.scraping.session import _detect_encoding_from_html

        html = b'<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">'
        assert _detect_encoding_from_html(html) == "iso-8859-1"

    def test_charset_detected_without_quotes(self):
        from fundus.scraping.session import _detect_encoding_from_html

        html = b"<meta charset=utf-8>"
        assert _detect_encoding_from_html(html) == "utf-8"

    def test_no_charset_returns_none(self):
        from fundus.scraping.session import _detect_encoding_from_html

        assert _detect_encoding_from_html(b"<html><body>no charset here</body></html>") is None

    def test_charset_only_scanned_in_first_2048_bytes(self):
        from fundus.scraping.session import _detect_encoding_from_html

        prefix = b"x" * 2048
        html = prefix + b'<meta charset="utf-8">'
        assert _detect_encoding_from_html(html) is None

    def test_detect_encoding_falls_back_to_utf8(self):
        from fundus.scraping.session import _detect_encoding_from_bytes

        # bytes that chardet cannot identify reliably → fallback
        assert _detect_encoding_from_bytes(b"") == "utf-8"

    def test_detect_encoding_prefers_html_meta_over_chardet(self):
        from fundus.scraping.session import _detect_encoding_from_bytes

        html = b'<meta charset="iso-8859-1">' + b"\xe9\xe0\xfc" * 100
        result = _detect_encoding_from_bytes(html)
        assert result == "iso-8859-1"
