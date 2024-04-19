from typing import Dict, Iterator, List, Literal, Optional, Type

import more_itertools

from fundus.logging import basic_logger
from fundus.parser import ParserProxy
from fundus.publishers.base_objects import PublisherEnum
from fundus.scraping.article import Article
from fundus.scraping.delay import Delay
from fundus.scraping.filter import (
    ExtractionFilter,
    FilterResultWithMissingAttributes,
    URLFilter,
)
from fundus.scraping.html import CCNewsSource, HTMLSource, WebSource
from fundus.scraping.url import URLSource


class BaseScraper:
    def __init__(self, *sources: HTMLSource, parser_mapping: Dict[str, ParserProxy]):
        self.sources = sources
        self.parser_mapping = parser_mapping

    def scrape(
        self,
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter] = None,
        url_filter: Optional[URLFilter] = None,
    ) -> Iterator[Article]:
        for source in self.sources:
            for html in source.fetch(url_filter=url_filter):
                parser = self.parser_mapping[html.source_info.publisher]

                try:
                    extraction = parser(html.crawl_date).parse(html.content, error_handling)

                except Exception as err:
                    if error_handling == "raise":
                        error_message = f"Run into an error processing article '{html.requested_url}'"
                        basic_logger.error(error_message)
                        err.args = (str(err) + "\n\n" + error_message,)
                        raise err
                    elif error_handling == "catch":
                        yield Article(html=html, exception=err)
                    elif error_handling == "suppress":
                        basic_logger.info(f"Skipped article at '{html.requested_url}' because of: {err!r}")
                    else:
                        raise ValueError(f"Unknown value '{error_handling}' for parameter <error_handling>'")

                else:
                    if extraction_filter and (filter_result := extraction_filter(extraction)):
                        if isinstance(filter_result, FilterResultWithMissingAttributes):
                            basic_logger.debug(
                                f"Skipped article at '{html.requested_url}' because attribute(s) "
                                f"{', '.join(filter_result.missing_attributes)!r} is(are) missing"
                            )
                        else:
                            basic_logger.debug(
                                f"Skipped article at '{html.requested_url}' because of extraction filter"
                            )
                    else:
                        article = Article.from_extracted(html=html, extracted=extraction)
                        yield article


class WebScraper(BaseScraper):
    def __init__(
        self,
        publisher: PublisherEnum,
        restrict_sources_to: Optional[List[Type[URLSource]]] = None,
        delay: Optional[Delay] = None,
    ):
        if restrict_sources_to:
            url_sources = tuple(
                more_itertools.flatten(publisher.source_mapping[source_type] for source_type in restrict_sources_to)
            )
        else:
            url_sources = tuple(more_itertools.flatten(publisher.source_mapping.values()))

        html_sources = [
            WebSource(
                url_source=url_source,
                publisher=publisher.publisher_name,
                request_header=publisher.request_header,
                delay=delay,
                query_parameters=publisher.query_parameter,
            )
            for url_source in url_sources
        ]
        parser_mapping: Dict[str, ParserProxy] = {publisher.publisher_name: publisher.parser}
        super().__init__(*html_sources, parser_mapping=parser_mapping)


class CCNewsScraper(BaseScraper):
    def __init__(self, source: CCNewsSource):
        parser_mapping: Dict[str, ParserProxy] = {
            publisher.publisher_name: publisher.parser for publisher in source.publishers
        }
        super().__init__(source, parser_mapping=parser_mapping)
