import threading
from typing import List
from unittest.mock import MagicMock, patch

import pytest
from curl_cffi.requests.exceptions import ConnectionError, HTTPError, ReadTimeout

from fundus.scraping.html import HTML, SourceInfo
from fundus.scraping.pipeline.source.web import WebSource, WebSourceInfo, _Pacer
from fundus.scraping.url import RSSFeed
from tests.fixtures.builders import make_http_error, mock_response, mock_robots, stub_publisher


class _RecordingIterable:
    """Iterable of URLs that counts how many times it is advanced (i.e. how many URLs were pulled)."""

    def __init__(self, urls: List[str]) -> None:
        self._it = iter(urls)
        self.pulled = 0

    def __iter__(self) -> "_RecordingIterable":
        return self

    def __next__(self) -> str:
        self.pulled += 1
        return next(self._it)


@pytest.fixture
def source(publisher, patched_web_session_handler):
    """A WebSource with robots disabled and pacer stubbed to allow calls through immediately."""
    s = WebSource(url_source=[], publisher=publisher, ignore_robots=True)
    s.pacer = MagicMock(return_value=True)
    return s


# ---- _Pacer ----------------------------------------------------------------


class TestPacer:
    def test_no_delay_never_sleeps(self):
        sleeps: List[float] = []
        pacer = _Pacer(delay=None, sleep=sleeps.append)
        pacer()
        pacer()
        assert sleeps == []

    def test_warm_start_first_call_does_not_sleep(self):
        sleeps: List[float] = []
        pacer = _Pacer(delay=lambda: 5.0, sleep=sleeps.append, warm_start=True)
        pacer()
        assert sleeps == []

    def test_without_warm_start_first_call_sleeps_for_delay(self):
        sleeps: List[float] = []
        pacer = _Pacer(delay=lambda: 0.5, sleep=sleeps.append, warm_start=False)
        pacer()
        assert len(sleeps) == 1
        assert 0.4 <= sleeps[0] <= 0.5

    def test_reset_makes_next_call_sleep(self):
        sleeps: List[float] = []
        pacer = _Pacer(delay=lambda: 1.0, sleep=sleeps.append, warm_start=True)
        pacer()
        pacer.reset()
        pacer()
        assert len(sleeps) == 1


# ---- WebSource.__init__ ----------------------------------------------------


class TestWebSourceConstruction:
    def test_ignore_robots_leaves_robots_none(self, publisher):
        source = WebSource(url_source=[], publisher=publisher, ignore_robots=True)
        assert source.robots is None

    def test_uses_publisher_robots_by_default(self):
        robots = mock_robots(crawl_delay=None)
        publisher = stub_publisher(robots=robots)
        source = WebSource(url_source=[], publisher=publisher)
        assert source.robots is robots

    def test_crawl_delay_resolution_deferred_to_first_request(self, patched_web_session_handler):
        # Resolving the crawl-delay may read robots.txt, so the pacer is deferred out of
        # construction: robots is untouched at build time and consulted on the first request.
        patched_web_session_handler.get_with_interrupt.return_value = mock_response()
        robots = mock_robots(can_fetch=True, crawl_delay=None)
        source = WebSource(url_source=[], publisher=stub_publisher(robots=robots))
        robots.crawl_delay.assert_not_called()
        source._fetch_one("https://example.com/article", lambda u: False)
        robots.crawl_delay.assert_called_once()


class TestApplyQueryParameters:
    def test_no_params_returns_url_unchanged(self):
        assert WebSource._apply_query_parameters("https://example.com/a", {}) == "https://example.com/a"

    def test_appends_to_url_without_query(self):
        assert (
            WebSource._apply_query_parameters("https://example.com/a", {"foo": "bar"})
            == "https://example.com/a?foo=bar"
        )

    def test_preserves_existing_query(self):
        assert (
            WebSource._apply_query_parameters("https://example.com/a?x=1", {"foo": "bar"})
            == "https://example.com/a?x=1&foo=bar"
        )

    def test_url_encodes_special_characters(self):
        result = WebSource._apply_query_parameters("https://example.com/a", {"q": "hello world&fish"})
        assert result == "https://example.com/a?q=hello+world%26fish"

    def test_url_encodes_unicode(self):
        result = WebSource._apply_query_parameters("https://example.com/a", {"q": "café"})
        assert result == "https://example.com/a?q=caf%C3%A9"


def _supplied_delay() -> float:
    return 1.0


class TestResolveDelay:
    def test_no_robots_returns_supplied(self):
        assert WebSource._resolve_delay(None, "*", _supplied_delay, ignore_crawl_delay=False) is _supplied_delay

    def test_ignore_crawl_delay_returns_supplied(self):
        robots = mock_robots()
        assert WebSource._resolve_delay(robots, "*", _supplied_delay, ignore_crawl_delay=True) is _supplied_delay

    def test_no_robots_delay_returns_supplied(self):
        robots = mock_robots(crawl_delay=None)
        assert WebSource._resolve_delay(robots, "*", _supplied_delay, ignore_crawl_delay=False) is _supplied_delay

    def test_robots_delay_overrides_supplied(self):
        robots = mock_robots(crawl_delay=5.0)
        resolved = WebSource._resolve_delay(robots, "*", lambda: 1.0, ignore_crawl_delay=False)
        assert resolved is not None
        assert resolved() == 5.0

    def test_robots_delay_returned_when_no_supplied(self):
        robots = mock_robots(crawl_delay=3.0)
        resolved = WebSource._resolve_delay(robots, "*", None, ignore_crawl_delay=False)
        assert resolved is not None
        assert resolved() == 3.0


