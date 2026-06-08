from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator, Optional
from urllib.parse import urlparse

import chardet
import requests
import urllib3.exceptions
from fastwarc import ArchiveIterator, WarcRecord, WarcRecordType
from fastwarc.stream_io import StreamError

from fundus.logging import create_logger
from fundus.publishers.base_objects import Publisher
from fundus.scraping.filter import URLFilter
from fundus.scraping.html import HTML, SourceInfo
from fundus.scraping.session import _default_header

logger = create_logger(__name__)


class WarcFileLoadError(Exception):
    """Raised when a CC-NEWS WARC archive cannot be downloaded or its stream is corrupt or truncated."""


@dataclass(frozen=True)
class WarcSourceInfo(SourceInfo):
    """Origin metadata attached to an HTML record extracted from a CC-NEWS WARC archive.

    Attributes:
        warc_path (str): HTTPS URL of the WARC archive the record came from.
        warc_headers (Dict[str, str]): WARC envelope headers (e.g. WARC-Target-URI, WARC-Date).
        http_headers (Dict[str, str]): HTTP response headers captured by the original crawl.
    """

    warc_path: str
    warc_headers: Dict[str, str]
    http_headers: Dict[str, str]


class CCNewsSource:
    """HTML source backed by a single CC-NEWS WARC archive on Common Crawl.

    Streams the archive once, walks its response records, and yields HTML for those records whose
    target URI matches one of the configured publishers' domains. Unlike WebSource, there is no
    per-URL network request: the archive contains pages already crawled by Common Crawl, so this
    source is effectively a selection-and-decode pipeline over a pre-fetched corpus.
    """

    def __init__(self, *publishers: Publisher, warc_path: str, headers: Optional[Dict[str, str]] = None) -> None:
        """Initialize a source over a single CC-NEWS WARC archive.

        Args:
            *publishers (Publisher): Publishers whose articles should be extracted. WARC records
                whose target URI does not belong to any of these publishers' domains are dropped
                during iteration.
            warc_path (str): HTTPS URL of the WARC archive to read (e.g. a CC-NEWS .warc.gz path).
            headers (Optional[Dict[str, str]]): Request headers for the WARC download. Defaults to
                the shared fundus user-agent header.

        """
        self.publishers = publishers
        self.warc_path = warc_path
        self.headers = headers or _default_header
        self._publisher_mapping: Dict[str, Publisher] = {
            urlparse(publisher.domain).netloc: publisher for publisher in self.publishers
        }

    @staticmethod
    def _extract_content(record: WarcRecord, target_url: str) -> Optional[str]:
        """Decode the WARC body using the declared charset, falling back to chardet detection."""
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

    def _validate(self, target_url: str, url_filter: Optional[URLFilter]) -> Optional[Publisher]:
        """Return the matching publisher, or None if the URL should be skipped."""
        if url_filter is not None and url_filter(target_url):
            logger.debug(f"Skipped WARC record with target URI {target_url!r} because of URL filter")
            return None
        publisher = self._publisher_mapping.get(urlparse(target_url).netloc)
        if publisher is None:
            return None
        if publisher.url_filter is not None and publisher.url_filter(target_url):
            logger.debug(f"Skipped WARC record with target URI {target_url!r} because of publisher specific URL filter")
            return None
        return publisher

    def _record_to_html(self, record: WarcRecord, url_filter: Optional[URLFilter]) -> Optional[HTML]:
        """Validate, decode, and assemble a single WARC record. Returns None if skipped."""
        record_date = record.record_date
        if record_date is None:
            return None
        target_url = str(record.headers["WARC-Target-URI"])
        if (publisher := self._validate(target_url, url_filter)) is None:
            return None
        if (content := self._extract_content(record, target_url)) is None:
            return None
        return HTML(
            requested_url=target_url,
            responded_url=target_url,
            content=content,
            crawl_date=record_date,
            source_info=WarcSourceInfo(
                publisher=publisher.name,
                warc_path=self.warc_path,
                warc_headers=dict(record.headers),
                http_headers=dict(record.http_headers or {}),
            ),
        )

    def _open_stream(self) -> requests.Response:
        """Open a streaming GET against the WARC archive. Wraps transport errors in WarcFileLoadError."""
        try:
            session = requests.Session()
            response = session.get(self.warc_path, stream=True, headers=self.headers)
            response.raise_for_status()
            return response
        except (requests.HTTPError, urllib3.exceptions.HTTPError) as error:
            raise WarcFileLoadError(f"{type(error).__name__}: {error}") from error

    @staticmethod
    def _iter_warc_records(response: requests.Response) -> Iterator[WarcRecord]:
        """Iterate WARC response records from the open stream. Wraps StreamError in WarcFileLoadError."""
        try:
            yield from ArchiveIterator(response.raw, record_types=WarcRecordType.response, verify_digests=True)
        except StreamError as error:
            raise WarcFileLoadError(f"{type(error).__name__}: {error}") from error

    def fetch(self, url_filter: Optional[URLFilter] = None) -> Iterator[HTML]:
        """Stream HTML records from the configured WARC archive.

        Walks every response record in the archive, keeps those whose target URI matches a
        configured publisher and passes the URL filters, decodes the body, and yields the
        resulting HTML record.

        Args:
            url_filter (Optional[URLFilter]): Per-call URL filter applied in addition to each
                publisher's own url_filter. Truthy means skip the URL.

        Yields:
            HTML: One record per kept WARC entry.

        Raises:
            WarcFileLoadError: If the archive cannot be downloaded or the WARC stream is corrupt.

        """
        response = self._open_stream()
        for record in self._iter_warc_records(response):
            if (html := self._record_to_html(record, url_filter)) is not None:
                yield html
