import asyncio
import time
from typing import (
    AsyncIterator,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    Protocol,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

import more_itertools

from fundus.logging import basic_logger
from fundus.publishers.base_objects import PublisherEnum
from fundus.scraping.article import Article
from fundus.scraping.filter import ExtractionFilter, URLFilter
from fundus.scraping.html import URLSource, session_handler
from fundus.scraping.scraper import Scraper
from fundus.utils.more_async import async_next, batched_async_interleave
from fundus.utils.validation import listify


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


class Pipeline:
    def __init__(self, *scrapers: Scraper):
        """Basic pipeline to utilize scrapers.

        Because scrapers are implemented asynchronously, this pipeline handles the necessary event loops
        and program logic to download articles in batches asynchronously.

        Args:
            *scrapers (Scraper): The scrapers which should be used.
        """
        self.scrapers: Tuple[Scraper, ...] = scrapers

    def run(
        self,
        error_handling: Literal["suppress", "catch", "raise"],
        max_articles: Optional[int] = None,
        extraction_filter: Optional[ExtractionFilter] = None,
        delay: Optional[Delay] = lambda: 0.1,
        url_filter: Optional[URLFilter] = None,
        only_unique: bool = True,
    ) -> Iterator[Article]:
        """Yields articles from initialized scrapers.

        The articles will be requested concurrently with batch size := len(self.scrapers).
        You can specify a Delay to be used between the batches with <delay>

        Works like a light-wight version of Crawler.crawl(). Ment to be used when dealing with
        custom scrapers outside the context of predefined publisher collections.
        Refer to the docstring of Crawler.crawl() for more detailed information about the Args.

        Args:
            max_articles (Optional[int]): Maximal number of articles to be yielded. Defaults to None.
            error_handling (Literal["suppress", "catch", "raise"]): Set error handling
                for extraction. Defaults to "suppress".
            extraction_filter (Optional[ExtractionFilter]): Set extraction filter. Defaults to None.
            delay (Optional[Delay]): Set waiting time between article batches. Defaults to None.
            url_filter (Optional[URLFilter]): Set URLFilter. Defaults to None
            only_unique: (bool): If true return only unique responses. Defaults to True.

        Returns:
            Iterator[Article]: An iterator yielding objects of type Article.
        """

        response_cache: Set[str] = set()

        for scraper in self.scrapers:
            for source in scraper.sources:
                if url_filter:
                    source.add_url_filter(url_filter=url_filter)
                if only_unique:
                    source.add_url_filter(url_filter=lambda url: url in response_cache)

        async_article_iterators: List[AsyncIterator[Optional[Article]]] = [
            scraper.scrape(
                error_handling=error_handling,
                extraction_filter=extraction_filter,
            )
            for scraper in self.scrapers
        ]

        event_loop = asyncio.get_event_loop()

        def article_gen() -> Iterator[Article]:
            interleave: AsyncIterator[Iterable[Optional[Article]]] = batched_async_interleave(*async_article_iterators)
            while True:
                start_time = time.time()
                batch: Optional[Iterable[Optional[Article]]] = event_loop.run_until_complete(
                    async_next(interleave, None)
                )
                batch_time = time.time() - start_time
                if delay:
                    actual_delay = max(delay() - batch_time, 0.0)
                    event_loop.run_until_complete(asyncio.sleep(actual_delay))
                basic_logger.debug(f"Batch took {batch_time} seconds")
                if batch is not None:
                    for next_article in cast(Iterable[Article], filter(bool, batch)):
                        if only_unique:
                            response_cache.add(next_article.html.responded_url)
                        yield next_article
                else:
                    break

        gen = article_gen()

        if max_articles is not None:
            if max_articles > 0:
                for article in gen:
                    if not max_articles:
                        break
                    yield article
                    max_articles -= 1
        else:
            yield from gen

        # close current aiohttp session
        event_loop.run_until_complete(session_handler.close_current_session())


class Crawler:
    def __init__(self, *publishers: Union[PublisherEnum, Type[PublisherEnum]]):
        """Fundus base class for crawling articles from the web.

        Examples:
            >>> from fundus import PublisherCollection, Crawler
            >>> crawler = Crawler(*PublisherCollection)
            >>> # Crawler(*PublisherCollection.us) to crawl only english news
            >>> for article in crawler.crawl():
            >>>     print(article)

        Args:
            *publishers (Union[PublisherEnum, Type[PublisherEnum]]): The publishers to crawl.
        """
        if not publishers:
            raise ValueError("param <publishers> of <Crawler.__init__> has to be non empty")
        nested_publisher = [listify(publisher) for publisher in publishers]
        self.publishers: Set[PublisherEnum] = set(more_itertools.flatten(nested_publisher))

    def crawl(
        self,
        max_articles: Optional[int] = None,
        restrict_sources_to: Optional[List[Type[URLSource]]] = None,
        error_handling: Literal["suppress", "catch", "raise"] = "suppress",
        only_complete: Union[bool, ExtractionFilter] = True,
        delay: Optional[Union[float, Delay]] = None,
        url_filter: Optional[URLFilter] = None,
        only_unique: bool = True,
    ) -> Iterator[Article]:
        """Yields articles from initialized publishers

        Args:
            max_articles (Optional[int]): Number of articles to crawl. If there are fewer articles
                than max_articles the Iterator will stop before max_articles. If None, all retrievable
                articles are returned. Defaults to None.
            restrict_sources_to (Optional[List[Literal["rss", "sitemap", "news"]]]): Let's you restrict
                sources defined in the publisher specs. If set, only articles from given source types
                will be yielded.
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

        extraction_filter: Optional[ExtractionFilter]

        if isinstance(only_complete, bool):
            extraction_filter = (
                None
                if only_complete is False
                else lambda extracted: not all(
                    bool(v) if not isinstance(v, Exception) else False for k, v in extracted.items()
                )
            )
        else:
            extraction_filter = only_complete

        if isinstance(delay, float):

            def constant_delay() -> float:
                return delay  # type: ignore[return-value]

            delay = constant_delay

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

        if scrapers:
            pipeline = Pipeline(*scrapers)
            return pipeline.run(
                error_handling=error_handling,
                max_articles=max_articles,
                extraction_filter=extraction_filter,
                delay=delay,
                url_filter=url_filter,
                only_unique=only_unique,
            )
        else:
            return iter(())
