from __future__ import annotations

from typing import Iterator, Optional

from more_itertools import roundrobin

from fundus.scraping.filter import URLFilter
from fundus.scraping.html import HTML
from fundus.scraping.pipeline import HTMLSource


class InterleavedSource:
    """Several HTMLSources drawn from in turn rather than one after another.

    Satisfies the HTMLSource protocol itself, so that a group of sources is interchangeable with a
    single one wherever a Pipeline takes an HTMLSource. Exhausted sources leave the rotation, so the
    remaining ones keep going, and a group of one is simply drawn as it is.

    Drawing in turn multiplies the request rate by the number of sources, unless they share their
    rate limiter: for WebSources, pass all of them one Pacer.
    """

    def __init__(self, *sources: HTMLSource) -> None:
        """Group the given sources, drawn from in the order given.

        Args:
            *sources (HTMLSource): The sources to draw from in turn.

        """
        self.sources = sources

    def fetch(self, url_filter: Optional[URLFilter] = None) -> Iterator[HTML]:
        """Stream HTML records, taking one from each source in turn until all are exhausted.

        Args:
            url_filter (Optional[URLFilter]): Per-call URL filter, forwarded to every source.

        Yields:
            HTML: The next record of the next source still holding one.

        """
        return roundrobin(*(source.fetch(url_filter) for source in self.sources))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self.sources)!r})"
