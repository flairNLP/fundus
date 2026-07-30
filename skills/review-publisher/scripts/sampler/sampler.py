"""Structural sampler for Fundus publishers.

Given an already-crawled pool of articles, reduce it to a small set that maximizes *layout*
coverage. Two modes:

    Sampler().diverse(articles, n=8)           # mode 1: the n most diverse/representative articles
    Sampler().per_layout(articles, k=1)         # mode 2: k representatives from every distinct layout

The pipeline is fully publisher-agnostic — no parser, no body selector, no per-site rules:

    isolate body by text density -> tagpath TF-IDF distance -> select

Mode 1 is farthest-point sampling (fixed size n). Mode 2 clusters the pool into layouts
(unsupervised, k discovered from the data) and takes k per layout, so the output size reflects how
many distinct layouts the publisher actually has.

Dependencies beyond Fundus: numpy, scikit-learn, lxml (see the skill's requirements.txt, installed
by skills/install.py). A helper for the review-publisher skill, not part of the shipped package.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Union

import numpy as np

from fundus import Article
from fundus.publishers.base_objects import Publisher

from ._features import DEFAULT_TEXT_SHARE, distance_matrix, fingerprint
from ._select import auto_cluster, farthest_first, layouts_by_size

logger = logging.getLogger(__name__)

# A publisher to crawl, or an already-crawled pool of articles (handy for tests / re-use).
Source = Union[Publisher, Iterable[Article]]


@dataclass(frozen=True)
class SampledArticle:
    """One selected article plus where it sits in the sample."""

    article: Article
    layout: int  # layout/cluster id (mode 2); in mode 1 each pick is its own layout
    rank: int  # selection order within the returned list
    is_representative: bool  # the layout's primary representative (medoid) vs an extra per-layout pick

    @property
    def url(self) -> str:
        return self.article.html.requested_url


class Sampler:
    """Reduce a crawled pool of articles to a layout-diverse sample.

    Parameters
    ----------
    text_share     : body-isolation tightness for the density finder (0.7 validated; <0.9).
    k_max          : cap on the number of layouts the clustering may find (mode 2).
    max_path_len   : optionally coarsen tag paths to the last m tags (None = full path).
    """

    def __init__(
        self,
        *,
        text_share: float = DEFAULT_TEXT_SHARE,
        k_max: int = 12,
        max_path_len: Union[int, None] = None,
    ) -> None:
        self.text_share = text_share
        self.k_max = k_max
        self.max_path_len = max_path_len

    # --- public API ---

    def diverse(self, articles: List[Article], n: int) -> List[SampledArticle]:
        """Mode 1 — the n most diverse yet representative articles (farthest-point sampling)."""
        if n < 1:
            raise ValueError("n must be >= 1")
        distances = self._compute_distance_matrix(articles)
        if not articles:
            return []
        order = farthest_first(distances, n)
        return [
            SampledArticle(article=articles[idx], layout=rank, rank=rank, is_representative=True)
            for rank, idx in enumerate(order)
        ]

    def per_layout(self, articles: List[Article], k: int = 1) -> List[SampledArticle]:
        """Mode 2 — k representatives from every distinct layout the publisher uses.

        The number of layouts is discovered unsupervised; the first pick per layout is its medoid
        (most typical), any extra picks are the most different members within that layout.
        """
        if k < 1:
            raise ValueError("k must be >= 1")
        if not articles:
            return []

        distances = self._compute_distance_matrix(articles)

        labels = auto_cluster(distances, min(self.k_max, len(articles) - 1))

        sampled: List[SampledArticle] = []
        for layout_id, members in enumerate(layouts_by_size(labels)):
            picks = farthest_first(distances, k, pool=members)  # medoid first, then farthest-within
            for within_rank, idx in enumerate(picks):
                sampled.append(
                    SampledArticle(
                        article=articles[idx],
                        layout=layout_id,
                        rank=len(sampled),
                        is_representative=(within_rank == 0),
                    )
                )
        return sampled

    # --- internals ---

    def _compute_distance_matrix(self, articles: List[Article]) -> np.ndarray:
        """Fingerprint each article's body, and build the distance matrix."""
        fingerprints = [fingerprint(a.html.content, self.text_share, self.max_path_len) for a in articles]
        return distance_matrix(fingerprints)


# --- module-level convenience wrappers ---


def sample_diverse(articles: List[Article], n: int, **kwargs: object) -> List[SampledArticle]:
    """Shortcut for `Sampler(**kwargs).diverse(source, n)`."""
    return Sampler(**kwargs).diverse(articles, n)  # type: ignore[arg-type]


def sample_per_layout(articles: List[Article], k: int = 1, **kwargs: object) -> List[SampledArticle]:
    """Shortcut for `Sampler(**kwargs).per_layout(source, k)`."""
    return Sampler(**kwargs).per_layout(articles, k)  # type: ignore[arg-type]
