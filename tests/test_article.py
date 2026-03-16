import datetime
from typing import Any, Dict

import pytest

from fundus import Article
from fundus.scraping.html import HTML, SourceInfo

info = SourceInfo(publisher="")
html = HTML(content="", responded_url="", requested_url="", crawl_date=datetime.datetime.now(), source_info=info)


class TestArticle:
    def test_constructor(self):
        extraction = {"authors": ["Author"], "title": "title"}

        with pytest.raises(TypeError):
            Article(extraction, html=html)  # type: ignore[call-overload]

        with pytest.raises(TypeError):
            Article(**extraction)  # type: ignore[call-overload]

        Article(**{}, html=html)
        Article(**extraction, html=html, exception=None)
        Article(html=html, **extraction, exception=None)
        Article(**extraction, html=html, exception=TypeError())

    def test_default_values(self):
        extraction: Dict[str, Any] = {}

        article = Article(**extraction, html=html)

        assert article.title is None
        assert article.body is None
        assert article.authors == []
        assert article.publishing_date is None
        assert article.topics == []
        assert article.free_access is False

    def test_view(self):
        extraction = {
            "authors": ["Author1", "Author2", "Author3"],
            "title": "<TITLE>",
        }

        article = Article(**extraction, html=html, exception=None)

        assert article.title == "<TITLE>"
        assert article.authors == ["Author1", "Author2", "Author3"]

    def test_extraction_view_getter(self):
        extraction = {"test_attribute": "test_value"}

        article = Article(**extraction, html=html, exception=None)

        assert article.test_attribute
        assert article.test_attribute == "test_value"

    def test_extraction_view_setter(self):
        extraction = {"test_attribute": "test_value"}

        article = Article(**extraction, html=html, exception=None)
        with pytest.raises(AttributeError):
            article.test_attribute = "another_value"
