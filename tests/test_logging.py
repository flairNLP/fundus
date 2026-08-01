import io
import logging
import logging.handlers
import sys
from multiprocessing import Manager
from multiprocessing.managers import SyncManager
from queue import Queue
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import pytest

from fundus.logging import (
    _BATCH_CAPACITY,
    LoggerRef,
    _BatchingQueueHandler,
    _configure_subprocess,
    add_handler,
    create_logger,
    flush_worker_logs,
    get_handlers,
    loggers,
    remove_handler,
    set_log_level,
    worker_logging,
)

_LIBRARY_ROOT = "fundus"

# Long enough that the sending thread will not act on its own inside a test, so what a test
# observes is the buffer's doing.
_NEVER = 3600.0

# Generous upper bound on delivery; a test that waits this long has already failed.
_DELIVERY_TIMEOUT = 5.0


@pytest.fixture(scope="module")
def manager() -> Iterator[SyncManager]:
    """One manager process for the whole module; `worker_logging` takes its queue from it."""
    with Manager() as active_manager:
        yield active_manager


def fundus_loggers() -> Iterator[Tuple[str, logging.Logger]]:
    """Yield the library root and every Fundus logger currently in the logging registry."""
    yield _LIBRARY_ROOT, logging.getLogger(_LIBRARY_ROOT)
    for name, logger in list(logging.Logger.manager.loggerDict.items()):
        if name.startswith(f"{_LIBRARY_ROOT}.") and isinstance(logger, logging.Logger):
            yield name, logger


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


class TestModuleLoggers:
    def test_nested_module_logger_emits_once(self):
        # A module logger nested under another module logger must not be handled once per
        # ancestor. Regression: fundus.scraping.pipeline.source.web under
        # fundus.scraping.pipeline printed every record twice.
        create_logger("fundus.parent")
        child = create_logger("fundus.parent.child")
        captured = probe()
        set_log_level(logging.DEBUG)

        child.error("once")

        assert lines(captured) == ["fundus.parent.child|ERROR|once"]

    def test_module_logger_reaches_library_handler(self):
        logger = create_logger("fundus.somewhere.deep")
        captured = probe()

        logger.error("inherited")

        assert lines(captured) == ["fundus.somewhere.deep|ERROR|inherited"]

    def test_rejects_logger_outside_the_hierarchy(self):
        # Such a logger would inherit neither the level nor the handlers set up here.
        with pytest.raises(ValueError):
            create_logger("not_fundus.module")

    def test_registers_logger_by_name(self):
        create_logger("fundus.registered")

        assert "fundus.registered" in loggers


class TestLogLevel:
    def test_level_gates_before_handlers(self):
        # The handler is wide open, so anything missing from the buffer was dropped by the
        # logger — which is the whole point of holding the level there.
        logger = create_logger("fundus.gated")
        captured = probe(level=logging.DEBUG)
        set_log_level(logging.ERROR)

        logger.debug("dropped")
        logger.error("kept")

        assert lines(captured) == ["fundus.gated|ERROR|kept"]

    def test_raising_level_for_one_module_leaves_siblings_alone(self):
        loud = create_logger("fundus.loud")
        quiet = create_logger("fundus.quiet")
        captured = probe()
        set_log_level(logging.ERROR)
        set_log_level(logging.DEBUG, logger="fundus.loud")

        loud.debug("heard")
        quiet.debug("unheard")

        assert lines(captured) == ["fundus.loud|DEBUG|heard"]

    def test_accepts_a_logger_object_as_target(self):
        logger = create_logger("fundus.by_object")
        captured = probe()
        set_log_level(logging.ERROR)
        set_log_level(logging.DEBUG, logger=logger)

        logger.debug("heard")

        assert lines(captured) == ["fundus.by_object|DEBUG|heard"]

    def test_configures_the_logger_it_was_given(self):
        # A logger built directly is not the registry's; configuring its namesake there
        # would leave the caller holding an object nothing happened to.
        detached = logging.Logger("fundus.detached")

        set_log_level(logging.DEBUG, logger=detached)

        assert detached.level == logging.DEBUG

    @pytest.mark.parametrize("target", ["requests", "fundusXYZ", "fundus.", "fundus..odd", ""])
    def test_rejects_targets_outside_the_hierarchy(self, target):
        with pytest.raises(ValueError):
            set_log_level(logging.DEBUG, logger=target)


