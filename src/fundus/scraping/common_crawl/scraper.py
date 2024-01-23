from typing import Dict, Iterator, Literal, Optional

from fundus.logging import basic_logger
from fundus.parser import ParserProxy
from fundus.scraping.article import Article
from fundus.scraping.common_crawl.html import CCNewsSource
from fundus.scraping.filter import ExtractionFilter, URLFilter


class CCNewsScraper:
    def __init__(self, source: CCNewsSource):
        self.source = source
        self._parser_mapping: Dict[str, ParserProxy] = {
            publisher.publisher_name: publisher.parser for publisher in source.publishers
        }

    def scrape(
        self,
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter] = None,
        url_filter: Optional[URLFilter] = None,
    ) -> Iterator[Article]:
        # TODO: Once we decided on weather to continue fundus with async functionality or not, refactor this to
        #   be suitable for a BaseScraper class
        for html in self.source.fetch(url_filter):
            parser = self._parser_mapping[html.source.publisher]
            try:
                extraction = parser(html.crawl_date).parse(html.content, error_handling)

            except Exception as err:
                if error_handling == "raise":
                    error_message = f"Run into an error processing article '{html.requested_url}'"
                    basic_logger.error(error_message)
                    err.args = (f"{err}\n\n{error_message},)
                    raise err
                elif error_handling == "catch":
                    yield Article(html=html, exception=err)
                elif error_handling == "suppress":
                    basic_logger.info(f"Skipped article at '{html.requested_url}' because of: {err!r}")
                else:
                    raise ValueError(f"Unknown value '{error_handling}' for parameter <error_handling>'")

            else:
                if extraction_filter is not None and extraction_filter(extraction):
                    basic_logger.debug(f"Skipped article at '{html.requested_url}' because of extraction filter")
                else:
                    article = Article.from_extracted(html=html, extracted=extraction)
                    yield article
