"""Driver for reviewing a Fundus publisher: crawl once, sweep, adjudicate, gate, report.

This is a *review aid*, not part of the shipped package. It owns the review's state
machine so the agent can't substitute "looks clean" for verification:

    crawl       crawl a candidate pool -> sweep all of it -> Tier-1 read + cache the worst/most diverse
    sweep       offline structural sweep of that same cache -> DROP / LEAK candidates with ids
    show        full detail for one candidate (text, articles, cached html paths)
    adjudicate  record the boilerplate-vs-body judgment for one candidate (the only judgment input)
    status      where the review stands; exit 0 only when nothing is pending
    payload     refuse while anything is un-adjudicated, else emit findings.json plus a
                review.json skeleton — the review to post, mechanical half prefilled (§5)

Both tiers and every re-run work the *same* crawled draw (PLAYBOOK.md §2): `crawl` is the
only networked step, everything else replays the cache. Re-sweeping (e.g. `--version V1`)
costs nothing and keeps existing adjudications — candidate ids are content-hashes.

Usage (any working directory; <skill>/ is this skill's directory):

    python <skill>/scripts/review.py crawl ca.NationalPost [--pool 100] [--review 10]
    python <skill>/scripts/review.py sweep ca.NationalPost [--version V1_1]
    python <skill>/scripts/review.py adjudicate ca.NationalPost D3f2a1c ok --note "cookie banner"
    python <skill>/scripts/review.py status ca.NationalPost
    python <skill>/scripts/review.py payload ca.NationalPost
"""

import argparse
import inspect
import io
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import lxml.etree
import lxml.html
from _store import (
    VERDICTS,
    blocker_candidates,
    body_units,
    candidate_id,
    candidates,
    default_cache_dir,
    load_state,
    missing_attributes,
    new_state,
    payload_gaps,
    pending_candidates,
    prepare_cache_dir,
    read_html,
    record_crawl_date,
    resolve_cache_dir,
    resolve_publisher,
    save_article,
    write_state,
)
from _sweep import (
    STRUCTURAL_TAGS,
    ArticleRisk,
    SweepResult,
    apply_risk_swaps,
    find_leaks,
    rank_pool,
    sweep_article,
    version_classes,
)

from fundus import Article, Crawler
from fundus.logging import set_log_level
from fundus.parser import ParserProxy

SCRIPT = Path(__file__).resolve()
RULE = "=" * 100

TEXT_CAP = 400  # stored/printed candidate text cap; `show` prints it in full from state
REVIEW_ARTICLES = 10  # articles actually reviewed (the draw), independent of the pool scanned


# --- small helpers ---


def _self_invocation(args: argparse.Namespace, command: str) -> str:
    """A copy-pasteable follow-up command with the resolved script path and cache dir."""
    cache_flag = f' --cache-dir "{args.cache_dir}"' if args.cache_dir else ""
    return f'python "{SCRIPT}" {command} {args.publisher}{cache_flag}'


def _require_state(cache_dir: Path, spec: str) -> Dict[str, Any]:
    state = load_state(cache_dir)
    if state is None:
        raise SystemExit(f"no review state in {cache_dir} - run `crawl {spec}` first.")
    return state


