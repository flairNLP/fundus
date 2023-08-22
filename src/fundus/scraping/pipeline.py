import asyncio
import time
from typing import (
    AsyncIterator,
    Iterator,
    List,
    Literal,
    Optional,
    Protocol,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    runtime_checkable,
)

import more_itertools

from fundus.logging import basic_logger
from fundus.publishers.base_objects import PublisherEnum
from fundus.scraping.article import Article
from fundus.scraping.filter import ExtractionFilter, URLFilter
from fundus.scraping.html import URLSource, session_handler
from fundus.scraping.scraper import Scraper
from fundus.utils.more_async import async_next
from fundus.utils.more_async import zip_longest as async_zip_longest
from fundus.utils.validation import listify

_T = TypeVar("_T")


@runtime_checkable
class Delay(Protocol):
    """Protocol to define crawl delays between batches."""

    def __call__(self) -> float:
        """Yields a float specifying the minimum crawler delay for the current article batch in seconds.

        The effective delay does include crawling execution time between batches,
        i.e. the effective delay is max(execution_time, delay).

        Examples:
            >>> import random
            >>> delay: Delay = lambda: random.random()
            Will use a random delay in [0, 1) seconds.

        Returns:
            float: The delay time in seconds.

        """
        ...


class BaseCrawler:
    def __init__(self, *scrapers: Scraper):
        """Basic pipeline to utilize scrapers.

        Because scrapers are implemented asynchronously, this pipeline handles the necessary event loops
        and program logic to download articles in batches asynchronously.

        Args:
            *scrapers (Scraper): The scrapers which should be used.
        """
        self.scrapers: Tuple[Scraper, ...] = scrapers

    async def crawl_async(
        self,
        max_articles: Optional[int] = None,
        error_handling: Literal["suppress", "catch", "raise"] = "suppress",
        only_complete: Union[bool, ExtractionFilter] = True,
        delay: Optional[Union[float, Delay]] = None,
        url_filter: Optional[URLFilter] = None,
        only_unique: bool = True,
    ) -> AsyncIterator[Article]:
        """Async variant of the crawl() method.

        See docstring for crawl(). for detailed information about the parameters.

        Args:
            max_articles (Optional[int]): Number of articles to crawl. Defaults to None.
            error_handling (Literal["suppress", "catch", "raise"]): Set error handling. Defaults to "suppress".
            only_complete (Union[bool, ExtractionFilter]): Set extraction filters. Defaults to True
            delay (Optional[Union[float, Delay]]): Set delay time between article batches. Defaults to None.
            url_filter (Optional[URLFilter]): Set URLFilter. Defaults to None.
            only_unique (bool): If true return only unique responses. Defaults to True.

        Returns:
            AsyncIterator[Article]: An iterator yielding objects of type Article.
        """

        def build_extraction_filter() -> Optional[ExtractionFilter]:
            if isinstance(only_complete, bool):
                return (
                    None
                    if only_complete is False
                    else lambda extracted: not all(
                        bool(v) if not isinstance(v, Exception) else False for k, v in extracted.items()
                    )
                )
            else:
                return only_complete

        def build_delay() -> Optional[Delay]:
            if isinstance(delay, float):

                def constant_delay() -> float:
                    return delay  # type: ignore[return-value]

                return constant_delay
            else:
                return delay

        def build_unique_url_filter() -> URLFilter:
            return lambda url: url in response_cache

        # build filters and delay. this is for readability and typeguard reasons
        extraction_filter = build_extraction_filter()
        unique_url_filter = build_unique_url_filter() if only_unique else None
        final_delay = build_delay()

        response_cache: Set[str] = set()

        for scraper in self.scrapers:
            for source in scraper.sources:
                if url_filter:
                    source.add_url_filter(url_filter=url_filter)
                if unique_url_filter:
                    source.add_url_filter(url_filter=unique_url_filter)

        async_article_iterators: List[AsyncIterator[Optional[Article]]] = [
            scraper.scrape(
                error_handling=error_handling,
                extraction_filter=extraction_filter,
            )
            for scraper in self.scrapers
        ]

        # we use this custom variant of interleave_longest in order to be able
        # to delay the program flow between batches
        async def _async_article_interleave_longest() -> AsyncIterator[Article]:
            batches: AsyncIterator[Tuple[Optional[Article], ...]] = async_zip_longest(*async_article_iterators)
            start_time = time.time()
            async for batch in batches:
                basic_logger.debug(f"Batch took {time.time() - start_time} seconds")
                for value in batch:
                    if value is not None:
                        response_cache.add(value.html.responded_url)
                        yield value
                if final_delay:
                    await asyncio.sleep(final_delay() - time.time() + start_time)
                start_time = time.time()

        i: int = 0

        if max_articles is None:
            max_articles = -1
        elif max_articles == 0:
            return

        try:
            async for article in _async_article_interleave_longest():
                if i == max_articles:
                    break
                yield article
                i += 1
        finally:
            await session_handler.close_current_session()

    def crawl(
        self,
        max_articles: Optional[int] = None,
        error_handling: Literal["suppress", "catch", "raise"] = "suppress",
        only_complete: Union[bool, ExtractionFilter] = True,
        delay: Optional[Union[float, Delay]] = None,
        url_filter: Optional[URLFilter] = None,
        only_unique: bool = True,
    ) -> Iterator[Article]:
        """Yields articles from initialized publishers.

        Args:
            max_articles (Optional[int]): Number of articles to crawl. If there are fewer articles
                than max_articles the Iterator will stop before max_articles. If None, all retrievable
                articles are returned. Defaults to None.
            error_handling (Literal["suppress", "catch", "raise"]): Define how to handle errors
                encountered during extraction. If set to "suppress", all errors will be skipped, either
                with None values for respective attributes in the extraction or by skipping entire articles.
                If set to "catch", errors will be caught as attribute values or, if an entire article fails,
                through Article.exception. If set to "raise" all errors encountered during extraction will
                be raised. Defaults to "suppress".
            only_complete (Union[bool, ExtractionFilter]): Set extraction filters. If False, all articles
                will be yielded, if True, only complete ones. Defaults to True. See the docs for more
                information about ExtractionFilter.
            delay (Optional[Union[float, Delay]]): Set a delay time in seconds to be used between article
                batches. You can set a delay directly using float or any callable satisfying the Delay
                protocol. If set to None, no delay will be used between batches. See Delay for more
                information. Defaults to None.
            url_filter (Optional[URLFilter]): A callable object satisfying the URLFilter protocol to skip
                URLs before download. This filter applies on both requested and responded URL. Defaults to None.
            only_unique (bool): If set to True, articles yielded will be unique on the responded URL.
                Always returns the first encountered article. the Defaults to True.

        Returns:
            Iterator[Article]: An iterator yielding objects of type Article.
        """

        async_article_iter = self.crawl_async(
            max_articles=max_articles,
            error_handling=error_handling,
            only_complete=only_complete,
            delay=delay,
            url_filter=url_filter,
            only_unique=only_unique,
        )

        try:
            event_loop = asyncio.get_running_loop()
            if event_loop:
                raise AssertionError(
                    "There is already an eventloop running. If you want to crawl articles inside an "
                    "async environment use crawl_async() instead."
                )
        except RuntimeError:
            event_loop = asyncio.new_event_loop()

        try:
            while True:
                if nxt := event_loop.run_until_complete(async_next(async_article_iter, None)):
                    yield nxt
                else:
                    break
        finally:
            event_loop.run_until_complete(event_loop.shutdown_asyncgens())
            event_loop.close()


