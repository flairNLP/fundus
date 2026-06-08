from typing import cast

import pytest

from fundus import PublisherCollection
from fundus.publishers import Publisher, PublisherGroup


@pytest.fixture(params=list(PublisherCollection), ids=lambda publisher: publisher.__name__)
def publisher(request) -> Publisher:
    """Fan a test out over every publisher in the live ``PublisherCollection``.

    Any test under ``tests/publishers/`` that declares a ``publisher`` argument is
    parametrized across the whole collection, with the publisher's ``__name__`` as the
    test id. Scoped to this directory (rather than a global ``fixture_*`` plugin) so it
    overrides the stub ``publisher`` fixture from ``tests/fixtures/fixture_source.py``
    only here, where every test wants the real collection.
    """
    return cast(Publisher, request.param)


@pytest.fixture(
    params=list(PublisherCollection.get_subgroup_mapping().values()),
    ids=lambda region: region.__name__,
)
def region(request) -> PublisherGroup:
    """Fan a test out over every region (country subgroup) in the live ``PublisherCollection``.

    Mirror of the ``publisher`` fixture for tests that operate per subgroup rather than
    per publisher, with the region's ``__name__`` as the test id.
    """
    return cast(PublisherGroup, request.param)
