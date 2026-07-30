# How to Review a Publisher PR

> **Audience: AI coding agents.** Operational playbook — also the source doc behind the
> `review-publisher` skill — for PRs that **add a new publisher** or **add/change a parser version**.
> You're reviewing the fruits of [`how_to_add_a_publisher.md`](/docs/how_to_add_a_publisher.md);
> doc links here are repo-root-relative.

All mechanics run through one driver (`<skill>` is the skill directory SKILL.md told you):

    python "<skill>/scripts/review.py" {crawl,sweep,show,adjudicate,status,payload} <cc>.<Class>

The driver owns the bookkeeping and prints its own next steps and warnings — trust that output, and
**act on its `!` lines rather than just acknowledging them**. What it never does is judge; this
playbook is about the judgment calls that stay yours.

**Scope: the PR's diff, not the whole publisher.** On a version bump, read the new version and its
delta only. **A multi-publisher PR is N independent reviews** — each publisher gets its own crawl,
sweep, and READY `status`, and a blocker on one never lightens the checks on another.

## What you're protecting

> **The extracted `ArticleBody` must mirror the real article — no missing content, no extra content.**

Fundus maps extracted text back to the source HTML for annotation, so a dropped paragraph or a leaked
photo caption corrupts that mapping. Over-capture is a blocker, not a nit.

## Rules

- **Don't run `pytest`/`mypy`/`ruff` locally — CI covers them.** Your value-add is correctness on
  **live** articles; the unit test freezes one HTML snapshot and proves nothing about today's site.
- **Cite everything**: the verbatim dropped/leaked text, the article URL, the offending selector.
  Adjudication notes land in `findings.json` verbatim — write them as evidence lines.
- **Scratch stays out of the repo** — use the cache dir the driver prints, or any OS temp dir.
- **Never truncate driver output** (no `[:N]`, no capped pipes): a cut-off crawl reads clean on
  articles you never saw.

## Inputs

- **The PR number**, and whether it's **your own** PR (changes the event — §4). If the user didn't
  name one: `gh pr view --json number,title,author` reads the current branch's PR — show and confirm
  it; if the branch has none, ask. Never guess. (`author` also settles the own-PR question.)
- The publisher(s) as `PublisherCollection.<cc>.<Class>` and the parser version(s) touched.

## 1. Static read

```bash
gh pr checkout <PR_NUMBER>
gh pr diff <PR_NUMBER>
```

- `@attribute` return types match [`attribute_guidelines.md`](/docs/attribute_guidelines.md).
- **`validate=False` attributes are checked by nobody but you** — CI type-checks validated
  attributes only. Read their logic and return values by hand.
- **`free_access`**: a publisher with a subscription model must implement it (off
  `isAccessibleForFree` in the `ld+json`). Missing or wrong on a premium publisher is a blocker;
  a fully free publisher needs nothing here.
- **`VALID_UNTIL` is not inherited** — every `BaseParser` subclass defaults to `date.max`. A new
  version for a layout change means the *previous* version gets an explicit `VALID_UNTIL` (the day
  before the change) and the newest leaves it unset. (Subclassing another publisher's version and
  leaving it unset is the intended `date.max`.)
- **Version bump fits the change**: selector-only fix → minor (`V1_1(V1)`); new or substantially
  changed attributes → major (`V2`). Flag a mismatch in either direction.
- **Changes to `parser/utility.py`** (`generic_topic_parsing`, `apply_result_filter`,
  `image_extraction`, …) affect every publisher — check the call sites.

## 2. Crawl live articles and verify the body

```bash
python "<skill>/scripts/review.py" crawl <cc>.<Class>                         # pool 100 -> read 10
python "<skill>/scripts/review.py" crawl <cc>.<Class> --pool 200 --review 16  # widen either half
```

**One live crawl per publisher; every later step replays its cache.** The crawl draws a candidate
pool (`--pool`), sweeps *all* of it offline, then caches the `--review` articles worth reading and
prints each one's Tier-1 view. The draw is **deliberately skewed toward flagged articles** — "all ten
read fine" is a weaker claim than the pool-wide scan counts, which you carry into the review as the
evidence about the articles nobody read. An interrupted crawl caches nothing; just re-run it.

- **Two crawl warnings demand action, not acknowledgement**: flagged articles that didn't fit the
  draw (raise `--review` or read their printed urls by hand), and a flagged *most-typical* article —
  a mainstream failure, which should lead the review.
