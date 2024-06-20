import _thread as thread
import contextlib
import threading
import time
from functools import wraps
from typing import Callable, Iterator, Literal, Optional, TypeVar, overload

from typing_extensions import ParamSpec

P = ParamSpec("P")
T = TypeVar("T")


class Stopwatch:
    def __init__(self):
        self._start = time.time()

    @property
    def time(self) -> float:
        return max(0.0, time.time() - self._start)

    def reset(self):
        self._start = time.time()


class Timer(threading.Thread):
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


@overload
def timeout(func: Callable[P, T], seconds: float, silent: Literal[False] = ...) -> Callable[P, T]:
    ...


@overload
def timeout(func: Callable[P, T], seconds: float, silent: Literal[True]) -> Callable[P, Optional[T]]:
    ...


def timeout(
    func: Callable[P, T], seconds: float, silent: bool = False, callback: Optional[Callable[[], None]] = None
) -> Callable[P, Optional[T]]:
    """Function wrapper raising a KeyboardInterrupt in main thread.

    This wrapper raises a KeyboardInterrupt in the main thread <time> seconds
    after <func> was called.

    The timeout is canceled if the function returns before <time> seconds.

    If <callback> is given, it will be called instead.

    If <silent> is set, the KeyboardInterrupt will be silently ignored and the wrapper
    returns None before <func> finished.

    Args:
        func: The function to wrap.
        seconds: The time after which to timout in seconds. If set to <= 0, set timer never start.
        silent: If True, the KeyboardInterrupt will be silently ignored and None returned instead.
            Defaults to False.
        callback: If given, will be called instead of raising KeyboardInterrupt. Defaults to None.

    Returns:
        Optional[T]: T if <func> returns before <time> seconds, else None if <silent> is set to True.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Optional[T]:
        timer = threading.Timer(seconds, callback or _interrupt_handler)

        try:
            if seconds > 0:
                timer.start()
            result = func(*args, **kwargs)
        except KeyboardInterrupt as err:
            if silent:
                return None
            else:
                raise TimeoutError from err
        finally:
            timer.cancel()
            del timer
        return result

    return wrapper


@contextlib.contextmanager
def Timeout(seconds: float, silent: bool = False, callback: Optional[Callable[[], None]] = None) -> Iterator[Timer]:
    """Context manager applying a resettable timeout.

    Contextmanager implementation of timeout which does not relly on a function.
    If enter the context manager will time out after <time> seconds.
    See docstring of 'timeout' for more information

    Args:
        seconds: The time after which to timout in seconds. If set to <= 0, set timer never start.
        silent: If True, the KeyboardInterrupt will be silently ignored and None returned instead.
            Defaults to False.
        callback: If given, will be called instead of raising KeyboardInterrupt. Defaults to None.

    Returns:
        Timer: A timer that can be reset or canceled
    """
    timer = Timer(seconds, callback or _interrupt_handler)
    try:
        if seconds > 0:
            timer.start()
        yield timer
    except KeyboardInterrupt as err:
        if not silent:
            raise TimeoutError from err
    finally:
        timer.cancel()
        del timer
