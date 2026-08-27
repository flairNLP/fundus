"""Tests for the review-publisher skill's sweep/store logic (skills/review-publisher/scripts).

The sweep is a review *gate*: each test here pins a failure mode the gate must not have —
above all, ways it could report a silent false "clean".
"""

import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, Iterator, List, Sequence, Tuple, cast

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
import review  # noqa: E402

PARAGRAPH_SELECTOR = XPath("//p[@class='b']")
SELECTORS: Dict[str, Any] = {"paragraph": PARAGRAPH_SELECTOR, "summary": None, "subheadline": None}

CHROME = "Sign up for our daily newsletter and never miss a story from the newsroom." * 3
UNIQUE = "A dropped paragraph of real article text that appears on exactly one page here." * 3


def _doc(body_html: str) -> lxml.html.HtmlElement:
    return lxml.html.document_fromstring(f"<html><body>{body_html}</body></html>")


def _result(*texts: str, reason: str = "") -> _sweep.SweepResult:
    """A sweep result carrying one <p> drop per text (or an inapplicable one, given `reason`)."""
    if reason:
        return _sweep.SweepResult(applicable=False, reason=reason)
    return _sweep.SweepResult(
        applicable=True,
        drops=[
            _sweep.DropCandidate(tag="p", description="<p>", text=text, chars=len(text), missing_segments=[])
            for text in texts
        ],
    )


def _ranked_risks(size: int, flagged: Sequence[int]) -> List[_sweep.ArticleRisk]:
    """One risk per pool index, worst-first — `flagged` in the order they should be swapped in."""
    return [
        _sweep.ArticleRisk(index=index, tier=1, flags=[], uncommon_chars=1000 - rank, result=_result())
        for rank, index in enumerate(flagged)
    ] + [
        _sweep.ArticleRisk(index=index, tier=0, flags=[], uncommon_chars=0, result=_result())
        for index in range(size)
        if index not in flagged
    ]


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


class TestRankPool:
    def test_site_chrome_does_not_outrank_a_one_off_miss(self):
        # Uncaptured characters raw would rank every article equally, since the same nav/footer
        # text is uncaptured on all of them. Only what *doesn't* repeat says anything.
        swept: List[Tuple[int, _sweep.SweepResult, Sequence[str]]] = [(i, _result(CHROME), []) for i in range(5)]
        swept[3] = (3, _result(CHROME, UNIQUE), [])

        risks = _sweep.rank_pool(swept)
        assert [risk.index for risk in risks][0] == 3
        assert risks[0].uncommon_chars == len(UNIQUE) and risks[0].flagged
        assert all(risk.uncommon_chars == 0 and not risk.flagged for risk in risks[1:])

    def test_a_broken_article_outranks_a_merely_chatty_one(self):
        swept: List[Tuple[int, _sweep.SweepResult, Sequence[str]]] = [
            (0, _result(UNIQUE * 5), []),  # lots of uncaptured text, but the parser did produce a body
            (1, _result(reason=_sweep.NO_BODY), ["body"]),
            (2, _result(), []),
        ]
        risks = _sweep.rank_pool(swept)
        assert [risk.index for risk in risks] == [1, 0, 2]
        assert risks[0].tier == 2 and risks[0].flags == ["missing body", _sweep.NO_BODY]
        assert risks[1].tier == 1 and risks[2].tier == 0

    def test_a_parser_without_a_paragraph_selector_flags_nothing(self):
        # That reason is a property of the parser - identical on every article, so it ranks nothing.
        # Making it a flag would mark the entire pool and leave the ranking meaningless.
        risks = _sweep.rank_pool([(i, _result(reason=_sweep.NO_PARAGRAPH_SELECTOR), []) for i in range(5)])
        assert all(risk.tier == 0 and risk.flags == [] for risk in risks)

    def test_a_stray_line_is_below_the_flagging_floor(self):
        stray = "x" * (_sweep.MIN_RISK_CHARS - 1)
        (risk,) = _sweep.rank_pool([(0, _result(stray), [])])
        assert risk.uncommon_chars == len(stray) and not risk.flagged

    def test_tiny_pools_discount_nothing(self):
        # Below three articles a "share of the pool" is meaningless; discounting there would erase
        # the only evidence a two-article scan has.
        risks = _sweep.rank_pool([(i, _result(CHROME), []) for i in range(2)])
        assert all(risk.uncommon_chars == len(CHROME) for risk in risks)