- **The draw is unfiltered** (`only_complete=False`): articles missing
  `title`/`body`/`publishing_date` — exactly what a broken parser produces — reach the scan and
  print as `! missing …`. Treat as blocker-level unless the page genuinely isn't an article (video
  stub, liveblog, photo gallery); say which in the review.
- **Layout coverage is yours**: the draw should span a straight news piece, an opinion/column, a
  listicle/bullet-list piece, and an image-heavy one. If a layout you know exists is missing, widen
  `--pool` and re-crawl — don't ask the user for numbers. Publisher too small or uniform for all
  four → note that in the review.
- **Far fewer articles than `--pool`?** Re-run with `--verbose` to surface parser-raise skips and
  per-attribute failures. **0 articles after a fair attempt is itself a blocker-level finding** —
  report it, don't stall. Inspect via the cached html (`show` prints paths); many publishers block
  generic fetchers, so never fetch manually with `urllib`/`requests`.

### Tier 1 — coherence read (every cached article, from the crawl output)

Each body should read like the article: no dangling sentences, no abrupt jumps ("…fell into either
of two groups:" followed by nothing), no boilerplate (newsletter sign-ups, "Read More" teasers,
photo captions) mixed in. Eyeball `title`/`authors`/`topics` for emptiness or junk (UUIDs, section
names, the domain, `Category:` prefixes). Note every article that trips a signal.

Coherence has one blind spot: a paragraph dropped mid-body leaves no seam — the text still flows.
Tier 2 exists for exactly that.

### Tier 2 — sweep, then adjudicate every candidate (hard gate, every publisher)

```bash
python "<skill>/scripts/review.py" sweep <cc>.<Class>                 # same cache, no network
python "<skill>/scripts/review.py" sweep <cc>.<Class> --version V1_1  # pin a legacy version; re-runs free
```

The sweep applies the version's real body selectors to each cached article and emits candidates with
ids. **A candidate is a question, not a verdict** — the answer depends on the kind and tag:

- **DROP** — a block in the body container whose text is absent from the extracted body:
  - `ul`/`ol`/`dl`/`pre`, `<p>`, `<h*>` — prose the selector should have caught. Blocker unless
    the text is page chrome.
  - `blockquote` — a pull-quote restating a paragraph that *is* in the body → `ok`; quoted source
    material appearing nowhere else → blocker.
  - `table` — Fundus can't represent tabular content, so a dropped data table is normally `ok`;
    blocker only when the element is layout and the missing text is ordinary prose.
