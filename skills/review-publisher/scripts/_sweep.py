"""Pure sweep logic for the publisher review: drop candidates, leak candidates, pool ranking.

No I/O and no crawling here — `review.py` feeds parsed documents and cached body text in,
results come out. That is what makes this file unit-testable (tests/test_review_skill.py),
and the tests pin exactly the failure modes a review gate must not have.

The same `sweep_article` serves two callers, and the distinction matters: over the *cached
draw* it produces the candidates a human adjudicates (the gate), while over the whole crawled
pool `rank_pool` turns it into a per-article score that decides which articles get cached at
all. Selection and gating therefore measure with one instrument and can never drift apart.

Design rule: **a heuristic may be noisy, but it must never be silently green.**
- Fewer than two captured nodes -> the walk falls back to the whole document and is
  flagged `loose_scope`, never silently scoped to the one captured node.
- A block whose text is judged "already in the body" is returned as a *duplicate* (and
  printed by the driver) so the suppression itself is visible and vetoable.
- Presence is checked on *every* segment of a block (each <li>, cell, paragraph), not a
  prefix probe — a list that opens by restating the lede still flags its dropped tail.
- Text is normalized with fundus's own `normalize_whitespace`, the same function that
  built the body text being compared against, so the two sides can never drift.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Type

import lxml.html

from fundus.parser import BaseParser, ParserProxy
from fundus.parser.utility import normalize_whitespace

# Structural blocks whose dropped content silently corrupts the body. A paragraph-only
# selector never matches these, so any one of them with real text is a drop candidate.
# Reported, never judged: `table` has no representation in `ArticleBody` and a `blockquote`
# may legitimately restate body text, so both are usually adjudicated `ok` (PLAYBOOK §2).
# They stay on the list because a `table` only reaches here when *none* of its text was
# captured — which is a real miss when the cell held prose.
STRUCTURAL_TAGS = {"table", "ul", "ol", "dl", "blockquote", "pre"}
# Text-bearing blocks the selector is *supposed* to catch; an uncaptured one usually
# means a selector gap (e.g. <p> whose text lives only inside <em>/<a>).
TEXT_TAGS = {"p", "h2", "h3", "h4", "h5"}
REPORT_TAGS = STRUCTURAL_TAGS | TEXT_TAGS

# The text-bearing leaves a structural block is split into for the presence check.
SEGMENT_TAGS = {"p", "li", "dt", "dd", "td", "th", "caption", "h2", "h3", "h4", "h5"}
# Segments shorter than this prove nothing on their own ("Yes.", a number cell).
MIN_SEGMENT_CHARS = 12

# A body unit must be at least this long to count for cross-article leak detection.
MIN_LEAK_CHARS = 8

# Why a sweep does not apply. `NO_PARAGRAPH_SELECTOR` is a property of the *parser* — identical for
# every article — while the others describe this one article, which is what `rank_pool` keys on.
NO_PARAGRAPH_SELECTOR = "no _paragraph_selector - body built another way"
NO_BODY = "parser extracted no body"

# A drop text this common across the pool is site chrome, not this article's problem. Same logic as
# `find_leaks` on the other side: boilerplate repeats across articles, article content doesn't.
COMMON_DROP_SHARE = 0.5
# Share of the review draw the scan's worst articles may claim from the diverse picks.
RISK_SWAP_SHARE = 0.5
# Uncommon uncaptured text below this (roughly a short paragraph) flags nothing: a stray line that
# merely failed to repeat is far more likely chrome than a body miss, and flagging it floods the scan.
MIN_RISK_CHARS = 120


@dataclass
class DropCandidate:
    """An uncaptured block whose text is absent from the extracted body."""

    tag: str
    description: str
    text: str
    chars: int
    missing_segments: List[str]

    @property
    def key(self) -> Tuple[str, str]:
        """Identity of this drop *across* articles: same tag, same (capped, folded) text.

        Shared by the pool scan's chrome subtraction and the driver's candidate merging, so the
        two can never disagree about what counts as "the same drop seen again".
        """
        return self.tag, self.text[:160].casefold()


@dataclass
class LeakCandidate:
    """A body unit repeated across many articles — the boilerplate signature."""

    text: str
    article_indices: List[int]


@dataclass
class SweepResult:
    applicable: bool
    reason: str = ""  # why the sweep does not apply; empty when it does
    counts: Dict[str, int] = field(default_factory=dict)
    container: Optional[str] = None
    loose_scope: bool = False
    captured_blocks: int = 0
    duplicates: List[str] = field(default_factory=list)
    drops: List[DropCandidate] = field(default_factory=list)


# --- version + selector access ---


def version_classes(parser_proxy: ParserProxy) -> Dict[str, Type[BaseParser]]:
    """Version label (e.g. 'V1_1') -> version class, from the proxy's own registry."""
    return {cls.__name__: cls for cls in parser_proxy}