# ---- WebSource._fetch_one -------------------------------------------------


class TestFetchOne:
    def test_returns_none_for_invalid_url(self, source):
        assert source._fetch_one("not-a-url", lambda u: False) is None

    def test_returns_none_when_url_filter_matches(self, source):
        assert source._fetch_one("https://example.com/", lambda u: True) is None

    def test_returns_none_when_robots_disallows(self, patched_web_session_handler):
        robots = mock_robots(can_fetch=False, crawl_delay=None)
        publisher = stub_publisher(robots=robots)
        source = WebSource(url_source=[], publisher=publisher)
        source.pacer = MagicMock(return_value=True)
        assert source._fetch_one("https://example.com/", lambda u: False) is None

    def test_returns_none_on_http_error(self, source, patched_web_session_handler):
        patched_web_session_handler.get_with_interrupt.side_effect = HTTPError("boom")
        assert source._fetch_one("https://example.com/", lambda u: False) is None

    def test_returns_none_on_connection_error(self, source, patched_web_session_handler):
        patched_web_session_handler.get_with_interrupt.side_effect = ConnectionError("boom")
        assert source._fetch_one("https://example.com/", lambda u: False) is None

    def test_returns_none_on_read_timeout(self, source, patched_web_session_handler):
        patched_web_session_handler.get_with_interrupt.side_effect = ReadTimeout("boom")
        assert source._fetch_one("https://example.com/", lambda u: False) is None

    def test_returns_none_on_5xx_status_code(self, source, patched_web_session_handler):
        patched_web_session_handler.get_with_interrupt.side_effect = make_http_error(status_code=503)
        assert source._fetch_one("https://example.com/", lambda u: False) is None

    def test_successful_fetch_returns_html(self, source, patched_web_session_handler):
        patched_web_session_handler.get_with_interrupt.return_value = mock_response(
            text="<html>body</html>", url="https://example.com/article"
        )
        result = source._fetch_one("https://example.com/article", lambda u: False)
        assert isinstance(result, HTML)
        assert result.requested_url == "https://example.com/article"
        assert result.responded_url == "https://example.com/article"
        assert result.content == "<html>body</html>"

    def test_appends_query_parameters_without_existing_query(self, publisher, patched_web_session_handler):
        source = WebSource(
            url_source=[],
            publisher=publisher,
            ignore_robots=True,
            query_parameters={"foo": "bar"},
        )
        source.pacer = MagicMock(return_value=True)
        source._fetch_one("https://example.com/article", lambda u: False)
        called_url = patched_web_session_handler.get_with_interrupt.call_args[0][0]
        assert called_url == "https://example.com/article?foo=bar"

    def test_appends_query_parameters_with_existing_query(self, publisher, patched_web_session_handler):
        source = WebSource(
            url_source=[],
            publisher=publisher,
            ignore_robots=True,
            query_parameters={"foo": "bar"},
        )
        source.pacer = MagicMock(return_value=True)
        source._fetch_one("https://example.com/article?x=1", lambda u: False)
        called_url = patched_web_session_handler.get_with_interrupt.call_args[0][0]
        assert called_url == "https://example.com/article?x=1&foo=bar"

    def test_url_filter_applied_to_responded_url(self, source, patched_web_session_handler):
        patched_web_session_handler.get_with_interrupt.return_value = mock_response(
            url="https://redirected.example.com/"
        )
        assert source._fetch_one("https://example.com/article", lambda u: "redirected" in u) is None

    def test_web_source_info_when_url_source_is_url_source(self, publisher, patched_web_session_handler):
        feed = RSSFeed(url="https://example.com/feed.xml")
        source = WebSource(url_source=feed, publisher=publisher, ignore_robots=True)
        source.pacer = MagicMock(return_value=True)
        result = source._fetch_one("https://example.com/article", lambda u: False)
        assert isinstance(result, HTML)
        assert isinstance(result.source_info, WebSourceInfo)
        assert result.source_info.type == "RSSFeed"
        assert result.source_info.url == "https://example.com/feed.xml"

    def test_plain_source_info_when_url_source_is_iterable(self, source, patched_web_session_handler):
        result = source._fetch_one("https://example.com/article", lambda u: False)
        assert isinstance(result, HTML)
        assert type(result.source_info) is SourceInfo  # not the Web subclass


# ---- WebSource._build_url_filter -------------------------------------------


