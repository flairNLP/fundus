import bz2
import gzip
import itertools
import lzma
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import cached_property
from typing import Callable, ClassVar, Dict, Iterable, Iterator, List, Optional, Set
from urllib.parse import unquote

import feedparser
import lxml.html
import validators
from lxml.cssselect import CSSSelector
from lxml.etree import XPath
from requests import ConnectionError, HTTPError, ReadTimeout

from fundus.logging import create_logger
from fundus.parser.utility import generic_nodes_to_text
from fundus.scraping.filter import URLFilter, inverse
from fundus.scraping.session import _default_header, session_handler

logger = create_logger(__name__)


class CompressionFormat:
    def __init__(
        self, name: str, decompression: Optional[Callable[[bytes], bytes]] = None, *, byte_mask: Optional[bytes] = None
    ) -> None:
        self.name = name
        self.decompression = decompression
        self.byte_mask = byte_mask

    def match(self, compressed_content: bytes) -> bool:
        if self.byte_mask:
            return compressed_content.startswith(self.byte_mask)
        return False

    def __call__(self, compressed_content: bytes) -> bytes:
        if self.decompression is None:
            raise NotImplementedError(f"Decompression not implemented for {self.name!r}")
        return self.decompression(compressed_content)

    def __repr__(self):
        if self.decompression is None:
            return f"{self.name} -- Not implemented"
        return self.name


class CompressionFormats:
    GZIP = CompressionFormat("gzip", gzip.decompress, byte_mask=b"\x1f\x8b")
    BZ2 = CompressionFormat("bz2", bz2.decompress, byte_mask=b"\x42\x5a")
    ZIP = CompressionFormat("zip", byte_mask=b"PK\x03\x04")
    LZMA = CompressionFormat("lzma", lzma.decompress, byte_mask=b"\x28\xb5\x2f\xfd")

    @classmethod
    def iter_formats(cls) -> Iterator[CompressionFormat]:
        for obj in cls.__dict__.values():
            if isinstance(obj, CompressionFormat):
                yield obj

    @classmethod
    def identify(cls, compressed_content: bytes) -> Optional[CompressionFormat]:
        for compression_format in cls.iter_formats():
            if compression_format.match(compressed_content):
                return compression_format
        return None


class _ArchiveDecompressor:
    def __init__(self):
        self.archive_mapping: Dict[str, Callable[[bytes], bytes]] = {
            "application/octet-stream": self._decompress_octet_stream,
            "application/x-gzip": CompressionFormats.GZIP,
            "gzip": CompressionFormats.GZIP,
        }

    def _decompress_octet_stream(self, compressed_content: bytes) -> bytes:
        if (compression_format := CompressionFormats.identify(compressed_content)) is None:
            logger.debug(f"Could not identify compression format")
            raise NotImplementedError

        return compression_format(compressed_content)

    def decompress(self, content: bytes, file_format: "str") -> bytes:
        decompress_function = self.archive_mapping[file_format]
        return decompress_function(content)

    @cached_property
    def supported_file_formats(self) -> List[str]:
        return list(self.archive_mapping.keys())


def clean_url(url: str) -> str:
    return unquote(url)


@dataclass
class URLSource(Iterable[str], ABC):
    url: str
    languages: Set[str] = field(default_factory=set)

    _request_header: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self._request_header:
            self._request_header = _default_header
        if not validators.url(self.url, strict_query=False):
            logger.error(f"{type(self).__name__} initialized with invalid URL {self.url}")

    def set_header(self, request_header: Dict[str, str]) -> None:
        self._request_header = request_header

    @abstractmethod
    def __iter__(self) -> Iterator[str]:
        raise NotImplemented

    def get_urls(self, max_urls: Optional[int] = None) -> Iterator[str]:
        """Returns a generator yielding up to <max_urls> URLs from <self>.


        Args:
            max_urls (int): Number of max URLs to return. Set value is
                an upper bound and not necessarily the actual number of
                URLs. If set to None, the source will be exhausted until
                StopIteration is hit. Defaults to None.

        Yields:
            str: The next URL.
        """
        return itertools.islice(self, max_urls)


@dataclass
class RSSFeed(URLSource):
    def __iter__(self) -> Iterator[str]:
        session = session_handler.get_session()
        try:
            response = session.get_with_interrupt(self.url, headers=self._request_header)

        except (HTTPError, ConnectionError, ReadTimeout) as err:
            logger.warning(f"Warning! Couldn't parse rss feed {self.url!r} because of {err}")
            return

        except Exception as error:
            logger.error(f"Warning! Couldn't parse rss feed {self.url!r} because of an unexpected error {error!r}")
            return

        html = response.text
        rss_feed = feedparser.parse(html)
        if exception := rss_feed.get("bozo_exception"):
            logger.warning(f"Warning! Couldn't parse rss feed {self.url!r} because of {exception}")
            return
        else:
            urls = filter(bool, (entry.get("link") for entry in rss_feed["entries"]))
            for url in urls:
                yield clean_url(url)


@dataclass
class Sitemap(URLSource):
    recursive: bool = True
    reverse: bool = False
    sitemap_filter: URLFilter = lambda url: not bool(url)

    _decompressor: ClassVar[_ArchiveDecompressor] = _ArchiveDecompressor()
    _sitemap_selector: ClassVar[XPath] = CSSSelector("sitemap > loc")
    _url_selector: ClassVar[XPath] = CSSSelector("url > loc")

    def __iter__(self) -> Iterator[str]:
        def yield_recursive(sitemap_url: str) -> Iterator[str]:
            session = session_handler.get_session()
            if not validators.url(sitemap_url):
                logger.info(f"Skipped sitemap {sitemap_url!r} because the URL is malformed")
            try:
                response = session.get_with_interrupt(url=sitemap_url, headers=self._request_header)

            except (HTTPError, ConnectionError, ReadTimeout) as error:
                logger.warning(f"Warning! Couldn't reach sitemap {sitemap_url!r} because of {error!r}")
                return

            except Exception as error:
                logger.error(
                    f"Warning! Couldn't reach sitemap {sitemap_url!r} because of an unexpected error {error!r}"
                )
                return

            content = response.content.strip()
            if (content_type := response.headers.get("content-type")) in self._decompressor.supported_file_formats:
                try:
                    content = self._decompressor.decompress(content, content_type)
                except NotImplementedError:
                    logger.warning(f"No matching decompression found for {sitemap_url!r}")
                    return
            if not content:
                logger.warning(f"Warning! Empty sitemap at {sitemap_url!r}")
                return
            tree = lxml.html.fromstring(content)
            urls = generic_nodes_to_text(self._url_selector(tree), normalize=True)
            if urls:
                for new_url in reversed(urls) if self.reverse else urls:
                    yield clean_url(new_url)
            elif self.recursive:
                sitemap_locs = [node.text_content() for node in self._sitemap_selector(tree)]
                filtered_locs = list(filter(inverse(self.sitemap_filter), sitemap_locs))
                for loc in reversed(filtered_locs) if self.reverse else filtered_locs:
                    yield from yield_recursive(loc)

        yield from yield_recursive(self.url)


@dataclass
class NewsMap(Sitemap):
    pass
