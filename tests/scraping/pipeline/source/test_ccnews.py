from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from unittest.mock import MagicMock, patch

import pytest
import requests
import urllib3.exceptions
from fastwarc.stream_io import StreamError

from fundus.scraping.html import HTML
from fundus.scraping.pipeline.source.ccnews import CCNewsSource, WarcFileLoadError, WarcSourceInfo
from tests.fixtures.builders import stub_publisher

# ---- helpers ---------------------------------------------------------------


def make_warc_record(
    target_url: str = "https://example.com/article",
    body: bytes = b"<html>hi</html>",
    http_charset: Optional[str] = "utf-8",
    record_date: Optional[datetime] = datetime(2024, 1, 1),
    record_id: str = "<urn:uuid:test>",
    http_headers: Optional[Dict[str, str]] = None,
    warc_headers: Optional[Dict[str, str]] = None,
) -> MagicMock:
    """Mock the fastwarc WarcRecord surface CCNewsSource reads."""
    record = MagicMock()
    record.reader.read.return_value = body
    record.http_charset = http_charset
    record.record_date = record_date
    record.record_id = record_id
    record.http_headers = http_headers or {"Content-Type": "text/html"}
    headers = {"WARC-Target-URI": target_url}
    if warc_headers:
        headers.update(warc_headers)
    record.headers = headers
    return record


def patch_archive_iterator(records: Iterable[Any]):
    """Replace ArchiveIterator with a callable that returns the given records."""
    return patch(
        "fundus.scraping.pipeline.source.ccnews.ArchiveIterator",
        return_value=iter(records),
    )


# ---- CCNewsSource.__init__ -------------------------------------------------


class TestCCNewsSourceConstruction:
    def test_stores_warc_path_and_publishers(self):
        publisher = stub_publisher()
        source = CCNewsSource(publisher, warc_path="https://commoncrawl.org/a.warc.gz")
        assert source.warc_path == "https://commoncrawl.org/a.warc.gz"
        assert source.publishers == (publisher,)

    def test_default_headers_when_none(self):
        from fundus.scraping.session import _default_header

        source = CCNewsSource(stub_publisher(), warc_path="x")
        assert source.headers == _default_header

    def test_custom_headers_override_default(self):
        headers = {"user-agent": "custom-agent"}
        source = CCNewsSource(stub_publisher(), warc_path="x", headers=headers)
        assert source.headers == headers

    def test_publisher_mapping_keyed_by_netloc(self):
        pub_a = stub_publisher(name="a", domain="https://a.example.com/")
        pub_b = stub_publisher(name="b", domain="https://b.example.com/path")
        source = CCNewsSource(pub_a, pub_b, warc_path="x")
        assert source._publisher_mapping == {"a.example.com": pub_a, "b.example.com": pub_b}

    def test_empty_publishers_yields_empty_mapping(self):
        source = CCNewsSource(warc_path="x")
        assert source._publisher_mapping == {}


# ---- CCNewsSource._open_stream --------------------------------------------


class TestOpenStream:
    def test_returns_response_on_success(self):
        source = CCNewsSource(stub_publisher(), warc_path="https://host/a.warc.gz")
        response = MagicMock()
        response.raise_for_status.return_value = None
        with patch("requests.Session.get", return_value=response) as mock_get:
            assert source._open_stream() is response
        mock_get.assert_called_once_with("https://host/a.warc.gz", stream=True, headers=source.headers)

    def test_wraps_http_error_as_warc_file_load_error(self):
        source = CCNewsSource(stub_publisher(), warc_path="x")
        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError("404")
        with patch("requests.Session.get", return_value=response):
            with pytest.raises(WarcFileLoadError, match="404"):
                source._open_stream()

    def test_wraps_urllib3_error_as_warc_file_load_error(self):
        source = CCNewsSource(stub_publisher(), warc_path="x")
        with patch(
            "requests.Session.get",
            side_effect=urllib3.exceptions.ProtocolError("conn reset"),
        ):
            with pytest.raises(WarcFileLoadError, match="conn reset"):
                source._open_stream()


# ---- CCNewsSource._extract_content ----------------------------------------


