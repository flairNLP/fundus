from __future__ import annotations

import bz2
import gzip
import lzma
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from curl_cffi.requests.exceptions import ConnectionError, HTTPError

from fundus.scraping.url import (
    RSSFeed,
    Sitemap,
    decompress,
    is_valid_url,
)

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


class TestIsValidUrl:
    def test_valid_http_url(self):
        assert is_valid_url("http://example.com")

    def test_valid_https_url(self):
        assert is_valid_url("https://example.com")

    def test_valid_url_with_path(self):
        assert is_valid_url("https://example.com/some/path")

    def test_valid_url_with_query(self):
        assert is_valid_url("https://example.com/page?id=1")

    def test_rejects_unsupported_scheme(self):
        assert not is_valid_url("ftp://example.com")

    def test_rejects_missing_netloc(self):
        assert not is_valid_url("https://")

    def test_rejects_empty_string(self):
        assert not is_valid_url("")


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

    def test_sort_predicate_orders_sub_sitemaps_descending(self):
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
            sort_predicate=re.compile(r"\d{4}"),
        )
        result = list(sitemap.fetch(session, {}))
        assert result == [
            "https://example.com/2021/article",
            "https://example.com/2020/article",
            "https://example.com/2019/article",
        ]
