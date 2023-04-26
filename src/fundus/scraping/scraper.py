from typing import Any, Dict, Iterator, Literal, Optional, Protocol

from fundus.logging.logger import basic_logger
from fundus.parser import BaseParser
from fundus.scraping.article import Article
from fundus.scraping.source import Source


class ExtractionFilter(Protocol):
    def __call__(self, extracted: Dict[str, Any]) -> bool:
        ...


class Requires:
    def __init__(self, *attrs: str) -> None:
        self.required_attrs = set(attrs)

    def __call__(self, extracted: Dict[str, Any]) -> bool:
        return all(
            bool(value := extracted.get(attr)) and not isinstance(value, Exception) for attr in self.required_attrs
        )


class Scraper:
    def __init__(
        self,
        *sources: Source,
        parser: BaseParser,
        extraction_filter: Optional[ExtractionFilter] = None,
    ):
        self.sources = list(sources)
        self.parser = parser
        self.filter = extraction_filter

        if isinstance(extraction_filter, Requires):
            supported_attrs = list(parser.attributes().names)
            for attr in extraction_filter.required_attrs:
                if attr not in supported_attrs:
                    basic_logger.info(
                        f"The required attribute '{attr}' is not supported by {self.parser.__class__.__name__}"
                    )

    def scrape(self, error_handling: Literal["suppress", "catch", "raise"], batch_size: int = 10) -> Iterator[Article]:
        for crawler in self.sources:
            for article_source in crawler.fetch(batch_size):
                try:
                    extraction = self.parser.parse(article_source.html, error_handling)
                    if self.filter and not self.filter(extraction):
                        continue
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

                article = Article.from_extracted(source=article_source, extracted=extraction)
                yield article
