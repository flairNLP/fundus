from threading import Thread

import pytest

from fundus.scraping.session import CONFIG, SessionHandler
from tests.exceptions import Success


class TestContext:
    def test_config_override(self):
        session_handler = SessionHandler()
        prev = session_handler.CONFIG

        with session_handler.context(TIMEOUT=-9999):
            assert session_handler.CONFIG != prev
            assert session_handler.CONFIG.TIMEOUT == -9999

        assert session_handler.CONFIG == prev

    def test_new_session(self):
        session_handler = SessionHandler()

        prev = session_handler.get_session()

        with session_handler.context():
            assert session_handler.get_session() != prev

        assert session_handler.get_session() == prev

    def test_nested_context(self):
        session_handler = SessionHandler()

        with session_handler.context(TIMEOUT=1):
            with session_handler.context(TIMEOUT=2):
                assert session_handler.get_session().timeout == 2

            assert session_handler.get_session().timeout == 1

        assert session_handler.get_session().timeout == CONFIG.TIMEOUT

    def test_thread_safety(self):
        session_handler = SessionHandler()

        def set_context(timeout: int = 100):
            with pytest.raises(Success):
                with session_handler.context(TIMEOUT=timeout):
                    assert session_handler.get_session().timeout == timeout
                    raise Success

        def set_context_fail():
            with pytest.raises(AssertionError):
                set_context()

        prev = session_handler.get_session()

        # 1. test if we can open a context in another thread
        thread = Thread(target=set_context, args=(11,))
        thread.start()
        thread.join()

        # 2. test if previous context where restored correctly
        assert session_handler.get_session() == prev

        # 3. open new context
        with session_handler.context(TIMEOUT=12):
            # 4. the thread should raise an AssertionError
            thread = Thread(target=set_context_fail)
            thread.start()
            thread.join()

            # 5. test if the session handler still resets
            assert session_handler.get_session().timeout == 12

        # 6. test if the context is closed properly
        thread = Thread(target=set_context, args=(13,))
        thread.start()
        thread.join()
