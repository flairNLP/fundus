from __future__ import annotations

from typing import Collection, Dict, Iterator, Optional, Protocol

from fundus.logging import create_logger
from fundus.publishers.base_objects import Publisher
from fundus.scraping.article import Article
from fundus.scraping.filter import ExtractionFilter, FilterResultWithMissingAttributes, URLFilter
from fundus.scraping.html import HTML, SourceInfo

logger = create_logger(__name__)

__all__ = [
    "HTML",
    "SourceInfo",
    "HTMLSource",
    "Pipeline",
    "PipelineError",
]


class HTMLSource(Protocol):
    """Protocol for HTML producers: yields HTML records, optionally gated by a URL filter.

    Implemented by WebSource (live web) and CCNewsSource (CC-NEWS WARC archive).
    """

    def fetch(self, url_filter: Optional[URLFilter] = None) -> Iterator[HTML]:
        """Stream HTML records from the underlying source.

        Args:
            url_filter (Optional[URLFilter]): Per-call URL filter; a truthy result skips the URL.
                Combined with any source- or publisher-level filter by the implementor.

        Yields:
            HTML: One record per kept/fetched URL.

        """
        ...


class PipelineError(Exception):
    """Raised when an error occurs during a pipeline run."""

    pass


class Pipeline:
    """Pairs an HTMLSource with publishers, turning each fetched HTML into an Article.

    Pulls HTML from the source, looks up the HTML's publisher by name, parses it with that
    publisher's parser, and applies the extraction filter and the publisher's language filter.
    HTML that fails parsing or any filter is dropped.
    """

    def __init__(self, source: HTMLSource, publishers: Collection[Publisher]) -> None:
        """Build a pipeline over the given source and the supplied publishers.

        Args:
            source (HTMLSource): The HTML producer to pull records from.
            publishers (Collection[Publisher]): Publishers that may be needed to process the
                source's HTML. Each HTML is re-associated with its publisher by name. A publisher
                restricted to certain languages (see Publisher.restrict) keeps only articles in
                one of them.

        """
        self.source = source
        # Identity -> publisher. The parser is behavior and can't ride on the (picklable) HTML, so
        # each HTML carries only its publisher's name and we re-associate the publisher here.
        self._publishers: Dict[str, Publisher] = {publisher.name: publisher for publisher in publishers}

    def _extract(
        self,
        html: HTML,
        raise_on_error: bool,
        extraction_filter: Optional[ExtractionFilter] = None,
    ) -> Optional[Article]:
        """Parse one HTML into an Article, or None if parsing fails or a filter drops it."""
        if (publisher := self._publishers.get(html.source_info.publisher)) is None:
            raise PipelineError(
                f"No publisher {html.source_info.publisher!r}; pipeline was built for {sorted(self._publishers)}"
            )

        try:
            extraction = publisher.parser(html.crawl_date).parse(html.content, raise_on_error)

        except Exception as error:
            if raise_on_error:
                error_message = f"Run into an error processing article {html.requested_url!r}"
                logger.error(error_message)
                error.args = (str(error) + "\n\n" + error_message,)
                raise
            logger.info(f"Skipped article at {html.requested_url!r} because of: {error!r}")
            return None

        else:
            if extraction_filter and (filter_result := extraction_filter(extraction)):
                if isinstance(filter_result, FilterResultWithMissingAttributes):
                    logger.debug(
                        f"Skipped article at {html.requested_url!r} because attribute(s) "
                        f"{', '.join(filter_result.missing_attributes)!r} is(are) missing"
                    )
                else:
                    logger.debug(f"Skipped article at {html.requested_url!r} because of extraction filter")
                return None

            article = Article(html=html, **extraction)
            # The exact half of a language restriction: selecting sources by the languages they
            # declare only narrows down what gets crawled, this decides what is kept. None lets
            # everything through, an empty restriction nothing.
            if (language_filter := publisher.language_filter) is not None and article.lang not in language_filter:
                logger.debug(
                    f"Skipped article at {html.requested_url!r} because article language "
                    f"{article.lang!r} is not in allowed languages: {sorted(language_filter)!r}"
                )
                return None

            return article

    def run(
        self,
        raise_on_error: bool,
        extraction_filter: Optional[ExtractionFilter] = None,
        url_filter: Optional[URLFilter] = None,
    ) -> Iterator[Article]:
        """Stream Articles by fetching HTML from the source and parsing each record.

        Args:
            raise_on_error (bool): If True, parser exceptions propagate; if False they are logged
                and the offending article is skipped.
            extraction_filter (Optional[ExtractionFilter]): Applied after extraction; a truthy
                result drops the article.
            url_filter (Optional[URLFilter]): Forwarded to the source's fetch() to skip URLs before
                they are downloaded/parsed.

        Yields:
            Article: One per HTML record that parses and passes all filters.

        """
        for html in self.source.fetch(url_filter=url_filter):
            if article := self._extract(html, raise_on_error, extraction_filter):
                yield article
