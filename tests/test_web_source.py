from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterator, List, Optional

import pytest

from fundus.publishers.base_objects import Publisher
from fundus.scraping.html import HTML, InterleavedSource, SourceInfo, WebSource
from fundus.scraping.session import InterruptableSession
from fundus.scraping.url import RSSFeed, URLSource


@dataclass
class StaticSource(URLSource):
    """A URLSource serving a fixed list of URLs, optionally crashing part way through."""

    urls: List[str] = field(default_factory=list)
    crash_after: Optional[int] = None

    def fetch(self, session: InterruptableSession, headers: Dict[str, str]) -> Iterator[str]:
        for index, url in enumerate(self.urls):
            if self.crash_after is not None and index == self.crash_after:
                raise RuntimeError("source crashed")
            yield url


def source(name: str, count: int, **kwargs) -> StaticSource:
    return StaticSource(
        f"https://test.com/{name}",
        urls=[f"https://test.com/{name}/{index}" for index in range(count)],
        **kwargs,
    )


@pytest.fixture
def publisher(parser_proxy_with_version) -> Publisher:
    return Publisher(
        name="test_pub",
        domain="https://test.com/",
        sources=[RSSFeed("https://test.com/feed")],
        parser=parser_proxy_with_version,
    )


def urls(web_source: WebSource, monkeypatch) -> List[str]:
    """Drives fetch() without hitting the network, recording the URLs _fetch_html was asked for.

    Returning None stands for a skipped URL, which fetch() simply moves past.
    """
    requested: List[str] = []

    def _fetch_html(url: str, url_filter) -> None:
        requested.append(url)
        return None

    monkeypatch.setattr(web_source, "_fetch_html", _fetch_html)
    assert not list(web_source.fetch())
    return requested


def web_source(publisher: Publisher, name: str, count: int, monkeypatch, **kwargs) -> WebSource:
    """A WebSource over <count> URLs, stubbed to report the URLs it requested as HTML.

    The reported HTML carries the requested URL, so that a group of sources stays traceable
    to the source each of its articles came from.
    """
    stubbed = WebSource(url_source=source(name, count, **kwargs), publisher=publisher)
    monkeypatch.setattr(
        stubbed,
        "_fetch_html",
        lambda url, url_filter: HTML(url, url, "", datetime.now(), SourceInfo(publisher.name)),
    )
    return stubbed


class TestPlainURLs:
    def test_urls_are_scraped_in_order(self, publisher: Publisher, monkeypatch) -> None:
        plain = WebSource(url_source=["https://test.com/a", "https://test.com/b"], publisher=publisher)
        assert urls(plain, monkeypatch) == ["https://test.com/a", "https://test.com/b"]

    def test_a_generator_of_urls_is_not_consumed_early(self, publisher: Publisher, monkeypatch) -> None:
        generated = (f"https://test.com/{index}" for index in range(3))
        plain = WebSource(url_source=generated, publisher=publisher)

        assert urls(plain, monkeypatch) == [
            "https://test.com/0",
            "https://test.com/1",
            "https://test.com/2",
        ]


class TestURLSources:
    def test_a_source_is_drawn_in_order(self, publisher: Publisher, monkeypatch) -> None:
        assert urls(WebSource(url_source=source("feed", 3), publisher=publisher), monkeypatch) == [
            "https://test.com/feed/0",
            "https://test.com/feed/1",
            "https://test.com/feed/2",
        ]

    def test_a_crashing_source_stops_without_taking_down_the_scraper(self, publisher: Publisher, monkeypatch) -> None:
        crashing = WebSource(url_source=source("broken", 3, crash_after=1), publisher=publisher)
        assert urls(crashing, monkeypatch) == ["https://test.com/broken/0"]


class TestInterleavedSource:
    def _requested(self, interleaved: InterleavedSource) -> List[str]:
        return [html.requested_url for html in interleaved.fetch()]

    def test_sources_are_drawn_in_turn(self, publisher: Publisher, monkeypatch) -> None:
        interleaved = InterleavedSource(
            web_source(publisher, "one", 2, monkeypatch),
            web_source(publisher, "two", 2, monkeypatch),
        )
        assert self._requested(interleaved) == [
            "https://test.com/one/0",
            "https://test.com/two/0",
            "https://test.com/one/1",
            "https://test.com/two/1",
        ]

    def test_an_exhausted_source_does_not_stop_the_others(self, publisher: Publisher, monkeypatch) -> None:
        interleaved = InterleavedSource(
            web_source(publisher, "short", 1, monkeypatch),
            web_source(publisher, "long", 3, monkeypatch),
        )
        assert self._requested(interleaved) == [
            "https://test.com/short/0",
            "https://test.com/long/0",
            "https://test.com/long/1",
            "https://test.com/long/2",
        ]

    def test_a_crashing_source_takes_down_only_itself(self, publisher: Publisher, monkeypatch) -> None:
        # without per-source isolation, one broken source would take the whole group with it
        interleaved = InterleavedSource(
            web_source(publisher, "broken", 3, monkeypatch, crash_after=1),
            web_source(publisher, "healthy", 3, monkeypatch),
        )
        assert self._requested(interleaved) == [
            "https://test.com/broken/0",
            "https://test.com/healthy/0",
            "https://test.com/healthy/1",
            "https://test.com/healthy/2",
        ]

    def test_a_lone_source_is_left_as_it_is(self, publisher: Publisher, monkeypatch) -> None:
        interleaved = InterleavedSource(web_source(publisher, "feed", 2, monkeypatch))
        assert self._requested(interleaved) == ["https://test.com/feed/0", "https://test.com/feed/1"]
