"""Shared setup for the logging tests, which all mutate process-global state."""

import io
import logging
from multiprocessing import Manager
from multiprocessing.managers import SyncManager
from typing import Dict, Iterator, List, Optional, Tuple

import pytest

from fundus.logging import LoggerRef, add_handler, loggers
from fundus.logging.workers import _BatchingQueueHandler

LIBRARY_ROOT = "fundus"


def fundus_loggers() -> Iterator[Tuple[str, logging.Logger]]:
    """Yield the library root and every Fundus logger currently in the logging registry."""
    yield LIBRARY_ROOT, logging.getLogger(LIBRARY_ROOT)
    for name, logger in list(logging.Logger.manager.loggerDict.items()):
        if name.startswith(f"{LIBRARY_ROOT}.") and isinstance(logger, logging.Logger):
            yield name, logger


def probe(logger: LoggerRef = None, name: str = "probe", level: Optional[int] = None) -> io.StringIO:
    """Attach a capturing handler to `logger` and return the buffer it writes to.

    The handler is left at NOTSET unless `level` says otherwise, so it filters nothing and a
    test sees exactly what the *logger* let through.
    """
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.set_name(name)
    handler.setFormatter(logging.Formatter("%(name)s|%(levelname)s|%(message)s"))
    if level is not None:
        handler.setLevel(level)
    add_handler(handler, logger=logger)
    return buffer


def lines(buffer: io.StringIO) -> List[str]:
    return buffer.getvalue().splitlines()


@pytest.fixture(scope="module")
def manager() -> Iterator[SyncManager]:
    """One manager process for the whole module; `worker_logging` takes its queue from it."""
    with Manager() as active_manager:
        yield active_manager


@pytest.fixture(autouse=True)
def _restore_logging() -> Iterator[None]:
    """Undo every mutation a test makes to the process-global logging state.

    Logging config lives in the interpreter, not in the objects under test, so without this
    a test that raises the level or adds a handler leaks into the next one. The registry is
    walked again on teardown rather than reused from setup, so that loggers a test creates
    are reset too instead of keeping their handlers for the rest of the session.
    """
    known: Dict[str, Tuple[int, List[logging.Handler], bool]] = {
        name: (logger.level, list(logger.handlers), logger.propagate) for name, logger in fundus_loggers()
    }
    registered = dict(loggers)
    started_with = {id(handler) for _, logger in fundus_loggers() for handler in logger.handlers}
    yield
    # A batching handler owns a thread, and restoring a handler list does not dispose of the
    # handlers it drops. Closing the ones a test introduced keeps their threads from piling
    # up for the rest of the session.
    for _, logger in fundus_loggers():
        for handler in logger.handlers:
            if isinstance(handler, _BatchingQueueHandler) and id(handler) not in started_with:
                handler.close()
    for name, logger in fundus_loggers():
        level, handlers, propagate = known.get(name, (logging.NOTSET, [], True))
        logger.setLevel(level)
        logger.handlers[:] = handlers
        logger.propagate = propagate
    loggers.clear()
    loggers.update(registered)
