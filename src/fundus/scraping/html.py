import time
from dataclasses import dataclass
from datetime import datetime
from typing import (
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Protocol,
    Union,
)
from urllib.parse import urlparse

import chardet
import requests
from curl_cffi.requests.exceptions import ConnectionError, HTTPError, Timeout
from fastwarc import ArchiveIterator, WarcRecord, WarcRecordType
from more_itertools import roundrobin

from fundus.logging import create_logger
from fundus.publishers.base_objects import Publisher, Robots
from fundus.scraping.delay import Delay
from fundus.scraping.filter import URLFilter
from fundus.scraping.session import _default_header, session_handler
from fundus.scraping.url import URLSource, is_valid_url
from fundus.utils.events import __EVENTS__

__all__ = [
    "HTML",
    "SourceInfo",
    "WarcSourceInfo",
    "WebSourceInfo",
    "HTMLSource",
    "WebSource",
    "InterleavedSource",
    "CCNewsSource",
    "build_clock",
]

logger = create_logger(__name__)


@dataclass(frozen=True)
class HTML:
    requested_url: str
    responded_url: str
    content: str
    crawl_date: datetime
    source_info: "SourceInfo"


@dataclass(frozen=True)
class SourceInfo:
    publisher: str


@dataclass(frozen=True)
class WarcSourceInfo(SourceInfo):
    warc_path: str
    warc_headers: Dict[str, str]
    http_headers: Dict[str, str]


@dataclass(frozen=True)
class WebSourceInfo(SourceInfo):
    type: str
    url: str


class HTMLSource(Protocol):
    def fetch(self, url_filter: Optional[URLFilter] = None) -> Iterator[HTML]: ...


class _Clock:
    def __init__(
        self, delay: Optional[Delay], sleep: Callable[[float], None] = time.sleep, warm_start: bool = True
    ) -> None:
        """Utility class for time-aligned delay.

        Keeps track of the time passed since last call or init and waits at most the remaining delay.

        Args:
            delay: A customized delay.
            sleep: A customized sleep function. Defaults to <time.sleep>.
            warm_start: If true, skips first delay.
        """
        self.delay = delay
        self.timestamp = time.time()

        if warm_start and self.delay is not None:
            self.timestamp -= self.delay()

        self.sleep = sleep

    def __call__(self, blocking: bool = True) -> bool:
        """Waits at most <delay> seconds since last called.

        Args:
            blocking: If True, blocks until <delay> seconds have elapsed since last call.
            If non-blocking returns False if less time has elapsed, else returns True.

        Returns: True if <delay> seconds have elapsed since last call. False otherwise.

        """
        if self.delay is None:
            return True

        if delay := max(0.0, self.delay() - time.time() + self.timestamp):
            if not blocking:
                return False
            self.sleep(delay)
        self.reset()
        return True

    def reset(self):
        self.timestamp = time.time()


def _interruptable_sleep(seconds: float) -> None:
    """Sleeps <seconds>, waking early once the crawl is stopped."""
    __EVENTS__.get("stop").wait(seconds)


def build_clock(
    publisher: Publisher,
    delay: Optional[Delay] = None,
    ignore_robots: bool = False,
    ignore_crawl_delay: bool = False,
) -> _Clock:
    """Builds the clock pacing the requests to <publisher>.

    A crawl-delay declared in the publisher's robots.txt overrides <delay>, unless robots.txt or
    the crawl-delay it declares is ignored. Since the delay paces a publisher rather than a single
    source, pass one clock to all the WebSources addressing it whenever they do not run one after
    another (see InterleavedSource).

    Args:
        publisher: The publisher the requests address.
        delay: The crawl-delay to keep between requests. If None, requests are not delayed.
        ignore_robots: If True, robots.txt is not consulted for a crawl-delay.
        ignore_crawl_delay: If True, a crawl-delay given by robots.txt does not overwrite <delay>.

    Returns:
        _Clock: A clock over the effective delay.
    """
    if not (ignore_robots or ignore_crawl_delay):
        if robots_delay := publisher.robots.crawl_delay(publisher.request_header.get("user-agent", "*")):
            logger.debug(
                f"Found crawl-delay of {robots_delay} seconds in robots.txt for {publisher.name}. "
                f"Overwriting existing delay."
            )

            def delay() -> float:
                return robots_delay

    return _Clock(delay=delay, sleep=_interruptable_sleep)


