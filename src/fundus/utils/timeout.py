import _thread as thread
import contextlib
import threading
import time
from typing import Callable, Iterator, Optional

from typing_extensions import ParamSpec

P = ParamSpec("P")


class Stopwatch:
    def __init__(self):
        self._start = time.time()

    @property
    def time(self) -> float:
        return max(0.0, time.time() - self._start)

    def reset(self):
        self._start = time.time()


class ResettableTimer(threading.Thread):
    def __init__(
        self,
        seconds: float,
        func: Callable[P, None],
        interval: float = 0.1,
        args: P.args = tuple(),
        kwargs: P.kwargs = None,
    ) -> None:
        """Resettable timer executing <func> after <time> seconds, checking every <interval>.

        Args:
            seconds: Time to pass in seconds.
            func: Callable to execute when <time> has passed.
            interval: Check every <interval> seconds if condition is met (reduce workload on CPU).
            *args: Arguments to <func>.
            **kwargs: Keyword arguments to <func>.
        """
        super().__init__(target=func, args=args, kwargs=kwargs)
        self.seconds = seconds
        self.interval = interval
        self.watch = Stopwatch()
        self._canceled = threading.Event()

    def run(self) -> None:
        self.watch.reset()
        while True and self.watch.time < self.seconds:
            time.sleep(self.interval)
            if self._canceled.is_set():
                return
        # noinspection PyUnresolvedReferences
        self._target(*self._args, **self._kwargs)  # type: ignore[attr-defined]

    def reset(self) -> None:
        self.watch.reset()

    def cancel(self) -> None:
        self._canceled.set()


def _interrupt_handler() -> None:
    thread.interrupt_main()


# noinspection PyPep8Naming
@contextlib.contextmanager
def Timeout(
    seconds: float, silent: bool = False, callback: Optional[Callable[[], None]] = None, disable: bool = False
) -> Iterator[ResettableTimer]:
    """Context manager applying a resettable timeout.

    Contextmanager implementation of timeout which does not relly on a function.
    If enter the context manager will time out after <time> seconds.
    See docstring of 'timeout' for more information

    Args:
        seconds: The time after which to timout in seconds. If set to <= 0, set timer never start.
        silent: If True, the KeyboardInterrupt will be silently ignored and None returned instead.
            Defaults to False.
        callback: If given, will be called instead of raising KeyboardInterrupt. Defaults to None.
        disable: If True, the timer will never start effectively disable the timeout.

    Returns:
        ResettableTimer: A timer to reset or cancel the timeout.
    """
    timer = ResettableTimer(seconds, callback or _interrupt_handler)
    try:
        if not disable:
            timer.start()
        yield timer
    except KeyboardInterrupt as err:
        if not silent:
            raise TimeoutError from err
    finally:
        timer.cancel()
        del timer
