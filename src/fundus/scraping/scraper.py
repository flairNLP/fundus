from typing import Any, Dict, Iterator, Literal, Optional, Protocol

from fundus.logging.logger import basic_logger
from fundus.parser import BaseParser
from fundus.scraping.article import Article
from fundus.scraping.source import Source


class ExtractionFilter(Protocol):
    def __call__(self, extracted: Dict[str, Any]) -> bool:
        ...


class ArticleClassifier(Protocol):
    """Classifies a website, represented by a given <url> and <html> as an article.

    When called with (<url>, <html>), an object satisfying this protocol should return
    the truth value of a binary classification classifying the website represented with
    <url> and <html> as article or not.

    Returns: This is a binary classification, so:
        <True>:     The represented website is considered to be an article:
        <False>:    The represented website is considered not to be an article
    """

    def __call__(self, url: str, html: str) -> bool:
        ...


class Requires:
    def __init__(self, *required_attributes: str) -> None:
        self.required_attributes = set(required_attributes)

    def __call__(self, extracted: Dict[str, Any]) -> bool:
        return all(
            bool(value := extracted.get(attr)) and not isinstance(value, Exception) for attr in self.required_attributes
        )


class Scraper:
    def __init__(
        self,
        *sources: Source,
        parser: BaseParser,
        extraction_filter: Optional[ExtractionFilter] = None,
        article_classifier: Optional[ArticleClassifier] = None,
    ):
        self.sources = list(sources)
        self.parser = parser
        self.extraction_filter = extraction_filter
        self.article_classifier = article_classifier

        if isinstance(extraction_filter, Requires):
            supported_attributes = set(parser.attributes().names)
            if missing_attributes := extraction_filter.required_attributes - supported_attributes:
                if len(missing_attributes) == 1:
                    basic_logger.info(
                        f"The required attribute `{missing_attributes}` "
                        f"is not supported by {type(self.parser).__name__}"
                    )
                else:
                    basic_logger.info(
                        f"The required attributes `{', '.join(missing_attributes)}` "
                        f"are not supported by {type(self.parser).__name__}"
                    )

    def scrape(self, error_handling: Literal["suppress", "catch", "raise"], batch_size: int = 10) -> Iterator[Article]:
        for crawler in self.sources:
            for article_source in crawler.fetch(batch_size):
                try:
                    if self.article_classifier and self.article_classifier(article_source.url, article_source.html):
                        continue

                    extraction = self.parser.parse(article_source.html, error_handling)

                    if self.extraction_filter and not self.extraction_filter(extraction):
                        continue
                except Exception as err:
                    if error_handling == "raise":
                        basic_logger.error(f"Run into an error processing '{article_source.url}'")
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