class TestAddHandler:
    def test_handler_on_library_root_receives_every_module(self):
        first = create_logger("fundus.first")
        second = create_logger("fundus.second")
        captured = probe()

        first.error("a")
        second.error("b")

        assert lines(captured) == ["fundus.first|ERROR|a", "fundus.second|ERROR|b"]

    def test_handler_on_a_module_receives_only_that_module(self):
        targeted = create_logger("fundus.targeted")
        other = create_logger("fundus.other")
        captured = probe(logger="fundus.targeted")

        targeted.error("mine")
        other.error("not mine")

        assert lines(captured) == ["fundus.targeted|ERROR|mine"]

    def test_handler_on_a_package_receives_its_subtree(self):
        child = create_logger("fundus.pkg.child")
        outside = create_logger("fundus.elsewhere")
        captured = probe(logger="fundus.pkg")

        child.error("subtree")
        outside.error("outside")

        assert lines(captured) == ["fundus.pkg.child|ERROR|subtree"]

    def test_handler_does_not_receive_records_the_logger_dropped(self):
        # The handler is not a second, independent gate: even wide open it sees nothing,
        # because raising verbosity means raising the logger's level.
        logger = create_logger("fundus.below_level")
        captured = probe(level=logging.DEBUG)
        set_log_level(logging.ERROR)

        logger.debug("dropped")

        assert lines(captured) == []

    @pytest.mark.parametrize("name", [None, ""])
    def test_rejects_handler_without_a_name(self, name):
        handler = logging.StreamHandler()
        handler.set_name(name)

        with pytest.raises(ValueError):
            add_handler(handler)

    def test_rejects_duplicate_name_on_the_same_logger(self):
        probe(name="taken")

        with pytest.raises(ValueError):
            probe(name="taken")

    def test_allows_the_same_name_on_different_loggers(self):
        first = create_logger("fundus.scope_a")
        second = create_logger("fundus.scope_b")
        captured_a = probe(logger="fundus.scope_a", name="scoped")
        captured_b = probe(logger="fundus.scope_b", name="scoped")

        first.error("a")
        second.error("b")

        assert lines(captured_a) == ["fundus.scope_a|ERROR|a"]
        assert lines(captured_b) == ["fundus.scope_b|ERROR|b"]


class TestRemoveHandler:
    def test_removed_handler_stops_receiving_records(self):
        logger = create_logger("fundus.removed")
        captured = probe()

        remove_handler("probe")
        logger.error("after removal")

        assert lines(captured) == []

    def test_returns_the_handler_without_closing_it(self, tmp_path):
        # Closing is the caller's business: a FileHandler needs it to release its
        # descriptor, but a returned handler must stay usable to be re-added elsewhere.
        # A closed FileHandler drops its stream, which is what makes this observable.
        file_handler = logging.FileHandler(tmp_path / "fundus.log", delay=False)
        file_handler.set_name("file")
        add_handler(file_handler)

        handler = remove_handler("file")
        try:
            assert handler.stream is not None  # type: ignore[attr-defined]
        finally:
            handler.close()

    def test_removes_from_the_logger_it_was_given(self):
        logger = create_logger("fundus.scoped_removal")
        captured = probe(logger="fundus.scoped_removal")

        remove_handler("probe", logger="fundus.scoped_removal")
        logger.error("after removal")

        assert lines(captured) == []

    def test_rejects_unknown_name(self):
        with pytest.raises(ValueError):
            remove_handler("never added")


class TestPropagation:
    def test_records_reach_an_application_configured_root(self):
        # Fundus ships its own handler but must not cut itself out of the host
        # application's logging; propagation to the root logger stays on.
        logger = create_logger("fundus.propagating")
        buffer = io.StringIO()
        app_handler = logging.StreamHandler(buffer)
        app_handler.setFormatter(logging.Formatter("APP|%(message)s"))
        logging.getLogger().addHandler(app_handler)
        try:
            logger.error("reaches the app")
        finally:
            logging.getLogger().removeHandler(app_handler)

        assert lines(buffer) == ["APP|reaches the app"]

    def test_removing_the_default_handler_leaves_propagation_intact(self):
        logger = create_logger("fundus.owned_by_app")
        buffer = io.StringIO()
        app_handler = logging.StreamHandler(buffer)
        app_handler.setFormatter(logging.Formatter("APP|%(message)s"))
        logging.getLogger().addHandler(app_handler)
        try:
            remove_handler("fundus-stderr")
            logger.error("still reaches the app")
        finally:
            logging.getLogger().removeHandler(app_handler)

        assert lines(buffer) == ["APP|still reaches the app"]
        assert get_handlers() == []


