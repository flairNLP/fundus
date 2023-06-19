import time
from collections import defaultdict
from typing import AsyncIterator, Literal, Optional

import more_itertools

from fundus.logging import basic_logger
from fundus.logging.context import get_current_context
from fundus.parser import ParserProxy
from fundus.scraping.article import Article
from fundus.scraping.filter import ExtractionFilter, Requires
from fundus.scraping.html import HTMLSource
from fundus.utils.more_async import timed


class Scraper:
    def __init__(self, *sources: HTMLSource, parser: ParserProxy):
        self.sources = list(sources)

        if not parser:
            raise ValueError(f"the given parser {type(parser).__name__} is empty")

        self.parser = parser

    async def scrape(
        self,
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter] = None,
    ) -> AsyncIterator[Optional[Article]]:
        if isinstance(extraction_filter, Requires):
            supported_attributes = set(
                more_itertools.flatten(collection.names for collection in self.parser.attribute_mapping.values())
            )
            if missing_attributes := extraction_filter.required_attributes - supported_attributes:
                if len(missing_attributes) == 1:
                    basic_logger.warn(
                        f"The required attribute `{missing_attributes}` "
                        f"is not supported by {type(self.parser).__name__}. Skipping Scraper"
                    )
                else:
                    basic_logger.warn(
                        f"The required attributes `{', '.join(missing_attributes)}` "
                        f"are not supported by {type(self.parser).__name__}. Skipping Scraper"
                    )

                return

        for html_source in self.sources:
            async for iteration_time, html in timed(html_source.async_fetch()):
                current_context = get_current_context()[html.source.publisher or html.requested_url]
                if not current_context.get("timings"):
                    current_context["timings"] = defaultdict(float)
                current_context["timings"]["fetch_async"] += iteration_time

                try:
                    pre_extraction_time = time.time()
                    extraction = self.parser(html.crawl_date).parse(html.content, error_handling)
                    current_context["timings"]["extraction"] += time.time() - pre_extraction_time
                except Exception as err:
                    if error_handling == "raise":
                        error_message = f"Run into an error processing article '{html.requested_url}'"
                        basic_logger.error(error_message)
                        err.args = (str(err) + "\n\n" + error_message,)
                        raise err
                    elif error_handling == "catch":
                        yield Article(html=html, exception=err)
                        continue
                    elif error_handling == "suppress":
                        basic_logger.info(f"Skipped article at '{html.requested_url}' because of: {err!r}")
                        continue
                    else:
                        raise ValueError(f"Unknown value '{error_handling}' for parameter <error_handling>'")

                if extraction_filter and extraction_filter(extraction):
                    basic_logger.debug(f"Skipped article at '{html.requested_url}' because of extraction filter")
                    yield None
                else:
                    article = Article.from_extracted(html=html, extracted=extraction)
                    yield article
