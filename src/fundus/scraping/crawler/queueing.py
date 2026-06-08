from __future__ import annotations

import multiprocessing
import time
import traceback
from functools import wraps
from multiprocessing.pool import MapResult
from queue import Empty, Full, Queue
from typing import Any, Callable, Iterator, Tuple, Type, TypeVar, Union

from typing_extensions import ParamSpec

from fundus.logging import create_logger
from fundus.utils.concurrency import get_execution_context
from fundus.utils.events import __EVENTS__, __MAIN_THREAD_ALIAS__

logger = create_logger(__name__)

_T = TypeVar("_T")
_P = ParamSpec("_P")


class RemoteException(Exception):
    """Carries a worker thread/process exception (with formatted traceback) back to the consumer via the queue."""


def enqueue_results(
    queue: Queue[Union[_T, Exception]],
    target: Callable[_P, Iterator[_T]],
    silenced_exceptions: Tuple[Type[BaseException], ...] = (),
) -> Callable[_P, None]:
    """Wrap a result-yielding callable so it pushes its results onto the queue instead of returning them.

    The wrapped callable drives ``target`` to exhaustion, putting each result onto the queue.
    When the queue is full it blocks until space frees up, bailing out early if the main-thread
    ``stop`` event is set. Exceptions in ``silenced_exceptions`` are swallowed; any other exception
    is forwarded to the consumer as a :class:`RemoteException` put onto the queue (so it surfaces in
    ``iter_pool_results`` rather than crashing the worker).

    Args:
        queue: The buffer queue results (and forwarded exceptions) are pushed onto.
        target: A callable returning an iterator of results to enqueue.
        silenced_exceptions: Exception types to swallow instead of forwarding.

    Returns:
        Callable[_P, None]: The wrapped target, which returns nothing and enqueues instead.
    """

    @wraps(target)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> None:
        def _delivered(result: _T) -> bool:
            """Block until result is queued; return False if the main-thread stop event aborts the wait."""
            while True:
                try:
                    queue.put_nowait(result)
                except Full:
                    if __EVENTS__.is_event_set("stop", __MAIN_THREAD_ALIAS__):
                        return False
                    time.sleep(0.05)
                else:
                    return True

        def _forward_exception(exception: Exception) -> None:
            """Push a worker exception to the consumer as a RemoteException with a formatted traceback."""
            tb_str = "".join(traceback.TracebackException.from_exception(exception).format())
            context, ident = get_execution_context()
            alias = __EVENTS__.get_alias(ident, "<unaliased>") if ident is not None else "<unaliased>"
            queue.put(
                RemoteException(
                    f"There was a(n) {type(exception).__name__!r} occurring in {context} "
                    f"with ident {ident} ({alias})\n{tb_str}"
                )
            )
            logger.debug(f"Encountered remote exception in thread {ident} ({alias}): {exception!r}")

        try:
            for obj in target(*args, **kwargs):
                if not _delivered(obj):
                    return
        except silenced_exceptions:
            pass
        except Exception as err:
            _forward_exception(err)

    return wrapper


def iter_pool_results(handle: MapResult[Any], queue: Queue[Union[_T, Exception]]) -> Iterator[_T]:
    """Yield results from a pool's queue as its workers produce them.

    Results are drained from the queue and yielded as they arrive. When the queue runs
    empty, the pool handle is polled: if every job has finished, any remaining buffered
    results are flushed and iteration ends; otherwise iteration waits for more results.
    If the main thread's ``stop`` event is set while waiting, the event is cleared and
    iteration ends immediately without draining the queue. Any exception a worker
    forwarded through the queue is re-raised to the consumer.

    Args:
        handle: The ``MapResult`` handle of the underlying multiprocessing pool.
        queue: The queue workers push their results (and forwarded exceptions) onto.

    Yields:
        _T: Each result pulled from the queue.
    """

    def _next_result() -> _T:
        """Pop the next buffered result, re-raising any exception a worker forwarded through the queue."""
        if isinstance(nxt := queue.get_nowait(), Exception):
            raise Exception("There was an exception occurring in a remote thread/process") from nxt
        return nxt

    def _pool_finished() -> bool:
        """Return True once every job in the pool has completed."""
        try:
            handle.get(timeout=0.01)
        except multiprocessing.TimeoutError:
            return False
        return True

    # Phase 1: drain results as the pool produces them, until it finishes or is stopped.
    while True:
        try:
            result = _next_result()
        except Empty:
            if _pool_finished():
                break
            # listen for stop-event set for main-thread
            if __EVENTS__.is_event_set("stop", __MAIN_THREAD_ALIAS__):
                __EVENTS__.clear_event("stop", __MAIN_THREAD_ALIAS__)
                return
            continue
        yield result

    # Phase 2: pool is done, so flush whatever results are still buffered.
    while not queue.empty():
        yield _next_result()
