"""Selection primitives over a precomputed distance matrix: unsupervised clustering (auto-k)
and farthest-point sampling. These back the Sampler's two modes.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Union

import numpy as np
import numpy.typing as npt
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score

# Row/column indices into a distance matrix, however the caller happens to hold them: `layouts_by_size`
# hands back arrays, hand-written call sites pass lists.
Indices = Union[Sequence[int], npt.NDArray[np.int_]]


def medoid(distances: npt.NDArray[np.float64], members: Indices) -> int:
    """Index (into the full matrix) of the most central member — minimizes summed distance."""
    member_indices = np.asarray(members)
    sub = distances[np.ix_(member_indices, member_indices)]
    return int(member_indices[int(np.argmin(sub.sum(axis=1)))])


def farthest_first(distances: npt.NDArray[np.float64], n: int, pool: Optional[Indices] = None) -> List[int]:
    """Greedy farthest-point sampling over `pool` (default all), seeded at the pool's medoid.

    Returns up to n indices, each maximally far from those already chosen. Seeding at the medoid
    makes the first pick the most *representative* article, then each subsequent pick adds the most
    *different* one — "diverse but meaningful".
    """
    candidates = np.arange(len(distances)) if pool is None else np.asarray(pool)
    n = min(n, len(candidates))
    if n <= 0:
        return []
    chosen = [medoid(distances, candidates)]
    while len(chosen) < n:
        nearest = distances[np.ix_(candidates, np.asarray(chosen))].min(axis=1)
        nearest[np.isin(candidates, chosen)] = -1.0  # never re-pick
        chosen.append(int(candidates[int(np.argmax(nearest))]))
    return chosen


def auto_cluster(distances: npt.NDArray[np.float64], k_max: int) -> npt.NDArray[np.int_]:
    """Average-linkage agglomerative clustering; k chosen unsupervised by maximizing silhouette.

    Returns a layout label per article. For very small pools (<4) everything is one layout.
    """
    n = len(distances)
    if n < 4 or k_max < 2:
        return np.zeros(n, dtype=int)
    best_score, best_labels = -2.0, np.zeros(n, dtype=int)
    for k in range(2, min(k_max, n - 1) + 1):
        labels = AgglomerativeClustering(n_clusters=k, metric="precomputed", linkage="average").fit_predict(distances)
        score = float(silhouette_score(distances, labels, metric="precomputed"))
        if score > best_score:
            best_score, best_labels = score, labels
    return best_labels


def layouts_by_size(labels: npt.NDArray[np.int_]) -> List[npt.NDArray[np.int_]]:
    """Member indices per layout, largest layout first."""
    groups = [np.where(labels == label)[0] for label in set(labels.tolist())]
    groups.sort(key=len, reverse=True)
    return groups
