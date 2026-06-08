from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from typing import (
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

import more_itertools

from fundus.logging import create_logger
from fundus.publishers.base_objects import FilteredPublisher, Publisher, PublisherGroup
from fundus.scraping.article import Article
from fundus.scraping.filter import ExtractionFilter, Requires, RequiresAll, URLFilter
from fundus.scraping.session import session_handler
from fundus.scraping.url import strip_query_and_fragment
from fundus.utils.events import __EVENTS__, __MAIN_THREAD_ALIAS__
from fundus.utils.timeout import Timeout

logger = create_logger(__name__)

PublisherType = Union[Publisher, PublisherGroup]


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
        self.publishers: List[Union[Publisher, FilteredPublisher]] = list(set(more_itertools.collapse(publishers)))
        if not self.publishers:
            raise ValueError("param <publishers> of <Crawler.__init__> must include at least one publisher.")

    @abstractmethod
    def _build_article_iterator(
        self,
        publishers: Tuple[Publisher, ...],
        raise_on_error: bool,
        extraction_filter: Optional[ExtractionFilter],
        url_filter: Optional[URLFilter],
        language_filter: Optional[List[str]],
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

    def _filter_publishers(
        self,
        extraction_filter: Optional[ExtractionFilter],
        language_filter: Optional[List[str]],
    ) -> List[Union[Publisher, FilteredPublisher]]:
        """Drop publishers that can't supply the required attributes or any requested language."""
        if not isinstance(extraction_filter, Requires):
            return list(self.publishers)

        fitting_publishers: List[Union[Publisher, FilteredPublisher]] = []
        for publisher in self.publishers:
            supported_attributes = set(
                more_itertools.flatten(collection.names for collection in publisher.parser.attribute_mapping.values())
            )
            if missing_attributes := extraction_filter.required_attributes - supported_attributes:
                logger.warning(
                    f"The required attribute(s) `{', '.join(missing_attributes)}` "
                    f"is(are) not supported by {publisher.name}. Skipping publisher"
                )
            elif language_filter and not publisher.supports(languages=language_filter):
                logger.warning(
                    f"None of the required language(s) `{', '.join(language_filter)}` "
                    f"is(are) supported by {publisher.name}. Skipping publisher"
                )
            else:
                fitting_publishers.append(publisher)

        if not fitting_publishers:
            logger.error(
                f"Could not find any fitting publishers for required attributes "
                f"`{', '.join(extraction_filter.required_attributes)}`"
            )

        return fitting_publishers

    @staticmethod
    def _resolve_language_filter(
        publishers: List[Union[Publisher, FilteredPublisher]],
        language_filter: Optional[List[str]],
    ) -> Optional[List[str]]:
        """Merge the caller's language filter with each FilteredPublisher's own language filter."""
        publisher_language_filter: Set[str] = set()
        for publisher in publishers:
            if isinstance(publisher, FilteredPublisher):
                publisher_language_filter.update(publisher.language_filter)

        if language_filter and publisher_language_filter:
            return list(set(language_filter).union(publisher_language_filter))
        if publisher_language_filter:
            return list(publisher_language_filter)
        return language_filter

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
                are skipped and excluded from the article count. Defaults to None.
            only_unique (bool): If True, deduplicates articles by their responded URL, yielding only
                the first article seen per URL. Defaults to True.
            save_to_file (Union[None, str, Path]): If set, collects the crawled articles and writes them
                to the given file as a JSON list. Defaults to None.
            skip_publishers_disallowing_training (bool): If True, skips publishers that disallow training.
                This is only an indicator; anyone gathering training data with Fundus should still review
                each publisher's terms of use. Defaults to False.

        Yields:
            Article: The extracted articles.
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
        fitting_publishers = self._filter_publishers(extraction_filter, language_filter)

        if not fitting_publishers:
            return

        language_filter = self._resolve_language_filter(fitting_publishers, language_filter)

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
                    language_filter,
                    skip_publishers_disallowing_training,
                ):
                    if (
                        max_articles_per_publisher
                        and state.article_count[article.publisher] == max_articles_per_publisher
                    ):
                        self._on_publisher_limit_reached(article.publisher)
                        if state.total_count == len(self.publishers) * max_articles_per_publisher:
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
