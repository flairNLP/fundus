from typing import Iterator, Literal

from fundus.logging.logger import basic_logger
from fundus.parser import BaseParser
from fundus.scraping.article import Article
from fundus.scraping.source import Source
from fundus.utils.DocumentType import UnClassifiedType


class Scraper:
    def __init__(self, *sources: Source, parser: BaseParser):
        self.sources = list(sources)
        self.parser = parser

    def scrape(self, error_handling: Literal["suppress", "catch", "raise"], batch_size: int = 10) -> Iterator[Article]:
        for crawler in self.sources:
            for article_source in crawler.fetch(batch_size):
                try:

                    self.parser._base_setup(article_source.html)

                    unknown_type = UnClassifiedType(article_source.html, article_source.html)
                    document_type = self.parser.classify(unknown_type)

                    data = self.parser.parse(article_source.html, error_handling)

                except Exception as err:
                    if error_handling == "raise":
                        raise err
                    elif error_handling == "catch":
                        yield Article(source=article_source, exception=err)
                        continue
                    elif error_handling == "suppress":
                        basic_logger.info(f"Skipped {article_source.url} because of: {err!r}")
                        continue
                    else:
                        raise ValueError(f"Unknown value '{error_handling}' for parameter <error_handling>'")

                article = Article.from_extracted(source=article_source, extracted=data)
                yield article
