"""Tests for the Wikinews edition table.

One publisher serves 36 language editions, so the parser test fixture can only exercise
one of them end to end. What varies between editions is how each spells a date, and that
is what these tests pin: every string below is a real category taken from the edition it
is attributed to.
"""

import datetime
from typing import Optional

import pytest

from fundus import PublisherCollection
from fundus.publishers.international.wikinews import DEFAULT_EDITION, EDITIONS, WikinewsParser

WIKINEWS = PublisherCollection.international.Wikinews


def parser_for_html(html: str) -> WikinewsParser.V1:
    """A parser set up on <html>, narrowed to the version under test."""
    parser = WIKINEWS.parser()
    assert isinstance(parser, WikinewsParser.V1)
    parser._base_setup(html)
    return parser


def parser_for(edition: str, *, lang: Optional[str] = None, host: Optional[str] = None) -> WikinewsParser.V1:
    """A parser bound to a minimal document identifying itself as <edition>."""
    canonical = f"https://{host or edition}.wikinews.org/wiki/Test"
    return parser_for_html(
        f'<html lang="{lang or edition}"><head><link rel="canonical" href="{canonical}"/></head><body></body></html>'
    )


class TestEditionTable:
    def test_every_source_has_a_row(self) -> None:
        assert WIKINEWS.sources.languages == set(EDITIONS)

    def test_every_row_is_reachable(self) -> None:
        # The sources are built by iterating the table, so a row without a source would
        # mean the two had drifted apart.
        assert len(WIKINEWS.sources) == len(EDITIONS)

    def test_every_edition_is_crawled_in_turn(self) -> None:
        # All editions are interleaved, so they have to collapse into a single batch. Without
        # that, the crawler would exhaust one edition before reaching the next.
        assert [len(batch) for batch in WIKINEWS.sources.batches()] == [len(EDITIONS)]

    def test_language_is_a_known_dateparser_locale(self) -> None:
        import dateparser

        for code, edition in EDITIONS.items():
            if edition.date_language is None:
                continue
            # Raises ValueError('Unknown language(s)') for a locale dateparser lacks,
            # which would take out publishing_date for that whole edition.
            dateparser.parse("1 January 2020", languages=[edition.date_language])


class TestEditionDetection:
    def test_reads_the_canonical_host(self) -> None:
        assert parser_for("de")._edition is EDITIONS["de"]

    def test_canonical_host_wins_over_lang(self) -> None:
        # Norwegian Wikinews serves lang="nb" from no.wikinews.org; the host is the key.
        assert parser_for("no", lang="nb")._edition is EDITIONS["no"]

    def test_falls_back_to_lang_without_a_canonical_link(self) -> None:
        parser = parser_for_html('<html lang="fr"><head></head><body></body></html>')
        assert parser._edition is EDITIONS["fr"]

    def test_unknown_host_falls_back_to_the_default(self) -> None:
        parser = parser_for_html(
            '<html lang="xx"><head><link rel="canonical" href="https://xx.example.org/a"/></head><body></body></html>'
        )
        assert parser._edition is DEFAULT_EDITION

    def test_another_wmf_project_is_read_by_its_language(self) -> None:
        # WikinewsAPI is subclassable for other WMF projects, so a sister project's host
        # must not be parsed as an edition code -- 'guw.wikipedia.org' is not the Gun
        # *Wikinews*. Falling through to lang still lands on Gun's date rules, which is
        # the right answer for a Gun-language page.
        parser = parser_for_html(
            '<html lang="guw"><head>'
            '<link rel="canonical" href="https://guw.wikipedia.org/wiki/A"/>'
            "</head><body></body></html>"
        )
        assert parser._edition is EDITIONS["guw"]

    def test_a_host_that_merely_ends_in_the_suffix_is_not_an_edition(self) -> None:
        parser = parser_for_html(
            '<html lang="xx"><head>'
            '<link rel="canonical" href="https://evil.wikinews.org.example.com/a"/>'
            "</head><body></body></html>"
        )
        assert parser._edition is DEFAULT_EDITION


# (edition, category as the edition publishes it, expected date)
DATES = [
    # a locale dateparser ships, needing nothing else
    ("de", "21.04.2025", datetime.datetime(2025, 4, 21)),
    ("en", "March 21, 2026", datetime.datetime(2026, 3, 21)),
    ("fr", "21 avril 2025", datetime.datetime(2025, 4, 21)),
    ("no", "2. januar 2020", datetime.datetime(2020, 1, 2)),
    # a template wrapping the date in words
    ("bg", "Новини от 26 ноември 2016 г.", datetime.datetime(2016, 11, 26)),
    ("li", "Datum: oktober 2, 2011", datetime.datetime(2011, 10, 2)),
    # an ordinal day
    ("eo", "4-a de majo 2026", datetime.datetime(2026, 5, 4)),
    # a different epoch
    ("th", "16 มีนาคม พ.ศ. 2554", datetime.datetime(2011, 3, 16)),
    # month names dateparser has no locale for, in both Gun orthographies
    ("guw", "Abɔ̀xúsun 15, 2025", datetime.datetime(2025, 11, 15)),
    ("guw", "Abọ̀húsun 15, 2025", datetime.datetime(2025, 11, 15)),
    ("guw", "Alunlunsun 3, 2023", datetime.datetime(2023, 1, 3)),
    ("sd", "10 نومبر 2006", datetime.datetime(2006, 11, 10)),
    ("sd", "10 ڊسمبر 2006", datetime.datetime(2006, 12, 10)),
    # numeric CJK, which dateparser does not read
    ("ja", "2026年8月4日", datetime.datetime(2026, 8, 4)),
    ("ko", "2026년 8월 4일", datetime.datetime(2026, 8, 4)),
    ("zh", "2026年8月4日", datetime.datetime(2026, 8, 4)),
    # an edition with no locale at all still reads the unambiguous form
    ("shn", "2025-04-21", datetime.datetime(2025, 4, 21)),
]

# Categories that merely mention a year. Reading one as a date would both invent a
# publication date and drop a real topic.
NON_DATES = [
    ("de", "Fußball-Weltmeisterschaft 2026"),
    ("bg", "Фидел Кастро"),
    ("eo", "Majo de 2026"),  # month and year, no day
    ("th", "วว ธันวาคม พ.ศ. 2548"),  # malformed day
    ("guw", "2022 Qatar World Cup"),
    ("sd", "انڊيا"),
    ("shn", "21 April 2025"),  # no locale, so a worded date stays unread
]


class TestEditionDates:
    @pytest.mark.parametrize("edition, category, expected", DATES)
    def test_reads_the_editions_own_spelling(self, edition, category, expected) -> None:
        assert parser_for(edition)._read_date(category) == expected

    @pytest.mark.parametrize("edition, category", NON_DATES)
    def test_leaves_non_dates_alone(self, edition, category) -> None:
        assert parser_for(edition)._read_date(category) is None

    def test_a_spelling_is_not_read_by_the_wrong_edition(self) -> None:
        # The Gun month map must not leak into an edition that does not use it.
        assert parser_for("de")._read_date("Abɔ̀xúsun 15, 2025") is None


class TestEditionBodySelectors:
    def test_prose_floor_differs_for_cjk(self) -> None:
        assert parser_for("ja")._paragraph_selector is not parser_for("de")._paragraph_selector

    def test_english_takes_lists_from_the_whole_page(self) -> None:
        assert parser_for("en")._paragraph_selector is not parser_for("de")._paragraph_selector

    def test_editions_sharing_a_shape_share_a_selector(self) -> None:
        assert parser_for("de")._paragraph_selector is parser_for("fr")._paragraph_selector