def worker_queue(initializer: Callable[[], None]) -> "Queue[Any]":
    """The queue a worker started with `initializer` logs onto.

    Standing in for the worker process itself: the queue cannot be reached any other way
    from here, and putting a record on it directly is what a worker's queue handler does.
    """
    queue: "Queue[Any]" = initializer.args[0]  # type: ignore[attr-defined]
    return queue


def worker_record(name: str, message: str, level: int = logging.ERROR) -> logging.LogRecord:
    return logging.LogRecord(name, level, "worker.py", 1, message, None, None)


def quiet_logger(queue: "Queue[Any]", interval: float) -> logging.Logger:
    """Set this process up as a worker logging onto `queue`, with a chosen flush interval.

    Records travel on a thread, so a test that wants to watch what the buffer does has to
    keep that thread from doing it first. Giving the handler an interval it will not reach
    within the test makes the outcome depend on the buffer alone, rather than on which of
    the two got there first.
    """
    library_root = logging.getLogger(_LIBRARY_ROOT)
    for existing in list(library_root.handlers):
        library_root.removeHandler(existing)
    handler = _BatchingQueueHandler(queue, interval=interval)
    handler.set_name("fundus-queue")
    library_root.addHandler(handler)
    library_root.setLevel(logging.DEBUG)
    return create_logger("fundus.worker")


class TestWorkerConfiguration:
    """What the initializer does to the worker process it runs in."""

    def test_worker_logs_through_the_queue_instead_of_its_own_handlers(self):
        queue: "Queue[Any]" = Queue()
        logger = create_logger("fundus.worker")
        captured = probe()  # a handler the worker process was started with
        set_log_level(logging.DEBUG)

        _configure_subprocess(queue, {_LIBRARY_ROOT: logging.DEBUG})
        logger.error("from the worker")

        assert lines(captured) == []
        assert [record.getMessage() for record in queue.get(timeout=_DELIVERY_TIMEOUT)] == ["from the worker"]

    def test_worker_sends_a_warning_without_waiting_out_the_interval(self):
        # A record that explains a failure should not be sitting in a buffer when that failure
        # ends the crawl. The interval here is long enough that only the wake-up can deliver.
        queue: "Queue[Any]" = Queue()
        logger = quiet_logger(queue, interval=_NEVER)

        logger.warning("something went wrong")

        assert [record.getMessage() for record in queue.get(timeout=_DELIVERY_TIMEOUT)] == ["something went wrong"]

    def test_worker_holds_routine_records_back(self):
        # Sending each record on its own is what caps the rate the parent can take them at.
        queue: "Queue[Any]" = Queue()
        logger = quiet_logger(queue, interval=_NEVER)

        logger.debug("routine chatter")

        assert queue.empty()

    def test_worker_sends_a_batch_once_it_is_full(self):
        queue: "Queue[Any]" = Queue()
        logger = quiet_logger(queue, interval=_NEVER)

        for index in range(_BATCH_CAPACITY):
            logger.debug("chatter %d", index)

        assert len(queue.get(timeout=_DELIVERY_TIMEOUT)) == _BATCH_CAPACITY

    def test_a_part_filled_buffer_goes_out_on_the_interval(self):
        # Without this a worker that goes quiet holds its last few records indefinitely.
        queue: "Queue[Any]" = Queue()
        logger = quiet_logger(queue, interval=0.01)

        logger.debug("routine chatter")

        assert [record.getMessage() for record in queue.get(timeout=_DELIVERY_TIMEOUT)] == ["routine chatter"]

    def test_one_record_that_cannot_be_sent_does_not_take_the_batch_with_it(self):
        # A batch crosses as a unit, so without a fallback a single record a queue refuses
        # would cost every record gathered beside it.
        class RefusesBatches(Queue):  # type: ignore[type-arg]
            def put(self, item, block=True, timeout=None):
                if len(item) > 1:
                    raise ValueError("no batches")
                super().put(item, block, timeout)

        queue: "Queue[Any]" = RefusesBatches()
        logger = quiet_logger(queue, interval=_NEVER)

        logger.debug("first")
        logger.debug("second")
        for handler in get_handlers():
            handler.flush()

        delivered = [record.getMessage() for _ in range(2) for record in queue.get(timeout=_DELIVERY_TIMEOUT)]
        assert delivered == ["first", "second"]

    def test_finishing_a_unit_of_work_sends_what_is_buffered(self):
        # Regression: the pool terminates its workers, so a buffer still full when the work
        # ends goes down with the process.
        queue: "Queue[Any]" = Queue()
        logger = create_logger("fundus.worker")
        _configure_subprocess(queue, {_LIBRARY_ROOT: logging.DEBUG})

        @flush_worker_logs
        def task() -> str:
            logger.debug("routine chatter")
            return "done"

        assert task() == "done"
        assert [record.getMessage() for record in queue.get_nowait()] == ["routine chatter"]

    def test_finishing_a_unit_of_work_sends_what_is_buffered_even_when_it_fails(self):
        queue: "Queue[Any]" = Queue()
        logger = create_logger("fundus.worker")
        _configure_subprocess(queue, {_LIBRARY_ROOT: logging.DEBUG})

        @flush_worker_logs
        def task() -> None:
            logger.debug("routine chatter")
            raise ValueError("boom")

        with pytest.raises(ValueError):
            task()

        assert [record.getMessage() for record in queue.get_nowait()] == ["routine chatter"]

    def test_worker_gets_the_library_level(self, manager):
        create_logger("fundus.worker")
        set_log_level(logging.DEBUG)

        with worker_logging(manager) as initializer:
            initializer()

            assert logging.getLogger("fundus.worker").getEffectiveLevel() == logging.DEBUG

    def test_worker_gets_a_scoped_level(self, manager):
        # Regression: carrying only the library root's level left a module raised to DEBUG
        # silent in every worker, which is where a CC-NEWS crawl does all its work.
        create_logger("fundus.loud")
        create_logger("fundus.quiet")
        set_log_level(logging.ERROR)
        set_log_level(logging.DEBUG, logger="fundus.loud")

        with worker_logging(manager) as initializer:
            initializer()

            assert logging.getLogger("fundus.loud").getEffectiveLevel() == logging.DEBUG
            assert logging.getLogger("fundus.quiet").getEffectiveLevel() == logging.ERROR

    def test_worker_drops_a_record_below_the_level_without_queueing_it(self):
        queue: "Queue[Any]" = Queue()
        logger = create_logger("fundus.worker")

        _configure_subprocess(queue, {_LIBRARY_ROOT: logging.ERROR})
        logger.debug("never sent")

        assert queue.empty()


