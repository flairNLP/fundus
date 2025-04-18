from typing import List

import lxml.html
import more_itertools
import pytest
import requests
from lxml.etree import XPath

from fundus import PublisherCollection
from fundus.publishers import Publisher, PublisherGroup

_language_code_selector = XPath("//table[contains(@class, 'wikitable') and @id='Table'] //td[@id] / @id")


def get_two_letter_code() -> List[str]:
    wiki_page = requests.get("https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes")
    two_letter_codes: List[str] = _language_code_selector(lxml.html.document_fromstring(wiki_page.content))
    return two_letter_codes


language_codes = get_two_letter_code()


class TestPublisherCollection:
    @pytest.mark.parametrize(
        "region",
        [pytest.param(group, id=group.__name__) for group in PublisherCollection.get_subgroup_mapping().values()],
    )
    def test_default_language(self, region: PublisherGroup):
        assert hasattr(region, "default_language"), f"Region {region.__name__!r} has no default language set"

        default_language = getattr(region, "default_language")

        assert (
            default_language in language_codes
        ), f"Default language {default_language!r} isn't a ISO 639 language code"

    @pytest.mark.parametrize(
        "publisher", [pytest.param(publisher, id=publisher.__name__) for publisher in PublisherCollection]
    )
    def test_source_languages(self, publisher: Publisher):
        for source in more_itertools.flatten(publisher.source_mapping.values()):
            assert source.languages.issubset(language_codes)
