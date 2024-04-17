import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, Iterator, List, Optional, Protocol
from urllib.parse import urlparse

import chardet
import requests
import validators
from fastwarc import ArchiveIterator, WarcRecord, WarcRecordType
from requests import ConnectionError, HTTPError

from fundus.logging import basic_logger
from fundus.publishers.base_objects import PublisherEnum
from fundus.scraping.delay import Delay
from fundus.scraping.filter import URLFilter
from fundus.scraping.session import _default_header

__all__ = [
    "HTML",
    "SourceInfo",
    "WarcSourceInfo",
    "WebSourceInfo",
    "HTMLSource",
    "WebSource",
    "CCNewsSource",
]

from fundus.scraping.session import session_handler
from fundus.scraping.url import URLSource


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
        publisher: str,
        url_filter: Optional[URLFilter] = None,
        request_header: Optional[Dict[str, str]] = None,
        delay: Optional[Delay] = None,
    ):
        self.url_source = url_source
        self.publisher = publisher
        self.url_filter = url_filter
        self.request_header = request_header or _default_header
        if isinstance(url_source, URLSource):
            url_source.set_header(self.request_header)
        self.delay = delay

    def fetch(self, url_filter: Optional[URLFilter] = None) -> Iterator[HTML]:
        combined_filters: List[URLFilter] = ([self.url_filter] if self.url_filter else []) + (
            [url_filter] if url_filter else []
        )

        timestamp = time.time() + self.delay() if self.delay is not None else time.time()

        def filter_url(u: str) -> bool:
            return any(f(u) for f in combined_filters)

        for url in self.url_source:
            if self.delay:
                time.sleep(max(0.0, self.delay() - time.time() + timestamp))
                timestamp = time.time()

            if not validators.url(url):
                basic_logger.debug(f"Skipped requested URL '{url}' because the URL is malformed")
                continue

            if filter_url(url):
                basic_logger.debug(f"Skipped requested URL '{url}' because of URL filter")
                continue

            session = session_handler.get_session()

            try:
                response = session.get(url, headers=self.request_header)

            except (HTTPError, ConnectionError) as error:
                basic_logger.info(f"Skipped requested URL '{url}' because of '{error}'")
                if isinstance(error, HTTPError) and error.response.status_code >= 500:
                    basic_logger.info(f"Skipped {self.publisher} due to server errors: '{error}'")
                continue

            except Exception as error:
                basic_logger.warning(f"Warning! Skipped  requested URL '{url}' because of an unexpected error {error}")
                continue

            else:
                if filter_url(str(response.url)):
                    basic_logger.debug(f"Skipped responded URL '{str(response.url)}' because of URL filter")
                    continue
                html = response.text

                if response.history:
                    basic_logger.info(f"Got redirected {len(response.history)} time(s) from {url} -> {response.url}")

                source_info = (
                    WebSourceInfo(self.publisher, type(self.url_source).__name__, self.url_source.url)
                    if isinstance(self.url_source, URLSource)
                    else SourceInfo(self.publisher)
                )

                yield HTML(
                    requested_url=url,
                    responded_url=str(response.url),
                    content=html,
                    crawl_date=datetime.now(),
                    source_info=source_info,
                )


class CCNewsSource:
    def __init__(self, *publishers: PublisherEnum, warc_path: str, headers: Optional[Dict[str, str]] = None):
        self.publishers = publishers
        self.warc_path = warc_path
        self.headers = headers or _default_header

        self._publisher_mapping: Dict[str, PublisherEnum] = {
            urlparse(publisher.domain).netloc: publisher for publisher in publishers
        }

    def fetch(self, url_filter: Optional[URLFilter] = None) -> Iterator[HTML]:
        def extract_content(record: WarcRecord) -> Optional[str]:
            warc_body: bytes = record.reader.read()

            try:
                return str(warc_body, encoding=record.http_charset)
            except (UnicodeDecodeError, TypeError):
                encoding: Optional[str] = chardet.detect(warc_body)["encoding"]

                if encoding is not None:
                    basic_logger.debug(
                        f"Trying to decode record {record.record_id!r} from {target_url!r} "
                        f"using detected encoding {encoding}."
                    )

                    try:
                        return str(warc_body, encoding=encoding)
                    except UnicodeDecodeError:
                        basic_logger.warning(
                            f"Couldn't decode record {record.record_id!r} from {target_url!r} with "
                            f"original charset {record.http_charset!r} using detected charset {encoding!r}."
                        )
                else:
                    basic_logger.warning(
                        f"Couldn't detect charset for record {record.record_id!r} from {target_url!r} "
                        f"with invalid original charset {record.http_charset!r}."
                    )

            return None

        with requests.Session() as session:
            stream = session.get(self.warc_path, stream=True, headers=self.headers).raw

            for warc_record in ArchiveIterator(stream, record_types=WarcRecordType.response, verify_digests=True):
                target_url = str(warc_record.headers["WARC-Target-URI"])

                if url_filter is not None and url_filter(target_url):
                    basic_logger.debug(f"Skipped WARC record with target URI {target_url!r} because of URL filter")
                    continue

                publisher_domain: str = urlparse(target_url).netloc

                if publisher_domain not in self._publisher_mapping:
                    continue

                publisher = self._publisher_mapping[publisher_domain]

                if publisher.url_filter is not None and publisher.url_filter(target_url):
                    basic_logger.debug(
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
                        publisher=publisher.publisher_name,
                        warc_path=self.warc_path,
                        warc_headers=dict(warc_record.headers),
                        http_headers=dict(warc_record.http_headers),
                    ),
                )
