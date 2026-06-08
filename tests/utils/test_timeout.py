import threading
import time

import pytest

from fundus.utils.timeout import ResettableTimer, Timeout


class TestStopwatch:
    def test_elapsed_starts_near_zero(self):
        sw = ResettableTimer._Stopwatch()
        assert sw.elapsed < 0.05

    def test_elapsed_increases_over_time(self):
        sw = ResettableTimer._Stopwatch()
        time.sleep(0.1)
        assert sw.elapsed >= 0.09

    def test_elapsed_is_never_negative(self):
        sw = ResettableTimer._Stopwatch()
        assert sw.elapsed >= 0.0

    def test_reset_restarts_elapsed(self):
        sw = ResettableTimer._Stopwatch()
        time.sleep(0.1)
        sw.reset()
        assert sw.elapsed < 0.05


class TestResettableTimer:
    def test_fires_callback_after_timeout(self):
        fired = threading.Event()
        timer = ResettableTimer(0.2, fired.set)
        timer.start()
        assert fired.wait(timeout=1.0)

    def test_does_not_fire_before_timeout(self):
        fired = threading.Event()
        timer = ResettableTimer(0.5, fired.set)
        timer.start()
        assert not fired.wait(timeout=0.2)
        timer.cancel()

    def test_does_not_fire_when_canceled(self):
        fired = threading.Event()
        timer = ResettableTimer(0.3, fired.set)
        timer.start()
        timer.cancel()
        assert not fired.wait(timeout=0.6)

    def test_reset_postpones_firing(self):
        fired = threading.Event()
        timer = ResettableTimer(0.3, fired.set)
        timer.start()
        time.sleep(0.15)
        timer.reset()
        assert not fired.wait(timeout=0.15)  # 0.15s since reset, not yet
        assert fired.wait(timeout=0.5)  # fires ~0.3s after reset
        timer.cancel()

    def test_thread_is_daemon(self):
        timer = ResettableTimer(10, lambda: None)
        assert timer._thread.daemon


class TestTimeout:
    def test_disabled_when_seconds_is_none(self):
        fired = threading.Event()
        with Timeout(seconds=None, callback=fired.set):
            time.sleep(0.1)
        assert not fired.is_set()

    def test_fires_callback_on_timeout(self):
        fired = threading.Event()
        with Timeout(seconds=0.1, callback=fired.set):
            fired.wait(timeout=1.0)
        assert fired.is_set()

    def test_silent_suppresses_timeout_error(self):
        with Timeout(seconds=0.1, silent=True):
            time.sleep(0.5)

    def test_not_silent_raises_timeout_error(self):
        with pytest.raises(TimeoutError):
            with Timeout(seconds=0.1, silent=False):
                time.sleep(0.5)

    def test_yields_resettable_timer(self):
        with Timeout(seconds=None) as timer:
            assert isinstance(timer, ResettableTimer)

    def test_reset_delays_timeout(self):
        fired = threading.Event()
        with Timeout(seconds=0.3, callback=fired.set) as timer:
            time.sleep(0.15)
            timer.reset()
            assert not fired.wait(timeout=0.15)  # 0.15s since reset, not yet

    def test_timer_canceled_on_context_exit(self):
        fired = threading.Event()
        with Timeout(seconds=0.3, callback=fired.set):
            pass
        assert not fired.wait(timeout=0.5)
