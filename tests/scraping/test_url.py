from __future__ import annotations

import bz2
import gzip
import lzma
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from curl_cffi.requests.exceptions import ConnectionError, HTTPError

from fundus.scraping.session import InterruptableSession
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap, SourceHandler, URLSource, decompress, numeric_sort_key

# ---- helpers ----------------------------------------------------------------

_RSS_FEED = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test</title>
    <link>https://example.com</link>
    <item><title>A1</title><link>https://example.com/article/1</link></item>
    <item><title>A2</title><link>https://example.com/article/2</link></item>
  </channel>
</rss>"""

_SITEMAP_URLS = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/article/1</loc></url>
  <url><loc>https://example.com/article/2</loc></url>
</urlset>"""

_SITEMAP_INDEX = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-a.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-b.xml</loc></sitemap>
</sitemapindex>"""

_SITEMAP_SINGLE_URL = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/article/sub</loc></url>
</urlset>"""


def _make_response(text: str = "", content: bytes = b"", headers: Optional[Dict[str, str]] = None) -> MagicMock:
    response = MagicMock()
    response.text = text
    response.content = content or text.encode()
    response.headers = headers or {}
    return response


def _make_session(response=None, side_effect=None) -> MagicMock:
    session = MagicMock()
    if side_effect is not None:
        session.get_with_interrupt.side_effect = side_effect
    else:
        session.get_with_interrupt.return_value = response
    return session


class TestDecompress:
    def test_decompresses_gzip_by_magic_bytes(self):
        data = b"hello world"
        assert decompress(gzip.compress(data)) == data

    def test_decompresses_bzip2_by_magic_bytes(self):
        data = b"hello world"
        assert decompress(bz2.compress(data)) == data

    def test_decompresses_xz_by_magic_bytes(self):
        data = b"hello world"
        assert decompress(lzma.compress(data)) == data

    def test_returns_uncompressed_content_unchanged(self):
        data = b"<?xml version='1.0'?><urlset/>"
        assert decompress(data) == data

    def test_returns_empty_unchanged(self):
        assert decompress(b"") == b""

    def test_raises_on_corrupt_gzip(self):
        # leading magic bytes match gzip but the rest is garbage
        with pytest.raises(Exception):
            decompress(b"\x1f\x8b" + b"\x00" * 10)


class TestURLSourceGetUrls:
    def _make_source(self, urls: List[str]) -> RSSFeed:
        class FixedSource(RSSFeed):
            def __iter__(self_inner):
                return iter(urls)

        return FixedSource(url="https://example.com")

    def test_limits_output_to_max_urls(self):
        source = self._make_source([f"https://example.com/{i}" for i in range(10)])
        assert len(list(source.get_urls(max_urls=3))) == 3

    def test_returns_all_when_max_urls_is_none(self):
        source = self._make_source([f"https://example.com/{i}" for i in range(5)])
        assert len(list(source.get_urls())) == 5

    def test_max_urls_zero_returns_nothing(self):
        source = self._make_source([f"https://example.com/{i}" for i in range(5)])
        assert list(source.get_urls(max_urls=0)) == []


