"""Simplified real-subclass implementations of internal interfaces.

A *fake* is a working, behavior-correct simplified implementation — distinct from a stub
(dumb data holder) and a mock (call-recorder). Use a fake when the real method dispatch
matters but the production implementation is expensive or pulls in external dependencies.

This module deliberately does NOT match the ``fixture_*.py`` glob picked up by conftest.
"""

from __future__ import annotations

from typing import Iterator, List, Optional, Sequence, Tuple

from fundus.publishers.base_objects import Publisher
from fundus.scraping.article import Article
from fundus.scraping.crawler.base import CrawlerBase, PublisherType
from fundus.scraping.filter import ExtractionFilter, URLFilter


class FakeCrawler(CrawlerBase):
    """CrawlerBase subclass that yields a fixed sequence of pre-built articles."""

    def __init__(self, *publishers: PublisherType, articles: Sequence[Article] = ()) -> None:
        super().__init__(*publishers)
        self._articles = list(articles)

    def _build_article_iterator(
        self,
        publishers: Tuple[Publisher, ...],
        raise_on_error: bool,
        extraction_filter: Optional[ExtractionFilter],
        url_filter: Optional[URLFilter],
        language_filter: Optional[List[str]],
        skip_publishers_disallowing_training: bool = False,
    ) -> Iterator[Article]:
        yield from self._articles