class TestApplyRiskSwaps:
    """The swap policy itself, as a pure function; TestSelectForReview covers its wiring."""

    def test_budget_share_rounds_down_and_replaces_from_the_back(self):
        drawn = _sweep.apply_risk_swaps([0, 1, 2, 3, 4], _ranked_risks(10, [5, 6, 7]), budget=5)
        assert drawn == [0, 1, 2, 6, 5]  # int(5 * RISK_SWAP_SHARE) = 2 swaps; the worst takes the last slot

    def test_no_swappable_position_stops_cleanly(self):
        # Every position but the protected first already holds a flagged article - nothing may
        # be given up, however much swap budget is left.
        drawn = _sweep.apply_risk_swaps([0, 8, 9], _ranked_risks(10, [8, 9, 5]), budget=6)
        assert drawn == [0, 8, 9]

    def test_input_draw_is_not_mutated(self):
        original = [0, 1, 2, 3]
        _sweep.apply_risk_swaps(original, _ranked_risks(10, [7]), budget=4)
        assert original == [0, 1, 2, 3]


class TestSelectForReview:
    """The swap policy's wiring into the draw. The diverse ranking itself is the sampler's business
    (and needs numpy / scikit-learn), so it is stubbed out here to leave exactly the driver's own
    decisions under test.
    """

    @pytest.fixture(autouse=True)
    def stub_sampler(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class StubSampler:
            def diverse(self, articles: List[Article], n: int) -> List[Any]:
                return [SimpleNamespace(article=article) for article in articles[:n]]

        module = ModuleType("sampler")
        module.Sampler = StubSampler  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "sampler", module)

    @staticmethod
    def _pool(size: int) -> List[Article]:
        return [
            cast(Article, SimpleNamespace(html=SimpleNamespace(requested_url=f"https://x.test/{i}")))
            for i in range(size)
        ]

    def test_flagged_articles_take_the_least_distinctive_picks(self):
        pool = self._pool(10)
        selection = review._select_for_review(pool, _ranked_risks(10, [7, 8, 9]), budget=6)

        assert [pool.index(article) for article, _, _ in selection] == [0, 1, 2, 9, 8, 7]
        assert [role for _, role, _ in selection] == ["diverse"] * 3 + ["flagged"] * 3

    def test_the_first_pick_survives_a_full_swap_budget(self):
        # The pool medoid is the review's only ordinary article; without it there is no baseline
        # for judging the odd ones, so it is never traded away.
        pool = self._pool(10)
        selection = review._select_for_review(pool, _ranked_risks(10, [5, 6, 7, 8, 9]), budget=4)

        assert pool.index(selection[0][0]) == 0 and selection[0][1] == "diverse"
        assert sum(1 for _, role, _ in selection if role == "flagged") == int(4 * _sweep.RISK_SWAP_SHARE)

    def test_a_flagged_article_already_drawn_costs_no_swap(self):
        pool = self._pool(10)
        selection = review._select_for_review(pool, _ranked_risks(10, [2, 7, 8, 9]), budget=8)

        drawn = [pool.index(article) for article, _, _ in selection]
        assert {2, 7, 8, 9} <= set(drawn)  # the in-draw flag did not consume one of the four swaps


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

    def test_commit_id_is_derived_from_the_imported_fundus_and_stays_inside_the_cache_root(self) -> None:
        # Derived, not passed: every agent computes the same key with no flag and no env var.
        # It must also never escape the cache root, whatever git hands back.
        assert _store.commit_id() and _store.commit_id().isalnum()
        assert _store.commit_cache_dir().parent == _store.cache_root()
        assert _store.commit_cache_dir().name == _store.commit_id()

    def test_commit_id_falls_back_when_git_cannot_answer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A tarball install, a missing git binary: still usable, still inside the cache root.
        # `commit_id` is cached, so each case needs a cold cache - and the real value restored after.
        for run in (
            lambda *a, **k: (_ for _ in ()).throw(OSError()),
            lambda *a, **k: SimpleNamespace(returncode=1, stdout=""),
            lambda *a, **k: SimpleNamespace(returncode=0, stdout="  \n"),  # git answered nothing
        ):
            _store.commit_id.cache_clear()
            monkeypatch.setattr(_store.subprocess, "run", run)
            assert _store.commit_id() == "detached"
        monkeypatch.undo()
        _store.commit_id.cache_clear()

    def test_remove_commit_cache_takes_every_publisher_but_refuses_foreign_entries(
        self, cache_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        commit = cache_root / "d732ca85"
        for spec in ("ca.NationalPost", "ca.TorontoStar"):
            (commit / spec).mkdir(parents=True)
            (commit / spec / _store.STATE_FILE).write_text("{}", encoding="utf-8")
        monkeypatch.setattr(_store, "commit_cache_dir", lambda: commit)

        # A crawl killed before its first write leaves an empty dir. It must not wedge teardown,
        # and since `rmtree` takes it too it belongs in what the caller is told was removed.
        (commit / "ca.Empty").mkdir()
        assert _store.remove_commit_cache() == ["ca.Empty", "ca.NationalPost", "ca.TorontoStar"]
        assert not commit.exists()
        assert _store.remove_commit_cache() == []  # already gone is a no-op, not an error

        # Anything that is *not* a review cache stops the teardown entirely.
        (commit / "notes").mkdir(parents=True)
        (commit / "notes" / "important.md").write_text("hand-written", encoding="utf-8")
        with pytest.raises(SystemExit):
            _store.remove_commit_cache()
        assert (commit / "notes" / "important.md").exists()

    def test_prune_stale_caches_skips_fresh_and_foreign_dirs(
        self, cache_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_store, "cache_root", lambda: cache_root)
        monkeypatch.setattr(_store, "commit_cache_dir", lambda: cache_root / "mine")

        def make(name: str, age_days: float) -> Path:
            path = cache_root / name / "ca.X"
            path.mkdir(parents=True)
            (path / _store.STATE_FILE).write_text("{}", encoding="utf-8")
            stale = time.time() - age_days * 86400
            os.utime(cache_root / name, (stale, stale))
            return cache_root / name

        make("mine", 30)  # this commit's own cache is never pruned out from under it
        make("old", 30)
        make("recent", 1)
        foreign = cache_root / "foreign" / "notes"
        foreign.mkdir(parents=True)
        (foreign / "keep.md").write_text("x", encoding="utf-8")
        os.utime(cache_root / "foreign", (time.time() - 30 * 86400,) * 2)

        assert _store.prune_stale_caches(max_age_days=7) == ["old"]
        assert (cache_root / "mine").exists() and (cache_root / "recent").exists()
        assert (foreign / "keep.md").exists()

    def test_new_state_records_the_declared_impersonation_profile(self) -> None:
        # The profile decides the TLS fingerprint the draw came back through, so the review's
        # claims are claims about it - it has to survive into the state, not just the crawl.
        declared = _store.new_state("mx.Test", "970", 100, "chrome")
        assert declared["crawl"]["impersonate"] == "chrome"
        assert _store.new_state("ca.Test", None, 100, None)["crawl"]["impersonate"] is None

    def test_impersonation_line_names_the_profile_and_survives_an_old_cache(self) -> None:
        assert "chrome131" in review._impersonation_line("chrome131")
        assert "none declared" in review._impersonation_line(None)
        # `status` reads it off a state dict, so a cache predating the field must not crash.
        assert review._impersonation_line({}.get("impersonate"))

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


class TestCommands:
    """The two contracts a caller acts on: `status`' exit code, and what `done` says it removed."""

    def test_status_exits_nonzero_until_the_gate_is_open(
        self, cache_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # SKILL.md and PLAYBOOK §2 both state "no verdict before status reports READY"; the exit
        # code is the machine-checkable half of that, so it needs to actually track the gate.
        cache = cache_root / "cache"
        cache.mkdir()
        monkeypatch.setattr(review, "default_cache_dir", lambda spec: cache)
        args = SimpleNamespace(publisher="xx.Test")

        ready = TestPayloadSkeleton._ready_state()
        pending = dict(ready, adjudications={})
        _store.write_state(cache, pending)
        assert review.cmd_status(cast(Any, args)) == 1  # a candidate is un-adjudicated

        _store.write_state(cache, ready)
        assert review.cmd_status(cast(Any, args)) == 0

    def test_done_reports_everything_it_removed(self, cache_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # `rmtree` takes the whole commit dir, so a publisher dir left empty by an interrupted
        # crawl is removed too - saying "nothing to remove" there would be a lie about a delete.
        commit = cache_root / "abc1234"
        (commit / "ca.Interrupted").mkdir(parents=True)  # crawl killed before its first write
        monkeypatch.setattr(_store, "commit_cache_dir", lambda: commit)
        monkeypatch.setattr(review, "commit_id", lambda: "abc1234")

        assert review.cmd_done(cast(Any, SimpleNamespace())) == 0
        assert not commit.exists()
        assert review.cmd_done(cast(Any, SimpleNamespace())) == 0  # gone already is still fine


class TestPayloadSkeleton:
    """`payload` must emit review.json as a fillable skeleton — and never clobber a filled one."""

    @staticmethod
    def _ready_state() -> Dict[str, Any]:
        return {
            "publisher": "xx.Test",
            "pr": "970",
            "crawl": {"pool": 50, "started": 1.0, "finished": 2.0, "completed": True},
            "articles": [{"index": 1, "url": "https://x.test/a", "html_file": "01.html"}],
            "scan": {"pool": 50, "flagged": 4, "reviewed": 1, "reviewed_flagged": 1, "medoid_flagged": False},
            "sweep": {
                "version": None,
                "swept_at": 3.0,
                "articles_swept": 1,
                "not_applicable": 0,
                "candidates": [{"id": "Dabc123", "kind": "drop", "text": "dropped text", "articles": [1]}],
            },
            "adjudications": {"Dabc123": {"verdict": "blocker", "note": "match results list dropped", "at": 4.0}},
        }

    def test_payload_emits_prefilled_skeleton_and_keeps_edits(
        self, cache_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cache = cache_root / "cache"
        cache.mkdir()
        _store.write_state(cache, self._ready_state())
        monkeypatch.setattr(review, "resolve_publisher", lambda spec: SimpleNamespace(parser=None))
        monkeypatch.setattr(review, "_parser_source_path", lambda proxy: "src/fundus/publishers/xx/test.py")
        monkeypatch.setattr(review, "default_cache_dir", lambda spec: cache)
        args = SimpleNamespace(publisher="xx.Test", pr=None)

        assert review.cmd_payload(cast(Any, args)) == 0
        skeleton = json.loads((cache / "review.json").read_text(encoding="utf-8"))
        assert skeleton["event"] == "REQUEST_CHANGES"
        assert "read 1 of 50 scanned (4 flagged, 1 in draw)" in skeleton["body"]
        (comment,) = skeleton["comments"]
        assert comment["path"] == "src/fundus/publishers/xx/test.py" and comment["side"] == "RIGHT"
        assert "match results list dropped" in comment["body"] and "https://x.test/a" in comment["body"]
        assert not isinstance(comment["line"], int)  # an unfilled stub must fail the POST, not post
        assert (cache / "findings.json").is_file()

        # A second run must keep the agent's edits rather than regenerate over them.
        (cache / "review.json").write_text("edited by the agent", encoding="utf-8")
        assert review.cmd_payload(cast(Any, args)) == 0
        assert (cache / "review.json").read_text(encoding="utf-8") == "edited by the agent"

    def test_parser_source_path_falls_back_outside_src_layout(self) -> None:
        # This test file is not under src/fundus/, so the repo-relative cut has nothing to cut at.
        assert review._parser_source_path(cast(Any, iter([TestPayloadSkeleton]))).startswith("<")


class TestBodySelectorsAccessor:
    def test_declared_and_absent_selectors(self):
        class Dummy(BaseParser):
            _paragraph_selector = XPath("//p")

        selectors = Dummy.body_selectors()
        assert selectors["paragraph"] is Dummy._paragraph_selector
        assert selectors["summary"] is None and selectors["subheadline"] is None
