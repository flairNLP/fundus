"""Pytest fixtures for tests of pipeline source classes (WebSource, CCNewsSource, ...).

Parameterized builders live in ``tests.fixtures.builders`` — this module only wraps the
default no-arg builder calls in ``@pytest.fixture`` decorators for the common-case
injection-by-name pattern.
"""

from unittest.mock import MagicMock, patch

import pytest

from fundus.publishers.base_objects import Publisher
from tests.fixtures.builders import mock_response, stub_publisher


@pytest.fixture
def publisher() -> Publisher:
    return stub_publisher()


@pytest.fixture
def patched_web_session_handler():
    """Patch the session_handler used by WebSource; yield the session mock."""
    with patch("fundus.scraping.pipeline.source.web.session_handler") as sh:
        session = MagicMock()
        session.get_with_interrupt.return_value = mock_response()
        sh.get_session.return_value = session
        yield session
