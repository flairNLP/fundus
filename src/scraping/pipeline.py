from typing import Iterator, List, Literal, Optional, Set, Tuple, Type, Union

import more_itertools

from src.publishers.base_objects import PublisherEnum
from src.scraping.article import Article
from src.scraping.scraper import Scraper
from src.scraping.source import RSSSource, SitemapSource, Source
from src.utils.validation import listify


class Pipeline:
    def __init__(self, *scrapers: Scraper):
        self.scrapers: Tuple[Scraper, ...] = scrapers

    def run(
        self,
        error_handling: Literal["suppress", "catch", "raise"],
        max_articles: Optional[int] = None,
        batch_size: int = 10,
    ) -> Iterator[Article]:
        scrape_map = map(lambda x: x.scrape(error_handling=error_handling, batch_size=batch_size), self.scrapers)
        robin = more_itertools.interleave_longest(*tuple(scrape_map))

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
        restrict_sources_to: Optional[Literal["rss", "sitemap", "news"]] = None,
        error_handling: Literal["suppress", "catch", "raise"] = "suppress",
        batch_size: int = 10,
    ) -> Iterator[Article]:
        scrapers: List[Scraper] = []
        for spec in self.publishers:
            sources: List[Source] = []
            if restrict_sources_to == "rss" or restrict_sources_to is None:
                sources.extend([RSSSource(url, publisher=spec.name) for url in spec.rss_feeds])
            if restrict_sources_to == "sitemap" or restrict_sources_to is None:
                sources.extend([SitemapSource(sitemap, publisher=spec.name) for sitemap in spec.sitemaps])
            if (restrict_sources_to == "news" or restrict_sources_to is None) and spec.news_map:
                sources.append(SitemapSource(spec.news_map, publisher=spec.name))

            if sources:
                scrapers.append(Scraper(*sources, parser=spec.parser()))

        if scrapers:
            pipeline = Pipeline(*scrapers)
            return pipeline.run(error_handling=error_handling, max_articles=max_articles, batch_size=batch_size)
        else:
            return iter(())
