from typing import Iterator, Literal

from src.parser.html_parser import BaseParser
from src.pipeline.articles import Article, BaseArticle
from src.pipeline.sources import Source


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
