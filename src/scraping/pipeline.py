from collections import defaultdict
from functools import cached_property
from typing import Literal, Union, List, Dict, Generator

import more_itertools

from src.library.collection.base_objects import PublisherEnum
from src.scraping.article import Article
from src.scraping.crawler.crawler import RSSCrawler, SitemapCrawler
from src.scraping.scraper import Scraper
from stream.utils import listify


class AutoPipeline:

    def __init__(self, publishers: Union[PublisherEnum, List[PublisherEnum]]):
        if not publishers:
            raise ValueError('param <publishers> of <Crawler.__init__> has to be non empty')
        self.publishers: List[PublisherEnum] = listify(publishers)

    @cached_property
    def rss_sources(self) -> Dict[str, List[str]]:
        sources = defaultdict(list)
        for spec in self.publishers:
            for url in spec.rss_feeds:
                sources[spec.domain].append(url)
        return sources

    def run(self,
            max_articles: int = None,
            restrict_sources_to: Literal['rss', 'sitemap'] = None,
            error_handling: Literal['suppress', 'catch', 'raise'] = 'raise') -> Generator[Article, None, None]:

        scraper: List[Scraper] = []
        for spec in self.publishers:
            sources = []
            if restrict_sources_to == 'rss' or restrict_sources_to is None:
                sources.extend([RSSCrawler(url) for url in spec.rss_feeds])
            if restrict_sources_to == 'sitemap' or restrict_sources_to is None:
                sources.extend([SitemapCrawler(sitemap) for sitemap in spec.sitemaps])
            if (restrict_sources_to == 'news' or restrict_sources_to is None) and spec.news_map:
                sources.append(SitemapCrawler(spec.news_map))

            if sources:
                scraper.append(Scraper(*sources, parser=spec.parser()))

        if scraper:
            scrape_map = map(lambda x: x.scrape(error_handling=error_handling), scraper)
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