class TestExtractContent:
    def test_decodes_with_declared_charset(self):
        record = make_warc_record(body="héllo".encode("utf-8"), http_charset="utf-8")
        assert CCNewsSource._extract_content(record, "https://x/a") == "héllo"

    def test_falls_back_to_chardet_when_declared_charset_fails(self):
        body = "héllo".encode("latin-1")
        record = make_warc_record(body=body, http_charset="utf-8")
        with patch(
            "fundus.scraping.pipeline.source.ccnews.chardet.detect",
            return_value={"encoding": "latin-1"},
        ):
            assert CCNewsSource._extract_content(record, "https://x/a") == "héllo"

    def test_falls_back_to_chardet_when_charset_missing(self):
        body = "ok".encode("utf-8")
        record = make_warc_record(body=body, http_charset=None)
        with patch(
            "fundus.scraping.pipeline.source.ccnews.chardet.detect",
            return_value={"encoding": "utf-8"},
        ):
            assert CCNewsSource._extract_content(record, "https://x/a") == "ok"

    def test_returns_none_when_chardet_detects_nothing(self):
        record = make_warc_record(body=b"\xff\xfe", http_charset=None)
        with patch(
            "fundus.scraping.pipeline.source.ccnews.chardet.detect",
            return_value={"encoding": None},
        ):
            assert CCNewsSource._extract_content(record, "https://x/a") is None

    def test_returns_none_when_chardet_encoding_still_fails(self):
        body = b"\xff\xfe\xfa"
        record = make_warc_record(body=body, http_charset="utf-8")
        with patch(
            "fundus.scraping.pipeline.source.ccnews.chardet.detect",
            return_value={"encoding": "ascii"},
        ):
            assert CCNewsSource._extract_content(record, "https://x/a") is None


# ---- CCNewsSource._validate -----------------------------------------------


class TestValidate:
    def test_returns_publisher_on_happy_path(self):
        publisher = stub_publisher(domain="https://example.com/")
        source = CCNewsSource(publisher, warc_path="x")
        assert source._validate("https://example.com/article", None) is publisher

    def test_returns_none_when_url_filter_blocks(self):
        publisher = stub_publisher(domain="https://example.com/")
        source = CCNewsSource(publisher, warc_path="x")
        assert source._validate("https://example.com/skip", lambda u: "skip" in u) is None

    def test_returns_none_for_unknown_publisher_netloc(self):
        publisher = stub_publisher(domain="https://known.example.com/")
        source = CCNewsSource(publisher, warc_path="x")
        assert source._validate("https://unknown.example.com/article", None) is None

    def test_returns_none_when_publisher_url_filter_blocks(self):
        publisher = stub_publisher(
            domain="https://example.com/",
            url_filter=lambda u: "drop" in u,
        )
        source = CCNewsSource(publisher, warc_path="x")
        assert source._validate("https://example.com/drop-this", None) is None

    def test_publisher_url_filter_does_not_block_when_publisher_filter_is_none(self):
        publisher = stub_publisher(domain="https://example.com/", url_filter=None)
        source = CCNewsSource(publisher, warc_path="x")
        assert source._validate("https://example.com/any", None) is publisher

    def test_url_filter_none_passes_through(self):
        publisher = stub_publisher(domain="https://example.com/")
        source = CCNewsSource(publisher, warc_path="x")
        assert source._validate("https://example.com/article", None) is publisher


# ---- CCNewsSource._record_to_html -----------------------------------------


