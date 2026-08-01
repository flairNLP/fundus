import io
import logging

import pytest

from fundus.logging import (
    add_handler,
    create_logger,
    get_handlers,
    loggers,
    remove_handler,
    set_log_level,
)
from tests.logging.conftest import lines, probe


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
