from collections import defaultdict
from functools import cached_property
from typing import Union, List, Dict, Literal, Generator

import more_itertools

from src.library.collection.base_objects import PublisherEnum
from src.pipeline.articles import Article
from src.pipeline.pipeline import CrawlerPipeline
from src.pipeline.sources import RSSSource
from stream.utils import listify


class Crawler:

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
                sources = [RSSSource(spec.domain, url) for url in spec.rss_feeds]
                rss_pipes = [CrawlerPipeline(source, spec.parser(), error_handling=error_handling) for source in
                             sources]
                pipelines.extend(rss_pipes)
            if restrict_sources_to == 'sitemap' or restrict_sources_to is None:
                pass

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
