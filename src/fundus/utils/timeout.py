import _thread as thread
import contextlib
import threading
import time
from typing import Callable, Iterator, Optional


def _interrupt_handler() -> None:
    thread.interrupt_main()


class ResettableTimer:
    class _Stopwatch:
        def __init__(self) -> None:
            self._start = time.time()

        @property
        def elapsed(self) -> float:
            return max(0.0, time.time() - self._start)

        def reset(self) -> None:
            self._start = time.time()

    def __init__(self, seconds: float, func: Callable[[], None], interval: float = 0.1) -> None:
        self.seconds = seconds
        self.interval = interval
        self._func = func
        self._watch = self._Stopwatch()
        self._canceled = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        self._watch.reset()
        while self._watch.elapsed < self.seconds:
            time.sleep(self.interval)
            if self._canceled.is_set():
                return
        self._func()

    def start(self) -> None:
        self._thread.start()

    def reset(self) -> None:
        self._watch.reset()

    def cancel(self) -> None:
        self._canceled.set()


# noinspection PyPep8Naming
@contextlib.contextmanager
def Timeout(
    seconds: Optional[float], silent: bool = False, callback: Optional[Callable[[], None]] = None
) -> Iterator[ResettableTimer]:
    """Context manager applying a resettable timeout.

    Args:
        seconds: The time after which to timeout in seconds. If None, the timeout is disabled.
        silent: If True, the KeyboardInterrupt will be silently ignored. Defaults to False.
        callback: If given, will be called instead of raising KeyboardInterrupt. Defaults to None.

    Returns:
        ResettableTimer: A timer to reset or cancel the timeout.
    """
    timer = ResettableTimer(seconds or 0, callback or _interrupt_handler)
    try:
        if seconds is not None:
            timer.start()
        yield timer
    except KeyboardInterrupt as err:
        if not silent:
            raise TimeoutError from err
    finally:
        timer.cancel()