# --- per-article helpers (bottom-up) ---


def _describe(el: lxml.html.HtmlElement) -> str:
    cls = el.get("class")
    return f"<{str(el.tag)}{(' class=' + repr(cls)) if cls else ''}>"


def _element_nodes(selector: Any, doc: lxml.html.HtmlElement) -> List[lxml.html.HtmlElement]:
    """Apply a selector once, keeping only real elements (a text()-XPath yields strings)."""
    return [el for el in selector(doc) if isinstance(el, lxml.html.HtmlElement)]


def lowest_common_ancestor(elements: Sequence[lxml.html.HtmlElement]) -> Optional[lxml.html.HtmlElement]:
    """LCA of the captured nodes = the body container to walk.

    Returns None for fewer than two *distinct* elements: the degenerate case must fall
    back to a loud whole-document walk, never scope the sweep to the lone captured node
    (which would cover its whole subtree and report a guaranteed false 'clean').

    Sets hold the *elements*, never bare id()s: lxml elements are proxies, and only a
    live reference guarantees the same node yields the same Python object again.
    """
    distinct: List[lxml.html.HtmlElement] = []
    for el in elements:
        if el not in distinct:
            distinct.append(el)
    if len(distinct) < 2:
        return None
    # Ancestor chain (root-first) of the first element.
    chain = list(reversed(list(distinct[0].iterancestors()))) + [distinct[0]]
    common = set(chain)
    for el in distinct[1:]:
        common &= set(el.iterancestors()) | {el}
    # Deepest element in `chain` that's still common across all.
    for el in reversed(chain):
        if el in common:
            return el
    return None


def coverage_sets(
    captured_nodes: Sequence[lxml.html.HtmlElement],
) -> Tuple[Set[lxml.html.HtmlElement], Set[lxml.html.HtmlElement]]:
    """Precompute coverage once per article: (elements above a captured node, elements inside one).

    'Above' (a captured descendant exists) covers `<p><strong>Subhead</strong></p>` where
    the <strong> is matched; 'inside' covers walking into a captured container's children.
    Replaces a per-element `iterdescendants` scan, which is O(elements x subtree). The sets
    keep the element proxies alive on purpose — see `lowest_common_ancestor`.
    """
    above: Set[lxml.html.HtmlElement] = set()
    inside: Set[lxml.html.HtmlElement] = set()
    for node in captured_nodes:
        above.add(node)
        inside.add(node)
        above.update(node.iterancestors())
        inside.update(node.iterdescendants())
    return above, inside


def _segments(el: lxml.html.HtmlElement) -> List[str]:
    """A block's text-bearing leaves (each <li>, cell, paragraph); the block itself if none."""
    segments = [
        normalize_whitespace(sub.text_content()) for sub in el.iter() if sub is not el and sub.tag in SEGMENT_TAGS
    ]
    segments = [segment for segment in segments if segment]
    return segments or [normalize_whitespace(el.text_content())]


def text_present(el: lxml.html.HtmlElement, body_norm_folded: str) -> Tuple[bool, List[str]]:
    """Is this block's text fully in the body? Returns (present, missing segments).

    Every long-enough segment must appear — a partial match is a drop, with the missing
    segments named. Blocks made only of short segments fall back to their whole text, so
    a tiny block can't pass by having nothing probative to check.
    """
    segments = _segments(el)
    missing = [
        segment
        for segment in segments
        if len(segment) >= MIN_SEGMENT_CHARS and segment.casefold() not in body_norm_folded
    ]
    if missing:
        return False, missing
    if all(len(segment) < MIN_SEGMENT_CHARS for segment in segments):
        whole = normalize_whitespace(el.text_content())
        if whole.casefold() not in body_norm_folded:
            return False, [whole]
    return True, []