class TestRecordToHtml:
    def test_returns_html_on_happy_path(self):
        publisher = stub_publisher(name="p", domain="https://example.com/")
        source = CCNewsSource(publisher, warc_path="https://host/a.warc.gz")
        record = make_warc_record(target_url="https://example.com/article", body=b"<html>hi</html>")
        html = source._record_to_html(record, url_filter=None)
        assert isinstance(html, HTML)
        assert html.requested_url == "https://example.com/article"
        assert html.responded_url == "https://example.com/article"
        assert html.content == "<html>hi</html>"
        assert html.crawl_date == datetime(2024, 1, 1)

    def test_html_carries_warc_source_info(self):
        publisher = stub_publisher(name="p", domain="https://example.com/")
        source = CCNewsSource(publisher, warc_path="https://host/a.warc.gz")
        record = make_warc_record(
            target_url="https://example.com/article",
            http_headers={"Content-Type": "text/html"},
        )
        html = source._record_to_html(record, url_filter=None)
        assert html is not None
        info = html.source_info
        assert isinstance(info, WarcSourceInfo)
        assert info.publisher == publisher.name
        assert info.warc_path == "https://host/a.warc.gz"
        assert info.warc_headers == {"WARC-Target-URI": "https://example.com/article"}
        assert info.http_headers == {"Content-Type": "text/html"}

    def test_returns_none_when_record_date_is_none(self):
        publisher = stub_publisher(domain="https://example.com/")
        source = CCNewsSource(publisher, warc_path="x")
        record = make_warc_record(target_url="https://example.com/article", record_date=None)
        assert source._record_to_html(record, url_filter=None) is None

    def test_returns_none_when_validate_rejects(self):
        # Validate paths are covered exhaustively in TestValidate; here we only check that
        # _record_to_html threads the rejection through to a None return.
        publisher = stub_publisher(domain="https://known.example.com/")
        source = CCNewsSource(publisher, warc_path="x")
        record = make_warc_record(target_url="https://unknown.example.com/article")
        assert source._record_to_html(record, url_filter=None) is None

    def test_returns_none_when_content_cannot_be_decoded(self):
        publisher = stub_publisher(domain="https://example.com/")
        source = CCNewsSource(publisher, warc_path="x")
        record = make_warc_record(target_url="https://example.com/a")
        with patch.object(CCNewsSource, "_extract_content", return_value=None):
            assert source._record_to_html(record, url_filter=None) is None


# ---- CCNewsSource._iter_warc_records --------------------------------------


class TestIterWarcRecords:
    def test_yields_records_from_archive_iterator(self):
        records = [make_warc_record(target_url=f"https://example.com/{i}") for i in range(3)]
        with patch_archive_iterator(records):
            result = list(CCNewsSource._iter_warc_records(MagicMock()))
        assert result == records

    def test_wraps_stream_error_as_warc_file_load_error(self):
        with patch(
            "fundus.scraping.pipeline.source.ccnews.ArchiveIterator",
            side_effect=StreamError("corrupt"),
        ):
            with pytest.raises(WarcFileLoadError, match="corrupt"):
                list(CCNewsSource._iter_warc_records(MagicMock()))


# ---- CCNewsSource.fetch ---------------------------------------------------


class TestFetch:
    def test_pipes_open_stream_into_iter_warc_records(self):
        publisher = stub_publisher(domain="https://example.com/")
        source = CCNewsSource(publisher, warc_path="https://host/a.warc.gz")
        record = make_warc_record(target_url="https://example.com/article")
        sentinel_response = MagicMock()
        with patch.object(source, "_open_stream", return_value=sentinel_response) as mock_open, patch_archive_iterator(
            [record]
        ) as mock_iter:
            results = list(source.fetch())
        assert len(results) == 1
        mock_open.assert_called_once_with()
        mock_iter.assert_called_once()
        # ArchiveIterator should be called with the raw stream from _open_stream's response
        assert mock_iter.call_args[0][0] is sentinel_response.raw

    def test_passes_url_filter_through(self):
        publisher = stub_publisher(domain="https://example.com/")
        source = CCNewsSource(publisher, warc_path="x")
        record = make_warc_record(target_url="https://example.com/skip-me")
        with patch.object(source, "_open_stream", return_value=MagicMock()), patch_archive_iterator([record]):
            assert list(source.fetch(url_filter=lambda u: "skip" in u)) == []

    def test_processes_multiple_records_independently(self):
        publisher = stub_publisher(domain="https://example.com/")
        source = CCNewsSource(publisher, warc_path="x")
        records: List[Any] = [
            make_warc_record(target_url="https://example.com/a"),
            make_warc_record(target_url="https://other.com/b"),  # filtered out by netloc
            make_warc_record(target_url="https://example.com/c"),
        ]
        with patch.object(source, "_open_stream", return_value=MagicMock()), patch_archive_iterator(records):
            results = list(source.fetch())
        assert [html.requested_url for html in results] == [
            "https://example.com/a",
            "https://example.com/c",
        ]
