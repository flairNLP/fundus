from typing import Iterator, Literal

from src.logging.logger import basic_logger
from src.parser.html_parser import BaseParser
from src.scraping.article import Article
from src.scraping.source import Source


class Scraper:
    def __init__(self, *sources: Source, parser: BaseParser):
        self.sources = list(sources)
        self.parser = parser

    def scrape(self, error_handling: Literal["suppress", "catch", "raise"], batch_size: int = 10) -> Iterator[Article]:
        for crawler in self.sources:
            for article_source in crawler.fetch(batch_size):
                try:
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
