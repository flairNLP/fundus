from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Callable, Optional, Protocol, runtime_checkable

from fundus.logging import create_logger

if TYPE_CHECKING:
    from fundus.publishers.base_objects import Robots

logger = create_logger(__name__)


@runtime_checkable
class Delay(Protocol):
    """Protocol to define crawl delays between batches."""

    def __call__(self) -> float:
        """Yields a float specifying the minimum crawler delay for the current article batch in seconds.

        The effective delay does include crawling execution time between batches,
        i.e. the effective delay is max(execution_time, delay).

        Examples:
            >>> import random
            >>> delay: Delay = lambda: random.random()
            Will use a random delay in [0, 1) seconds.

        Returns:
            float: The delay time in seconds.

        """
        ...


class RobotsCrawlDelay:
    """Delay following the crawl-delay a robots.txt declares, falling back to <default>.

    Resolved on the first call rather than at construction, since reading robots.txt is I/O.
    Without a crawl-delay and without a <default>, there is nothing to wait for: 0.0.
    """

    def __init__(self, robots: Robots, user_agent: str, default: Optional[Delay] = None) -> None:
        """Build a delay over the crawl-delay <robots> declares for <user_agent>.

        Args:
            robots (Robots): The robots.txt declaring the crawl-delay.
            user_agent (str): The user agent the crawl-delay is looked up for.
            default (Optional[Delay]): The delay to keep if robots.txt declares none. Defaults to None.

        """
        self.robots = robots
        self.user_agent = user_agent
        self.default = default
        self._resolved = False
        self._crawl_delay: Optional[float] = None

    def __call__(self) -> float:
        """Return the crawl-delay robots.txt declares, else the default delay, else 0.0."""
        if not self._resolved:
            self._crawl_delay = self.robots.crawl_delay(self.user_agent)
            self._resolved = True
            if self._crawl_delay is not None:
                logger.debug(
                    f"Found crawl-delay of {self._crawl_delay} seconds in robots.txt {self.robots.url!r}. "
                    f"Overwriting existing delay."
                )
        if self._crawl_delay is not None:
            return self._crawl_delay
        return self.default() if self.default is not None else 0.0


class Pacer:
    """Rate limiter keeping consecutive calls at least <delay> apart.

    Whoever calls a pacer is paced by it, so callers sharing one are paced as one: the crawler
    shares a pacer among all sources addressing a publisher to keep the delay per publisher rather
    than per source. Safe to share across threads; concurrent callers wait their turn.
    """

    def __init__(self, delay: Optional[Delay], sleep: Callable[[float], object] = time.sleep) -> None:
        """Build a pacer over <delay>.

        Args:
            delay (Optional[Delay]): The delay to keep between calls, evaluated on every call that
                follows another. If None, calls are never delayed.
            sleep (Callable[[float], object]): Waits the given number of seconds. Pass an event's
                wait() to make the delay interruptable. Defaults to time.sleep.

        """
        self.delay = delay
        self.sleep = sleep
        self._last: Optional[float] = None
        self._lock = threading.Lock()

    def __call__(self) -> None:
        """Wait out what is left of the delay since the previous call. The first call never waits."""
        if self.delay is None:
            return
        with self._lock:
            if self._last is not None and (remaining := self.delay() - (time.time() - self._last)) > 0:
                self.sleep(remaining)
            self._last = time.time()
