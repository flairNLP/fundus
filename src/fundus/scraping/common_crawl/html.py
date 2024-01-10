from typing import Dict, Iterator, List, Optional, cast
from urllib.parse import urlparse

import requests
from fastwarc import ArchiveIterator, WarcRecord, WarcRecordType
from ftfy import guess_bytes

from fundus.logging import basic_logger
from fundus.publishers.base_objects import PublisherEnum
from fundus.scraping.filter import URLFilter
from fundus.scraping.html import HTML, WarcSource


class CCNewsSource:
    def __init__(self, *publishers: PublisherEnum, warc_path: str, headers: Optional[Dict[str, str]] = None):
        self.publishers = publishers
        self.warc_path = warc_path
        self.headers = headers or {}

        self._publisher_mapping: Dict[str, PublisherEnum] = {
            urlparse(publisher.domain).netloc: publisher for publisher in publishers
        }
        self._url_filters: List[URLFilter] = [
            url_filter for publisher in publishers if (url_filter := publisher.url_filter) is not None
        ]

    def fetch(self, url_filter: Optional[URLFilter] = None) -> Iterator[HTML]:
        domains = list(self._publisher_mapping)

        def extract_body(record: WarcRecord) -> str:
            raw_body = record.reader.read()
            try:
                return str(raw_body, encoding=record.http_charset)
            except (UnicodeDecodeError, TypeError):
                return guess_bytes(raw_body)[0]

        with requests.Session() as session:
            stream = session.get(self.warc_path, stream=True, headers=self.headers).raw

            for warc_record in ArchiveIterator(stream, record_types=WarcRecordType.response, verify_digests=True):
                target_uri = str(warc_record.headers["WARC-Target-URI"])

                # TODO: Don't apply all filter at once, but per publisher
                if url_filter and url_filter(target_uri):
                    basic_logger.debug(f"Skipped WARC record with target URI {target_uri!r} because of URL filter")
                    continue
                elif (netloc := urlparse(target_uri).netloc) in domains:
                    publisher = self._publisher_mapping[netloc]

                    if publisher.url_filter is not None and publisher.url_filter(target_uri):
                        basic_logger.debug(
                            f"Skipped WARC record with target URI {target_uri!r} because of "
                            f"publisher specific URL filter"
                        )
                        continue

                    # parse record
                    body = extract_body(warc_record)
                    html = HTML(
                        requested_url=target_uri,
                        responded_url=target_uri,
                        content=body,
                        crawl_date=warc_record.record_date,
                        source=WarcSource(
                            publisher=publisher.publisher_name,
                            warc_path=self.warc_path,
                            warc_headers=dict(warc_record.headers),
                            http_headers=dict(warc_record.http_headers),
                        ),
                    )
                    yield html
