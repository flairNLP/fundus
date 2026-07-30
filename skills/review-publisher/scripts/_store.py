"""Persistence for the publisher-review driver (`review.py`): one cache dir per review.

The cache dir holds the raw crawled bytes (`NN.html`) plus a single `state.json` that is
the source of truth for the whole review: crawl parameters, the per-article records, the
pool-wide scan, the sweep's candidates, and the agent's adjudications. Everything `review.py`
knows it knows from here, which is what makes the workflow crash-safe (state is rewritten after
every article) and gateable (`payload_gaps` can name exactly what is still missing).

Layout of a cache dir (default: <tempdir>/fundus-review/<cc>.<Class>/):

    state.json   # crawl meta + article records + pool scan + sweep candidates + adjudications
    01.html      # raw html.content bytes for article 1 (exact crawled bytes)
    02.html      # ...
"""

import hashlib
import json
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fundus import Article, PublisherCollection, Requires
from fundus.publishers.base_objects import Publisher

STATE_FILE = "state.json"

# Adjudication verdicts: "ok" = benign (boilerplate outside the body for a drop candidate,
# legitimately repeated content for a leak candidate); "blocker" = a real finding.
VERDICTS = ("ok", "blocker")

# The completeness filter fundus' `crawl` applies by default. The review crawls without it (see
# `cmd_crawl`) so the broken articles reach the sampler; this re-applies it only to *name* what an
# article is missing, so the Tier-1 read says "missing: body" instead of printing a bare `None`.
REQUIRED_ATTRIBUTES = ("title", "body", "publishing_date")
_completeness_filter = Requires(*REQUIRED_ATTRIBUTES)


# --- publisher + path resolution ---


def resolve_publisher(spec: str) -> Publisher:
    """`ca.NationalPost` -> the Publisher object on PublisherCollection."""
    try:
        cc, name = spec.split(".", 1)
    except ValueError:
        raise SystemExit(f"publisher spec must be '<cc>.<Class>', got {spec!r}")
    region = getattr(PublisherCollection, cc, None)
    if region is None:
        raise SystemExit(f"no such country code on PublisherCollection: {cc!r}")
    publisher = getattr(region, name, None)
    if not isinstance(publisher, Publisher):
        raise SystemExit(f"no publisher {name!r} under PublisherCollection.{cc}")
    return publisher


def default_cache_dir(spec: str) -> Path:
    """Predictable per-publisher temp location, so every subcommand agrees without a path."""
    return Path(tempfile.gettempdir()) / "fundus-review" / spec


def resolve_cache_dir(spec: str, provided: Optional[str]) -> Path:
    return Path(provided) if provided else default_cache_dir(spec)


def prepare_cache_dir(cache_dir: Path) -> None:
    """Wipe and recreate `cache_dir` for a fresh crawl — refusing anything that isn't a review cache.

    The guard is what makes `--cache-dir` safe: a non-empty directory without a
    `state.json` (someone's working tree, a typo'd path) is never deleted.
    """
    if cache_dir.exists():
        if any(cache_dir.iterdir()) and not (cache_dir / STATE_FILE).exists():
            raise SystemExit(
                f"refusing to wipe {cache_dir}: non-empty and no {STATE_FILE}, so it doesn't look like "
                f"a review cache. Use a valid or not-yet-existing --cache-dir."
            )
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)


# --- state file ---


def new_state(spec: str, pool: int) -> Dict[str, Any]:
    return {
        "publisher": spec,
        "crawl": {"pool": pool, "started": time.time(), "finished": None, "completed": False},
        "articles": [],
        "scan": None,
        "sweep": None,
        "adjudications": {},
    }


