import bidict
import pytest

from fundus.utils.events import EventDict


class TestEvents:
    def test_default_events(self):
        events = EventDict(default_events=["success"])

        events.alias("test")
        events.get("success")

        with pytest.raises(KeyError):
            events.get("failure")

    def test_set_clear(self):
        events = EventDict(default_events=["success"])

        events.alias("test")
        events.set_event("success")
        assert events.is_event_set("success")

        events.clear_event("success")
        assert events.is_event_set("success") == False

    def test_set_clear_all(self):
        events = EventDict(default_events=["success"])

        events.alias("thread-1", 1)
        events.alias("thread-2", 2)

        events.set_for_all("success")
        assert events.is_event_set("success", "thread-1") == events.is_event_set("success", "thread-2") == True

        events.clear_for_all("success")
        assert events.is_event_set("success", "thread-1") == events.is_event_set("success", "thread-2") == False

        events.register_event("failure", "thread-1")
        events.register_event("failure", "thread-2")

        events.set_for_all()
        assert events.is_event_set("success", "thread-1") == events.is_event_set("success", "thread-2") == True
        assert events.is_event_set("failure", "thread-1") == events.is_event_set("failure", "thread-2") == True

        events.clear_for_all()
        assert events.is_event_set("success", "thread-1") == events.is_event_set("success", "thread-2") == False
        assert events.is_event_set("failure", "thread-1") == events.is_event_set("failure", "thread-2") == False

    def test_new_event_after_set_for_all(self):
        events = EventDict(default_events=["success"])

        events.alias("thread-1", 1)
        events.set_for_all("success")
        events.alias("thread-2", 2)

        assert events.is_event_set("success", "thread-1") == True
        assert events.is_event_set("success", "thread-2") == False

    def test_set_for_all_future_true(self):
        events = EventDict(default_events=["success"])

        events.alias("thread-1", 1)
        events.set_for_all("success", future=True)
        events.alias("thread-2", 2)

        assert events.is_event_set("success", "thread-1") == True
        assert events.is_event_set("success", "thread-2") == True

    def test_clear_for_all_resets_futures(self):
        events = EventDict(default_events=["success"])

        events.set_for_all("success", future=True)
        events.clear_for_all("success")

        events.alias("thread-1", 1)
        assert events.is_event_set("success", "thread-1") == False

    def test_alias(self):
        events = EventDict(default_events=["success"])

        events.alias("main-thread")

        events.set_event("success", "main-thread")

        assert events.is_event_set("success", "main-thread") == True

    def test_set_all_with_alias(self):
        events = EventDict(default_events=["success"])

        events.alias("main-thread")

        events.set_for_all("success")

        assert events.is_event_set("success", "main-thread") == True

        events.clear_for_all("success")

        assert events.is_event_set("success", "main-thread") == False

    def test_duplicate(self):
        events = EventDict()

        events.alias("main-thread", 1)

        with pytest.raises(bidict.ValueDuplicationError):
            events.alias("new-thread", 1)

        events.alias("main-thread", 2)

        events.alias("new-thread", 1)

    def test_context_manager(self):
        events = EventDict(default_events=["success"])

        with events.context("main-thread", 1):
            with pytest.raises(bidict.ValueDuplicationError):
                events.alias("new-thread", 1)

        events.alias("new-thread", 1)

    def test_events_accessible_after_context_exits(self):
        """Events set inside a context should remain accessible after the thread exits.

        Regression test for the KeyError crash where the main crawl loop tried to call
        is_event_set("stop", publisher_name) after the publisher thread had already
        finished and its context() cleaned up.
        """
        events = EventDict(default_events=["stop"])

        with events.context("Sportschau", 1):
            events.set_event("stop", "Sportschau")

        # context has exited – alias is no longer active, but events must persist
        assert events.is_event_set("stop", "Sportschau") is True

    def test_no_context_raises_runtime_error(self):
        """Calling with key=None from a thread with no active context must raise RuntimeError."""
        events = EventDict(default_events=["stop"])

        with pytest.raises(RuntimeError):
            events.is_event_set("stop")

    def test_unknown_alias_raises_key_error(self):
        """Accessing a never-registered alias must still raise KeyError."""
        events = EventDict(default_events=["stop"])

        with pytest.raises(KeyError):
            events.is_event_set("stop", "NonExistent")

    def test_main_context_resets_on_exit(self):
        """__EVENTS__ state must be fully cleared once main_context exits."""
        events = EventDict(default_events=["stop"])

        with events.main_context("main-thread"):
            events.alias("Sportschau", 1)
            events.set_event("stop", "Sportschau")
            events.set_for_all("stop", future=True)

        # aliases, events, and futures must all be gone
        assert not events._aliases
        assert not events._events
        assert not events._futures

    def test_main_context_raises_when_already_active(self):
        """Entering a second main_context while one is active must raise RuntimeError."""
        events = EventDict()

        with events.main_context("main-thread"):
            with pytest.raises(RuntimeError):
                with events.main_context("other"):
                    pass

    def test_reregistration_creates_fresh_events(self):
        """Re-registering an alias after its thread exits must clear stale event state."""
        events = EventDict(default_events=["stop"])

        with events.context("Sportschau", 1):
            events.set_event("stop", "Sportschau")

        # Re-register the same alias (simulates a second crawl)
        with events.context("Sportschau", 2):
            assert events.is_event_set("stop", "Sportschau") is False

    def test_set_for_all_active_only(self):
        """active_only=True must skip aliases whose threads have already finished."""
        events = EventDict(default_events=["stop"])

        with events.context("inactive", 1):
            pass  # alias removed on exit, _events["inactive"] persists

        with events.context("active", 2):
            events.set_for_all("stop", active_only=True)

            assert events.is_event_set("stop", "active") is True
            assert events.is_event_set("stop", "inactive") is False
