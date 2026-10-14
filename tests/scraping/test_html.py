import datetime

from fundus.scraping.html import HTML, SourceInfo
from fundus.scraping.pipeline.source.ccnews import WarcSourceInfo
from fundus.scraping.pipeline.source.web import WebSourceInfo


class TestSourceInfoSerialize:
    def test_base_class_serializes_publisher(self):
        info = SourceInfo(publisher="example.com")
        assert info.serialize() == {"publisher": "example.com"}

    def test_web_subclass_includes_inherited_and_own_fields(self):
        info = WebSourceInfo(publisher="example.com", type="rss", url="https://example.com/feed.xml")
        assert info.serialize() == {
            "publisher": "example.com",
            "type": "rss",
            "url": "https://example.com/feed.xml",
        }

    def test_warc_subclass_includes_inherited_and_own_fields(self):
        info = WarcSourceInfo(
            publisher="example.com",
            warc_path="cc-news/2024/path.warc.gz",
            warc_headers={"WARC-Type": "response"},
            http_headers={"Content-Type": "text/html"},
        )
        assert info.serialize() == {
            "publisher": "example.com",
            "warc_path": "cc-news/2024/path.warc.gz",
            "warc_headers": {"WARC-Type": "response"},
            "http_headers": {"Content-Type": "text/html"},
        }


class TestHTMLSerialize:
    def test_serializes_all_fields_with_isoformat_and_nested_source_info(self):
        html = HTML(
            requested_url="https://example.com/article",
            responded_url="https://example.com/article",
            content="<html/>",
            crawl_date=datetime.datetime(2024, 1, 2, 3, 4, 5),
            source_info=SourceInfo(publisher="example.com"),
        )
        assert html.serialize() == {
            "requested_url": "https://example.com/article",
            "responded_url": "https://example.com/article",
            "content": "<html/>",
            "crawl_date": "2024-01-02T03:04:05",
            "source_info": {"publisher": "example.com"},
        }

    def test_uses_subclass_source_info_serialize(self):
        html = HTML(
            requested_url="https://example.com/article",
            responded_url="https://example.com/article",
            content="<html/>",
            crawl_date=datetime.datetime(2024, 1, 2, 3, 4, 5),
            source_info=WebSourceInfo(publisher="example.com", type="rss", url="https://example.com/feed.xml"),
        )
        assert html.serialize()["source_info"] == {
            "publisher": "example.com",
            "type": "rss",
            "url": "https://example.com/feed.xml",
        }