class WebSource:
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
        clock: Optional["_Clock"] = None,
    ):
        """
        Args:
            url_source: The URLs to scrape, given either as a single URLSource or as a plain
                iterable of URLs.
            publisher: The publisher the URLs belong to.
            url_filter: Filter to apply to the requested and responded URLs.
            query_parameters: Query parameters to append to every crawled URL.
            delay: The crawl-delay to keep between requests. Ignored if <clock> is given.
            ignore_robots: If True, robots.txt restrictions are ignored.
            ignore_crawl_delay: If True, a crawl-delay given by robots.txt does not overwrite <delay>.
            impersonate: If True, use the publisher's browser profile to impersonate.
            clock: The clock pacing the requests. Pass one clock to every WebSource addressing a
                publisher to keep the crawl-delay per publisher rather than per source, which
                matters once the sources are drawn from in turn (see InterleavedSource). If None,
                this source paces itself using <delay>.
        """
        self.url_source = url_source
        self.publisher = publisher
        self.url_filter = url_filter
        self.query_parameters = query_parameters or {}
        self._impersonate_profile = publisher.impersonate if impersonate else None

        # parse robots:
        self.robots: Optional[Robots] = None if ignore_robots else self.publisher.robots

        self.clock = clock if clock is not None else build_clock(publisher, delay, ignore_robots, ignore_crawl_delay)

    @property
    def _is_stopped(self):
        return __EVENTS__.is_event_set("stop")

    def _fetch_html(self, url: str, url_filter: URLFilter) -> Optional[HTML]:
        # check if URL is malformed
        if not is_valid_url(url):
            logger.debug(f"Skipped requested URL {url!r} because the URL is malformed")
            return None

        # apply URL filter to requested URL
        if url_filter(url):
            logger.debug(f"Skipped requested URL {url!r} because of URL filter")
            return None

        # check robots
        if not (
            self.robots is None or self.robots.can_fetch(self.publisher.request_header.get("user-agent", "*"), url)
        ):
            logger.debug(f"Skipped requested URL {url!r} because of robots.txt")
            return None

        session = session_handler.get_session(self._impersonate_profile)

        # prepare query parameters
        for key, value in self.query_parameters.items():
            if "?" in url:
                url += "&" + key + "=" + value
            else:
                url += "?" + key + "=" + value

        # apply crawl-delay
        self.clock()

        # fetch html
        try:
            response = session.get_with_interrupt(url, headers=self.publisher.request_header)

        except (HTTPError, ConnectionError, Timeout) as error:
            logger.warning(f"Skipped requested URL {url!r} because of {error!r}")
            if isinstance(error, HTTPError) and error.response.status_code >= 500:
                logger.warning(f"Skipped {self.publisher.name!r} due to server errors: {error!r}")
            return None

        # apply URL filter to responded URL
        if url_filter(str(response.url)):
            logger.debug(f"Skipped responded URL {str(response.url)!r} because of URL filter")
            return None

        html = response.text

        # check for redirects
        if response.history:
            logger.info(f"Got redirected {len(response.history)} time(s) from {url!r} -> {response.url!r}")

        # create WebSourceInfo
        source_info = (
            WebSourceInfo(self.publisher.name, type(self.url_source).__name__, self.url_source.url)
            if isinstance(self.url_source, URLSource)
            else SourceInfo(self.publisher.name)
        )

        # create HTML
        return HTML(
            requested_url=url,
            responded_url=str(response.url),
            content=html,
            crawl_date=datetime.now(),
            source_info=source_info,
        )

    def _build_url_filter(self, url_filter: Optional[URLFilter]) -> URLFilter:
        combined_filters: List[URLFilter] = ([self.url_filter] if self.url_filter else []) + (
            [url_filter] if url_filter else []
        )

        def combined_url_filter(url: str) -> bool:
            return any(f(url) for f in combined_filters)

        return combined_url_filter

    def fetch(self, url_filter: Optional[URLFilter] = None) -> Iterator[HTML]:
        if isinstance(self.url_source, URLSource):
            url_iterator = self.url_source.fetch(
                session_handler.get_session(self._impersonate_profile),
                self.publisher.request_header,
            )
        else:
            url_iterator = iter(self.url_source)

        while not self._is_stopped:
            try:
                # check iterator
                if (url := next(url_iterator, None)) is None:
                    return
            except Exception as error:
                logger.error(
                    f"Warning! URLSource {self.url_source!r} crashed because of an unexpected error: {error!r}"
                )
                return

            try:
                if html := self._fetch_html(url, self._build_url_filter(url_filter)):
                    yield html
            except Exception as error:
                logger.error(f"Warning! Skipped requested URL {url!r} because of an unexpected error {error!r}")
                continue