def write_state(cache_dir: Path, state: Dict[str, Any]) -> None:
    """Atomically (write-then-replace) persist the state, so a crash never corrupts it."""
    tmp = cache_dir / (STATE_FILE + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(cache_dir / STATE_FILE)


def load_state(cache_dir: Path) -> Optional[Dict[str, Any]]:
    state_file = cache_dir / STATE_FILE
    if not state_file.exists():
        return None
    state: Dict[str, Any] = json.loads(state_file.read_text(encoding="utf-8"))
    return state


# --- article records ---


def html_filename(index: int) -> str:
    return f"{index:02d}.html"


def missing_attributes(article: Article) -> List[str]:
    """The required attributes fundus' default extraction filter would have rejected `article` for.

    Delegates the truthiness call to fundus' own `Requires` rather than re-implementing it: an
    `ArticleBody` is falsy when it holds no section with paragraphs, so a summary-only body counts
    as missing here exactly as it does in the default draw.
    """
    rejected = _completeness_filter({name: getattr(article, name) for name in REQUIRED_ATTRIBUTES})
    return [name for name in REQUIRED_ATTRIBUTES if name in rejected.missing_attributes]


def save_article(cache_dir: Path, index: int, article: Article) -> Dict[str, Any]:
    """Write one article's raw bytes and return its state record.

    `write_bytes` keeps the cached file the *exact* crawled bytes — text mode would
    newline-translate on Windows (\\r\\n -> \\r\\r\\n on disk).
    """
    (cache_dir / html_filename(index)).write_bytes(article.html.content.encode("utf-8"))
    body = article.body
    return {
        "index": index,
        "url": article.html.requested_url,
        "crawl_date": article.html.crawl_date.isoformat(),
        "title": article.title,
        "authors": article.authors,
        "topics": article.topics,
        "images": len(article.images),
        "body": body.serialize() if body is not None else None,
        "html_file": html_filename(index),
    }


def read_html(cache_dir: Path, record: Dict[str, Any]) -> str:
    return (cache_dir / str(record["html_file"])).read_bytes().decode("utf-8")


def record_crawl_date(record: Dict[str, Any]) -> datetime:
    return datetime.fromisoformat(str(record["crawl_date"]))


def body_units(serialized_body: Optional[Dict[str, Any]]) -> List[str]:
    """Flatten a serialized ArticleBody into its text units (summary, headlines, paragraphs)."""
    if not serialized_body:
        return []
    units: List[str] = list(serialized_body.get("summary") or [])
    for section in serialized_body.get("sections") or []:
        units.extend(section.get("headline") or [])
        units.extend(section.get("paragraphs") or [])
    return units


# --- candidates + adjudication gate ---


def candidate_id(kind: str, *key_parts: str) -> str:
    """Stable short id from the candidate's content, so re-sweeps keep existing adjudications."""
    digest = hashlib.sha1("\x1f".join(key_parts).encode("utf-8")).hexdigest()[:6]
    return f"{kind[0].upper()}{digest}"


def candidates(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    sweep = state.get("sweep") or {}
    result: List[Dict[str, Any]] = sweep.get("candidates") or []
    return result


def pending_candidates(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    adjudicated = state.get("adjudications") or {}
    return [c for c in candidates(state) if c["id"] not in adjudicated]


def blocker_candidates(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    adjudications = state.get("adjudications") or {}
    return [c for c in candidates(state) if adjudications.get(c["id"], {}).get("verdict") == "blocker"]


def payload_gaps(state: Dict[str, Any]) -> List[str]:
    """Every reason the review is not ready to be written up; empty means the gate is open."""
    gaps: List[str] = []
    crawl = state.get("crawl") or {}
    if not crawl.get("completed"):
        gaps.append("the crawl did not complete (interrupted?) — re-run `crawl`")
    if not state.get("articles"):
        gaps.append("no articles in the cache — 0 crawled is itself a blocker-level finding")
    sweep = state.get("sweep")
    if not sweep:
        gaps.append("no sweep recorded — run `sweep`")
    else:
        if crawl.get("finished") and sweep.get("swept_at", 0) < crawl["finished"]:
            gaps.append("the sweep predates the last crawl — re-run `sweep`")
        pending = pending_candidates(state)
        if pending:
            ids = ", ".join(c["id"] for c in pending[:15]) + (", ..." if len(pending) > 15 else "")
            gaps.append(f"{len(pending)} candidate(s) un-adjudicated: {ids}")
    return gaps
