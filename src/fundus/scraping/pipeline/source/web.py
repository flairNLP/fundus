from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, Iterable, Iterator, List, Optional, Union
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from curl_cffi.requests import Response
from curl_cffi.requests.exceptions import ConnectionError, HTTPError, ReadTimeout

from fundus.logging import create_logger
from fundus.publishers.base_objects import Publisher, Robots
from fundus.scraping.delay import Delay
from fundus.scraping.filter import URLFilter
from fundus.scraping.html import HTML, SourceInfo
from fundus.scraping.session import session_handler
from fundus.scraping.url import URLSource, is_valid_url

logger = create_logger(__name__)


@dataclass(frozen=True)
class WebSourceInfo(SourceInfo):
    """Origin metadata attached to an HTML record fetched via a URLSource.

    Attributes:
        type (str): Class name of the URLSource that produced the URL (e.g. "RSSFeed", "Sitemap").
        url (str): The feed/sitemap URL the article was discovered from.
    """

    type: str
    url: str


class _Pacer:
    """Per-source rate limiter. Sleeps as needed so consecutive calls are at least `delay` apart."""

    def __init__(
        self, delay: Optional[Delay], sleep: Callable[[float], object] = time.sleep, warm_start: bool = True
    ) -> None:
        """Build a pacer with the given delay and sleep function. warm_start=True skips sleep on first call."""
        self.delay = delay
        self.timestamp = time.time()
        if warm_start and self.delay is not None:
            self.timestamp -= self.delay()
        self.sleep = sleep

    def __call__(self) -> None:
        """Sleep just long enough to enforce the configured delay since the last call, then reset."""
        if self.delay is None:
            return
        if delay := max(0.0, self.delay() - time.time() + self.timestamp):
            self.sleep(delay)
        self.reset()

    def reset(self) -> None:
        """Mark the current time as the last call; the next call will wait the full delay from now."""
        self.timestamp = time.time()


