"""Persistence for the publisher-review driver (`review.py`): one cache dir per publisher.

The cache dir holds the raw crawled bytes (`NN.html`) plus a single `state.json` that is
the source of truth for the whole review: crawl parameters, the per-article records, the
pool-wide scan, the sweep's candidates, and the agent's adjudications. Everything `review.py`
knows it knows from here, which is what makes the workflow crash-safe (state is rewritten after
every article) and gateable (`payload_gaps` can name exactly what is still missing).

Caches are keyed on the **commit under review** — the HEAD of the repo the parser is imported from.
Derived, not passed, so there is no flag to get wrong and every agent computes the same key. Two
consequences fall out of that choice rather than needing code: a review of a *different* commit
can never inherit these articles and adjudications, and when the PR author pushes a fix the old
cache simply stops being addressed, so adjudications made against superseded parser code can't be
replayed. `review.py done` removes the commit's caches; `crawl` prunes ones nobody cleaned up.

Layout (<tempdir>/fundus-review/<short-sha>/<cc>.<Class>/):

    d732ca85/
      ca.NationalPost/
        state.json      # crawl meta + article records + pool scan + candidates + adjudications
        01.html         # article 1's html.content, re-encoded UTF-8 (see `save_article`)
        findings.json   # `payload`: the adjudicated evidence
        review.json     # `payload`: the review to post, as a skeleton
      ca.TorontoStar/   # another publisher in the same review — its own crawl, sweep and gate
"""

import functools
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import fundus
from fundus import Article, PublisherCollection, Requires
from fundus.publishers.base_objects import Publisher

STATE_FILE = "state.json"
# What `payload` writes: the adjudicated evidence, and the review built from it.
FINDINGS_FILE = "findings.json"
REVIEW_FILE = "review.json"

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


def cache_root() -> Path:
    return Path(tempfile.gettempdir()) / "fundus-review"


@functools.lru_cache(maxsize=1)
def commit_id() -> str:
    """Short SHA of the repo the parser under review comes from, or "detached" if git can't say.

    Cached: it is constant within a process, and two `git` calls in one command could otherwise
    straddle a checkout and have the driver name a different commit than the one it acted on.

    Anchored to `fundus.__file__` (<root>/src/fundus/__init__.py), not the working directory: the
    cache is about the parser code being imported, and the driver runs from anywhere. Sanitised on
    the way out, because it builds directories that later get deleted.
    """
    root = Path(fundus.__file__).resolve().parents[2]
    try:
        git = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "detached"
    return (re.sub(r"[^A-Za-z0-9]", "", git.stdout.strip()) if git.returncode == 0 else "") or "detached"


def commit_cache_dir() -> Path:
    """Everything this commit's review wrote — the unit `done` tears down."""
    return cache_root() / commit_id()


def default_cache_dir(spec: str) -> Path:
    """Per-publisher location inside the commit's dir, so every subcommand agrees without a path."""
    return commit_cache_dir() / spec


def _assert_review_cache(cache_dir: Path, action: str) -> None:
    """Refuse to touch a directory that isn't ours: a non-empty dir with no `state.json` is
    somebody's files, not a review cache. An empty one is a crawl killed before its first write.

    Mostly matters for `remove_commit_cache`, which walks whatever the commit dir happens to hold;
    `prepare_cache_dir` only ever reaches a path this module built.
    """
    if any(cache_dir.iterdir()) and not (cache_dir / STATE_FILE).exists():
        raise SystemExit(
            f"refusing to {action} {cache_dir}: non-empty and no {STATE_FILE}, so it doesn't look "
            f"like a review cache. Remove it by hand if that is really what you want."
        )


def prepare_cache_dir(cache_dir: Path) -> None:
    """Wipe and recreate `cache_dir` for a fresh crawl — refusing anything that isn't a review cache."""
    if cache_dir.exists():
        _assert_review_cache(cache_dir, "wipe")
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)


def remove_commit_cache() -> List[str]:
    """Delete this commit's caches, returning the specs removed.

    Refuses if the dir holds anything that isn't a review cache, so a stray `done` can't take down
    real work. An *empty* child is fine to remove — that is a crawl killed before its first write,
    not somebody's files (same rule as `_assert_review_cache`).
    """
    commit_dir = commit_cache_dir()
    if not commit_dir.exists():
        return []
    children = sorted(commit_dir.iterdir())
    for child in children:
        if child.is_dir():
            _assert_review_cache(child, "remove")
        else:
            raise SystemExit(f"refusing to remove {commit_dir}: it holds the file {child.name!r}.")
    # Every child, not just the ones with state: `rmtree` takes the lot, so reporting only the
    # stateful ones would tell the reviewer "nothing to remove" right after removing something.
    removed = [child.name for child in children]
    try:
        shutil.rmtree(commit_dir)
    except OSError as error:  # a file still open (an editor, a pager) - fail like the rest of the module
        raise SystemExit(f"could not remove {commit_dir}: {error}")
    return removed


def prune_stale_caches(max_age_days: int = 7) -> List[str]:
    """Drop caches from reviews that ended without `done`, so abandoned ones can't pile up.

    Only touches dirs that look like review caches throughout, and never this commit's own.
    Best-effort: a dir that vanishes underneath us (or that we may not delete) is skipped.
    """
    root, mine = cache_root(), commit_cache_dir()
    if not root.exists():
        return []
    cutoff = time.time() - max_age_days * 86400
    pruned: List[str] = []
    for cached in sorted(root.iterdir()):
        # The whole body, not just the rmtree: another review pruning or crawling concurrently can
        # delete `cached` between any two of these calls, and housekeeping must never be the reason
        # a crawl dies before it crawls.
        try:
            if not cached.is_dir() or cached == mine or cached.stat().st_mtime > cutoff:
                continue
            children = list(cached.iterdir())
            if any(not c.is_dir() or (any(c.iterdir()) and not (c / STATE_FILE).exists()) for c in children):
                continue  # not ours throughout — leave it alone
            shutil.rmtree(cached)
        except OSError:
            continue  # vanished underneath us, or not ours to delete
        pruned.append(cached.name)
    return pruned


# --- state file ---


def new_state(spec: str, pr: Optional[str], pool: int, impersonate: Optional[str]) -> Dict[str, Any]:
    return {
        "publisher": spec,
        # Metadata, not identity: the commit owns the path. Recorded so `status` says what this
        # cache is about and `payload` can fill in the `gh` commands.
        "pr": pr,
        "crawl": {
            "pool": pool,
            "started": time.time(),
            "finished": None,
            "completed": False,
            # The declared browser profile, or None: the fingerprint the draw came back through.
            "impersonate": impersonate,
        },
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
    """Write one article's html and return its state record.

    The cache stores `html.content` — already decoded by fundus — re-encoded as UTF-8; the
    original response bytes are gone, so on a legacy-encoded site the file's `<meta charset>`
    no longer matches its bytes. Readers must decode UTF-8 themselves (`read_html` does; so
    does the playbook's by-hand snippet) rather than let lxml sniff the charset from bytes.
    `write_bytes` because text mode would newline-translate on Windows (\\r\\n -> \\r\\r\\n).
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
