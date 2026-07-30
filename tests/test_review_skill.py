"""Tests for the review-publisher skill's sweep/store logic (skills/review-publisher/scripts).

The sweep is a review *gate*: each test here pins a failure mode the gate must not have —
above all, ways it could report a silent false "clean".
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterator, cast

import lxml.html
import pytest
from lxml.etree import XPath

from fundus import Article
from fundus.parser import ArticleBody, BaseParser
from fundus.parser.data import ArticleSection, TextSequence

_SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "review-publisher" / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import _store  # noqa: E402
import _sweep  # noqa: E402

PARAGRAPH_SELECTOR = XPath("//p[@class='b']")
SELECTORS: Dict[str, Any] = {"paragraph": PARAGRAPH_SELECTOR, "summary": None, "subheadline": None}


def _doc(body_html: str) -> lxml.html.HtmlElement:
    return lxml.html.document_fromstring(f"<html><body>{body_html}</body></html>")


@pytest.fixture
def cache_root(tmp_path: Path) -> Iterator[Path]:
    """`tmp_path`, emptied again afterwards — pytest itself keeps the last three runs' dirs around."""
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)


class TestSweepArticle:
    def test_single_captured_node_falls_back_to_loud_whole_document_walk(self):
        # One captured <p> must never scope the walk to itself - that covered its whole
        # subtree and guaranteed a false "clean" on exactly the worst article.
        doc = _doc(
            """
            <div class="content">
              <p class="b">Intro paragraph text here.</p>
              <ul><li>First dropped item with enough characters.</li></ul>
            </div>
            """
        )
        result = _sweep.sweep_article(doc, SELECTORS, ["Intro paragraph text here."])
        assert result.applicable
        assert result.loose_scope
        assert [drop.tag for drop in result.drops] == ["ul"]

    def test_nested_uncaptured_blocks_report_outermost_only(self):
        doc = _doc(
            """
            <div class="content">
              <p class="b">Para one long enough text.</p>
              <p class="b">Para two long enough text.</p>
              <table><tr><td><ul><li>Nested dropped list item text.</li></ul></td></tr></table>
            </div>
            """
        )
        result = _sweep.sweep_article(doc, SELECTORS, ["Para one long enough text.", "Para two long enough text."])
        assert not result.loose_scope
        assert [drop.tag for drop in result.drops] == ["table"]

    def test_duplicated_opening_does_not_suppress_a_dropped_tail(self):
        # A block that *opens* with body text but carries unseen content is a drop -
        # the old 60-char prefix probe suppressed it silently.
        lede = "The lede sentence appears in the body fully."
        dropped = "Completely different dropped content sentence."
        doc = _doc(
            f"""
            <div class="content">
              <p class="b">{lede}</p>
              <p class="b">Second body paragraph with plenty of text.</p>
              <ul><li>{lede}</li><li>{dropped}</li></ul>
            </div>
            """
        )
        result = _sweep.sweep_article(doc, SELECTORS, [lede, "Second body paragraph with plenty of text."])
        assert len(result.drops) == 1
        assert dropped in result.drops[0].missing_segments

    def test_true_duplicate_is_suppressed_but_visibly(self):
        text = "Second body paragraph with plenty of text."
        doc = _doc(
            f"""
            <div class="content">
              <p class="b">First body paragraph with plenty of text.</p>
              <p class="b">{text}</p>
              <p class="dek">{text}</p>
            </div>
            """
        )
        result = _sweep.sweep_article(doc, SELECTORS, ["First body paragraph with plenty of text.", text])
        assert result.drops == []
        assert len(result.duplicates) == 1 and text[:40] in result.duplicates[0]

    def test_zero_width_characters_do_not_false_flag(self):
        # The parser body is normalize_whitespace()-normalized; the sweep must use the
        # same normalization or zero-width characters cause false drop candidates.
        raw = "Zero​width joined words make a sentence."
        from fundus.parser.utility import normalize_whitespace

        doc = _doc(
            f"""
            <div class="content">
              <p class="b">Some captured paragraph with text.</p>
              <p class="dek">{raw}</p>
            </div>
            """
        )
        result = _sweep.sweep_article(doc, SELECTORS, [normalize_whitespace(raw)])
        assert result.drops == []

    def test_empty_body_is_not_applicable_rather_than_all_drops(self):
        # The crawl draws unfiltered, so a parser that extracted nothing reaches the sweep. Comparing
        # against an empty body would make every block a drop candidate and bury the gate.
        doc = _doc(
            """
            <div class="content">
              <p class="b">Intro paragraph text here.</p>
              <ul><li>A list item with enough characters.</li></ul>
            </div>
            """
        )
        result = _sweep.sweep_article(doc, SELECTORS, [])
        assert not result.applicable and result.drops == []
        assert "no body" in result.reason

    def test_missing_paragraph_selector_reports_its_own_reason(self):
        result = _sweep.sweep_article(_doc("<p>text</p>"), {"paragraph": None}, ["some body text"])
        assert not result.applicable and "_paragraph_selector" in result.reason


