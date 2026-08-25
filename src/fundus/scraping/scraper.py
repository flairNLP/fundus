from typing import Dict, Iterator, Literal, Optional

from fundus.logging import create_logger
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
    def __init__(self, *sources: HTMLSource, publisher_mapping: Dict[str, Publisher]):
        """
        Args:
            *sources: The sources to draw HTML from.
            publisher_mapping: The publishers this scraper serves, keyed by the name <HTML.source_info>
                carries. A single source can serve several publishers, each restricted to sources and
                languages of its own, so the publisher an article is interpreted with is resolved per
                article rather than per scraper.
        """
        self.sources = sources
        self.publisher_mapping = publisher_mapping

    def scrape(
        self,
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter] = None,
        url_filter: Optional[URLFilter] = None,
    ) -> Iterator[Article]:

        for source in self.sources:
            for html in source.fetch(url_filter=url_filter):
                publisher = self.publisher_mapping[html.source_info.publisher]

                try:
                    extraction = publisher.parser(html.crawl_date).parse(html.content, error_handling)

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
                        # the exact half of the language restriction: selecting sources by the languages
                        # they declare only narrows down what gets crawled, this decides what is kept.
                        # None is the only value letting everything through, an empty restriction
                        # letting nothing through.
                        language_filter = publisher.language_filter
                        if language_filter is not None and article.lang not in language_filter:
                            logger.debug(
                                f"Skipped article at {html.requested_url!r} because article language: "
                                f"{article.lang!r} is not in allowed languages: {sorted(language_filter)!r}"
                            )
                        else:
                            yield article


class WebScraper(BaseScraper):
    def __init__(
        self,
        publisher: Publisher,
        delay: Optional[Delay] = None,
        ignore_robots: bool = False,
        ignore_crawl_delay: bool = False,
        impersonate: bool = False,
    ):
        """
        Args:
            publisher: The publisher to scrape, restricted to the sources and languages it is
                meant to contribute.
            delay: The crawl-delay to keep between requests.
            ignore_robots: If True, robots.txt restrictions are ignored.
            ignore_crawl_delay: If True, a crawl-delay given by robots.txt does not overwrite <delay>.
            impersonate: If True, use the publisher's browser profile to impersonate.
        """
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
            InterleavedSource(*(build(url_source) for url_source in batch)) for batch in publisher.sources.batches()
        ]
        super().__init__(*html_sources, publisher_mapping={publisher.name: publisher})


class CCNewsScraper(BaseScraper):
    def __init__(self, source: CCNewsSource):
        super().__init__(source, publisher_mapping={publisher.name: publisher for publisher in source.publishers})
