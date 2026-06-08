from typing import Iterator

import pytest

from fundus.utils.events import __EVENTS__, __MAIN_THREAD_ALIAS__


@pytest.fixture
def main_thread_context() -> Iterator[None]:
    """Register the main-thread alias, mirroring the context ``CrawlerBase.crawl`` sets up.

    Without this context, tests that probe events hit an unregistered alias and
    raise ``KeyError``.
    """
    with __EVENTS__.main_context(__MAIN_THREAD_ALIAS__):
        yield