class TestFindLeaks:
    def test_repeated_unit_is_flagged(self):
        boilerplate = "Subscribe to our newsletter for daily updates!"
        units = [(i, [f"unique article text number {i} here", boilerplate]) for i in range(1, 6)]
        units += [(i, [f"unique article text number {i} here"]) for i in range(6, 11)]
        leaks = _sweep.find_leaks(units)
        assert [leak.text for leak in leaks] == [boilerplate]
        assert leaks[0].article_indices == [1, 2, 3, 4, 5]

    def test_below_threshold_and_tiny_samples_yield_nothing(self):
        boilerplate = "Subscribe to our newsletter for daily updates!"
        units = [(i, [f"unique article text number {i} here", boilerplate]) for i in range(1, 5)]
        units += [(i, [f"unique article text number {i} here"]) for i in range(5, 11)]
        assert _sweep.find_leaks(units) == []  # 4 of 10 < threshold 5
        assert _sweep.find_leaks(units[:2]) == []  # <3 articles: scan is inactive

    def test_articles_without_body_do_not_raise_the_threshold(self):
        # Body-less articles reach the sweep now; counting them would demand that boilerplate clear
        # a threshold it cannot reach, since they contribute no unit at all.
        boilerplate = "Subscribe to our newsletter for daily updates!"
        units = [(i, [f"unique article text number {i} here", boilerplate]) for i in range(1, 4)]
        units += [(i, []) for i in range(4, 11)]
        assert [leak.text for leak in _sweep.find_leaks(units)] == [boilerplate]


class TestStore:
    def test_save_article_round_trips_exact_bytes(self, cache_root: Path):
        # CRLF must survive: text mode would write \r\r\n on Windows and read back \n\n.
        content = "<html>\r\n<body>line1\r\nline2</body>\r\n</html>"
        article = SimpleNamespace(
            html=SimpleNamespace(content=content, requested_url="https://x.test/a", crawl_date=datetime(2026, 6, 1)),
            title="t",
            authors=["a"],
            topics=[],
            images=[],
            body=None,
        )
        record = _store.save_article(cache_root, 1, cast(Article, article))
        assert _store.read_html(cache_root, record) == content
        assert _store.body_units(record["body"]) == []

    def test_prepare_cache_dir_refuses_foreign_directories(self, cache_root: Path):
        foreign = cache_root / "foreign"
        foreign.mkdir()
        (foreign / "important.txt").write_text("do not delete", encoding="utf-8")
        with pytest.raises(SystemExit):
            _store.prepare_cache_dir(foreign)
        assert (foreign / "important.txt").exists()

        cache = cache_root / "cache"
        cache.mkdir()
        (cache / _store.STATE_FILE).write_text("{}", encoding="utf-8")
        (cache / "01.html").write_text("x", encoding="utf-8")
        _store.prepare_cache_dir(cache)  # a real cache is wiped and recreated
        assert cache.exists() and not any(cache.iterdir())

        _store.prepare_cache_dir(cache_root / "fresh")  # nonexistent is simply created
        assert (cache_root / "fresh").is_dir()

    def test_missing_attributes_matches_the_default_draw(self):
        # `Requires` is fundus' own filter, so a summary-only body counts as missing here exactly
        # as it does in the default crawl - the review must not invent its own truthiness.
        summary_only = ArticleBody(summary=TextSequence(["A standfirst."]), sections=[])
        complete = ArticleBody(
            summary=TextSequence([]), sections=[ArticleSection(TextSequence([]), TextSequence(["A paragraph."]))]
        )

        def article(**overrides: Any) -> Article:
            attributes = {"title": "t", "body": complete, "publishing_date": datetime(2026, 6, 1), **overrides}
            return cast(Article, SimpleNamespace(**attributes))

        assert _store.missing_attributes(article()) == []
        assert _store.missing_attributes(article(body=summary_only)) == ["body"]
        assert _store.missing_attributes(article(title=None, body=None)) == ["title", "body"]
        assert _store.missing_attributes(article(publishing_date=None)) == ["publishing_date"]

    def test_candidate_ids_are_stable_content_hashes(self):
        assert _store.candidate_id("drop", "x", "ul", "text") == _store.candidate_id("drop", "x", "ul", "text")
        assert _store.candidate_id("drop", "x", "ul", "text") != _store.candidate_id("drop", "x", "ul", "other")
        assert _store.candidate_id("leak", "x", "text").startswith("L")

    def test_payload_gaps_gate(self):
        candidate = {"id": "Dabc123", "kind": "drop", "text": "x", "articles": [1]}
        state: Dict[str, Any] = {
            "publisher": "xx.Test",
            "crawl": {"pool": 50, "started": 1.0, "finished": 2.0, "completed": True},
            "articles": [{"index": 1}],
            "sweep": {"version": None, "swept_at": 3.0, "not_applicable": 0, "candidates": [candidate]},
            "adjudications": {},
        }
        assert any("un-adjudicated" in gap for gap in _store.payload_gaps(state))

        state["adjudications"] = {"Dabc123": {"verdict": "ok", "note": "chrome"}}
        assert _store.payload_gaps(state) == []
        assert _store.blocker_candidates(state) == []

        state["sweep"]["swept_at"] = 1.5  # sweep predates the crawl -> stale
        assert any("re-run `sweep`" in gap for gap in _store.payload_gaps(state))

        state["crawl"]["completed"] = False
        assert any("did not complete" in gap for gap in _store.payload_gaps(state))


class TestBodySelectorsAccessor:
    def test_declared_and_absent_selectors(self):
        class Dummy(BaseParser):
            _paragraph_selector = XPath("//p")

        selectors = Dummy.body_selectors()
        assert selectors["paragraph"] is Dummy._paragraph_selector
        assert selectors["summary"] is None and selectors["subheadline"] is None
