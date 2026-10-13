import threading
import time
from typing import List

from fundus.scraping.delay import Pacer, RobotsCrawlDelay
from tests.fixtures.builders import mock_robots


def _supplied_delay() -> float:
    return 1.0


class TestPacer:
    def test_no_delay_never_sleeps(self):
        sleeps: List[float] = []
        pacer = Pacer(delay=None, sleep=sleeps.append)
        pacer()
        pacer()
        assert sleeps == []

    def test_first_call_does_not_sleep(self):
        sleeps: List[float] = []
        pacer = Pacer(delay=lambda: 5.0, sleep=sleeps.append)
        pacer()
        assert sleeps == []

    def test_next_call_sleeps_the_remaining_delay(self):
        sleeps: List[float] = []
        pacer = Pacer(delay=lambda: 1.0, sleep=sleeps.append)
        pacer()
        pacer()
        assert len(sleeps) == 1
        assert 0.9 <= sleeps[0] <= 1.0

    def test_elapsed_delay_is_not_slept_again(self):
        sleeps: List[float] = []
        pacer = Pacer(delay=lambda: 0.01, sleep=sleeps.append)
        pacer()
        time.sleep(0.02)
        pacer()
        assert sleeps == []

    def test_delay_is_not_evaluated_before_it_is_due(self):
        # lets a delay resolve lazily, e.g. by reading robots.txt (see RobotsCrawlDelay)
        calls: List[None] = []

        def delay() -> float:
            calls.append(None)
            return 1.0

        pacer = Pacer(delay=delay, sleep=lambda seconds: None)
        assert calls == []
        pacer()
        assert calls == []
        pacer()
        assert len(calls) == 1

    def test_shared_across_threads_paces_callers_as_one(self):
        sleeps: List[float] = []
        pacer = Pacer(delay=lambda: 1.0, sleep=sleeps.append)
        threads = [threading.Thread(target=pacer) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        # every caller but the first waits on its predecessor
        assert len(sleeps) == 3


class TestRobotsCrawlDelay:
    def test_robots_delay_overrides_default(self):
        assert RobotsCrawlDelay(mock_robots(crawl_delay=5.0), "*", default=_supplied_delay)() == 5.0

    def test_falls_back_to_default(self):
        assert RobotsCrawlDelay(mock_robots(crawl_delay=None), "*", default=_supplied_delay)() == 1.0

    def test_without_crawl_delay_and_default_there_is_nothing_to_wait_for(self):
        assert RobotsCrawlDelay(mock_robots(crawl_delay=None), "*")() == 0.0

    def test_looks_up_the_given_user_agent(self):
        robots = mock_robots(crawl_delay=None)
        RobotsCrawlDelay(robots, "fundus")()
        robots.crawl_delay.assert_called_once_with("fundus")

    def test_robots_is_read_on_first_call_not_at_construction(self):
        robots = mock_robots(crawl_delay=5.0)
        delay = RobotsCrawlDelay(robots, "*")
        robots.crawl_delay.assert_not_called()
        delay()
        robots.crawl_delay.assert_called_once()

    def test_resolves_once(self):
        robots = mock_robots(crawl_delay=None)
        delay = RobotsCrawlDelay(robots, "*", default=_supplied_delay)
        delay()
        delay()
        robots.crawl_delay.assert_called_once()
