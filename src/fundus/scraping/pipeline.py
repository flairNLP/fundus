from typing import Iterator, List, Literal, Optional, Set, Tuple, Type, Union

import more_itertools

from fundus.logging.logger import basic_logger
from fundus.publishers.base_objects import PublisherEnum
from fundus.scraping.article import Article
from fundus.scraping.filter import ExtractionFilter
from fundus.scraping.scraper import Scraper
from fundus.scraping.source import RSSSource, SitemapSource, Source
from fundus.utils.validation import listify


class Pipeline:
    def __init__(self, *scrapers: Scraper):
        self.scrapers: Tuple[Scraper, ...] = scrapers

    def run(
        self,
        max_articles: Optional[int] = None,
        error_handling: Literal["suppress", "catch", "raise"] = "suppress",
        extraction_filter: Optional[ExtractionFilter] = None,
        batch_size: Optional[int] = None,
    ) -> Iterator[Article]:
        """Yields articles from initialized scrapers.

        Works like a light-wight version of Crawler.crawl(). Ment to be used when dealing with
        custom scrapers outside the context of predefined publisher collections.

        Refer to the docstring of Crawler.crawl() for more detailed information about the Args.

        Args:
            max_articles (Optional[int]): Maximal number of articles to be yielded. Defaults to None.
            error_handling (Literal["suppress", "catch", "raise"]): Set error handling
                for extraction. Defaults to "suppress".
            extraction_filter (Optional[ExtractionFilter]): Set extraction filter. Defaults to None.
            batch_size (Optional[int]): Set batch size used for concurrent downloads. Defaults to None

        Returns:
            Iterator[Article]: An iterator yielding objects of type Article.


        """
        scrape_map = map(
            lambda x: x.scrape(
                error_handling=error_handling,
                batch_size=batch_size,
                extraction_filter=extraction_filter,
                force_article=False,
            ),
            self.scrapers,
        )
        # we ignore the type because mypy complains about bool not being a fitting TypeGuard for Optional[Article]
        robin: Iterator[Article] = filter(bool, more_itertools.interleave_longest(*tuple(scrape_map)))  # type: ignore

        if max_articles:
            while max_articles:
                try:
                    yield next(robin)
                except StopIteration:
                    pass
                max_articles -= 1
        else:
            yield from robin


class Crawler:
    def __init__(self, *publishers: Union[PublisherEnum, Type[PublisherEnum]]):
        if not publishers:
            raise ValueError("param <publishers> of <Crawler.__init__> has to be non empty")
        nested_publisher = [listify(publisher) for publisher in publishers]
        self.publishers: Set[PublisherEnum] = set(more_itertools.flatten(nested_publisher))

    def crawl(
        self,
        max_articles: Optional[int] = None,
        restrict_sources_to: Optional[List[Literal["rss", "sitemap", "news"]]] = None,
        error_handling: Literal["suppress", "catch", "raise"] = "suppress",
        only_complete: Union[bool, ExtractionFilter] = True,
        batch_size: Optional[int] = None,
    ) -> Iterator[Article]:
        """Yields articles from initialized publishers.

        Args:
            max_articles (Optional[int]): Number of articles to retrieve. If there are fewer articles
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
            batch_size: Size of article batch that which will be downloaded concurrently per publisher.
                If set to None batch_size is cpu_count() + 4. This will also affect the ThreadPool size.
                Upper bound here is cpu_count() + 4. Defaults to None.

        Returns:
            Iterator[Article]: An iterator yielding objects of type Article.

        """
        extraction_filter: Optional[ExtractionFilter]
        if isinstance(only_complete, bool):
            extraction_filter = (
                None
                if only_complete is False
                else lambda extracted: all(
                    bool(v) if not isinstance(v, Exception) else False for k, v in extracted.items()
                )
            )
        else:
            extraction_filter = only_complete

        scrapers: List[Scraper] = []
        for spec in self.publishers:
            sources: List[Source] = []

            if restrict_sources_to is None or "rss" in restrict_sources_to:
                sources.extend([RSSSource(url, publisher=spec.publisher_name) for url in spec.rss_feeds])

            if (restrict_sources_to is None or "news" in restrict_sources_to) and spec.news_map:
                sources.append(SitemapSource(spec.news_map, publisher=spec.publisher_name))

            if restrict_sources_to is None or "sitemap" in restrict_sources_to:
                sources.extend([SitemapSource(sitemap, publisher=spec.publisher_name) for sitemap in spec.sitemaps])

            if sources:
                scrapers.append(
                    Scraper(
                        *sources,
                        parser=spec.parser,
                        url_filter=spec.url_filter,
                    )
                )

        if scrapers:
            pipeline = Pipeline(*scrapers)
            return pipeline.run(
                error_handling=error_handling,
                max_articles=max_articles,
                batch_size=batch_size,
                extraction_filter=extraction_filter,
            )
        else:
            basic_logger.warn(
                f"Empty Pipeline. No scrapers could be build with current publishers "
                f"{self.publishers} and source restrictions {restrict_sources_to}"
            )
            return iter(())
