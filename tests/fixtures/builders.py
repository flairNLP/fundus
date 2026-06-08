"""Canonical test-data builders. See tests/README.md for conventions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type, Union, cast
from unittest.mock import MagicMock

from curl_cffi.requests import BrowserTypeLiteral
from curl_cffi.requests.exceptions import HTTPError

from fundus.parser import BaseParser, ParserProxy
from fundus.publishers.base_objects import Publisher, PublisherGroup, Robots
from fundus.scraping.article import Article
from fundus.scraping.filter import URLFilter
from fundus.scraping.html import HTML, SourceInfo
from fundus.scraping.url import NewsMap, URLSource

_DEFAULT_REQUEST_HEADER: Dict[str, str] = {"user-agent": "test-agent"}


class _DefaultParserProxy(ParserProxy):
    # Module-level so a Publisher carrying this parser pickles by qualified name.
    class Default(BaseParser):
        pass


def make_publisher(
    *,
    name: str = "test_pub",
    domain: str = "https://test.com/",
    sources: Optional[List[URLSource]] = None,
    parser: Type[ParserProxy] = _DefaultParserProxy,
    request_header: Optional[Dict[str, str]] = None,
    url_filter: Optional[URLFilter] = None,
    impersonate: Optional[BrowserTypeLiteral] = None,
    suppress_robots: bool = False,
    disallows_training: bool = False,
) -> Publisher:
    return Publisher(
        name=name,
        domain=domain,
        sources=sources if sources is not None else [NewsMap("https://test.com/test_news_map")],
        parser=parser,
        request_header=request_header if request_header is not None else dict(_DEFAULT_REQUEST_HEADER),
        url_filter=url_filter,
        impersonate=impersonate,
        suppress_robots=suppress_robots,
        disallows_training=disallows_training,
    )


def make_publisher_group(
    *,
    name: str = "TestGroup",
    default_language: Optional[str] = None,
    **members: Union[Publisher, PublisherGroup],
) -> PublisherGroup:
    """Build a PublisherGroup from named Publisher/PublisherGroup members.

    Inline equivalent of ``class <name>(metaclass=PublisherGroup): ...``, so a test can construct
    exactly the group it asserts against right next to the assertion instead of reaching for a
    distant fixture. Member kwargs become the group's attributes (``eng=...`` -> ``group.eng``),
    and ``default_language`` propagates to member sources that declare no languages of their own —
    exactly as the metaclass does for real publisher groups.
    """
    namespace: Dict[str, object] = {}
    if default_language is not None:
        namespace["default_language"] = default_language
    namespace.update(members)
    return PublisherGroup(name, (), namespace)


@dataclass
class _PublisherStub:
    """Picklable stand-in for Publisher exposing only the attributes consumers read.

    Lives behind ``stub_publisher`` which casts it to ``Publisher`` for the type checker.
    Tests should not reference this class directly.
    """

    name: str = "test_pub"
    domain: str = "https://example.com/"
    impersonate: Optional[str] = None
    request_header: Dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_REQUEST_HEADER))
    robots: Optional[Any] = None
    url_filter: Optional[Callable[[str], bool]] = None

    def serialize(self) -> str:
        return self.name


def stub_publisher(
    *,
    name: str = "test_pub",
    domain: str = "https://example.com/",
    impersonate: Optional[str] = None,
    request_header: Optional[Dict[str, str]] = None,
    robots: Optional[Any] = None,
    url_filter: Optional[Callable[[str], bool]] = None,
) -> Publisher:
    stub = _PublisherStub(
        name=name,
        domain=domain,
        impersonate=impersonate,
        request_header=request_header if request_header is not None else dict(_DEFAULT_REQUEST_HEADER),
        robots=robots,
        url_filter=url_filter,
    )
    return cast(Publisher, stub)


def make_source_info(*, publisher: str = "test_pub") -> SourceInfo:
    return SourceInfo(publisher=publisher)


def make_html(
    *,
    requested_url: str = "https://example.com/article",
    responded_url: Optional[str] = None,
    content: str = "<html/>",
    crawl_date: Optional[datetime] = None,
    publisher: str = "test_pub",
) -> HTML:
    return HTML(
        requested_url=requested_url,
        responded_url=responded_url if responded_url is not None else requested_url,
        content=content,
        crawl_date=crawl_date if crawl_date is not None else datetime(2024, 1, 1),
        source_info=make_source_info(publisher=publisher),
    )


def make_article(*, html: Optional[HTML] = None, **extraction: Any) -> Article:
    return Article(html=html if html is not None else make_html(), **extraction)


def make_http_error(*, status_code: int) -> HTTPError:
    """Real curl_cffi HTTPError carrying a MagicMock response with the given status_code."""
    return HTTPError("boom", response=MagicMock(status_code=status_code))


# --- test doubles ---
# Everything below fabricates a stand-in, not a real domain object. The prefix says which:
# ``mock_*`` returns a MagicMock; ``stub_publisher`` (above) returns a hand-rolled stub.


def mock_response(
    *,
    text: str = "<html/>",
    url: str = "https://example.com/article",
    history: Optional[List[Any]] = None,
) -> MagicMock:
    """MagicMock for curl_cffi Response — wide surface, only a few fields tests touch."""
    response = MagicMock()
    response.text = text
    response.url = url
    response.history = history if history is not None else []
    return response


def mock_robots(*, can_fetch: bool = True, crawl_delay: Optional[float] = None) -> MagicMock:
    """MagicMock for Robots — a behavioral collaborator (can_fetch / crawl_delay).

    Defaults are permissive: fetching allowed, no crawl-delay.
    """
    robots = MagicMock(spec=Robots)
    robots.can_fetch.return_value = can_fetch
    robots.crawl_delay.return_value = crawl_delay
    return robots
