import io
import logging
import logging.handlers
import sys
from queue import Queue
from typing import Any, Callable

import pytest

from fundus.logging import create_logger, get_handlers, set_log_level
from fundus.logging.workers import (
    _BATCH_CAPACITY,
    _BatchingQueueHandler,
    _configure_subprocess,
    flush_worker_logs,
    worker_logging,
)
from tests.logging.conftest import LIBRARY_ROOT as _LIBRARY_ROOT
from tests.logging.conftest import lines, probe

# Long enough that the sending thread will not act on its own inside a test, so what a test
# observes is the buffer's doing.
_NEVER = 3600.0

# Generous upper bound on delivery; a test that waits this long has already failed.
_DELIVERY_TIMEOUT = 5.0


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
