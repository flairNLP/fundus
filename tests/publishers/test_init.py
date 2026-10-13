import csv
from typing import Dict, Iterable, Set

import pytest

from fundus.publishers import Publisher, PublisherCollectionMeta, PublisherGroup
from tests.fixtures.builders import make_publisher, make_publisher_group
from tests.resources import __module_path__ as resources_path
from tests.utility import get_meta_info_file

# The ISO 639-3 registration authority's own export, frozen so the checks below run offline and
# trimmed to the columns they need: 'Id' holds a language's three-letter 639-3 code, 'Part1' the
# two-letter 639-1 code for the languages that have one. If a new publisher needs a code missing
# here, re-snapshot it with:
#   curl -sSf https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab \
#     | cut -f1,4 > tests/resources/iso_639_3.tab
with open(resources_path / "iso_639_3.tab", encoding="utf-8", newline="") as file:
    _iso_639_table = list(csv.DictReader(file, delimiter="\t"))

# Every language gets exactly one accepted code: the two-letter one where it exists and
# the three-letter one otherwise. So German is 'de' and never 'deu', while Shan ('shn')
# and Gun ('guw'), which have no two-letter form, are referenced by their 639-3 code.
language_codes: Set[str] = {row["Part1"] or row["Id"] for row in _iso_639_table}
superseded_codes: Dict[str, str] = {row["Id"]: row["Part1"] for row in _iso_639_table if row["Part1"]}


def _assert_iso_639(codes: Iterable[str], owner: str) -> None:
    rejected = sorted(set(codes) - language_codes)
    superseded = ", ".join(f"{code!r} -> {superseded_codes[code]!r}" for code in rejected if code in superseded_codes)
    assert not rejected, f"{owner} uses language code(s) {rejected} that are no ISO 639 codes" + (
        f", or that ISO 639-1 supersedes: use {superseded}" if superseded else ""
    )


class TestPublisherCollection:
    def test_default_language(self, region: PublisherGroup):
        assert hasattr(region, "default_language"), f"Region {region.__name__!r} has no default language set"

        _assert_iso_639([getattr(region, "default_language")], f"Default language of region {region.__name__!r}")

    def test_source_languages(self, publisher: Publisher):
        for source in publisher.sources:
            _assert_iso_639(source.languages, f"{type(source).__name__} of {publisher.name!r}")


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
