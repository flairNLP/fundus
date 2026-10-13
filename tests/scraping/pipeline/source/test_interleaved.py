from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterator, List, Optional

import pytest

from fundus.publishers.base_objects import Publisher
from fundus.scraping.html import HTML, SourceInfo
from fundus.scraping.pipeline.source.interleaved import InterleavedSource
from fundus.scraping.pipeline.source.web import WebSource
from fundus.scraping.session import InterruptableSession
from fundus.scraping.url import URLSource


@dataclass
class _StaticSource(URLSource):
    """A URLSource serving a fixed list of URLs, optionally crashing part way through."""

    urls: List[str] = field(default_factory=list)
    crash_after: Optional[int] = None

    def fetch(self, session: InterruptableSession, headers: Dict[str, str]) -> Iterator[str]:
        for index, url in enumerate(self.urls):
            if self.crash_after is not None and index == self.crash_after:
                raise RuntimeError("source crashed")
            yield url


def _web_source(publisher: Publisher, name: str, count: int, monkeypatch, **kwargs) -> WebSource:
    """A WebSource over <count> URLs, stubbed to report the URLs it requested as HTML.

    The reported HTML carries the requested URL, so that a group of sources stays traceable
    to the source each of its articles came from.
    """
    url_source = _StaticSource(
        f"https://example.com/{name}",
        urls=[f"https://example.com/{name}/{index}" for index in range(count)],
        **kwargs,
    )
    stubbed = WebSource(url_source=url_source, publisher=publisher, ignore_robots=True)
    monkeypatch.setattr(
        stubbed,
        "_fetch_one",
        lambda url, url_filter: HTML(url, url, "", datetime.now(), SourceInfo(publisher.name)),
    )
    return stubbed


def _requested(interleaved: InterleavedSource) -> List[str]:
    return [html.requested_url for html in interleaved.fetch()]


@pytest.mark.usefixtures("patched_web_session_handler")
class TestInterleavedSource:
    def test_sources_are_drawn_in_turn(self, publisher, monkeypatch):
        interleaved = InterleavedSource(
            _web_source(publisher, "one", 2, monkeypatch),
            _web_source(publisher, "two", 2, monkeypatch),
        )
        assert _requested(interleaved) == [
            "https://example.com/one/0",
            "https://example.com/two/0",
            "https://example.com/one/1",
            "https://example.com/two/1",
        ]

    def test_an_exhausted_source_does_not_stop_the_others(self, publisher, monkeypatch):
        interleaved = InterleavedSource(
            _web_source(publisher, "short", 1, monkeypatch),
            _web_source(publisher, "long", 3, monkeypatch),
        )
        assert _requested(interleaved) == [
            "https://example.com/short/0",
            "https://example.com/long/0",
            "https://example.com/long/1",
            "https://example.com/long/2",
        ]

    def test_a_crashing_source_takes_down_only_itself(self, publisher, monkeypatch):
        # without per-source isolation, one broken source would take the whole group with it
        interleaved = InterleavedSource(
            _web_source(publisher, "broken", 3, monkeypatch, crash_after=1),
            _web_source(publisher, "healthy", 3, monkeypatch),
        )
        assert _requested(interleaved) == [
            "https://example.com/broken/0",
            "https://example.com/healthy/0",
            "https://example.com/healthy/1",
            "https://example.com/healthy/2",
        ]

    def test_a_lone_source_is_left_as_it_is(self, publisher, monkeypatch):
        interleaved = InterleavedSource(_web_source(publisher, "feed", 2, monkeypatch))
        assert _requested(interleaved) == ["https://example.com/feed/0", "https://example.com/feed/1"]

    def test_url_filter_is_forwarded_to_every_source(self, publisher, monkeypatch):
        received = []
        sources = [_web_source(publisher, name, 1, monkeypatch) for name in ("one", "two")]
        for web_source in sources:
            monkeypatch.setattr(web_source, "fetch", lambda url_filter=None: received.append(url_filter) or iter(()))

        def url_filter(url: str) -> bool:
            return False

        assert list(InterleavedSource(*sources).fetch(url_filter)) == []
        assert received == [url_filter, url_filter]
