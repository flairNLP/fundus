"""Structural sampler for Fundus publishers — reduce a crawled pool to layout-diverse articles.

Helper for the review-publisher skill: it lets `review.py crawl` review one article per distinct
layout instead of the first N, for full layout coverage at minimal cost. Run from `scripts/`, so:

    from sampler import Sampler

    sampler = Sampler()
    diverse = sampler.diverse(articles, n=8)        # mode 1: the n most diverse
    layouts = sampler.per_layout(articles, k=1)     # mode 2: one per distinct layout

    for s in layouts:
        print(s.layout, s.is_representative, s.url)
"""

from .sampler import SampledArticle, Sampler, sample_diverse, sample_per_layout

__all__ = ["Sampler", "SampledArticle", "sample_diverse", "sample_per_layout"]