class WebSource:
    """HTML source backed by live HTTP requests over a URLSource (RSSFeed/Sitemap/NewsMap) or any iterable of URLs.

    Iterates URLs one at a time, applies URL filters and robots.txt, rate-limits requests via an
    internal pacer, and fetches each URL through an InterruptableSession. Yields one HTML record per
    successful fetch. Honors a cooperative stop_event for early cancellation.
    """

    def __init__(
        self,
        url_source: Union[URLSource, Iterable[str]],
        publisher: Publisher,
        url_filter: Optional[URLFilter] = None,
        query_parameters: Optional[Dict[str, str]] = None,
        delay: Optional[Delay] = None,
        ignore_robots: bool = False,
        ignore_crawl_delay: bool = False,
        impersonate: bool = False,
        stop_event: Optional[threading.Event] = None,
    ):
        """Initialize a source that fetches HTML from URLs produced by a URLSource or any iterable.

        Args:
            url_source (Union[URLSource, Iterable[str]]): A URLSource (RSSFeed/Sitemap/NewsMap) or
                any iterable of URL strings. URLSource instances are passed the publisher's session
                and request headers when iterated.
            publisher (Publisher): Publisher the URLs belong to. Provides request headers, robots,
                impersonate profile, and the publisher-level URL filter.
            url_filter (Optional[URLFilter]): Source-level URL filter, OR-combined with any
                per-call filter passed to fetch(). Truthy means skip the URL.
            query_parameters (Optional[Dict[str, str]]): Query parameters appended to every URL
                before it is requested. Existing query strings are preserved.
            delay (Optional[Delay]): Per-request delay (seconds). Overridden by robots.txt
                crawl-delay unless ignore_crawl_delay=True.
            ignore_robots (bool): If True, skip robots.txt checks (both can_fetch and crawl-delay).
            ignore_crawl_delay (bool): If True, keep the supplied delay even when robots.txt
                declares its own crawl-delay.
            stop_event (Optional[threading.Event]): Cooperative-cancellation flag. When set, any
                in-flight sleep is interrupted and the source stops iterating URLs.

        """
        self.url_source = url_source
        self.publisher = publisher
        self.url_filter = url_filter
        self.query_parameters = query_parameters or {}
        self._impersonate_profile = publisher.impersonate if impersonate else None
        self.robots: Optional[Robots] = None if ignore_robots else self.publisher.robots
        self.stop_event = stop_event
        self._delay = delay
        self._ignore_crawl_delay = ignore_crawl_delay
        # Built lazily on the first request (see _build_pacer): resolving the crawl-delay may
        # read robots.txt, and construction must stay free of I/O.
        self.pacer: Optional[_Pacer] = None

        # source_info depends only on url_source's type, which is fixed at construction time.
        self.source_info: SourceInfo = (
            WebSourceInfo(publisher.name, type(url_source).__name__, url_source.url)
            if isinstance(url_source, URLSource)
            else SourceInfo(publisher.name)
        )

    @staticmethod
    def _resolve_delay(
        robots: Optional[Robots],
        user_agent: str,
        supplied_delay: Optional[Delay],
        ignore_crawl_delay: bool,
        publisher_name: str = "",
    ) -> Optional[Delay]:
        """Return the effective per-request delay.

        Robots' crawl_delay (if present) overrides supplied_delay; the override is skipped
        when robots is None or ignore_crawl_delay is True or robots has no crawl_delay set.
        """
        if robots is None or ignore_crawl_delay:
            return supplied_delay
        robots_delay = robots.crawl_delay(user_agent)
        if robots_delay is None:
            return supplied_delay
        logger.debug(
            f"Found crawl-delay of {robots_delay} seconds in robots.txt for {publisher_name}. "
            f"Overwriting existing delay."
        )
        return lambda: robots_delay

    def _build_pacer(self) -> _Pacer:
        """Resolve the effective delay (may read robots.txt) and build the rate limiter.

        Deferred out of __init__ so construction performs no I/O; called on the first request.
        """
        user_agent = self.publisher.request_header.get("user-agent", "*")
        resolved_delay = self._resolve_delay(
            self.robots, user_agent, self._delay, self._ignore_crawl_delay, publisher_name=self.publisher.name
        )
        # stop_event.wait makes the per-request delay interruptable; time.sleep does not.
        sleep: Callable[[float], object]
        if self.stop_event is None:
            sleep = time.sleep
        else:
            sleep = self.stop_event.wait
        return _Pacer(delay=resolved_delay, sleep=sleep)

    @staticmethod
    def _apply_query_parameters(url: str, params: Dict[str, str]) -> str:
        """Append query parameters to a URL, preserving existing ones and URL-encoding values."""
        if not params:
            return url
        parts = urlsplit(url)
        existing = parse_qsl(parts.query, keep_blank_values=True)
        new_query = urlencode([*existing, *params.items()])
        return urlunsplit(parts._replace(query=new_query))

    @property
    def _is_stopped(self) -> bool:
        """True if a stop_event was supplied and has been set."""
        return self.stop_event is not None and self.stop_event.is_set()

    def _pre_validate(self, url: str, url_filter: URLFilter) -> bool:
        """Return True if the URL is fit to request. Logs the reason and returns False otherwise."""
        if not is_valid_url(url):
            logger.debug(f"Skipped requested URL {url!r} because the URL is malformed")
            return False
        if url_filter(url):
            logger.debug(f"Skipped requested URL {url!r} because of URL filter")
            return False
        user_agent = self.publisher.request_header.get("user-agent", "*")
        if self.robots is not None and not self.robots.can_fetch(user_agent, url):
            logger.debug(f"Skipped requested URL {url!r} because of robots.txt")
            return False
        return True

    def _request(self, url: str) -> Optional[Response]:
        """Sleep on the pacer, then GET the URL. Returns None on request error."""
        session = session_handler.get_session(self._impersonate_profile)
        pacer = self.pacer
        if pacer is None:
            pacer = self.pacer = self._build_pacer()
        pacer()
        try:
            return session.get_with_interrupt(url, headers=self.publisher.request_header)
        except (HTTPError, ConnectionError, ReadTimeout) as error:
            logger.warning(f"Skipped requested URL {url!r} because of {error!r}")
            return None

    @staticmethod
    def _post_validate(response: Response, url_filter: URLFilter) -> bool:
        """Return True if the response should be kept. Logs the reason and returns False otherwise."""
        if url_filter(str(response.url)):
            logger.debug(f"Skipped responded URL {str(response.url)!r} because of URL filter")
            return False
        return True

    def _build_html(self, requested_url: str, response: Response) -> HTML:
        """Assemble the HTML record from a successful response."""
        return HTML(
            requested_url=requested_url,
            responded_url=str(response.url),
            content=response.text,
            crawl_date=datetime.now(),
            source_info=self.source_info,
        )

    def _fetch_one(self, url: str, url_filter: URLFilter) -> Optional[HTML]:
        """Run the full per-URL pipeline: pre-validate, request, post-validate, build. None if skipped."""
        if not self._pre_validate(url, url_filter):
            return None
        url = self._apply_query_parameters(url, self.query_parameters)
        response = self._request(url)
        if response is None:
            return None
        if not self._post_validate(response, url_filter):
            return None
        return self._build_html(url, response)

    def _iter_urls(self) -> Iterator[str]:
        """Yield URLs from the configured source, swallowing iterator crashes with a warning."""
        if isinstance(self.url_source, URLSource):
            source_iter: Iterator[str] = self.url_source.fetch(
                session_handler.get_session(self._impersonate_profile),
                self.publisher.request_header,
            )
        else:
            source_iter = iter(self.url_source)
        while True:
            try:
                url = next(source_iter, None)
            except Exception as error:
                logger.error(
                    f"Warning! URLSource {self.url_source!r} crashed because of an unexpected error: {error!r}"
                )
                return
            if url is None:
                return
            yield url

    def _build_url_filter(self, url_filter: Optional[URLFilter]) -> URLFilter:
        """Combine source-level and per-call URL filters with logical OR. Returns a pass-through if both are None."""
        combined: List[URLFilter] = ([self.url_filter] if self.url_filter else []) + (
            [url_filter] if url_filter else []
        )

        def combined_url_filter(url: str) -> bool:
            return any(f(url) for f in combined)

        return combined_url_filter

    def fetch(self, url_filter: Optional[URLFilter] = None) -> Iterator[HTML]:
        """Stream HTML records by iterating url_source and fetching each URL.

        Each URL is gated by the combined URL filter (source-level OR per-call), robots.txt, and
        rate-limited by the configured delay. Per-URL request errors (HTTP / connection / timeout)
        are logged and skipped; the iteration continues. If stop_event is set, iteration short-
        circuits at the next boundary.

        Args:
            url_filter (Optional[URLFilter]): Per-call URL filter, OR-combined with the source's
                own url_filter. Truthy means skip the URL.

        Yields:
            HTML: One record per successfully fetched URL.

        """
        combined_filter = self._build_url_filter(url_filter)
        url_iterator = self._iter_urls()
        # Check the stop event BEFORE advancing the iterator: pulling the next URL from a
        # URLSource triggers its feed/sitemap download, so a stopped source must return without
        # ever touching its iterator — otherwise every remaining source is fetched after stop.
        while not self._is_stopped:
            url = next(url_iterator, None)
            if url is None:
                return
            try:
                if html := self._fetch_one(url, combined_filter):
                    yield html
            except Exception as error:
                logger.error(f"Warning! Skipped requested URL {url!r} because of an unexpected error {error!r}")
