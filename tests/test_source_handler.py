from dataclasses import dataclass
from typing import Dict, Iterator, List

import pytest

from fundus.scraping.session import InterruptableSession
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap, SourceHandler, URLSource


@dataclass
class UnregisteredSource(URLSource):
    """A URLSource living outside url.py, i.e. missing from <__SOURCE_ORDER__>."""

    def fetch(self, session: InterruptableSession, headers: Dict[str, str]) -> Iterator[str]:
        yield from ()


def feed(name: str, **kwargs) -> RSSFeed:
    return RSSFeed(f"https://test.com/{name}", **kwargs)


def types_of(handler: SourceHandler) -> List[type]:
    return [type(source) for source in handler]


class TestOrdering:
    def test_sources_follow_the_source_order(self) -> None:
        handler = SourceHandler(
            [
                Sitemap("https://test.com/sitemap"),
                NewsMap("https://test.com/newsmap"),
                RSSFeed("https://test.com/feed"),
            ]
        )
        assert types_of(handler) == [RSSFeed, NewsMap, Sitemap]

    def test_declaration_order_is_kept_within_a_type(self) -> None:
        handler = SourceHandler([feed("second"), Sitemap("https://test.com/sitemap"), feed("first")])
        assert [source.url for source in handler] == [
            "https://test.com/second",
            "https://test.com/first",
            "https://test.com/sitemap",
        ]

    def test_unregistered_types_are_proceeded_last(self) -> None:
        handler = SourceHandler(
            [
                UnregisteredSource("https://test.com/custom"),
                Sitemap("https://test.com/sitemap"),
                RSSFeed("https://test.com/feed"),
            ]
        )
        assert types_of(handler) == [RSSFeed, Sitemap, UnregisteredSource]

    def test_news_map_does_not_fall_into_the_sitemap_bucket(self) -> None:
        # NewsMap subclasses Sitemap, so an isinstance-based rank would collapse the two.
        handler = SourceHandler([Sitemap("https://test.com/sitemap"), NewsMap("https://test.com/newsmap")])
        assert types_of(handler) == [NewsMap, Sitemap]

    def test_rejects_anything_that_is_not_a_url_source(self) -> None:
        with pytest.raises(TypeError):
            SourceHandler(["https://test.com/feed"])  # type: ignore[list-item]


class TestBatches:
    def test_plain_sources_form_one_batch_each(self) -> None:
        sources = [feed("one"), feed("two")]
        assert list(SourceHandler(sources).batches()) == [(sources[0],), (sources[1],)]

    def test_interleaved_sources_of_one_type_share_a_batch(self) -> None:
        sources = [feed("one", interleave=True), feed("two", interleave=True)]
        assert list(SourceHandler(sources).batches()) == [tuple(sources)]

    def test_the_shared_batch_sits_at_the_first_interleaved_source(self) -> None:
        first, interleaved, last = feed("first"), feed("interleaved", interleave=True), feed("last")
        second_interleaved = feed("second-interleaved", interleave=True)

        batches = list(SourceHandler([first, interleaved, last, second_interleaved]).batches())

        assert batches == [(first,), (interleaved, second_interleaved), (last,)]

    def test_interleaved_sources_of_different_types_stay_apart(self) -> None:
        rss = feed("feed", interleave=True)
        news_map = NewsMap("https://test.com/newsmap", interleave=True)

        assert list(SourceHandler([news_map, rss]).batches()) == [(rss,), (news_map,)]

    def test_no_sources_means_no_batches(self) -> None:
        assert list(SourceHandler([]).batches()) == []


class TestFilter:
    @pytest.fixture
    def handler(self) -> SourceHandler:
        return SourceHandler(
            [
                feed("feed", languages={"es", "pl"}),
                NewsMap("https://test.com/newsmap", languages={"es"}),
                Sitemap("https://test.com/sitemap", languages={"ind"}),
            ]
        )

    def test_filters_by_source_type(self, handler: SourceHandler) -> None:
        assert types_of(handler.filter(source_types=[RSSFeed, NewsMap])) == [RSSFeed, NewsMap]

    def test_filters_by_language(self, handler: SourceHandler) -> None:
        assert types_of(handler.filter(languages=["es"])) == [RSSFeed, NewsMap]

    def test_filters_by_both(self, handler: SourceHandler) -> None:
        assert types_of(handler.filter(source_types=[NewsMap], languages=["es"])) == [NewsMap]

    def test_empty_arguments_do_not_restrict(self, handler: SourceHandler) -> None:
        assert handler.filter() == handler
        assert handler.filter(source_types=[], languages=[]) == handler

    def test_chained_filters_intersect(self, handler: SourceHandler) -> None:
        assert handler.filter(languages=["es", "ind"]).filter(languages=["ind"]) == handler.filter(languages=["ind"])

    def test_filtering_keeps_the_crawl_order(self) -> None:
        handler = SourceHandler([Sitemap("https://test.com/sitemap"), feed("feed")])
        assert types_of(handler.filter(source_types=[Sitemap, RSSFeed])) == [RSSFeed, Sitemap]

    def test_a_filter_matching_nothing_yields_an_empty_handler(self, handler: SourceHandler) -> None:
        filtered = handler.filter(languages=["de"])
        assert not filtered
        assert len(filtered) == 0
        assert filtered.languages == set()


class TestProperties:
    def test_languages_unions_over_all_sources(self) -> None:
        handler = SourceHandler([feed("feed", languages={"es", "pl"}), NewsMap("https://test.com/n", languages={"es"})])
        assert handler.languages == {"es", "pl"}

    def test_languages_of_an_empty_handler(self) -> None:
        assert SourceHandler([]).languages == set()

    def test_languages_sees_sources_mutated_after_construction(self) -> None:
        # PublisherGroup fills in a default language this way, so the property must not cache.
        source = feed("feed")
        handler = SourceHandler([source])
        source.languages = {"en"}
        assert handler.languages == {"en"}

    def test_source_types(self) -> None:
        handler = SourceHandler([feed("one"), feed("two"), Sitemap("https://test.com/sitemap")])
        assert handler.source_types == {RSSFeed, Sitemap}
