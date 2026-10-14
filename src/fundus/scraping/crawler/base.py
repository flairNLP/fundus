from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from typing import (
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

import more_itertools

from fundus.logging import create_logger
from fundus.parser import BaseParser
from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.article import Article
from fundus.scraping.filter import ExtractionFilter, Requires, RequiresAll, URLFilter
from fundus.scraping.session import session_handler
from fundus.scraping.url import strip_query_and_fragment
from fundus.utils.events import __EVENTS__, __MAIN_THREAD_ALIAS__
from fundus.utils.timeout import Timeout

logger = create_logger(__name__)

PublisherType = Union[Publisher, PublisherGroup]


def supports_attributes(extraction_filter: Optional[ExtractionFilter], versions: Iterable[Type[BaseParser]]) -> bool:
    """Returns True, if one of <versions> covers what <extraction_filter> requires.

    The required attributes have to be covered by one and the same version, since an article is
    parsed by a single version: versions splitting the requirements between them cover none of
    them. Without a version in reach, nothing can be extracted at all.

    Args:
        extraction_filter (Optional[ExtractionFilter]): The filter the extractions are checked
            against. Only a <Requires> names attributes a parser version has to support.
        versions (Iterable[Type[BaseParser]]): The parser versions the extraction can end up using.

    Returns:
        bool: True if the required attributes are within reach.
    """
    if not isinstance(extraction_filter, Requires):
        return True

    return any(extraction_filter.required_attributes <= set(version.attributes().names) for version in versions)


class _CrawlState:
    """Tracks per-publisher and total article counts, a dedup cache, and optionally the kept articles."""

    def __init__(self, only_unique: bool, track_articles: bool) -> None:
        """Initialize counters; only_unique enables URL dedup, track_articles retains accepted articles."""
        self._only_unique = only_unique
        self._track_articles = track_articles

        self._response_cache: Set[str] = set()

        self.article_count: Dict[str, int] = defaultdict(int)
        self.total_count: int = 0
        self.crawled_articles: Dict[str, List[Article]] = defaultdict(list)

    def accept(self, article: Article) -> bool:
        """Record the article in the running counts; return False if dropped as a duplicate."""
        url = strip_query_and_fragment(article.html.responded_url)
        if self._only_unique and url in self._response_cache:
            return False
        self._response_cache.add(url)
        self.article_count[article.publisher] += 1
        self.total_count += 1
        if self._track_articles:
            self.crawled_articles[article.publisher].append(article)
        return True


class CrawlerBase(ABC):
    """Base class for crawlers: holds the publisher set and drives the shared crawl() loop.

    Subclasses implement _build_article_iterator to supply articles from a concrete backend
    (the live web in Crawler, the CC-NEWS archive in CCNewsCrawler); crawl() layers on the
    publisher/attribute/language filtering, limits, timeout, dedup, and optional file export.
    """

    def __init__(self, *publishers: PublisherType) -> None:
        """Collect and de-duplicate the publishers to crawl.

        Args:
            *publishers (PublisherType): Publishers or publisher groups to crawl. Groups are
                flattened and duplicate publishers removed.

        Raises:
            ValueError: If no publishers are supplied.

        """
        self.publishers: List[Publisher] = list(set(more_itertools.collapse(publishers)))
        if not self.publishers:
            raise ValueError("param <publishers> of <Crawler.__init__> must include at least one publisher.")

    @abstractmethod
    def _supports_attributes(self, publisher: Publisher, extraction_filter: Optional[ExtractionFilter]) -> bool:
        """Returns True, if <publisher> can extract what <extraction_filter> requires.

        Which parser versions an extraction can end up using depends on how the crawler reaches
        its articles, so every crawler answers this for the versions within its own reach.
        """
        raise NotImplementedError

    @abstractmethod
    def _build_article_iterator(
        self,
        publishers: Tuple[Publisher, ...],
        raise_on_error: bool,
        extraction_filter: Optional[ExtractionFilter],
        url_filter: Optional[URLFilter],
        skip_publishers_disallowing_training: bool = False,
    ) -> Iterator[Article]:
        """Yield articles from the concrete backend. Implemented by each crawler subclass."""
        raise NotImplementedError

    def _on_timeout(self) -> None:
        """Hook invoked when the crawl timeout fires; no-op by default, overridden where cleanup is needed."""
        pass

    def _on_publisher_limit_reached(self, publisher_name: str) -> None:
        """Hook invoked when a publisher hits its per-publisher article limit; no-op by default."""
        pass

    @staticmethod
    def _build_extraction_filter(only_complete: Union[bool, ExtractionFilter]) -> Optional[ExtractionFilter]:
        """Resolve the only_complete argument into an ExtractionFilter, or None to keep everything."""
        if isinstance(only_complete, bool):
            return None if only_complete is False else RequiresAll()
        return only_complete

    def _fitting_publishers(
        self,
        extraction_filter: Optional[ExtractionFilter],
        language_filter: Optional[List[str]],
    ) -> List[Publisher]:
        """Restrict the publishers to <language_filter> and keep those left with something to contribute.

        Restricted here rather than while crawling, since <language_filter> is the last piece of
        information to arrive. From now on a publisher carries exactly the sources and languages
        it is meant to contribute, and nothing downstream has to filter again.
        """
        fitting_publishers: List[Publisher] = []
        for publisher in (publisher.restrict(languages=language_filter) for publisher in self.publishers):
            if not publisher.supports():
                logger.debug(f"Skipping {publisher.name} because none of its sources matches the restrictions")
            elif not self._supports_attributes(publisher, extraction_filter):
                logger.debug(f"Skipping {publisher.name} because it can't extract the required attributes")
            else:
                fitting_publishers.append(publisher)

        if fitting_publishers and (skipped := len(self.publishers) - len(fitting_publishers)):
            logger.warning(f"Skipping {skipped} of {len(self.publishers)} publisher(s) not matching the restrictions")
        return fitting_publishers

    @staticmethod
    def _save_articles(path: Union[str, Path], articles: Dict[str, List[Article]]) -> None:
        """Write the collected articles to <path> as a JSON list, creating parent dirs as needed."""
        if isinstance(path, str):
            path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            logger.info(f"Writing crawled articles to {path!r}")
            file.write(json.dumps(articles, default=lambda o: o.to_json(), ensure_ascii=False, indent=4))

    def crawl(
        self,
        max_articles: Optional[int] = None,
        max_articles_per_publisher: Optional[int] = None,
        timeout: Optional[float] = None,
        raise_on_error: bool = False,
        only_complete: Union[bool, ExtractionFilter] = Requires("title", "body", "publishing_date"),
        url_filter: Optional[URLFilter] = None,
        language_filter: Optional[List[str]] = None,
        only_unique: bool = True,
        save_to_file: Union[None, str, Path] = None,
        skip_publishers_disallowing_training: bool = False,
    ) -> Iterator[Article]:
        """Yields articles from the initialized crawlers.

        Args:
            max_articles (Optional[int]): Total number of articles to crawl. The iterator stops early
                if fewer articles are available. If None, yields every retrievable article. Defaults to None.
            max_articles_per_publisher (Optional[int]): Number of articles to crawl per publisher.
                Overrides <max_articles>. Defaults to None.
            timeout (Optional[float]): How long, in seconds, the crawler waits without receiving an
                article before stopping. If <= 0 or None, it runs until all sources are exhausted.
                Defaults to None.
            raise_on_error (bool): If True, errors encountered while parsing an Article are raised
                immediately, failing fast. If False, errors are skipped and attributes that fail to
                extract fall back to their default values. Defaults to False.
            only_complete (Union[bool, ExtractionFilter]): An ExtractionFilter, or a boolean shorthand.
                False yields every article; True yields only fully extracted ones. Defaults to a filter
                that passes articles with at least title, body, and publishing_date set.
            url_filter (Optional[URLFilter]): A URLFilter callable used to skip articles by URL, both
                before and after download. Applied to the requested and the responded URL. Defaults to None.
            language_filter (Optional[List[str]]): Language codes to keep. Articles in other languages
                are skipped and excluded from the article count. Publishers already restricted to
                certain languages, as returned by PublisherCollection.search, narrow this down further
                rather than widening it, so that a publisher never yields a language neither side asked
                for. Defaults to None.
            only_unique (bool): If True, deduplicates articles by their responded URL, yielding only
                the first article seen per URL. Defaults to True.
            save_to_file (Union[None, str, Path]): If set, collects the crawled articles and writes them
                to the given file as a JSON list. Defaults to None.
            skip_publishers_disallowing_training (bool): If True, skips publishers that disallow training.
                This is only an indicator; anyone gathering training data with Fundus should still review
                each publisher's terms of use. Defaults to False.

        Yields:
            Article: The extracted articles.

        Raises:
            ValueError: If no publisher matches the given restrictions.
        """
        if max_articles == 0:
            return

        if max_articles_per_publisher:
            if timeout is None or timeout < 120:
                logger.warning(
                    "It is recommended to set a minimum <timeout> of 120 seconds when using max_articles_per_publisher."
                )
            max_articles = None

        extraction_filter = self._build_extraction_filter(only_complete)
        fitting_publishers = self._fitting_publishers(extraction_filter, language_filter)

        if not fitting_publishers:
            raise ValueError("No publisher matches the given crawl restrictions.")

        state = _CrawlState(only_unique=only_unique, track_articles=save_to_file is not None)

        try:
            with __EVENTS__.main_context(__MAIN_THREAD_ALIAS__), Timeout(
                seconds=timeout,
                silent=True,
                callback=self._on_timeout,
            ) as timer:
                for article in self._build_article_iterator(
                    tuple(fitting_publishers),
                    raise_on_error,
                    extraction_filter,
                    url_filter,
                    skip_publishers_disallowing_training,
                ):
                    if (
                        max_articles_per_publisher
                        and state.article_count[article.publisher] == max_articles_per_publisher
                    ):
                        self._on_publisher_limit_reached(article.publisher)
                        if state.total_count == len(fitting_publishers) * max_articles_per_publisher:
                            break
                        continue

                    timer.reset()
                    if state.accept(article):
                        yield article

                    if max_articles is not None and state.total_count == max_articles:
                        break
        finally:
            session_handler.close_sessions()
            if save_to_file is not None:
                self._save_articles(save_to_file, state.crawled_articles)