class TestRSSFeedFetch:
    def test_yields_urls_from_valid_feed(self):
        session = _make_session(_make_response(text=_RSS_FEED))
        result = list(RSSFeed(url="https://example.com/feed.xml").fetch(session, {}))
        assert result == ["https://example.com/article/1", "https://example.com/article/2"]

    def test_decodes_percent_encoded_urls(self):
        rss = _RSS_FEED.replace("https://example.com/article/1", "https://example.com/caf%C3%A9")
        session = _make_session(_make_response(text=rss))
        result = list(RSSFeed(url="https://example.com/feed.xml").fetch(session, {}))
        assert "https://example.com/café" in result

    def test_yields_nothing_on_http_error(self):
        session = _make_session(side_effect=HTTPError("error"))
        result = list(RSSFeed(url="https://example.com/feed.xml").fetch(session, {}))
        assert result == []

    def test_yields_nothing_on_connection_error(self):
        session = _make_session(side_effect=ConnectionError("error"))
        result = list(RSSFeed(url="https://example.com/feed.xml").fetch(session, {}))
        assert result == []

    def test_yields_nothing_on_bozo_exception(self):
        session = _make_session(_make_response(text=_RSS_FEED))
        with patch("fundus.scraping.url.feedparser.parse", return_value={"bozo_exception": Exception("bad")}):
            result = list(RSSFeed(url="https://example.com/feed.xml").fetch(session, {}))
        assert result == []

    def test_skips_entries_without_link(self):
        rss = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item><title>No link</title></item>
    <item><title>Has link</title><link>https://example.com/article/1</link></item>
  </channel>
</rss>"""
        session = _make_session(_make_response(text=rss))
        result = list(RSSFeed(url="https://example.com/feed.xml").fetch(session, {}))
        assert result == ["https://example.com/article/1"]


class TestSitemapFetch:
    def test_yields_urls_from_urlset(self):
        session = _make_session(_make_response(content=_SITEMAP_URLS))
        result = list(Sitemap(url="https://example.com/sitemap.xml").fetch(session, {}))
        assert result == ["https://example.com/article/1", "https://example.com/article/2"]

    def test_follows_sub_sitemaps_recursively(self):
        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs["url"]
            return _make_response(content=_SITEMAP_INDEX if "sitemap-index" in url else _SITEMAP_SINGLE_URL)

        session = _make_session(side_effect=side_effect)
        result = list(Sitemap(url="https://example.com/sitemap-index.xml").fetch(session, {}))
        # _SITEMAP_INDEX has two sub-sitemaps, each yielding one URL
        assert result == ["https://example.com/article/sub", "https://example.com/article/sub"]

    def test_reverse_reverses_url_order(self):
        session = _make_session(_make_response(content=_SITEMAP_URLS))
        result = list(Sitemap(url="https://example.com/sitemap.xml", reverse=True).fetch(session, {}))
        assert result == ["https://example.com/article/2", "https://example.com/article/1"]

    def test_sitemap_filter_excludes_matching_sub_sitemaps(self):
        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs["url"]
            return _make_response(content=_SITEMAP_SINGLE_URL if "sitemap-" in url else _SITEMAP_INDEX)

        session = _make_session(side_effect=side_effect)
        # filter out sitemap-b, keep sitemap-a
        sitemap = Sitemap(
            url="https://example.com/sitemap-index.xml",
            sitemap_filter=lambda url: "sitemap-b" in url,
        )
        result = list(sitemap.fetch(session, {}))
        assert result == ["https://example.com/article/sub"]

    def test_yields_nothing_on_http_error(self):
        session = _make_session(side_effect=HTTPError("error"))
        result = list(Sitemap(url="https://example.com/sitemap.xml").fetch(session, {}))
        assert result == []

    def test_decompresses_gzip_content(self):
        session = _make_session(
            _make_response(content=gzip.compress(_SITEMAP_URLS), headers={"content-type": "application/x-gzip"})
        )
        result = list(Sitemap(url="https://example.com/sitemap.xml.gz").fetch(session, {}))
        assert result == ["https://example.com/article/1", "https://example.com/article/2"]

    def test_yields_nothing_on_empty_sitemap(self):
        session = _make_session(_make_response(content=b""))
        result = list(Sitemap(url="https://example.com/sitemap.xml").fetch(session, {}))
        assert result == []

    def test_sort_key_orders_sub_sitemaps(self):
        import re

        sitemap_index = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-2019.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-2021.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-2020.xml</loc></sitemap>
</sitemapindex>"""

        def _sub_sitemap(year: str) -> bytes:
            return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/{year}/article</loc></url>
