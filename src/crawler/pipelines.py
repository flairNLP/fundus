from collections import defaultdict
from functools import cached_property
from typing import Iterator, Literal, Union, List, Dict, Generator

import more_itertools

from src.library.collection.base_objects import PublisherEnum
from src.parser.html_parser import BaseParser
from src.crawler.articles import Article, BaseArticle
from src.crawler.sources import Source, RSSSource, AutoSitemapSource, SitemapSource
from stream.utils import listify


class CrawlerPipeline:

    def __init__(self,
                 source: Source,
                 parser: BaseParser,
                 error_handling: Literal['suppress', 'catch', 'raise'] = 'raise'):

        self.source = source
        self.parser = parser
        self.error_handling = error_handling

    def __iter__(self) -> Iterator[BaseArticle]:
        for article_source in self.source:

            try:

                data = self.parser.parse(article_source.html, self.error_handling)

            except Exception as err:

                if self.error_handling == 'raise':
                    raise err
                elif self.error_handling == 'catch':
                    yield Article(extracted={}, exception=err, **article_source.serialize())
                    continue
                elif self.error_handling == 'suppress':
                    continue
                else:
                    raise ValueError(f"Unknown value '{self.error_handling}' for parameter <error_handling>'")

            article = Article(extracted=data, **article_source.serialize())
            yield article


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

    def crawl(self,
              max_articles: int = None,
              restrict_sources_to: Literal['rss', 'sitemap'] = None,
              error_handling: Literal['suppress', 'catch', 'raise'] = 'raise') -> Generator[Article, None, None]:

        pipelines: List[CrawlerPipeline] = []
        for spec in self.publishers:
            if restrict_sources_to == 'rss' or restrict_sources_to is None:
                sources = [RSSSource(url) for url in spec.rss_feeds]
                rss_pipes = [CrawlerPipeline(source, spec.parser(), error_handling=error_handling)
                             for source in sources]
                pipelines.extend(rss_pipes)
            if restrict_sources_to == 'sitemap' or restrict_sources_to is None:
                if spec.sitemaps:
                    sources = [SitemapSource(sitemap) for sitemap in spec.sitemaps]
                else:
                    sources = [AutoSitemapSource(spec.domain)]
                sitemap_pipes = [CrawlerPipeline(source, spec.parser(), error_handling=error_handling)
                                 for source in sources]
                pipelines.extend(sitemap_pipes)

        robin = more_itertools.interleave_longest(*tuple(pipelines))

        if max_articles:
            while max_articles:
                try:
                    yield next(robin)
                except StopIteration:
                    pass
                max_articles -= 1
        else:
            yield from robin