- **LEAK** — a body unit repeated across half the cached articles: the signature of boilerplate
  *inside* the body (newsletter pitches, teasers, bios repeat; article text doesn't).

```bash
python "<skill>/scripts/review.py" show <cc>.<Class> <id>      # full text + cached html paths
python "<skill>/scripts/review.py" adjudicate <cc>.<Class> <id> ok --note "site-wide cookie banner"
python "<skill>/scripts/review.py" adjudicate <cc>.<Class> <id> blocker --note "<ul> of match results dropped; <url>"
```

`ok` = benign; `blocker` = real finding, with the note as its evidence line. Adjudicate from the
**cached** html (paths in `show`) so there's no "site changed" ambiguity. The duplicates the sweep
prints as suppressed are vetoable, not authoritative — skim them.

Still on you, sweep or no sweep:

- **One-off over-capture** — the LEAK scan only catches *recurring* boilerplate. A leaked caption or
  "Related:" line in a single body never repeats; on the articles you read, check for anything that
  isn't article content.
- **N/A articles** — a version without a `_paragraph_selector`, or an empty extracted body (itself
  the finding). The sweep reports these with the reason; walk the cached html by hand:

  ```python
  from pathlib import Path
  from lxml import html as lhtml
  # The cache is UTF-8 (re-encoded) — decode it yourself: from raw bytes, lxml would trust a
  # legacy site's stale <meta charset> and mojibake the text. Path from `show`.
  doc = lhtml.fromstring(Path("<cache>/01.html").read_text(encoding="utf-8"))
  # illustrative xpath — the real selectors are the version class's `.body_selectors()`
  for el in doc.xpath("//div[@class='story-content']/*"):
      print(el.tag, "|", " ".join(el.text_content().split())[:100])
  ```

**Subagents**: with many candidates or huge HTML, fan out one cheap-model subagent per suspect
article, pointed at the cached `NN.html` and the candidate's `show` output — the dumps stay out of
your context and nothing re-crawls. The subagent reports evidence; the adjudication stays yours.

### The gate

```bash
python "<skill>/scripts/review.py" status <cc>.<Class>
```

Exits non-zero until the crawl completed, the sweep ran on it, and every candidate is adjudicated.
It also reprints the scan counts and lists what it *can't* check — run those checks yourself before
any verdict. **No verdict before `status` reports READY for every publisher in the PR.**

## 3. Diagnose a miss

Usual culprits for missing content:

- **`<ul>/<ol>` lists** dropped by a paragraph-only selector.
- **`<p>` whose text is only inside `<em>`/`<i>`/`<a>`** dropped when the selector needs direct
  `text()` (e.g. every address in a listicle: `<p><em>73 York St.</em></p>`).
- **`<span>`-wrapped paragraphs** the selector doesn't allow.
- **Over-capture**: boilerplate or captions leaking *into* the body.

For images, compare each `caption`/`authors`/`is_cover` against the live `<figure>`: paired with the
right image, prefixes like `"Photo by "` stripped. These map to `caption_selector`,
`author_selector` (its `credits` named group is stripped from the caption), and the
`upper_`/`lower_boundary_selector` cover boundaries. Name the offending selector when you report.

To re-run a parser against one cached article while iterating on a selector:
`PublisherCollection.<cc>.<Class>.parser(date.today()).parse(content, "raise")` — source the HTML
from the cache or the crawler's session, never a manual fetch.

## 4. Decide the verdict

A multi-publisher PR gets a per-publisher verdict; the PR's event is the most severe of them.
Classify every finding — the split decides the event:

- **Blockers** — crashes; empty/wrong required attributes; body that misrepresents the article
  (missing paragraphs/lists or leaked boilerplate); mis-paired image data; missing/incorrect
  `free_access` on a premium publisher; `VALID_UNTIL`/version-bump mistakes; a wrong
  `validate=False` attribute.
- **Nits** — dropped trailers ("With files from …"), minor topic noise.

Event: **any blocker → `REQUEST_CHANGES`; no blockers → `COMMENT`; your own PR → `COMMENT`
regardless. Never `APPROVE`** — an agent reports findings; a human signs off the merge gate.

If a gap lives in a **base/parent parser** other publishers inherit, say so — the fix likely belongs
there. When proposing a fix, prefer locking it in with a new test case.

## 5. Post the review

```bash
python "<skill>/scripts/review.py" payload <cc>.<Class>   # refuses while anything is pending
```

`payload` writes two files into the cache dir: `findings.json` — the adjudicated evidence — and
`review.json`, **the review itself as a skeleton**: suggested event, the per-publisher scope line,
and one inline-comment stub per adjudicated blocker, all prefilled from the state. Your half is
judgment: replace every `<...>` placeholder, add inline comments for your Tier-1 / image /
static-read findings, delete template lines that don't apply. One PR gets **one review** — on a
multi-publisher PR, fold the other publishers' skeletons into a single body and comment list under
one verdict line.

Placement rules for what you fill in and add:

- **Every finding lives in exactly one place**: an inline comment if it has a diff line to anchor
  to, one `Not inline:` bullet if it doesn't. The summary never restates findings — GitHub renders
  every inline comment directly under it. A `Not inline` bullet is a nit unless it opens
  `**Blocker —**` (e.g. "0 articles crawled", which has no diff line).
- **The scope line states what was checked, never what passed** — no passing evidence, no attribute
  inventory: anything not named as a finding is already claimed clean by that line.
- **Inline comment** — one finding each, ~60–80 words: one claim, one proof, one fix.
  - `**Blocker — <one-line claim>.**` (or `**Nit — …**`)
  - **One** ellipsized quote — the most damning example; if it recurs, append `(also N more)`.
  - `Fix:` one line naming the selector/change.
  - The article URL as an anchored footnote (`[[1]](https://…)`), never bare inline.
  - `line` must fall inside a diff hunk (added or context; any line of a brand-new file).

> **Confirm before posting.** A review is outward-facing and hard to retract: show the filled
> `review.json` to the user and run the POST only once they approve.

```bash
gh pr view <PR> --json headRefOid -q .headRefOid                    # -> commit_id in review.json
gh api repos/flairNLP/fundus/pulls/<PR>/reviews -X POST --input "<cache>/review.json"
```

The review posts under the `gh`-authenticated user; with `REQUEST_CHANGES` it blocks merge until
resolved if the repo enforces review gating.

---

*Cleanup: with scratch in the cache/temp dir there's nothing to clean in the repo. If anything of
yours did land in the working dir, remove only that; never touch pre-existing untracked files
without asking.*