</urlset>""".encode()

        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs["url"]
            if "sitemap-index" in url:
                return _make_response(content=sitemap_index)
            match = re.search(r"\d{4}", url)
            assert match is not None
            return _make_response(content=_sub_sitemap(match.group()))

        session = _make_session(side_effect=side_effect)
        sitemap = Sitemap(
            url="https://example.com/sitemap-index.xml",
            sort_key=numeric_sort_key(r"sitemap-(\d{4})", reverse=True),
        )
        result = list(sitemap.fetch(session, {}))
        assert result == [
            "https://example.com/2021/article",
            "https://example.com/2020/article",
            "https://example.com/2019/article",
        ]

    def test_sort_key_only_sees_sitemaps_kept_by_the_filter(self):
        sitemap_index = b"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-10.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-video.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-2.xml</loc></sitemap>
</sitemapindex>"""

        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs["url"]
            if "sitemap-index" in url:
                return _make_response(content=sitemap_index)
            name = url.rsplit("/", 1)[-1][: -len(".xml")]
            return _make_response(
                content=f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/{name}/article</loc></url>
</urlset>""".encode()
            )

        session = _make_session(side_effect=side_effect)
        sitemap = Sitemap(
            url="https://example.com/sitemap-index.xml",
            sitemap_filter=lambda url: "video" in url,
            # would raise on sitemap-video.xml if the filter didn't drop it first
            sort_key=numeric_sort_key(r"sitemap-(\d+)"),
        )
        result = list(sitemap.fetch(session, {}))
        assert result == ["https://example.com/sitemap-2/article", "https://example.com/sitemap-10/article"]


# ---- SourceHandler ---------------------------------------------------------


@dataclass
class _UnregisteredSource(URLSource):
    """A URLSource living outside url.py, i.e. missing from <__SOURCE_ORDER__>."""

    def fetch(self, session: InterruptableSession, headers: Dict[str, str]) -> Iterator[str]:
        yield from ()


def _feed(name: str, **kwargs) -> RSSFeed:
    return RSSFeed(f"https://test.com/{name}", **kwargs)


def _types_of(handler: SourceHandler) -> List[type]:
    return [type(source) for source in handler]


class TestSourceHandlerOrdering:
    def test_sources_follow_the_source_order(self) -> None:
        handler = SourceHandler(
            [
                Sitemap("https://test.com/sitemap"),
                NewsMap("https://test.com/newsmap"),
                RSSFeed("https://test.com/feed"),
            ]
        )
        assert _types_of(handler) == [RSSFeed, NewsMap, Sitemap]

    def test_declaration_order_is_kept_within_a_type(self) -> None:
        handler = SourceHandler([_feed("second"), Sitemap("https://test.com/sitemap"), _feed("first")])
        assert [source.url for source in handler] == [
            "https://test.com/second",
            "https://test.com/first",
            "https://test.com/sitemap",
        ]

    def test_unregistered_types_are_proceeded_last(self) -> None:
        handler = SourceHandler(
            [
                _UnregisteredSource("https://test.com/custom"),
                Sitemap("https://test.com/sitemap"),
                RSSFeed("https://test.com/feed"),
            ]
        )
        assert _types_of(handler) == [RSSFeed, Sitemap, _UnregisteredSource]

    def test_news_map_does_not_fall_into_the_sitemap_bucket(self) -> None:
        # NewsMap subclasses Sitemap, so an isinstance-based rank would collapse the two.
        handler = SourceHandler([Sitemap("https://test.com/sitemap"), NewsMap("https://test.com/newsmap")])
        assert _types_of(handler) == [NewsMap, Sitemap]

    def test_rejects_anything_that_is_not_a_url_source(self) -> None:
        with pytest.raises(TypeError):
            SourceHandler(["https://test.com/feed"])  # type: ignore[list-item]


class TestSourceHandlerBatches:
    def test_plain_sources_form_one_batch_each(self) -> None:
        sources = [_feed("one"), _feed("two")]
        assert list(SourceHandler(sources).batches()) == [(sources[0],), (sources[1],)]

    def test_interleaved_sources_of_one_type_share_a_batch(self) -> None:
        sources = [_feed("one", interleave=True), _feed("two", interleave=True)]
        assert list(SourceHandler(sources).batches()) == [tuple(sources)]

    def test_the_shared_batch_sits_at_the_first_interleaved_source(self) -> None:
        first, interleaved, last = _feed("first"), _feed("interleaved", interleave=True), _feed("last")
        second_interleaved = _feed("second-interleaved", interleave=True)

        batches = list(SourceHandler([first, interleaved, last, second_interleaved]).batches())

        assert batches == [(first,), (interleaved, second_interleaved), (last,)]

    def test_interleaved_sources_of_different_types_stay_apart(self) -> None:
        rss = _feed("feed", interleave=True)
        news_map = NewsMap("https://test.com/newsmap", interleave=True)

        assert list(SourceHandler([news_map, rss]).batches()) == [(rss,), (news_map,)]

    def test_no_sources_means_no_batches(self) -> None:
        assert list(SourceHandler([]).batches()) == []


class TestSourceHandlerFilter:
    @pytest.fixture
    def handler(self) -> SourceHandler:
        return SourceHandler(
            [
                _feed("feed", languages={"es", "pl"}),
                NewsMap("https://test.com/newsmap", languages={"es"}),
                Sitemap("https://test.com/sitemap", languages={"ind"}),
            ]
        )

    def test_filters_by_source_type(self, handler: SourceHandler) -> None:
        assert _types_of(handler.filter(source_types=[RSSFeed, NewsMap])) == [RSSFeed, NewsMap]

    def test_filters_by_language(self, handler: SourceHandler) -> None:
        assert _types_of(handler.filter(languages=["es"])) == [RSSFeed, NewsMap]

    def test_filters_by_both(self, handler: SourceHandler) -> None:
        assert _types_of(handler.filter(source_types=[NewsMap], languages=["es"])) == [NewsMap]

    def test_empty_arguments_do_not_restrict(self, handler: SourceHandler) -> None:
        assert handler.filter() == handler
        assert handler.filter(source_types=[], languages=[]) == handler

    def test_chained_filters_intersect(self, handler: SourceHandler) -> None:
        assert handler.filter(languages=["es", "ind"]).filter(languages=["ind"]) == handler.filter(languages=["ind"])

    def test_filtering_keeps_the_crawl_order(self) -> None:
        handler = SourceHandler([Sitemap("https://test.com/sitemap"), _feed("feed")])
        assert _types_of(handler.filter(source_types=[Sitemap, RSSFeed])) == [RSSFeed, Sitemap]

    def test_a_filter_matching_nothing_yields_an_empty_handler(self, handler: SourceHandler) -> None:
        filtered = handler.filter(languages=["de"])
        assert not filtered
        assert len(filtered) == 0
        assert filtered.languages == set()


class TestSourceHandlerProperties:
    def test_languages_unions_over_all_sources(self) -> None:
        handler = SourceHandler(
            [_feed("feed", languages={"es", "pl"}), NewsMap("https://test.com/n", languages={"es"})]
        )
        assert handler.languages == {"es", "pl"}

    def test_languages_of_an_empty_handler(self) -> None:
        assert SourceHandler([]).languages == set()

    def test_languages_sees_sources_mutated_after_construction(self) -> None:
        # PublisherGroup fills in a default language this way, so the property must not cache.
        source = _feed("feed")
        handler = SourceHandler([source])
        source.languages = {"en"}
        assert handler.languages == {"en"}

    def test_source_types(self) -> None:
        handler = SourceHandler([_feed("one"), _feed("two"), Sitemap("https://test.com/sitemap")])
        assert handler.source_types == {RSSFeed, Sitemap}
