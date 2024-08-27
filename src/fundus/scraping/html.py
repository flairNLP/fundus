import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, Iterator, List, Optional, Protocol
from urllib.parse import urlparse

import chardet
import lxml.html
import requests
import validators
from fastwarc import ArchiveIterator, WarcRecord, WarcRecordType
from lxml.cssselect import CSSSelector
from requests import ConnectionError, HTTPError

from fundus.logging import create_logger
from fundus.publishers.base_objects import Publisher
from fundus.scraping.delay import Delay
from fundus.scraping.filter import URLFilter
from fundus.scraping.session import _default_header, session_handler
from fundus.scraping.url import URLSource

__all__ = [
    "HTML",
    "SourceInfo",
    "WarcSourceInfo",
    "WebSourceInfo",
    "HTMLSource",
    "WebSource",
    "CCNewsSource",
]

logger = create_logger(__name__)

# unfortunately lxml does not support case-insensitive CSSSelectors
_content_type_selector = CSSSelector("meta[http-equiv='Content-Type'], meta[http-equiv='content-type']")


def _detect_charset_from_response(response: requests.Response) -> str:
    """Detects HTML encoding based on meta tag <http-equiv='Content-Type'>

    Args:
        response: Response to detect encoding for

    Returns:
        str: detected encoding or response.apparent_encoding
    """
    # see https://github.com/flairNLP/fundus/issues/446
    # use response fallback to decode HTML in a first guess
    guessed_text = response.content.decode(response.encoding or "utf-8")
    charset = None
    if (content_type_nodes := _content_type_selector(lxml.html.document_fromstring(guessed_text))) and len(
        content_type_nodes
    ) == 1:
        content_type_node = content_type_nodes.pop()
        for field in content_type_node.attrib.get("content", "").split(";"):
            if "charset" in field:
                charset = field.replace("charset=", "").strip()
    return charset or response.apparent_encoding


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
    def fetch(self, url_filter: Optional[URLFilter] = None) -> Iterator[HTML]:
        ...


class WebSource:
    def __init__(
        self,
        url_source: Iterable[str],
        publisher: Publisher,
        url_filter: Optional[URLFilter] = None,
        request_header: Optional[Dict[str, str]] = None,
        query_parameters: Optional[Dict[str, str]] = None,
        delay: Optional[Delay] = None,
        ignore_robots: Optional[bool] = False,
    ):
        self.url_source = url_source
        self.publisher = publisher
        self.url_filter = url_filter
        self.request_header = request_header or _default_header
        self.query_parameters = query_parameters or {}
        if isinstance(url_source, URLSource):
            url_source.set_header(self.request_header)
        self.delay = delay
        self.ignore_robots = ignore_robots

    def fetch(self, url_filter: Optional[URLFilter] = None) -> Iterator[HTML]:
        combined_filters: List[URLFilter] = ([self.url_filter] if self.url_filter else []) + (
            [url_filter] if url_filter else []
        )

        timestamp = time.time() + self.delay() if self.delay is not None else time.time()

        if not self.publisher.robots.timestamp:
            self.publisher.robots.read()

        def filter_url(u: str) -> bool:
            return any(f(u) for f in combined_filters)

        for url in self.url_source:
            if not validators.url(url):
                logger.debug(f"Skipped requested URL {url!r} because the URL is malformed")
                continue

            if filter_url(url):
                logger.debug(f"Skipped requested URL {url!r} because of URL filter")
                continue

            if not (
                self.ignore_robots or self.publisher.robots.can_fetch(self.request_header.get("user-agent") or "*", url)
            ):
                logger.debug(f"Skipped requested URL {url!r} because of robots.txt")
                continue

            session = session_handler.get_session()
            for key, value in self.query_parameters.items():
                if "?" in url:
                    url += "&" + key + "=" + value
                else:
                    url += "?" + key + "=" + value

            if self.delay:
                time.sleep(max(0.0, self.delay() - time.time() + timestamp))
                timestamp = time.time()

            try:
                response = session.get(url, headers=self.request_header)

            except (HTTPError, ConnectionError) as error:
                logger.info(f"Skipped requested URL {url!r} because of {error!r}")
                if isinstance(error, HTTPError) and error.response.status_code >= 500:
                    logger.info(f"Skipped {self.publisher!r} due to server errors: {error!r}")
                continue

            except Exception as error:
                logger.warning(f"Warning! Skipped  requested URL {url!r} because of an unexpected error {error!r}")
                continue

            else:
                if "charset" not in response.headers["content-type"]:
                    # That's actually the only place requests checks to detect encoding, so if charset
                    # is not set, requests falls back to default encodings (latin-1/utf-8)
                    response.encoding = _detect_charset_from_response(response)

                if filter_url(str(response.url)):
                    logger.debug(f"Skipped responded URL {str(response.url)!r} because of URL filter")
                    continue
                html = response.text

                if response.history:
                    logger.info(f"Got redirected {len(response.history)} time(s) from {url!r} -> {response.url!r}")

                source_info = (
                    WebSourceInfo(self.publisher.name, type(self.url_source).__name__, self.url_source.url)
                    if isinstance(self.url_source, URLSource)
                    else SourceInfo(self.publisher.name)
                )

                yield HTML(
                    requested_url=url,
                    responded_url=str(response.url),
                    content=html,
                    crawl_date=datetime.now(),
                    source_info=source_info,
                )


class CCNewsSource:
    def __init__(self, *publishers: Publisher, warc_path: str, headers: Optional[Dict[str, str]] = None):
        self.publishers = publishers
        self.warc_path = warc_path
        self.headers = headers or _default_header
        self._publisher_mapping: Dict[str, Publisher] = {
            urlparse(publisher.domain).netloc: publisher for publisher in self.publishers
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
                        f"Skipped WARC record with target URI {target_url!r} because of "
                        f"publisher specific URL filter"
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
