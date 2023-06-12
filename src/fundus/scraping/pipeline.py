import asyncio
from typing import Iterator, List, Literal, Optional, Set, Tuple, Type, Union

import more_itertools

from fundus.publishers.base_objects import PublisherEnum
from fundus.scraping.article import Article
from fundus.scraping.filter import ExtractionFilter
from fundus.scraping.scraper import Scraper
from fundus.scraping.source import URLSource
from fundus.utils.more_async import async_next, async_gen_interleave
from fundus.utils.validation import listify


class Pipeline:
    def __init__(self, *scrapers: Scraper):
        self.scrapers: Tuple[Scraper, ...] = scrapers

    def run(
            self,
            error_handling: Literal["suppress", "catch", "raise"],
            max_articles: Optional[int] = None,
            extraction_filter: Optional[ExtractionFilter] = None,
    ) -> Iterator[Article]:
        scrape_map = map(
            lambda x: x.async_scrape(
                error_handling=error_handling, extraction_filter=extraction_filter
            ),
            self.scrapers,
        )

        loop = asyncio.get_event_loop()

        def article_gen() -> Iterator[Article]:
            scrape_gen = async_gen_interleave(*tuple(scrape_map))
            while True:
                nxt = loop.run_until_complete(async_next(scrape_gen, None))
                if nxt:
                    yield from nxt
                else:
                    break

        gen = article_gen()

        if max_articles:
            while max_articles:
                if article := next(gen, None):
                    yield article
                else:
                    break
                max_articles -= 1
        else:
            yield from gen


class Crawler:
    def __init__(self, *publishers: Union[PublisherEnum, Type[PublisherEnum]]):
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
    ) -> Iterator[Article]:
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
            )
        else:
            return iter(())
