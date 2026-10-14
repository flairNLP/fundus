import pickle
from unittest.mock import patch

import langdetect
import pytest

from fundus import Article
from tests.fixtures.builders import make_html

html = make_html()


class _StubBody:
    """Minimal stand-in for ArticleBody so we can control str(body) without importing the parser."""

    def __init__(self, text: str) -> None:
        self._text = text

    def __str__(self) -> str:
        return self._text


class TestConstructor:
    def test_rejects_positional_extraction(self):
        with pytest.raises(TypeError):
            Article({"title": "t"}, html=html)  # type: ignore[arg-type, misc]

    def test_requires_html_keyword(self):
        with pytest.raises(TypeError):
            Article(title="t")  # type: ignore[call-arg]

    def test_accepts_empty_extraction(self):
        Article(html=html)

    def test_accepts_extraction_kwargs(self):
        Article(html=html, title="t", authors=["A"])


class TestProperties:
    def test_defaults_when_extraction_is_empty(self):
        article = Article(html=html)
        assert article.title is None
        assert article.body is None
        assert article.authors == []
        assert article.publishing_date is None
        assert article.topics == []
        assert article.free_access is False
        assert article.images == []

    def test_returns_values_from_extraction(self):
        article = Article(html=html, title="<TITLE>", authors=["A", "B", "C"])
        assert article.title == "<TITLE>"
        assert article.authors == ["A", "B", "C"]

    def test_publisher_comes_from_html_source_info(self):
        article = Article(html=make_html(publisher="example.com"))
        assert article.publisher == "example.com"


class TestExtractionView:
    """Arbitrary extraction kwargs are exposed as read-only attributes via AttributeView."""

    def test_read_returns_extraction_value(self):
        article = Article(html=html, custom="value")
        assert article.custom == "value"

    def test_read_reflects_extraction_mutation(self):
        article = Article(html=html, custom="value")
        article.__extraction__["custom"] = "mutated"  # type: ignore[index]
        assert article.custom == "mutated"

    def test_write_raises_attribute_error(self):
        article = Article(html=html, custom="value")
        with pytest.raises(AttributeError):
            article.custom = "new"


class TestPickleProtocol:
    """Article must survive the pickle protocol used by multiprocessing.Queue.

    Production CCNewsCrawler workers return articles to the main process through a
    multiprocessing.Queue, which serializes payloads with pickle. Pickling probes
    ``hasattr(obj, "__setstate__")`` during unpickling before ``__extraction__`` is
    restored — ``Article.__getattr__`` must short-circuit on the missing dict instead of
    recursing infinitely.
    """

    def test_getattr_does_not_recurse_during_unpickle(self):
        article = Article(html=html, title="t", custom="value")
        restored = pickle.loads(pickle.dumps(article))
        assert restored.title == "t"
        assert restored.custom == "value"

    def test_article_survives_pickle(self):
        """An Article must round-trip through pickle — it is what CCNews returns across the
        multiprocessing.Queue. Guards SourceInfo carrying lightweight publisher identity (the name)
        rather than a live Publisher, so the Article never drags unpicklable parser/filter state.
        """
        article = Article(html=make_html(publisher="DerStandard"), title="t")
        restored = pickle.loads(pickle.dumps(article))
        assert restored.publisher == "DerStandard"
        assert restored.title == "t"


class TestPlaintext:
    def test_returns_str_of_body(self):
        article = Article(html=html, body=_StubBody("Article text."))
        assert article.plaintext == "Article text."

    def test_returns_none_when_str_body_is_empty(self):
        article = Article(html=html, body=_StubBody(""))
        assert article.plaintext is None

    def test_returns_none_when_body_is_exception(self):
        article = Article(html=html, body=ValueError("parse failed"))
        assert article.plaintext is None

    def test_returns_none_when_body_is_none(self):
        article = Article(html=html)
        assert article.plaintext is None


class TestLang:
    def test_detects_language_from_plaintext(self):
        article = Article(html=html, body=_StubBody("Some article text"))
        with patch("fundus.scraping.article.langdetect.detect", return_value="en"):
            assert article.lang == "en"

    def test_falls_back_to_html_lang_on_detect_exception(self):
        article = Article(
            html=make_html(content='<html lang="de"><body>x</body></html>'),
            body=_StubBody("text"),
        )
        with patch(
            "fundus.scraping.article.langdetect.detect",
            side_effect=langdetect.LangDetectException(0, "fail"),
        ):
            assert article.lang == "de"

    def test_falls_back_to_html_lang_when_detector_returns_unknown(self):
        unknown = langdetect.detector_factory.Detector.UNKNOWN_LANG
        article = Article(
            html=make_html(content='<html lang="fr"><body>x</body></html>'),
            body=_StubBody("text"),
        )
        with patch("fundus.scraping.article.langdetect.detect", return_value=unknown):
            assert article.lang == "fr"

    def test_strips_region_suffix_from_html_lang(self):
        # no body → plaintext is None → detection is skipped, falling to html lang
        article = Article(html=make_html(content='<html lang="en-US"><body>x</body></html>'))
        assert article.lang == "en"

    def test_returns_none_when_no_plaintext_and_no_html_lang(self):
        article = Article(html=make_html(content="<html><body>x</body></html>"))
        assert article.lang is None


class TestToJson:
    def test_default_uses_default_export_fields(self):
        article = Article(html=html, title="t")
        result = article.to_json()
        assert set(result.keys()) == set(Article.DEFAULT_EXPORT_FIELDS)
        assert result["title"] == "t"

    def test_default_does_not_include_arbitrary_extras(self):
        article = Article(html=html, title="t", meta={"k": "v"}, ld={"k": "v"})
        result = article.to_json()
        assert "meta" not in result
        assert "ld" not in result

    def test_explicit_fields_filter_output(self):
        article = Article(html=html, title="t", topics=["a", "b"])
        result = article.to_json("title")
        assert result == {"title": "t"}

    def test_preserves_field_order(self):
        article = Article(html=html, title="t", topics=["a"])
        result = article.to_json("topics", "title")
        assert list(result.keys()) == ["topics", "title"]

    def test_can_export_arbitrary_extraction_key_by_request(self):
        article = Article(html=html, meta={"k": "v"})
        result = article.to_json("meta")
        assert result == {"meta": {"k": "v"}}

    def test_raises_key_error_on_unknown_field(self):
        article = Article(html=html, title="t")
        with pytest.raises(KeyError):
            article.to_json("title", "nonexistent")


class TestStr:
    def test_renders_title_and_plaintext(self):
        article = Article(html=html, title="The Title", body=_StubBody("The text."))
        rendered = str(article)
        assert "The Title" in rendered
        assert "The text." in rendered

    def test_marks_missing_title(self):
        article = Article(html=html, body=_StubBody("text"))
        assert "--missing title--" in str(article)

    def test_marks_missing_plaintext(self):
        article = Article(html=html, title="t")
        assert "--missing plaintext--" in str(article)