def _records_by_index(state: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    return {int(record["index"]): record for record in state["articles"]}


def _candidate_lines(state: Dict[str, Any]) -> List[str]:
    adjudications = state.get("adjudications") or {}
    lines = []
    for candidate in candidates(state):
        verdict = adjudications.get(candidate["id"], {}).get("verdict", "PENDING")
        marker = "  [STRUCTURAL]" if candidate.get("tag") in STRUCTURAL_TAGS else ""
        where = f"articles {candidate['articles']}"
        lines.append(
            f"  {candidate['id']}  [{verdict:>7}]  {candidate['kind']}: "
            f'{candidate.get("description", "")} "{candidate["text"][:90]}" ({where}){marker}'
        )
    return lines


# --- crawl ---


def _scan_pool(parser_proxy: ParserProxy, pool: List[Article]) -> List[ArticleRisk]:
    """Sweep *every* crawled article and rank the pool by how badly the parser handled it.

    The sweep is offline and the pool is already parsed, so this costs one lxml parse per article
    and no network. It is what lets the review say anything about the articles nobody read: the
    draw is ten, but the check behind "0 flagged" covers the whole pool.
    """
    swept: List[Tuple[int, SweepResult, List[str]]] = []
    for index, article in enumerate(pool):
        missing = missing_attributes(article)
        try:
            doc = lxml.html.document_fromstring(article.html.content)
        except (lxml.etree.ParserError, ValueError) as error:
            # An unparseable page is a finding about that page, not a reason to abandon the scan.
            swept.append((index, SweepResult(applicable=False, reason=f"html did not parse: {error}"), missing))
            continue
        version_cls = type(parser_proxy(article.html.crawl_date))
        units = body_units(article.body.serialize() if article.body is not None else None)
        swept.append((index, sweep_article(doc, version_cls.body_selectors(), units), missing))
    return rank_pool(swept)


def _select_for_review(
    pool: List[Article], risks: List[ArticleRisk], budget: int
) -> List[Tuple[Article, str, ArticleRisk]]:
    """Reduce the crawled pool to the `budget` articles worth a human read.

    Two rankings decide the draw, because they answer different questions. `diverse` ranks by
    *structure*: its first pick is the pool's most typical article and every later pick is the most
    different one left, so it covers the page shapes a publisher uses, rare ones included. The scan
    ranks by what the parser actually did — the part structure cannot see, since a class-name
    variant that breaks a selector leaves a structurally identical page. `apply_risk_swaps` (the
    policy, unit-tested in _sweep) then lets the scan's worst flagged articles claim their share
    of the diverse draw.
    """
    if not pool:
        return []
    from sampler import Sampler  # numpy / scikit-learn — only imported when we actually reduce

    # `diverse` hands back the articles themselves; map by identity to line them up with the scan.
    pool_index = {id(article): index for index, article in enumerate(pool)}
    drawn = [pool_index[id(s.article)] for s in Sampler().diverse(pool, n=min(budget, len(pool)))]
    drawn = apply_risk_swaps(drawn, risks, budget)

    risk_by_index = {risk.index: risk for risk in risks}
    return [
        (pool[index], "flagged" if risk_by_index[index].flagged else "diverse", risk_by_index[index]) for index in drawn
    ]


def _scan_summary(pool: List[Article], risks: List[ArticleRisk], cached: Dict[int, int]) -> Dict[str, Any]:
    """The scan as it lands in state.json: pool-wide counts plus one row per *pooled* article.

    Every article is recorded, not just the flagged ones — the unflagged rows are the evidence that
    the check covered the pool rather than the draw.
    """
    return {
        "pool": len(pool),
        "flagged": sum(1 for risk in risks if risk.flagged),
        "reviewed": len(cached),
        "reviewed_flagged": sum(1 for risk in risks if risk.flagged and risk.index in cached),
        # Cached article 1 is `diverse`'s first pick, the pool medoid, which the swap step never
        # touches — so a flag on it means the *mainstream* layout is broken, not an edge case.
        "medoid_flagged": any(risk.flagged and cached.get(risk.index) == 1 for risk in risks),
        "articles": [
            {
                "url": pool[risk.index].html.requested_url,
                "tier": risk.tier,
                "flags": risk.flags,
                "uncommon_chars": risk.uncommon_chars,
                "signatures": risk.signatures,
                "cached_index": cached.get(risk.index),
            }
            for risk in risks
        ],
    }


def cmd_crawl(args: argparse.Namespace) -> int:
    if args.verbose:
        # Fundus' handlers default to ERROR, so the two things a short crawl needs explaining —
        # articles skipped because the parser raised, and per-attribute extraction failures — are
        # invisible. Opt-in, because the redirect log fires per article and buries the Tier-1 read.
        set_log_level(logging.INFO)

    publisher = resolve_publisher(args.publisher)
    cache_dir = resolve_cache_dir(args.publisher, args.cache_dir)
    prepare_cache_dir(cache_dir)

    state = new_state(args.publisher, args.pool)
    write_state(cache_dir, state)

    pool: List[Article] = []
    risks: List[ArticleRisk] = []
    cached: Dict[int, int] = {}
    completed = False
    try:
        # The only networked step: draw a candidate pool, scan all of it, then read a subset.
        # Scanning and sampling both need the whole pool up front, so unlike the per-article cache
        # this buffers in memory — an interrupted crawl caches nothing and is simply re-run.
        # `only_complete=False`: fundus' default draw drops articles missing title/body/publishing_date,
        # which is exactly the parser failure a review must see. They reach the scan like any other.
        pool = list(Crawler(publisher).crawl(max_articles=args.pool, only_complete=False))
        risks = _scan_pool(publisher.parser, pool)
        selection = _select_for_review(pool, risks, args.review)

        cached = {risk.index: position for position, (_, _, risk) in enumerate(selection, start=1)}
        state["scan"] = _scan_summary(pool, risks, cached)
        for index, (article, role, risk) in enumerate(selection, start=1):
            state["articles"].append(save_article(cache_dir, index, article))
            write_state(cache_dir, state)

            # Tier-1 coherence view: read each body here for dangling sentences / boilerplate.
            print(RULE)
            print(f"[{index}] ({role}{': ' + risk.detail if risk.detail else ''}) {article.html.requested_url}")
            print(f"{article.title} | {article.authors} | {article.topics} | imgs: {len(article.images)}")
            if missing := missing_attributes(article):
                print(f"! missing {', '.join(missing)} - fundus' default crawl would have dropped this article.")
            print(str(article.body))
        completed = True
    finally:
        state["crawl"]["finished"] = time.time()
        state["crawl"]["completed"] = completed
        write_state(cache_dir, state)

    reviewing = len(state["articles"])
    flagged = [risk for risk in risks if risk.flagged]
    unreviewed = [risk for risk in flagged if risk.index not in cached]
    reviewed_flagged = len(flagged) - len(unreviewed)
    print(RULE)
    print(
        f"crawled and scanned {len(pool)} article(s): {len(flagged)} flagged; reviewing {reviewing} "
        f"({reviewed_flagged} flagged, {reviewing - reviewed_flagged} diverse) -> {cache_dir}"
    )
    if reviewing == 0:
        print("0 articles crawled - sources or parser likely broken; that is itself a blocker-level finding.")
        return 0
    if (state["scan"] or {}).get("medoid_flagged"):
        print("! the most typical article in the pool is flagged - a mainstream failure, not an edge case.")
    if unreviewed:
        # Expected, not a coverage gap: the draw is capped and the pool scan already covers these.
        # Grouped by class because that is the unit of judgment - the review owes one line per
        # class, not a read per article.
        classes: Dict[str, List[ArticleRisk]] = {}
        for risk in unreviewed:
            label = "; ".join(risk.flags) or (f"{risk.signatures[0]} dropped" if risk.signatures else "uncaptured text")
            classes.setdefault(label, []).append(risk)
        print(
            f"undrawn: {len(unreviewed)} flagged article(s) outside the draw - expected; the pool scan above\n"
            "         already covers them. Account for each class below in the review with one line;\n"
            "         re-crawling with a bigger --review needs a stated reason and the user's go-ahead."
        )
        for label, members in sorted(classes.items(), key=lambda item: -len(item[1])):
            print(f"    {len(members):>3}x  {label}  e.g. {pool[members[0].index].html.requested_url}")
        print("         (per-article rows, with flags and drop signatures, are in state.json under `scan`)")
    print(f"next (Tier 2): {_self_invocation(args, 'sweep')}")
    return 0


# --- sweep ---


def _aggregate_drops(per_article: List[Tuple[int, SweepResult]], spec: str) -> List[Dict[str, Any]]:
    """Merge identical-text drops across articles (nav/chrome repeats) into one candidate."""
    merged: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for index, result in per_article:
        for drop in result.drops:
            key = drop.key
            entry = merged.get(key)
            if entry is None:
                merged[key] = entry = {
                    "id": candidate_id("drop", spec, *key),
                    "kind": "drop",
                    "tag": drop.tag,
                    "description": drop.description,
                    "text": drop.text[:TEXT_CAP],
                    "chars": drop.chars,
                    "missing": drop.missing_segments,
                    "articles": [],
                }
            entry["articles"].append(index)
    return list(merged.values())


def cmd_sweep(args: argparse.Namespace) -> int:
    publisher = resolve_publisher(args.publisher)
    cache_dir = resolve_cache_dir(args.publisher, args.cache_dir)
    state = _require_state(cache_dir, args.publisher)

    parser_proxy = publisher.parser
    version_map = version_classes(parser_proxy)
    pinned_cls = None
    if args.version is not None:
        pinned_cls = version_map.get(args.version)
        if pinned_cls is None:
            raise SystemExit(f"no version {args.version!r}; available: {sorted(version_map)}")

    per_article: List[Tuple[int, SweepResult]] = []
    units_per_article: List[Tuple[int, List[str]]] = []
    not_applicable = 0
    for record in state["articles"]:
        index = int(record["index"])
        crawl_date = record_crawl_date(record)
        version_cls = pinned_cls or type(parser_proxy(crawl_date))
        doc = lxml.html.document_fromstring(read_html(cache_dir, record))
        units = body_units(record["body"])
        units_per_article.append((index, units))
        result = sweep_article(doc, version_cls.body_selectors(), units)
        per_article.append((index, result))

        print(RULE)
        print(f"[{index}] {record['url']}")
        print(f"     version={version_cls.__name__}  crawl_date={record['crawl_date']}")
        if not result.applicable:
            not_applicable += 1
            print(f"     sweep N/A ({result.reason}).")
            print("     MANUAL diff required for this article - walk the cached html by hand.")
            continue
        counts = result.counts
        print(
            f"     captured nodes: {counts['paragraph']} paragraph, {counts['summary']} summary, "
            f"{counts['subheadline']} subheadline | other captured blocks: {result.captured_blocks}"
        )
        print(f"     body container: {result.container}")
        if result.loose_scope:
            print(
                "     ! walking the WHOLE page (selectors share no tight ancestor) - "
                "expect chrome noise; adjudicate carefully."
            )
        for duplicate in result.duplicates[:12]:
            print(f"     duplicate (text already in body - verify, not a drop): {duplicate}")
        if len(result.duplicates) > 12:
            print(f"     ... and {len(result.duplicates) - 12} more duplicates")
        print(f"     uncaptured blocks with text: {len(result.drops)}")

    drop_candidates = _aggregate_drops(per_article, args.publisher)
    leaks = find_leaks(units_per_article)
    leak_candidates: List[Dict[str, Any]] = [
        {
            "id": candidate_id("leak", args.publisher, leak.text.casefold()),
            "kind": "leak",
            "text": leak.text[:TEXT_CAP],
            "articles": leak.article_indices,
        }
        for leak in leaks
    ]

    state["sweep"] = {
        "version": args.version,
        "swept_at": time.time(),
        "articles_swept": len(per_article),
        "not_applicable": not_applicable,
        "candidates": drop_candidates + leak_candidates,
    }
    write_state(cache_dir, state)

    print(RULE)
    print(
        f"swept {len(per_article)} article(s): {len(drop_candidates)} drop, {len(leak_candidates)} leak candidate(s)."
    )
    if len(state["articles"]) < 3:
        print("note: <3 articles cached, so the cross-article leak scan is inactive - scan bodies by hand.")
    if not_applicable:
        print(f"! {not_applicable} article(s) not sweepable - the manual diff there is on you.")
    for line in _candidate_lines(state):
        print(line)
    if state["sweep"]["candidates"]:
        print("adjudicate each candidate (`show <id>` for detail, cached html included):")
        print(f'  {_self_invocation(args, "adjudicate")} <id> ok|blocker --note "..."')
    print(f"then: {_self_invocation(args, 'status')}")
    return 0


# --- show / adjudicate ---


def _find_candidate(state: Dict[str, Any], candidate_ref: str) -> Dict[str, Any]:
    for candidate in candidates(state):
        if candidate["id"] == candidate_ref:
            return candidate
    known = ", ".join(c["id"] for c in candidates(state)) or "(none - run `sweep` first)"
    raise SystemExit(f"no candidate {candidate_ref!r}; known: {known}")


def cmd_show(args: argparse.Namespace) -> int:
    cache_dir = resolve_cache_dir(args.publisher, args.cache_dir)
    state = _require_state(cache_dir, args.publisher)
    candidate = _find_candidate(state, args.id)
    records = _records_by_index(state)

    print(f"{candidate['id']}  kind={candidate['kind']}  {candidate.get('description', '')}")
    print(f"text ({candidate.get('chars', len(candidate['text']))} chars):")
    print(f"  {candidate['text']}")
    for segment in candidate.get("missing") or []:
        print(f'  missing from body: "{segment[:120]}"')
    print("articles:")
    for index in candidate["articles"]:
        record = records.get(index)
        if record is not None:
            print(f"  [{index}] {record['url']}")
            print(f"       raw html: {cache_dir / str(record['html_file'])}")
    adjudication = (state.get("adjudications") or {}).get(candidate["id"])
    if adjudication:
        print(f"adjudicated: {adjudication['verdict']} - {adjudication['note']}")
    return 0


def cmd_adjudicate(args: argparse.Namespace) -> int:
    cache_dir = resolve_cache_dir(args.publisher, args.cache_dir)
    state = _require_state(cache_dir, args.publisher)
    candidate = _find_candidate(state, args.id)

    state.setdefault("adjudications", {})[candidate["id"]] = {
        "verdict": args.verdict,
        "note": args.note,
        "at": time.time(),
    }
    write_state(cache_dir, state)

    pending = pending_candidates(state)
    print(f"{candidate['id']} -> {args.verdict}: {args.note}")
    print(
        f"{len(pending)} candidate(s) still pending" + (f": {', '.join(c['id'] for c in pending)}" if pending else "")
    )
    return 0


# --- status / payload ---


def cmd_status(args: argparse.Namespace) -> int:
    cache_dir = resolve_cache_dir(args.publisher, args.cache_dir)
    state = _require_state(cache_dir, args.publisher)
    crawl, scan, sweep = state["crawl"], state.get("scan"), state.get("sweep")
    adjudications = state.get("adjudications") or {}

    print(f"publisher: {state['publisher']}")
    print(f"cache:     {cache_dir}")
    print(
        f"crawl:     {len(state['articles'])} reviewed (pool {crawl.get('pool', '?')}), "
        f"{'completed' if crawl.get('completed') else 'NOT completed (interrupted?)'}"
    )
    if scan is None:
        print("scan:      not run - this cache predates the pool scan; re-crawl to get it")
    else:
        print(
            f"scan:      {scan['pool']} scanned, {scan['flagged']} flagged, "
            f"{scan['reviewed_flagged']} of those in the draw"
        )
        print("draw:      skewed toward flagged articles by design; the rest of the pool is covered by the scan")
        if scan["flagged"] > scan["reviewed_flagged"]:
            print(
                f"           {scan['flagged'] - scan['reviewed_flagged']} flagged not in the draw "
                f"(expected; per-article rows under `scan` in state.json)"
            )
        if scan["medoid_flagged"]:
            print("!          the most typical article in the pool is flagged - a mainstream failure")
    if sweep is None:
        print("sweep:     not run")
    else:
        version = sweep["version"] or "by crawl date"
        print(f"sweep:     {sweep['articles_swept']} article(s), selectors {version}, N/A: {sweep['not_applicable']}")
        if sweep["articles_swept"] and sweep["articles_swept"] == sweep["not_applicable"]:
            # Zero candidates here means nothing was checkable, not that nothing was wrong - and the
            # gate opens on zero candidates.
            print("! no article was sweepable - the sweep verified nothing; the by-hand walk is the whole review")
        verdicts = [adjudications.get(c["id"], {}).get("verdict") for c in candidates(state)]
        print(
            f"candidates: {len(verdicts)} total - {verdicts.count('blocker')} blocker, "
            f"{verdicts.count('ok')} ok, {verdicts.count(None)} PENDING"
        )
        for line in _candidate_lines(state):
            print(line)

    print("still yours (not machine-checked): Tier-1 coherence read; layout coverage (story/opinion/")
    print("listicle/image-heavy); the over-capture scan beyond repeated boilerplate; image attributes.")

    gaps = payload_gaps(state)
    if gaps:
        print("gate: NOT READY")
        for gap in gaps:
            print(f"  - {gap}")
        return 1
    print("gate: READY - `payload` will emit findings.json")
    return 0


def _parser_source_path(parser_proxy: ParserProxy) -> str:
    """Repo-relative path of the parser's file — the diff file the comment stubs anchor to."""
    try:
        posix = Path(inspect.getfile(next(iter(parser_proxy)))).as_posix()
        return posix[posix.rindex("src/fundus/") :]
    except (StopIteration, TypeError, ValueError, OSError):
        return "<path of the parser file in the PR diff>"


def _review_skeleton(parser_path: str, findings: Dict[str, Any], blockers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The review to post, per PLAYBOOK §5, with everything the state knows prefilled.

    What's left is exactly the judgment half — every `<...>` placeholder. The `line` fields are
    deliberately non-integer strings: an unfilled stub makes the GitHub POST fail loudly instead
    of posting a template.
    """
    event = findings["event_suggestion"]
    scope_line = (
        f"`{findings['publisher']}`: read {findings['articles_cached']} of {findings['articles_scanned']} scanned "
        f"({findings['flagged_by_scan']} flagged, {findings['flagged_by_scan'] - findings['flagged_not_reviewed']} "
        f"in draw); layouts, over-capture, image attributes checked. <X> blockers + <Y> nits inline."
    )
    comments = [
        {
            "path": parser_path,
            "line": "<int: a diff line at the offending selector>",
            "side": "RIGHT",
            "body": (
                f"**Blocker — <one-line claim; your note: {blocker['note']}>.** "
                f'"…<the single most damning quote — `show {blocker["id"]}` prints the full text>…" '
                f"Fix: <one line naming the selector/change>. "
                f"[[1]]({blocker['urls'][0] if blocker['urls'] else '<article url>'})"
            ),
        }
        for blocker in blockers
    ]
    return {
        "commit_id": "<PR head SHA: gh pr view <PR> --json headRefOid -q .headRefOid>",
        "event": event,
        "body": "\n".join(
            [
                f"**{event}** — <what drove the verdict, one line>.",
                "",
                scope_line,
                "Not inline:",
                "- <one bullet per finding with no diff line to anchor to; delete the block if none>",
                "",
                "<open questions, if any; delete if none>",
            ]
        ),
        "comments": comments,
    }


def cmd_payload(args: argparse.Namespace) -> int:
    cache_dir = resolve_cache_dir(args.publisher, args.cache_dir)
    state = _require_state(cache_dir, args.publisher)

    gaps = payload_gaps(state)
    if gaps:
        print("refusing to emit findings - the review is not complete:")
        for gap in gaps:
            print(f"  - {gap}")
        return 2

    records = _records_by_index(state)
    adjudications = state.get("adjudications") or {}
    blockers = []
    for candidate in blocker_candidates(state):
        blockers.append(
            {
                "id": candidate["id"],
                "kind": candidate["kind"],
                "text": candidate["text"],
                "note": adjudications[candidate["id"]]["note"],
                "urls": [records[i]["url"] for i in candidate["articles"] if i in records],
            }
        )
    scan = state.get("scan") or {}
    findings = {
        "publisher": state["publisher"],
        "articles_cached": len(state["articles"]),
        "articles_scanned": scan.get("pool", 0),
        "flagged_by_scan": scan.get("flagged", 0),
        "flagged_not_reviewed": scan.get("flagged", 0) - scan.get("reviewed_flagged", 0),
        "selector_version": (state["sweep"] or {}).get("version") or "by crawl date",
        "not_applicable_articles": (state["sweep"] or {}).get("not_applicable", 0),
        "event_suggestion": "REQUEST_CHANGES" if blockers else "COMMENT",
        "blockers": blockers,
        "ok_candidates": sum(1 for c in candidates(state) if adjudications.get(c["id"], {}).get("verdict") == "ok"),
    }

    findings_file = cache_dir / "findings.json"
    findings_file.write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(findings, ensure_ascii=False, indent=2))
    print(RULE)

    review_file = cache_dir / "review.json"
    if review_file.exists():
        print(f"{review_file} already exists - keeping your edits (delete it and re-run to regenerate).")
    else:
        skeleton = _review_skeleton(_parser_source_path(resolve_publisher(args.publisher).parser), findings, blockers)
        review_file.write_text(json.dumps(skeleton, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"findings.json (the evidence) + review.json (the review, as a skeleton) -> {cache_dir}")

    print("review.json prefills the mechanical half; the judgment half is yours:")
    print("  - replace every <...> placeholder; delete template lines that don't apply")
    print("  - add inline comments for your Tier-1 / image / static-read findings, same shape")
    print("  - the event is suggested from adjudicated blockers only - your own findings can escalate")
    print("    it; your own PR -> COMMENT regardless; never APPROVE")
    print("  - a multi-publisher PR gets ONE review: fold the other publishers into this body/comments")
    print("show the filled review.json to the user, and once they approve:")
    print("  gh pr view <PR> --json headRefOid -q .headRefOid          # -> commit_id")
    print(f'  gh api repos/flairNLP/fundus/pulls/<PR>/reviews -X POST --input "{review_file}"')
    return 0


# --- entry point ---


def main() -> int:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")  # smart quotes survive on Windows

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add(name: str, help_text: str) -> argparse.ArgumentParser:
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("publisher", help="publisher spec, e.g. 'ca.NationalPost'")
        sub.add_argument(
            "--cache-dir", default=None, help=f"override the cache dir (default: {default_cache_dir('<spec>')})"
        )
        return sub

    crawl = add("crawl", "crawl a candidate pool, scan all of it, then Tier-1 read + cache a subset")
    crawl.add_argument("--pool", type=int, default=100, help="candidate articles to crawl and scan")
    crawl.add_argument("--review", type=int, default=REVIEW_ARTICLES, help="articles to cache and read from that pool")
    crawl.add_argument(
        "--verbose", action="store_true", help="surface fundus' INFO logs: why articles/attributes were skipped"
    )
    crawl.set_defaults(func=cmd_crawl)

    sweep = add("sweep", "offline structural sweep of the cached draw -> candidates")
    sweep.add_argument("--version", default=None, help="pin a version label (e.g. V1_1) instead of by crawl date")
    sweep.set_defaults(func=cmd_sweep)

    show = add("show", "full detail for one candidate")
    show.add_argument("id", help="candidate id, e.g. D3f2a1c")
    show.set_defaults(func=cmd_show)

    adjudicate = add("adjudicate", "record the judgment for one candidate")
    adjudicate.add_argument("id", help="candidate id, e.g. D3f2a1c")
    adjudicate.add_argument("verdict", choices=list(VERDICTS), help="ok = benign; blocker = real finding")
    adjudicate.add_argument("--note", required=True, help="one line of evidence/reasoning (lands in findings.json)")
    adjudicate.set_defaults(func=cmd_adjudicate)

    status = add("status", "where the review stands; exit 0 only when the gate is open")
    status.set_defaults(func=cmd_status)

    payload = add("payload", "emit findings.json - refuses while anything is pending")
    payload.set_defaults(func=cmd_payload)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
