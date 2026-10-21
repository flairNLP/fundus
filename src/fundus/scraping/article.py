"""Deprecated alias of :mod:`fundus.scraping.publication`.

TODO: Remove this module in release 1.0.0.
"""

import warnings

from fundus.scraping.publication import Article

warnings.warn(
    "'fundus.scraping.article' is deprecated and will be removed in release 1.0.0. "
    "Import 'Article' from 'fundus.scraping.publication' (or 'fundus') instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["Article"]