# --- the per-article sweep ---


def sweep_article(doc: lxml.html.HtmlElement, selectors: Dict[str, Optional[Any]], units: Sequence[str]) -> SweepResult:
    """Sweep one parsed document against the body units the parser extracted from it."""
    paragraph_selector = selectors.get("paragraph")
    if paragraph_selector is None:
        return SweepResult(applicable=False, reason=NO_PARAGRAPH_SELECTOR)
    if not units:
        # Without body text every block reads as missing, burying the gate in drop candidates.
        return SweepResult(applicable=False, reason=NO_BODY)

    para_nodes = _element_nodes(paragraph_selector, doc)
    summary_selector = selectors.get("summary")
    summ_nodes = _element_nodes(summary_selector, doc) if summary_selector is not None else []
    subheadline_selector = selectors.get("subheadline")
    sub_nodes = _element_nodes(subheadline_selector, doc) if subheadline_selector is not None else []

    above, inside = coverage_sets(para_nodes + summ_nodes + sub_nodes)
    body_norm_folded = " ".join(normalize_whitespace(unit) for unit in units).casefold()

    # Scope the walk to the body container: the LCA of paragraph + subheadline nodes.
    # Summary often lives in the page header, so it's excluded from the LCA.
    container = lowest_common_ancestor(para_nodes + sub_nodes)
    loose_scope = container is None or container.tag in ("html", "body")
    walk_root = doc if loose_scope or container is None else container

    result = SweepResult(
        applicable=True,
        counts={"paragraph": len(para_nodes), "summary": len(summ_nodes), "subheadline": len(sub_nodes)},
        container=_describe(container) if container is not None and not loose_scope else "(whole document)",
        loose_scope=loose_scope,
    )
    reported: Set[lxml.html.HtmlElement] = set()
    for el in walk_root.iter():
        if el.tag not in REPORT_TAGS:
            continue
        if el in above or el in inside:
            result.captured_blocks += 1
            continue
        text = normalize_whitespace(el.text_content())
        if not text:
            continue
        # Only the outermost uncaptured block is a candidate; its nested blocks ride along.
        if any(ancestor in reported for ancestor in el.iterancestors()):
            continue
        present, missing = text_present(el, body_norm_folded)
        if present:
            # Visible, vetoable suppression — never a silent one.
            result.duplicates.append(f'{_describe(el)} "{text[:80]}"')
            continue
        result.drops.append(
            DropCandidate(
                tag=str(el.tag),
                description=_describe(el),
                text=text,
                chars=len(text),
                missing_segments=missing[:3],
            )
        )
        reported.add(el)
    return result


# --- the cross-article leak scan ---


