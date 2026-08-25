import csv
import io
from typing import Dict, List, Set

import pytest
import requests

from fundus import PublisherCollection
from fundus.publishers import Publisher, PublisherGroup
from fundus.scraping.session import _default_header

# The registration authority's own export. 'Id' holds a language's three-letter 639-3
# code, 'Part1' the two-letter 639-1 code for the 184 languages that have one.
_iso_639_3_url = "https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab"


def get_iso_639_table() -> List[Dict[str, str]]:
    response = requests.get(_iso_639_3_url, headers=_default_header)
    response.raise_for_status()
    return list(csv.DictReader(io.StringIO(response.text), delimiter="\t"))


_iso_639_table = get_iso_639_table()

# Every language gets exactly one accepted code: the two-letter one where it exists and
# the three-letter one otherwise. So German is 'de' and never 'deu', while Shan ('shn')
# and Gun ('guw'), which have no two-letter form, are referenced by their 639-3 code.
language_codes: Set[str] = {row["Part1"] or row["Id"] for row in _iso_639_table}
superseded_codes: Dict[str, str] = {row["Id"]: row["Part1"] for row in _iso_639_table if row["Part1"]}


class TestPublisherCollection:
    @pytest.mark.parametrize(
        "region",
        [pytest.param(group, id=group.__name__) for group in PublisherCollection.get_subgroup_mapping().values()],
    )
    def test_default_language(self, region: PublisherGroup):
        assert hasattr(region, "default_language"), f"Region {region.__name__!r} has no default language set"

        default_language = getattr(region, "default_language")

        assert default_language in language_codes, (
            f"Default language {default_language!r} isn't a ISO 639 language code"
        )

    @pytest.mark.parametrize(
        "publisher", [pytest.param(publisher, id=publisher.__name__) for publisher in PublisherCollection]
    )
    def test_source_languages(self, publisher: Publisher):
        for source in publisher.sources:
            rejected = source.languages - language_codes
            superseded = ", ".join(
                f"{code!r} -> {superseded_codes[code]!r}" for code in sorted(rejected) if code in superseded_codes
            )
            assert not rejected, (
                f"{type(source).__name__} of {publisher.name!r} uses language code(s) {sorted(rejected)} "
                f"that are no ISO 639 codes"
                + (f", or that ISO 639-1 supersedes: use {superseded}" if superseded else "")
            )
