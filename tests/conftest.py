from pathlib import Path
from typing import Iterator, List

import pytest

from fundus.utils.events import __EVENTS__


def path_to_plugin(path: Path) -> str:
    return str(path).replace("/", ".").replace("\\", ".").replace(".py", "")


# Load all fixtures from 'fixture_' modules in the 'tests/fixtures' package as pytest plugins.
# This exposes all fixtures defined in the detected modules to use in pytests.
# The setup is inspired by https://gist.github.com/peterhurford/09f7dcda0ab04b95c026c60fa49c2a68
# Documentation on the `pytest_plugins` variable:
# https://docs.pytest.org/en/latest/reference/reference.html#globalvar-pytest_plugins
pytest_plugins: List[str] = [path_to_plugin(fixture) for fixture in Path("tests/fixtures").glob("fixture_*.py")]


@pytest.fixture(autouse=True)
def _reset_events_registry() -> Iterator[None]:
    """Clear the process-global ``__EVENTS__`` registry after every test.

    ``__EVENTS__`` holds alias→event mappings that persist across tests by design.
    Without an explicit reset, a test that sets the ``"stop"``event or registers
    an alias leaks that state into the next test. ``CrawlerBase.crawl``already
    resets on exit via ``main_context``, but tests that touch ``WebSource`` /
    ``CCNewsSource`` / the registry directly bypass that.
    """
    yield
    __EVENTS__.reset()
