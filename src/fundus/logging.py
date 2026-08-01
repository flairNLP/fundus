"""Logging setup for Fundus.

Every module logger is a child of the library root logger (``fundus``), which carries the
log level and the handlers; children are created unconfigured and inherit both. Two things
follow that are worth knowing:

- **The level lives on the logger, not the handler.** A handler only filters further, per
  destination, so a handler added via :func:`add_handler` never sees records
  :func:`set_log_level` already dropped.
- **Propagation to the root logger stays on.** Fundus ships a stderr handler, unusually for
  a library, because silent failures during a crawl would be worse. An application that
  configures logging itself will therefore see records twice, and can take ownership with
  ``remove_handler("fundus-stderr")`` without losing them.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
import threading
import traceback
from contextlib import contextmanager, suppress
from functools import partial, wraps
from multiprocessing.managers import SyncManager
from queue import Queue
from typing import Any, Callable, Dict, Iterator, List, Optional, TypeVar, Union

from typing_extensions import ParamSpec

__all__ = [
    "LoggerRef",
    "create_logger",
    "set_log_level",
    "add_handler",
    "remove_handler",
    "get_handlers",
    "loggers",
]

# Derived from this module's package so vendoring or renaming cannot break the hierarchy.
_LIBRARY_ROOT: str = __name__.split(".")[0]

_DEFAULT_LEVEL: int = logging.ERROR
_DEFAULT_HANDLER_NAME: str = "fundus-stderr"
_DEFAULT_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Never give the queue handler a formatter: what it forwards is formatted again on arrival.
_QUEUE_HANDLER_NAME: str = "fundus-queue"

# Records a worker gathers before sending them on, and how long it sits on a part-filled
# batch. The capacity is also the ceiling on what a killed worker can lose.
_BATCH_CAPACITY: int = 256
_FLUSH_INTERVAL: float = 0.2

# Batches in flight before workers are made to wait. Workers produce records far faster than
# handlers write them, so without this a verbose crawl grows a backlog that costs memory and
# has to be paid for at shutdown. ``ccnews`` bounds its article queue for the same reason.
_QUEUE_CAPACITY: int = 32

#: A logger to target: its name, the logger itself, or ``None`` for the library root.
LoggerRef = Union[str, logging.Logger, None]

_T = TypeVar("_T")
_P = ParamSpec("_P")

#: Module loggers created through :func:`create_logger`, keyed by module name. They are
#: ``NOTSET`` and hold no handlers unless :func:`set_log_level` or :func:`add_handler` is
#: pointed at one of them.
loggers: Dict[str, logging.Logger] = {}


def _resolve(ref: LoggerRef) -> logging.Logger:
    """Resolve a name, a logger, or ``None`` to a Fundus logger, rejecting anything else."""
    if ref is None:
        return logging.getLogger(_LIBRARY_ROOT)

    name = ref.name if isinstance(ref, logging.Logger) else ref
    if name != _LIBRARY_ROOT and not name.startswith(f"{_LIBRARY_ROOT}."):
        raise ValueError(f"{name!r} is not a {_LIBRARY_ROOT!r} logger")
    if name.endswith(".") or ".." in name:
        raise ValueError(f"{name!r} is not a valid logger name")
    # Hand back the logger passed in: one built directly is not the registry's, and
    # configuring its namesake would leave the caller holding an untouched object.
    return ref if isinstance(ref, logging.Logger) else logging.getLogger(name)


def _configure(level: int = _DEFAULT_LEVEL) -> None:
    """Install the default handler and level, unless something already configured them."""
    library_root = _resolve(None)
    if any(handler.name == _DEFAULT_HANDLER_NAME for handler in library_root.handlers):
        return

    library_root.setLevel(level)

    # Left at NOTSET on purpose: the logger is the gate, the handler emits what reaches it.
    handler = logging.StreamHandler()
    handler.set_name(_DEFAULT_HANDLER_NAME)
    handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
    library_root.addHandler(handler)


_configure()


def create_logger(name: str) -> logging.Logger:
    """Create the logger for a Fundus module.

    The logger is left unconfigured and inherits its level and handlers from the library
    root, which is what keeps a record from being emitted once per ancestor holding a handler.

    Args:
        name: Reference name for the logger, conventionally the module's ``__name__``.

    Returns:
        The logger for ``name``.

    Raises:
        ValueError: If ``name`` lies outside the Fundus logger hierarchy, where it would
            inherit neither the level nor the handlers configured here.
    """
    logger = _resolve(name)
    loggers[name] = logger
    return logger


def set_log_level(level: int, logger: LoggerRef = None) -> None:
    """Set the log level for the library, or for a single module.

    Args:
        level: The new log level.
        logger: The logger to set it on. Defaults to the library root, which applies to every
            module that has not been given a level of its own.
    """
    _resolve(logger).setLevel(level)


def add_handler(handler: logging.Handler, logger: LoggerRef = None) -> None:
    """Add a handler to the library, or to a single module.

    A handler only receives records its logger let through, so pair this with
    :func:`set_log_level` when it is meant to capture more than the current level.

    Args:
        handler: The handler to add. Must have a name set.
        logger: The logger to add it to. Defaults to the library root, which applies to every
            module. Naming a package logger — ``"fundus.scraping.pipeline"`` — covers that
            subtree.

    Raises:
        ValueError: If the handler has no name, if the target logger already carries a handler
            of that name, or if ``logger`` is outside the Fundus hierarchy.
    """
    if not handler.name:
        raise ValueError("Handlers to add must have a name set")

    target = _resolve(logger)
    if any(existing.name == handler.name for existing in target.handlers):
        raise ValueError(f"Handler with name {handler.name!r} already exists on {target.name!r}")

    target.addHandler(handler)


def remove_handler(name: str, logger: LoggerRef = None) -> logging.Handler:
    """Remove a handler from the library, or from a single module.

    The handler is returned rather than closed, so it stays usable elsewhere. Closing it —
    which a :class:`logging.FileHandler` needs to release its descriptor — is the caller's.

    Args:
        name: Name of the handler to remove.
        logger: The logger to remove it from. Defaults to the library root.

    Returns:
        The removed handler.

    Raises:
        ValueError: If the target logger carries no handler of that name, or if ``logger`` is
            outside the Fundus hierarchy.
    """
    target = _resolve(logger)
    for handler in target.handlers:
        if handler.name == name:
            target.removeHandler(handler)
            return handler
    raise ValueError(f"No handler with name {name!r} on {target.name!r}")


def get_handlers(logger: LoggerRef = None) -> List[logging.Handler]:
    """Get a logger's own handlers, not those it inherits by propagation.

    Args:
        logger: The logger to inspect. Defaults to the library root.

    Returns:
        The logger's handlers.
    """
    return list(_resolve(logger).handlers)


class _NoTaskDone:
    """Hides ``task_done`` from :class:`~logging.handlers.QueueListener`.

    The listener calls it once per record when the queue has it — across a manager, a second
    round trip to signal a completion nothing waits on.
    """

    def __init__(self, queue: Queue[Any]) -> None:
        self._queue = queue

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        return self._queue.get(block, timeout)

    def put_nowait(self, item: Any) -> None:
        self._queue.put_nowait(item)


class _BatchingQueueHandler(logging.handlers.QueueHandler):
    """Sends records to the parent process in batches.

    The trip costs the same for one record as for many, and paying it per record caps the
    rate the parent can accept well below what several workers produce. The cost is the
    buffer: a worker is terminated rather than asked to stop, so it dies with whatever it
    was holding — at most ``capacity`` records, and :func:`flush_worker_logs` empties it
    where a completed crawl ends up.
    """

    def __init__(
        self,
        queue: Queue[Any],
        capacity: int = _BATCH_CAPACITY,
        interval: float = _FLUSH_INTERVAL,
    ) -> None:
        super().__init__(queue)
        # Kept apart from ``self.queue``, which is typed for ``put_nowait`` alone.
        self._queue: Queue[Any] = queue
        self._capacity = capacity
        self._interval = interval
        self._buffer: List[logging.LogRecord] = []
        self._lock = threading.Lock()
        self._wakeup = threading.Event()
        self._closing = threading.Event()
        self._ticker = threading.Thread(target=self._tick, daemon=True, name="fundus-log-flush")
        self._ticker.start()

    def _tick(self) -> None:
        while not self._closing.is_set():
            self._wakeup.wait(self._interval)
            self._wakeup.clear()
            with suppress(Exception):
                self.flush()

    def enqueue(self, record: logging.LogRecord) -> None:
        with self._lock:
            self._buffer.append(record)
            full = len(self._buffer) >= self._capacity
        if full:
            self.flush()
        elif record.levelno >= logging.WARNING:
            # Records explaining a failure should not wait out an interval when that failure
            # is about to end the crawl. Waking the sender rather than sending from here
            # keeps a run that warns steadily — one bad WARC file warns per record — from
            # paying for the wire on every one of them.
            self._wakeup.set()

    def flush(self) -> None:
        with self._lock:
            batch, self._buffer = self._buffer, []
        if not batch:
            return
        try:
            # Blocks once the queue is full, which is the point: a worker outrunning the
            # handlers is made to wait rather than allowed to build a backlog. Nothing waits
            # forever — the pool terminates its workers before the listener is stopped.
            self._queue.put(batch)
        except Exception:
            self._send_individually(batch)

    def _send_individually(self, batch: List[logging.LogRecord]) -> None:
        """Retry a record at a time, so one that cannot be pickled costs only itself."""
        for record in batch:
            try:
                self._queue.put([record])
            except Exception:
                self.handleError(record)

    def close(self) -> None:
        self._closing.set()
        self._wakeup.set()
        with suppress(Exception):
            self.flush()
        super().close()


class _Listener(logging.handlers.QueueListener):
    """Emits what workers send back, handing each record to the logger it came from.

    Going through the logger rather than a fixed handler list is what makes a worker's record
    behave like one logged here: module-scoped handlers fire, propagation to an application's
    root logger happens, and a handler added mid-crawl is picked up. ``Logger.handle`` applies
    no level check, so the worker's level is not applied twice.

    Stopping drains what is left, unbounded in time; the bound is the queue's size instead.
    """

    def handle(self, record: Any) -> None:
        for item in record if isinstance(record, list) else (record,):
            try:
                logging.getLogger(item.name).handle(item)
            except Exception:
                # This thread dying would leave every worker blocked on a queue nobody is
                # emptying, turning one bad record into a stalled crawl.
                if logging.raiseExceptions and sys.stderr:
                    traceback.print_exc(file=sys.stderr)


def _configure_subprocess(queue: Queue[Any], levels: Dict[str, int]) -> None:
    """Point this process at `queue`, replacing the handlers it started with."""
    library_root = _resolve(None)
    for handler in list(library_root.handlers):
        library_root.removeHandler(handler)

    handler = _BatchingQueueHandler(queue)
    handler.set_name(_QUEUE_HANDLER_NAME)
    library_root.addHandler(handler)

    for name, level in levels.items():
        logging.getLogger(name).setLevel(level)


def flush_worker_logs(target: Callable[_P, _T]) -> Callable[_P, _T]:
    """Wrap a worker task so its buffered records are sent on before it returns.

    Workers are terminated rather than asked to stop, so a buffer still full when a unit of
    work ends would go down with the process. This is what makes a completed crawl lossless.

    Args:
        target: The worker task to wrap. Must not be a generator function, whose body would
            not have run by the time the flush happens.

    Returns:
        The task, flushing this process' Fundus handlers on the way out.
    """

    @wraps(target)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        try:
            return target(*args, **kwargs)
        finally:
            for handler in _resolve(None).handlers:
                with suppress(Exception):
                    handler.flush()

    return wrapper


@contextmanager
def worker_logging(manager: SyncManager) -> Iterator[Callable[[], None]]:
    """Emit worker-process log records here, yielding the initializer that arranges it.

    Workers get a single queue handler and none of their own; this process drains the queue
    and emits what arrives. Handlers therefore stay in the process that built them, so one
    that cannot be rebuilt from a description keeps working, and a log file has one writer
    rather than several — which the standard library does not support.

    Records are emitted on the listener's thread, and the queue is bounded, so a crawl
    logging faster than its handlers can write is slowed to their pace.

    Args:
        manager: The manager whose queue carries records between the processes.

    Yields:
        The initializer to start the worker processes with.
    """
    library_root = _resolve(None)
    queue: Queue[Any] = manager.Queue(maxsize=_QUEUE_CAPACITY)

    levels = {library_root.name: library_root.level}
    levels.update({name: logger.level for name, logger in loggers.items() if logger.level != logging.NOTSET})

    listener = _Listener(_NoTaskDone(queue))
    listener.start()
    try:
        yield partial(_configure_subprocess, queue, levels)
    finally:
        # An error here would replace whatever exception is already leaving the crawl.
        with suppress(Exception):
            listener.stop()