class Crawler(BaseCrawler):
    def __init__(
        self,
        *publishers: Union[PublisherEnum, Type[PublisherEnum]],
        restrict_sources_to: Optional[List[Type[URLSource]]] = None,
    ):
        """Fundus base class for crawling articles from the web.

        Examples:
            >>> from fundus import PublisherCollection, Crawler
            >>> crawler = Crawler(*PublisherCollection)
            >>> # Crawler(*PublisherCollection.us) to crawl only english news
            >>> for article in crawler.crawl():
            >>>     print(article)

        Args:
            *publishers (Union[PublisherEnum, Type[PublisherEnum]]): The publishers to crawl.
            restrict_sources_to (Optional[List[Literal["rss", "sitemap", "news"]]]): Let's you restrict
                sources defined in the publisher specs. If set, only articles from given source types
                will be yielded.
        """

        if not publishers:
            raise ValueError("param <publishers> of <Crawler.__init__> has to be non empty")
        nested_publisher = [listify(publisher) for publisher in publishers]
        self.publishers: Set[PublisherEnum] = set(more_itertools.flatten(nested_publisher))

        # build scraper
        scrapers: List[Scraper] = []
        for spec in self.publishers:
            if restrict_sources_to:
                sources = more_itertools.flatten(
                    spec.source_mapping[source_type] for source_type in restrict_sources_to
                )
            else:
                sources = more_itertools.flatten(spec.source_mapping.values())

            if sources:
                scrapers.append(
                    Scraper(
                        *sources,
                        parser=spec.parser,
                    )
                )

        super().__init__(*scrapers)
