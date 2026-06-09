import multiprocessing
from queue import Queue
from typing import Union
from unittest.mock import MagicMock

import pytest

from fundus.scraping.crawler.queueing import (
    RemoteException,
    iter_pool_results,
)
from fundus.utils.events import __EVENTS__, __MAIN_THREAD_ALIAS__


def _never_ready_handle() -> MagicMock:
    """Stand-in for a pool MapResult whose jobs never finish: get() always times out."""
    handle = MagicMock()
    handle.get.side_effect = multiprocessing.TimeoutError
    return handle


def _ready_handle() -> MagicMock:
    """Stand-in for a finished pool MapResult: get() returns immediately."""
    handle = MagicMock()
    handle.get.return_value = None
    return handle


class TestPoolQueueIter:
    def test_main_thread_stop_event_ends_iteration(self):
        # Pool still running (handle never ready) and queue empty: setting the main-thread stop
        # event must terminate the iterator instead of spinning forever waiting for results.
        queue: Queue[Union[str, Exception]] = Queue()
        with __EVENTS__.main_context(__MAIN_THREAD_ALIAS__):
            __EVENTS__.set_event("stop", __MAIN_THREAD_ALIAS__)
            assert list(iter_pool_results(_never_ready_handle(), queue)) == []

    def test_stop_event_is_cleared_on_exit(self):
        # Breaking on the stop event clears it, so a later crawl reusing the alias is not
        # short-circuited by a stale flag.
        queue: Queue[Union[str, Exception]] = Queue()
        with __EVENTS__.main_context(__MAIN_THREAD_ALIAS__):
            __EVENTS__.set_event("stop", __MAIN_THREAD_ALIAS__)
            list(iter_pool_results(_never_ready_handle(), queue))
            assert __EVENTS__.is_event_set("stop", __MAIN_THREAD_ALIAS__) is False

    def test_drains_remaining_queue_when_pool_finished(self):
        # Once the pool is done (handle ready), everything still buffered must be yielded.
        queue: Queue[Union[str, Exception]] = Queue()
        queue.put("a")
        queue.put("b")
        assert list(iter_pool_results(_ready_handle(), queue)) == ["a", "b"]

    def test_raises_when_queue_yields_remote_exception(self):
        # A RemoteException put on the queue by a worker is re-raised to the consumer.
        queue: Queue[Exception] = Queue()
        queue.put(RemoteException("boom"))
        with pytest.raises(Exception, match="remote thread/process"):
            list(iter_pool_results(_ready_handle(), queue))
