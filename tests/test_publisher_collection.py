import pytest

from fundus import PublisherCollection
from fundus.publishers import PublisherGroup


@pytest.mark.parametrize(
    "region", [pytest.param(group, id=group.__name__) for group in PublisherCollection.get_subgroup_mapping().values()]
)
class TestPublisherCollection:
    def test_default_language(self, region: PublisherGroup):
        assert hasattr(region, "default_language"), f"Region {region.__name__!r} has no default language set"
