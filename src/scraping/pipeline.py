from typing import Literal, Union, List, Generator, Optional, Type, Set

import more_itertools

from src.library.collection.base_objects import PublisherEnum
from src.scraping.article import Article
from src.scraping.crawler import RSSCrawler, SitemapCrawler, Crawler
from src.scraping.scraper import Scraper
from src.utils.validation import listify


class AutoPipeline:

    def __init__(self, *publishers: Union[PublisherEnum, Type[PublisherEnum]]):
        if not publishers:
            raise ValueError('param <publishers> of <Crawler.__init__> has to be non empty')
        nested_publisher = [listify(publisher) for publisher in publishers]
        self.publishers: Set[PublisherEnum] = set(more_itertools.flatten(nested_publisher))

    def run(self,
            max_articles: Optional[int] = None,
            restrict_sources_to: Optional[Literal['rss', 'sitemap', 'news']] = None,
            error_handling: Literal['suppress', 'catch', 'raise'] = 'suppress') -> Generator[Article, None, None]:

        scraper: List[Scraper] = []
        for spec in self.publishers:
            sources: List[Crawler] = []
            if restrict_sources_to == 'rss' or restrict_sources_to is None:
                sources.extend([RSSCrawler(url, publisher=spec.name) for url in spec.rss_feeds])
            if restrict_sources_to == 'sitemap' or restrict_sources_to is None:
                sources.extend([SitemapCrawler(sitemap, publisher=spec.name) for sitemap in spec.sitemaps])
            if (restrict_sources_to == 'news' or restrict_sources_to is None) and spec.news_map:
                sources.append(SitemapCrawler(spec.news_map, publisher=spec.name))

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
