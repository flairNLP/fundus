"""Featurization: raw article HTML -> a publisher-agnostic structural fingerprint, and the
pairwise distance matrix over a pool of them.

The design choices here are the ones the clustering study landed on:

* **Body isolation by text density, not tags.** A new publisher has no parser, so we can't ask
  where its body is. `content_region` finds the tightest subtree holding most of the body
  text, after stripping link-heavy boilerplate (nav/related/comment rails). Pure text + link
  ratios over tag-agnostic text blocks — no tag/class/parser assumptions — so it generalizes
  across publishers.
* **`tagpath` representation.** Each page becomes the multiset of its root-to-node tag paths;
  TF-IDF over the pool then zeroes out the chrome that's constant across a publisher's articles
  and amplifies the body structures that vary. Robust even when the body isolation is imperfect.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import lxml.html
import numpy as np
from lxml.html import HtmlElement
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_distances

# Tags carrying no layout meaning (or only noise) — skipped when building tag paths.
_SKIP_TAGS = frozenset({"script", "style", "noscript", "template", "svg", "path", "br", "wbr"})

DEFAULT_TEXT_SHARE = 0.7  # tightest container holding >= this share of body text (validated)
_MAX_LINK_DENSITY = 0.5  # a block whose text is > this fraction inside <a> is boilerplate
_MIN_BLOCK_TEXT = 40  # ignore tiny blocks when stripping boilerplate / protecting prose


# --- body isolation ---


def _link_density(el: HtmlElement) -> float:
    total = len((el.text_content() or "").strip())
    if not total:
        return 0.0
    return sum(len(a.text_content() or "") for a in el.iter("a")) / total


def _direct_text_len(el: HtmlElement) -> int:
    """Length of the text ``el`` owns directly — its own ``text`` plus its children's ``tail`` — but
    not text nested deeper. Keeps text blocks disjoint so summing their lengths never double-counts
    the same characters up the tree."""
    parts = [el.text or ""] + [child.tail or "" for child in el]
    return len("".join(parts).strip())


def _text_blocks(root: HtmlElement) -> Dict[HtmlElement, int]:
    """The prose leaves keyed to their direct-text length: every element under ``root`` that owns a
    substantial run of direct text. Tag-agnostic — replaces the old ``<p>``-only assumption so that
    ``<div>``/``<span>``-based bodies are found too — while link labels (text inside ``<a>``) stay
    below threshold and so never register as prose."""
    blocks: Dict[HtmlElement, int] = {}
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        length = _direct_text_len(el)
        if length >= _MIN_BLOCK_TEXT:
            blocks[el] = length
    return blocks


def _strip_boilerplate(doc: HtmlElement) -> None:
    """Drop link-heavy blocks in place; never drop a block that still holds real prose."""
    for el in list(doc.iter("div", "section", "ul", "ol", "nav", "aside", "header", "footer")):
        if el is doc or el.getroottree().getroot() is not doc:  # root, or removed with an ancestor
            continue
        if (
            len((el.text_content() or "").strip()) >= _MIN_BLOCK_TEXT
            and _link_density(el) > _MAX_LINK_DENSITY
            and sum(_text_blocks(el).values()) < _MIN_BLOCK_TEXT
        ):
            el.drop_tree()


def content_region(doc: HtmlElement, text_share: float = DEFAULT_TEXT_SHARE) -> HtmlElement:
    """The article body subtree, found by text density after boilerplate removal."""
    _strip_boilerplate(doc)
    blocks = _text_blocks(doc)
    if not blocks:
        return doc
    total = sum(blocks.values())
    scores: Dict[HtmlElement, int] = {}
    for block, length in blocks.items():
        for ancestor in block.iterancestors():
            scores[ancestor] = scores.get(ancestor, 0) + length
    candidates = [el for el, score in scores.items() if score >= text_share * total]
    if not candidates:
        return doc
    return min(candidates, key=lambda el: sum(1 for _ in el.iter()))


# --- tag-path fingerprint ---


def tag_paths(region: HtmlElement, max_path_len: Optional[int] = None) -> List[str]:
    """One ``a/b/c`` root-to-node path per element in the region (noise tags skipped)."""
    paths: List[str] = []

    def walk(el: HtmlElement, ancestry: List[str]) -> None:
        if not isinstance(el.tag, str) or el.tag in _SKIP_TAGS:
            return
        ancestry = ancestry + [el.tag]
        kept = ancestry if max_path_len is None else ancestry[-max_path_len:]
        paths.append("/".join(kept))
        for child in el:
            walk(child, ancestry)

    walk(region, [])
    return paths


def fingerprint(html: str, text_share: float = DEFAULT_TEXT_SHARE, max_path_len: Optional[int] = None) -> List[str]:
    """Tag-path multiset of one article's body region — the unit the distance is computed over."""
    doc = lxml.html.document_fromstring(html)
    return tag_paths(content_region(doc, text_share), max_path_len)


# --- distance ---


def distance_matrix(fingerprints: Sequence[List[str]]) -> np.ndarray:
    """Symmetric (m, m) tagpath TF-IDF cosine distances; IDF suppresses the shared site chrome."""
    vectorizer = TfidfVectorizer(analyzer=lambda paths: paths, norm="l2", sublinear_tf=True)
    matrix = vectorizer.fit_transform(list(fingerprints))
    distances: np.ndarray = cosine_distances(matrix)
    np.fill_diagonal(distances, 0.0)
    return np.asarray(distances, dtype=float)