class TestWorkerLogging:
    """What this process does with the records its workers send back."""

    def test_queued_records_reach_the_library_handler(self, manager):
        create_logger("fundus.worker")
        captured = probe()

        with worker_logging(manager) as initializer:
            worker_queue(initializer).put(worker_record("fundus.worker", "from the worker"))

        assert lines(captured) == ["fundus.worker|ERROR|from the worker"]

    def test_queued_records_reach_a_module_scoped_handler(self, manager):
        # The listener hands each record back to its own logger, so a handler scoped to one
        # module sees worker records exactly as it sees records logged here.
        create_logger("fundus.scoped_worker")
        captured = probe(logger="fundus.scoped_worker")

        with worker_logging(manager) as initializer:
            worker_queue(initializer).put(worker_record("fundus.scoped_worker", "scoped"))

        assert lines(captured) == ["fundus.scoped_worker|ERROR|scoped"]

    def test_queued_records_propagate_to_an_application_configured_root(self, manager):
        create_logger("fundus.worker")
        buffer = io.StringIO()
        app_handler = logging.StreamHandler(buffer)
        app_handler.setFormatter(logging.Formatter("APP|%(message)s"))
        logging.getLogger().addHandler(app_handler)
        try:
            with worker_logging(manager) as initializer:
                worker_queue(initializer).put(worker_record("fundus.worker", "reaches the app"))
        finally:
            logging.getLogger().removeHandler(app_handler)

        assert lines(buffer) == ["APP|reaches the app"]

    def test_a_traceback_survives_the_trip(self, manager):
        logger = create_logger("fundus.worker")
        captured = probe()
        try:
            raise ValueError("boom")
        except ValueError:
            record = logger.makeRecord("fundus.worker", logging.ERROR, "worker.py", 1, "failed", (), sys.exc_info())
        with worker_logging(manager) as initializer:
            # A worker's queue handler renders the traceback into the message before sending,
            # which is what lets it cross a process boundary at all.
            handler = logging.handlers.QueueHandler(worker_queue(initializer))
            handler.emit(record)

        assert "ValueError: boom" in captured.getvalue()

    def test_leaves_this_process_logging_as_it_found_it(self, manager):
        captured = probe()

        with worker_logging(manager):
            pass
        logging.getLogger("fundus.after").error("after")

        assert lines(captured) == ["fundus.after|ERROR|after"]

    def test_records_queued_after_shutdown_are_not_emitted(self, manager):
        create_logger("fundus.worker")
        captured = probe()

        with worker_logging(manager) as initializer:
            queue = worker_queue(initializer)
        queue.put(worker_record("fundus.worker", "too late"))

        assert lines(captured) == []
