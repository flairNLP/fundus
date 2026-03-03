import bidict
import pytest

from fundus.utils.events import EventDict


class TestEvents:
    def test_default_events(self):
        events = EventDict(default_events=["success"])

        events.get("success")

        with pytest.raises(KeyError):
            events.get("failure")

    def test_set_clear(self):
        events = EventDict(default_events=["success"])

        events.set_event("success")

        assert events.is_event_set("success")

        events.clear_event("success")

        assert events.is_event_set("success") == False

    def test_set_clear_all(self):
        events = EventDict()

        events.register_event("success", 1)
        events.register_event("success", 2)

        events.set_for_all("success")

        assert events.is_event_set("success", 1) == events.is_event_set("success", 2) == True

        events.clear_for_all("success")

        assert events.is_event_set("success", 1) == events.is_event_set("success", 2) == False

        events.register_event("failure", 1)
        events.register_event("failure", 2)

        events.set_for_all()

        assert events.is_event_set("success", 1) == events.is_event_set("success", 2) == True
        assert events.is_event_set("failure", 1) == events.is_event_set("failure", 2) == True

        events.clear_for_all()

        assert events.is_event_set("success", 1) == events.is_event_set("success", 2) == False
        assert events.is_event_set("failure", 1) == events.is_event_set("failure", 2) == False

    def test_new_event_after_set_for_all(self):
        events = EventDict()

        events.register_event("success", 1)

        events.set_for_all("success")

        events.register_event("success", 2)

        assert events.is_event_set("success", 1) == True
        assert events.is_event_set("success", 2) == False

    def test_set_for_all_future_true(self):
        events = EventDict()

        events.register_event("success", 1)

        events.set_for_all("success", future=True)

        events.register_event("success", 2)

        assert events.is_event_set("success", 1) == True
        assert events.is_event_set("success", 2) == True

    def test_clear_for_all_resets_futures(self):
        events = EventDict()

        events.set_for_all("success", future=True)
        events.clear_for_all("success")

        events.register_event("success", 1)

        assert events.is_event_set("success", 1) == False

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