class InterleavedSource:
    """Several HTMLSources drawn from in turn rather than one after another.

    Satisfies the HTMLSource protocol itself, so that a group of sources is interchangeable with a
    single one wherever a scraper takes HTMLSources. Exhausted sources leave the rotation, so the
    remaining ones keep going, and a group of one is simply drawn as it is.
    """

    def __init__(self, *sources: HTMLSource) -> None:
        self.sources = sources

    def fetch(self, url_filter: Optional[URLFilter] = None) -> Iterator[HTML]:
        return roundrobin(*(source.fetch(url_filter) for source in self.sources))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self.sources)!r})"


class CCNewsSource:
    def __init__(self, *publishers: Publisher, warc_path: str, headers: Optional[Dict[str, str]] = None):
        self.publishers = publishers
        self.warc_path = warc_path
        self.headers = headers or _default_header
        self._publisher_mapping: Dict[str, Publisher] = {
            urlparse(domain).netloc: publisher
            for publisher in self.publishers
            for domain in [publisher.domain] + publisher.deprecated_domains
        }

    def fetch(self, url_filter: Optional[URLFilter] = None) -> Iterator[HTML]:
        def extract_content(record: WarcRecord) -> Optional[str]:
            warc_body: bytes = record.reader.read()

            try:
                return str(warc_body, encoding=record.http_charset)  # type: ignore[arg-type]
            except (UnicodeDecodeError, TypeError):
                encoding: Optional[str] = chardet.detect(warc_body)["encoding"]

                if encoding is not None:
                    logger.debug(
                        f"Trying to decode record {record.record_id!r} from {target_url!r} "
                        f"using detected encoding {encoding}."
                    )

                    try:
                        return str(warc_body, encoding=encoding)
                    except UnicodeDecodeError:
                        logger.warning(
                            f"Couldn't decode record {record.record_id!r} from {target_url!r} with "
                            f"original charset {record.http_charset!r} using detected charset {encoding!r}."
                        )
                else:
                    logger.warning(
                        f"Couldn't detect charset for record {record.record_id!r} from {target_url!r} "
                        f"with invalid original charset {record.http_charset!r}."
                    )

            return None

        with requests.Session() as session:
            response = session.get(self.warc_path, stream=True, headers=self.headers)
            response.raise_for_status()

            for warc_record in ArchiveIterator(response.raw, record_types=WarcRecordType.response, verify_digests=True):
                if not warc_record.record_date:
                    continue

                target_url = str(warc_record.headers["WARC-Target-URI"])

                if url_filter is not None and url_filter(target_url):
                    logger.debug(f"Skipped WARC record with target URI {target_url!r} because of URL filter")
                    continue

                publisher_domain: str = urlparse(target_url).netloc

                if publisher_domain not in self._publisher_mapping:
                    continue

                publisher = self._publisher_mapping[publisher_domain]

                if publisher.url_filter is not None and publisher.url_filter(target_url):
                    logger.debug(
                        f"Skipped WARC record with target URI {target_url!r} because of publisher specific URL filter"
                    )
                    continue

                if (content := extract_content(warc_record)) is None:
                    continue

                yield HTML(
                    requested_url=target_url,
                    responded_url=target_url,
                    content=content,
                    crawl_date=warc_record.record_date,
                    source_info=WarcSourceInfo(
                        publisher=publisher.name,
                        warc_path=self.warc_path,
                        warc_headers=dict(warc_record.headers),
                        http_headers=dict(warc_record.http_headers or {}),
                    ),
                )