class TestBuildUrlFilter:
    def test_no_filters_returns_pass_through(self, publisher):
        source = WebSource(url_source=[], publisher=publisher, ignore_robots=True)
        combined = source._build_url_filter(None)
        assert combined("https://example.com/") is False

    def test_instance_filter_only(self, publisher):
        source = WebSource(
            url_source=[],
            publisher=publisher,
            url_filter=lambda u: "blocked" in u,
            ignore_robots=True,
        )
        combined = source._build_url_filter(None)
        assert combined("https://example.com/blocked") is True
        assert combined("https://example.com/ok") is False

    def test_per_call_filter_only(self, publisher):
        source = WebSource(url_source=[], publisher=publisher, ignore_robots=True)
        combined = source._build_url_filter(lambda u: "blocked" in u)
        assert combined("https://example.com/blocked") is True
        assert combined("https://example.com/ok") is False

    def test_combined_filters_via_any(self, publisher):
        source = WebSource(
            url_source=[],
            publisher=publisher,
            url_filter=lambda u: "first" in u,
            ignore_robots=True,
        )
        combined = source._build_url_filter(lambda u: "second" in u)
        assert combined("https://host/first") is True
        assert combined("https://host/second") is True
        assert combined("https://host/third") is False


# ---- WebSource.fetch -------------------------------------------------------


class TestFetch:
    def test_iterates_plain_iterable_and_yields_html(self, publisher, patched_web_session_handler):
        source = WebSource(
            url_source=["https://example.com/a", "https://example.com/b"],
            publisher=publisher,
            ignore_robots=True,
        )
        source.pacer = MagicMock(return_value=True)
        results = list(source.fetch())
        assert len(results) == 2
        assert all(isinstance(r, HTML) for r in results)

    def test_iterates_url_source_passing_session_and_headers(self, publisher, patched_web_session_handler):
        url_source = MagicMock(spec=RSSFeed)
        url_source.fetch.return_value = iter(["https://example.com/a"])
        url_source.url = "https://example.com/feed.xml"
        source = WebSource(url_source=url_source, publisher=publisher, ignore_robots=True)
        source.pacer = MagicMock(return_value=True)
        list(source.fetch())
        url_source.fetch.assert_called_once()
        assert url_source.fetch.call_args[0][1] == publisher.request_header

    def test_stop_event_set_mid_stream_halts_before_pulling_next_url(self, publisher, patched_web_session_handler):
        # Setting the stop event after the first article must halt fetch at the next loop check,
        # before the second URL is pulled — so no further feed/page is requested. The recording
        # iterable proves the next URL was never pulled (pulled stays 1).
        stop_event = threading.Event()
        urls = _RecordingIterable(["https://example.com/a", "https://example.com/b"])
        source = WebSource(
            url_source=urls,
            publisher=publisher,
            ignore_robots=True,
            stop_event=stop_event,
        )
        source.pacer = MagicMock(return_value=True)

        gen = source.fetch()
        next(gen)  # pull and fetch the first URL's article
        stop_event.set()  # stop arrives between articles
        list(gen)  # fully drive the generator after the stop

        assert urls.pulled == 1

    def test_set_stop_event_does_not_pull_url_iterator(self, publisher, patched_web_session_handler):
        # A stop event set at a source boundary must short-circuit BEFORE the URL iterator is
        # advanced, so the feed/sitemap is never downloaded. "No HTML yielded" is not enough to
        # prove this (a plain list advances for free), so we assert the URLSource is never
        # fetched. Regression: fetch pulled the first URL before checking the stop event.
        stop_event = threading.Event()
        stop_event.set()
        url_source = MagicMock(spec=RSSFeed)
        url_source.fetch.return_value = iter(["https://example.com/a"])
        url_source.url = "https://example.com/feed.xml"
        source = WebSource(
            url_source=url_source,
            publisher=publisher,
            ignore_robots=True,
            stop_event=stop_event,
        )
        source.pacer = MagicMock(return_value=True)
        assert list(source.fetch()) == []
        url_source.fetch.assert_not_called()

    def test_url_iterator_crash_terminates_fetch(self, publisher, patched_web_session_handler, caplog):
        def crashing_iter():
            yield "https://example.com/a"
            raise RuntimeError("boom")

        source = WebSource(url_source=crashing_iter(), publisher=publisher, ignore_robots=True)
        source.pacer = MagicMock(return_value=True)
        with caplog.at_level("ERROR"):
            results = list(source.fetch())
        assert len(results) == 1
        assert any("crashed" in record.message for record in caplog.records)

    def test_fetch_one_crash_continues_to_next_url(self, publisher, patched_web_session_handler, caplog):
        source = WebSource(
            url_source=["https://example.com/a", "https://example.com/b"],
            publisher=publisher,
            ignore_robots=True,
        )
        source.pacer = MagicMock(return_value=True)
        sentinel_html = HTML(
            requested_url="https://example.com/b",
            responded_url="https://example.com/b",
            content="",
            crawl_date=__import__("datetime").datetime(2024, 1, 1),
            source_info=SourceInfo(publisher="x"),
        )
        with patch.object(source, "_fetch_one", side_effect=[RuntimeError("boom"), sentinel_html]):
            with caplog.at_level("ERROR"):
                results = list(source.fetch())
        assert results == [sentinel_html]
        assert any("unexpected error" in record.message for record in caplog.records)
