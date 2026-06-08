from typing import Set

import more_itertools
import pytest

from fundus.publishers import Publisher, PublisherCollectionMeta, PublisherGroup
from tests.fixtures.builders import make_publisher, make_publisher_group
from tests.resources import __module_path__ as resources_path
from tests.utility import get_meta_info_file

# ISO 639-1 codes, frozen from the "List of ISO 639 language codes" Wikipedia table
# (en.wikipedia.org/wiki/List_of_ISO_639_language_codes, table id="Table", td/@id) so the
# data-hygiene checks below run offline. If a new publisher needs a code not listed here,
# re-snapshot that table into iso_639_codes.txt.
language_codes: Set[str] = set((resources_path / "iso_639_codes.txt").read_text(encoding="utf-8").split())


class TestPublisherCollection:
    def test_default_language(self, region: PublisherGroup):
        assert hasattr(region, "default_language"), f"Region {region.__name__!r} has no default language set"

        default_language = getattr(region, "default_language")

        assert default_language in language_codes, (
            f"Default language {default_language!r} isn't a ISO 639 language code"
        )

    def test_source_languages(self, publisher: Publisher):
        for source in more_itertools.flatten(publisher.source_mapping.values()):
            assert source.languages.issubset(language_codes)


class TestPublisherCollectionMeta:
    def test_rejects_duplicate_publisher_across_subgroups(self):
        with pytest.raises(ValueError):
            PublisherCollectionMeta(
                "C",
                (),
                {"a": make_publisher_group(Foo=make_publisher()), "b": make_publisher_group(Foo=make_publisher())},
            )

    def test_rejects_non_publisher_attribute(self):
        with pytest.raises(TypeError):
            PublisherCollectionMeta("C", (), {"x": "not a publisher"})

    def test_accepts_valid_collection(self):
        PublisherCollectionMeta("C", (), {"a": make_publisher_group(Foo=make_publisher())})  # must not raise


class TestMetaInfo:
    def test_order(self, region: PublisherGroup):
        meta_file = get_meta_info_file(region)
        meta_info = meta_file.load()
        assert meta_info, f"Meta info file {meta_file.path} is missing"
        assert sorted(meta_info.keys()) == list(meta_info.keys()), (
            f"Meta info file {meta_file.path} isn't ordered properly."
        )
