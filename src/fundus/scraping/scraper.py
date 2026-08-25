from typing import Dict, Iterator, List, Literal, Optional, Type

from fundus.logging import create_logger
from fundus.parser import ParserProxy
from fundus.publishers.base_objects import Publisher
from fundus.scraping.article import Article
from fundus.scraping.delay import Delay
from fundus.scraping.filter import (
    ExtractionFilter,
    FilterResultWithMissingAttributes,
    URLFilter,
)
from fundus.scraping.html import (
    CCNewsSource,
    HTMLSource,
    InterleavedSource,
    WebSource,
    build_clock,
)
from fundus.scraping.url import URLSource

logger = create_logger(__name__)


class BaseScraper:
    def __init__(self, *sources: HTMLSource, parser_mapping: Dict[str, ParserProxy]):
        self.sources = sources
        self.parser_mapping = parser_mapping

    def scrape(
        self,
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter] = None,
        url_filter: Optional[URLFilter] = None,
        language_filter: Optional[List[str]] = None,
    ) -> Iterator[Article]:
        for source in self.sources:
            for html in source.fetch(url_filter=url_filter):
                parser = self.parser_mapping[html.source_info.publisher]

                try:
                    extraction = parser(html.crawl_date).parse(html.content, error_handling)

                except Exception as error:
                    if error_handling == "raise":
                        error_message = f"Run into an error processing article {html.requested_url!r}"
                        logger.error(error_message)
                        error.args = (str(error) + "\n\n" + error_message,)
                        raise error
                    elif error_handling == "catch":
                        yield Article(html=html, exception=error)
                    elif error_handling == "suppress":
                        logger.info(f"Skipped article at {html.requested_url!r} because of: {error!r}")
                    else:
                        raise ValueError(f"Unknown value {error_handling!r} for parameter <error_handling>'")

                else:
                    if extraction_filter and (filter_result := extraction_filter(extraction)):
                        if isinstance(filter_result, FilterResultWithMissingAttributes):
                            logger.debug(
                                f"Skipped article at {html.requested_url!r} because attribute(s) "
                                f"{', '.join(filter_result.missing_attributes)!r} is(are) missing"
                            )
                        else:
                            logger.debug(f"Skipped article at {html.requested_url!r} because of extraction filter")
                    else:
                        article = Article(html=html, **extraction)
                        if language_filter and article.lang not in language_filter:
                            logger.debug(
                                f"Skipped article at {html.requested_url!r} because article language: "
                                f"{article.lang!r} is not in allowed languages: {language_filter!r}"
                            )
                        else:
                            yield article


class WebScraper(BaseScraper):
    def __init__(
        self,
        publisher: Publisher,
        restrict_sources_to: Optional[List[Type[URLSource]]] = None,
        delay: Optional[Delay] = None,
        ignore_robots: bool = False,
        ignore_crawl_delay: bool = False,
        impersonate: bool = False,
    ):
        url_sources = publisher.sources.filter(source_types=restrict_sources_to)

        # a single clock for all of the publisher's sources, so that the crawl-delay paces the
        # publisher rather than each source separately. Without this, round-robining a batch of n
        # sources would fire n requests before any of them waits.
        clock = build_clock(publisher, delay, ignore_robots, ignore_crawl_delay)

        def build(url_source: URLSource) -> WebSource:
            return WebSource(
                url_source=url_source,
                publisher=publisher,
                url_filter=publisher.url_filter,
                query_parameters=publisher.query_parameter,
                ignore_robots=ignore_robots,
                impersonate=impersonate,
                clock=clock,
            )

        html_sources = [
            InterleavedSource(*(build(url_source) for url_source in batch)) for batch in url_sources.batches()
        ]
        parser_mapping: Dict[str, ParserProxy] = {publisher.name: publisher.parser}
        super().__init__(*html_sources, parser_mapping=parser_mapping)


class CCNewsScraper(BaseScraper):
    def __init__(self, source: CCNewsSource):
        parser_mapping: Dict[str, ParserProxy] = {publisher.name: publisher.parser for publisher in source.publishers}
        super().__init__(source, parser_mapping=parser_mapping)