def find_leaks(units_per_article: Sequence[Tuple[int, Sequence[str]]]) -> List[LeakCandidate]:
    """Body units repeated across at least half the articles — language-agnostic boilerplate.

    The sweep's drop side cannot see leaks (leaked text is *in* the body), but boilerplate
    repeats across articles while article text doesn't. Needs >= 3 articles to mean anything;
    below that it returns nothing and the driver says so.

    Articles without body text are excluded outright: counting them would raise the threshold
    that real boilerplate has to clear without contributing any unit that could clear it.
    """
    units_per_article = [(index, units) for index, units in units_per_article if units]
    n = len(units_per_article)
    if n < 3:
        return []
    threshold = max(2, (n + 1) // 2)
    occurrences: Dict[str, Tuple[str, List[int]]] = {}
    for index, units in units_per_article:
        per_article: Dict[str, str] = {}
        for unit in units:
            normalized = normalize_whitespace(unit)
            if len(normalized) >= MIN_LEAK_CHARS:
                per_article[normalized.casefold()] = normalized
        for key, display in per_article.items():
            occurrences.setdefault(key, (display, []))[1].append(index)
    leaks = [
        LeakCandidate(text=display, article_indices=indices)
        for display, indices in occurrences.values()
        if len(indices) >= threshold
    ]
    leaks.sort(key=lambda leak: (-len(leak.article_indices), leak.text))
    return leaks


# --- the pool-wide risk scan ---


@dataclass
class ArticleRisk:
    """How badly the parser handled one *pooled* article, measured from its own sweep result."""

    index: int  # position in the crawled pool
    tier: int  # 2 = parser produced nothing usable, 1 = real uncaptured text, 0 = nominal
    flags: List[str]  # what makes this article stand out; empty below tier 2
    uncommon_chars: int  # uncaptured text left once site chrome is discounted
    result: SweepResult

    @property
    def flagged(self) -> bool:
        return self.tier > 0

    @property
    def detail(self) -> str:
        """One line of evidence for the printout and the state file."""
        parts = list(self.flags)
        if self.uncommon_chars:
            parts.append(f"{self.uncommon_chars} uncaptured chars")
        return "; ".join(parts)


def rank_pool(swept: Sequence[Tuple[int, SweepResult, Sequence[str]]]) -> List[ArticleRisk]:
    """Rank a whole crawled pool by how badly the parser handled each article, worst first.

    Takes one `(pool index, sweep result, missing required attributes)` triple per article — the
    caller supplies the missing attributes, which keeps this free of fundus' `Article` and as
    unit-testable as the rest of the file.

    Ranking uncaptured characters raw would only rank *page chrome*, which is near-identical on
    every article of a publisher. Discounting whatever repeats across the pool leaves what is
    unusual about this article's extraction, which is the only part that says anything.
    """
    n = len(swept)
    articles_per_key: Dict[Tuple[str, str], int] = {}
    for _, result, _ in swept:
        for key in {drop.key for drop in result.drops}:  # a repeat *within* one article proves nothing
            articles_per_key[key] = articles_per_key.get(key, 0) + 1
    # Below three articles a "share of the pool" means nothing, so nothing is discounted.
    common: Set[Tuple[str, str]] = set()
    if n >= 3:
        threshold = max(2, math.ceil(COMMON_DROP_SHARE * n))
        common = {key for key, count in articles_per_key.items() if count >= threshold}

    risks: List[ArticleRisk] = []
    for index, result, missing in swept:
        # A sweep that could not run is a finding about this article - unless the reason is the
        # parser's own design, which is identical for every article and so ranks nothing.
        inapplicable = not result.applicable and result.reason != NO_PARAGRAPH_SELECTOR
        flags: List[str] = []
        if missing:
            flags.append("missing " + ", ".join(missing))
        if inapplicable:
            flags.append(result.reason)
        uncommon_chars = sum(drop.chars for drop in result.drops if drop.key not in common)
        risks.append(
            ArticleRisk(
                index=index,
                tier=2 if flags else (1 if uncommon_chars >= MIN_RISK_CHARS else 0),
                flags=flags,
                uncommon_chars=uncommon_chars,
                result=result,
            )
        )
    risks.sort(key=lambda risk: (-risk.tier, -risk.uncommon_chars, risk.index))
    return risks


def apply_risk_swaps(drawn: Sequence[int], risks: Sequence[ArticleRisk], budget: int) -> List[int]:
    """Let the scan's worst flagged articles claim up to `RISK_SWAP_SHARE` of the draw.

    `drawn` is the diverse ranking's pick (pool indices, most typical first); `risks` is
    `rank_pool`'s output and stays worst-first. Each flagged article not already drawn replaces
    the lowest-ranked pick that isn't itself flagged — never position 0, so the draw always keeps
    the pool's most typical article: the read's baseline, or, when the scan flags that one too,
    the finding that the failure is mainstream rather than an edge case.
    """
    drawn = list(drawn)
    risk_by_index = {risk.index: risk for risk in risks}
    swaps_left = int(budget * RISK_SWAP_SHARE)
    for risk in risks:  # worst first, so the swaps go to the worst articles that missed the draw
        if swaps_left <= 0 or not risk.flagged:
            break
        if risk.index in drawn:
            continue
        # Give up the least distinctive diverse pick that isn't itself flagged; never position 0.
        position = next((p for p in range(len(drawn) - 1, 0, -1) if not risk_by_index[drawn[p]].flagged), None)
        if position is None:
            break
        drawn[position] = risk.index
        swaps_left -= 1
    return drawn
