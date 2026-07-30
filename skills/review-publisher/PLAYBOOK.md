# How to Review a Publisher PR

> **Audience: AI coding agents.** This is an operational playbook meant to be executed by an agent,
> not a human contributor guide. It's also the source doc behind the `review-publisher` skill.

A review playbook for PRs that **add a new publisher** or **add/change a parser version**. The matching
authoring process is [`how_to_add_a_publisher.md`](/docs/how_to_add_a_publisher.md) — you're reviewing the
fruits of it, so the checks below map onto the promises that process makes.

All mechanics run through one driver. `<skill>` below is the skill directory SKILL.md told you
(`${CLAUDE_SKILL_DIR}` is substituted only there); the cross-doc links above and below are
repo-root-relative — read them from the repo root, where you are anyway.

    python "<skill>/scripts/review.py" {crawl,sweep,show,adjudicate,status,payload} <cc>.<Class>

The driver enforces the bookkeeping (what was crawled, what was swept, what is still un-adjudicated);
this playbook is about the part that stays yours: **judgment**. The split is deliberate — the driver
may refuse, warn, and count, but it never decides; you never count by hand.

**The unit of review is the PR's diff, not the whole publisher.** Review what *this PR* changes. On a
parser-version bump, scope your reading to the new version and how it differs from the old — don't
re-litigate code the PR doesn't touch. A new publisher is all-new, so there the diff *is* the whole file.

**A multi-publisher PR is N independent reviews, not one.** Run §2 once per publisher — each gets its
own crawl, sweep, and `status` READY. A blocker on one publisher does **not** discharge the body checks
on the others: the loud finding is a distraction from the clean-reading publishers, which get the *same*
full treatment, never a lighter pass.

## What you're protecting

> **The extracted `ArticleBody` must mirror the real article — no missing content, no extra content.**

This isn't aesthetic. Fundus maps extracted text back to the source HTML for annotation, so a dropped
paragraph or a leaked photo caption corrupts that mapping. Over-capture is a blocker, not a nit.

## Rules

- **Don't run `pytest`, `mypy`, `ruff`, or any other checks locally — the GitHub CI covers all of
  that.** Your value-add is confirming the parser is correct on **live** articles; the unit test only
  checks one frozen HTML snapshot, so a green test proves nothing about today's site or other layouts.
- **Cite everything.** Every finding needs quotable evidence: the verbatim dropped/leaked text, the
  article URL, and the offending selector. Adjudication notes are part of that trail — they land in
  `findings.json` verbatim.
- **Keep scratch out of the repo.** `review.json` and any throwaway dump go in the cache dir the
  driver prints (`<tempdir>/fundus-review/…`) or any OS temp dir — never the working directory.
- **Never truncate driver output.** Don't pipe `crawl` through `[:N]` or cap the printed text — a
  slice that cuts off partway through the draw reads clean on articles you never saw. The state file
  records what was actually cached, and `status` reconciles the counts for you.

## Inputs

- **PR number** and whether it's **your own** PR (changes the verdict event — see §4). **If the user
  didn't name a PR, resolve it before doing anything else:** `gh pr view --json number,title,author`
  reads the current branch's open PR; show it and confirm. If the branch has no open PR, ask — don't
  guess. (The `author` also settles the own-PR question.)
- The publisher(s) under review as `PublisherCollection.<cc>.<Class>`, and the parser version(s) touched.

## 1. Static read

```bash
gh pr checkout <PR_NUMBER>
gh pr diff <PR_NUMBER>
```

Skim the diff and sanity-check the parser:

- `@attribute` return types match [`attribute_guidelines.md`](/docs/attribute_guidelines.md).
- **`@attribute(validate=False)` bypasses CI.** Type conformance is enforced by the unit tests for
  *validated* attributes only. Any attribute marked `validate=False` is checked by **nobody but you** —
  read its logic and return value by hand.
- **`free_access` / paywall.** If the publisher runs a subscription model, `free_access` must be
  implemented (off `isAccessibleForFree` in the `ld+json`). A missing or wrong `free_access` on a
  premium publisher is a blocker. If the publisher is fully free, there's nothing to check here.
- **`VALID_UNTIL` is *not* inherited** — every `BaseParser` subclass defaults to `date.max`. When a PR
  adds a new version for a layout change, the *previous* version must get an explicit `VALID_UNTIL`
  (the day before the change), and the newest must leave it unset. (Subclassing another publisher's
  version and leaving `VALID_UNTIL` unset is fine — that's the intended `date.max`.)
- **Version bump fits the change.** Selector-only fix → minor bump (`V1_1(V1)`); new or substantially
  changed attributes → major bump (`V2`). Flag a `V2` that's really just selectors, or a minor bump
  that quietly changes attribute behavior.
- **Shared-utility changes** (`parser/utility.py`: `generic_topic_parsing`, `apply_result_filter`,
  `image_extraction`, …) affect **every** publisher, not just this one. Check the call sites and rely
  on the full (CI-run) suite staying green.

## 2. Crawl live articles and verify the body

### Crawl once

```bash
python "<skill>/scripts/review.py" crawl <cc>.<Class>                         # pool 100 -> read 10
python "<skill>/scripts/review.py" crawl <cc>.<Class> --pool 200 --review 16  # widen either half
```

One live crawl per publisher; everything after it replays the cache, so the read set and the swept
set are the same draw by construction. The crawl draws a **candidate pool** (`--pool`, default 100),
**sweeps every article in it** offline, then caches only the `--review` (default 10) articles worth
your time and prints the **Tier-1 view** for each (url / title / authors / topics / image count /
body). Scanning and sampling both need the whole pool up front, so an interrupted crawl caches
nothing — just re-run it (the crawl is the only networked step).

**The scan covers the pool; the draw is what you read.** That split is the point — selection can only
show you ten articles, but `0 flagged` is a statement about all hundred. Two rankings fill the draw,
and each cached article prints which one put it there:

- `diverse` — structural coverage. The first pick is the pool's most typical article and every later
  pick is the most different one left, so the page shapes a publisher uses get represented.
- `flagged` — what the parser actually *did*, which structure cannot see: a class-name variant that
  breaks a selector leaves a structurally identical page. Flagged articles claim up to half the draw
  from the least distinctive diverse picks. The first pick — the pool's most typical article, your
  baseline for what a correct extraction looks like here — is never traded away.

So **the draw is skewed toward broken articles on purpose**: "all ten read fine" is a weaker claim
than "this publisher reads fine", and it's the scan counts that carry the second one. Two lines the
crawl prints deserve action rather than acknowledgement — *more articles flagged than the draw holds*
(re-run with a bigger `--review`, or read the printed urls by hand; every scanned article is in
`state.json` under `scan`), and *the most typical article in the pool is flagged*, which is a
mainstream failure rather than an edge case and should lead the review.

**Layout coverage stays your judgment.** The draw should span the layouts that break parsers — a
straight news piece, an opinion/column, a **listicle or bullet-list** piece, and an **image-heavy**
one. Diverse sampling surfaces these automatically; if a layout you know exists is still missing,
**widen the pool (`--pool`) and re-crawl**. If the publisher is too small or uniform to cover all
four, note that in the review. Don't prompt the user for a number; the defaults are the floor and
coverage decides the rest.

**The draw is deliberately unfiltered** (`only_complete=False`). Fundus' default crawl drops any
article missing `title`, `body` or `publishing_date` — precisely the articles a parser broke — so
filtering before the scan would hide the worst findings. Such an article is flagged outright and
almost always lands in the draw, where the Tier-1 view repeats it as `! missing title, body`. Treat
that as **blocker-level unless the page genuinely isn't an article** (video stub, liveblog, photo
gallery); say which in the review.
Note that a parser that *raises* is skipped by fundus before it reaches the pool, and its reason is
logged below the default handler level. If the crawl returns far fewer articles than `--pool`, re-run
it with `--verbose` to surface both those skips and every per-attribute extraction failure.

**Stop condition:** 0 articles after a fair attempt means the sources or parser are broken — that is
itself a blocker-level finding; report it, don't silently stall. Many publishers block generic
fetchers, so inspect via the cached html (`show` prints the per-article file paths), never a manual
`urllib`/`requests` fetch.

### Tier 1 — coherence read (all articles, from the crawl output)

Read each extracted body. It should read like the article: no dangling sentences, no abrupt jumps, no
sentence referencing something that isn't there ("…fell into either of two groups:" followed by
nothing), and no boilerplate (newsletter sign-ups, "Read More" teasers, photo captions) mixed in. Also
eyeball `title`/`authors`/`topics` for emptiness or obvious junk (UUIDs, section names, the domain,
`Category:` prefixes). Note every article that trips a signal.

Coherence has **one blind spot**: a paragraph dropped mid-body leaves the surrounding text still
flowing — the seam closes and nothing reads wrong. Tier 2 exists for exactly that.

### Tier 2 — sweep, then adjudicate every candidate (hard gate, every publisher)

```bash
python "<skill>/scripts/review.py" sweep <cc>.<Class>                 # same cache, no network
python "<skill>/scripts/review.py" sweep <cc>.<Class> --version V1_1  # pin a legacy version; re-runs free
```

This is the same sweep the crawl already ran across the whole pool — the difference is what it's for.
There it *ranked* articles so the draw would contain the right ones; here it applies the version's
*real* body selectors to each cached article and turns what it finds into adjudicable candidates. The
scan selects, the sweep gates. It emits two kinds of candidate, each with an id:

- **DROP** — a structural block (`ul`/`ol`/`dl`/`pre`/`blockquote`/`table`) or `<p>`/`<h*>` in the
  body container whose text is **absent from the extracted body**. A candidate is a question, not a
  verdict, and the answer depends on the tag:
  - `ul`/`ol`/`dl`/`pre`, `<p>`, `<h*>` — prose the selector should have caught. A blocker unless
    the text is page chrome.
  - `blockquote` — case by case. A pull-quote restating a paragraph that *is* in the body is fine
    (`ok`); quoted source material appearing nowhere else is a blocker.
  - `table` — Fundus has no representation for tabular content (`ArticleBody` is a summary plus
    sections of plain text), so a dropped data table is normally `ok`. It is a blocker only when
    the element is layout and the missing text is ordinary prose.
- **LEAK** — a body unit **repeated across half the cached articles**: the signature of boilerplate
  *inside* the body (newsletter pitches, teasers, bios repeat; article text doesn't).

The boilerplate-vs-body call is yours, and it's recorded, not implied:

```bash
python "<skill>/scripts/review.py" show <cc>.<Class> <id>      # full text + cached html paths
python "<skill>/scripts/review.py" adjudicate <cc>.<Class> <id> ok --note "site-wide cookie banner"
python "<skill>/scripts/review.py" adjudicate <cc>.<Class> <id> blocker --note "<ul> of match results dropped; <url>"
```

`ok` means benign (chrome outside the body for a DROP; legitimately recurring content for a LEAK);
`blocker` means a real finding — the note is your evidence line and lands in `findings.json` verbatim.
Adjudicate from the **cached** html (`show` prints each article's `NN.html` path) so there's no "site
changed" ambiguity. Heads-up: the sweep *prints* the blocks it suppressed as duplicates (text already
in the body) — skim them; that suppression is vetoable, not authoritative.

What the sweep **cannot** do, and stays on you:

- **Over-capture beyond repetition.** The LEAK scan only catches *recurring* boilerplate. A one-off
  caption or "Related:" line leaked into a single body never repeats — on the articles you read,
  check the body for anything that isn't article content.
- **Not-sweepable articles.** A version without a `_paragraph_selector` builds its body another way,
  and an article whose body came out empty has nothing to compare against. The sweep reports both
  N/A with the reason and you do the by-hand walk below — an empty body is itself the finding.
- **Layout coverage** (§2 crawl) and the **image attributes** (§3).

When you want the raw container — a candidate needs context, or an article is N/A — walk the cached
bytes directly:

```python
from pathlib import Path
from lxml import html as lhtml
doc = lhtml.fromstring(Path("<cache>/01.html").read_bytes())  # path from `show`
# ILLUSTRATIVE selector - use the actual ones: the version class's public accessor
# `.body_selectors()` returns the real paragraph/summary/subheadline selectors.
for el in doc.xpath("//div[@class='story-content']/*"):
    print(el.tag, "|", " ".join(el.text_content().split())[:100])
```

**Delegating to subagents.** When multiple candidates trip or the HTML is large, fan out — one
cheap-model subagent per suspect article, pointed at the cached `NN.html` and the candidate's `show`
output, so the dumps stay out of this context and nothing re-crawls. The subagent reports evidence;
the adjudication call stays with you.

### The gate

```bash
python "<skill>/scripts/review.py" status <cc>.<Class>
```

`status` is the self-audit the old coverage table used to be, but machine-checked: it exits non-zero
until the crawl completed, the sweep ran on it, and **every candidate is adjudicated**. It also lists
what it *can't* check (coherence read, layout coverage, one-off over-capture, images) — those become
one line each in your review body per publisher. It reprints the scan counts too; carry them into the
review, since they are the only evidence you have about the articles nobody read. **No verdict before `status` reports READY for every
publisher in the PR.**

## 3. Diagnose a miss

When the sweep shows content missing, the usual culprits:

- **`<ul>/<ol>` lists dropped** — a paragraph-only selector skips list items.
- **`<p>` whose text is only inside `<em>`/`<i>`/`<a>`** dropped when the selector needs direct
  `text()` (e.g. every address in a listicle: `<p><em>73 York St.</em></p>`).
- **`<span>`-wrapped paragraphs** missing if the selector doesn't allow them.
- **Over-capture**: boilerplate or captions leaking *into* the body.

For images, compare each `caption`/`authors`/`is_cover` against the live `<figure>` to confirm they're
paired with the right image and that prefixes like `"Photo by "` are stripped — these map to the
parser's `caption_selector`, `author_selector` (whose `credits` named group is stripped from the
caption), and the `upper_`/`lower_boundary_selector` cover boundaries. Name the offending selector when
you report.

Articles the default extraction filter would have dropped are already in the draw (§2), so there is
nothing to re-crawl for them. To re-run a parser against one cached article while you iterate on a
selector: `PublisherCollection.<cc>.<Class>.parser(date.today()).parse(content, "raise")` — but source
the HTML from the cache or the crawler's session; many publishers block generic fetchers.

## 4. Decide the verdict

**Don't decide until `status` reports READY for every publisher.** A multi-publisher PR gets a
per-publisher verdict; the PR's overall event is the most severe of them.

Group findings by severity with quotable evidence (the dropped text, the URL, the selector at fault):

- **Blockers** — crashes, empty/wrong required attributes, body that misrepresents the article
  (missing paragraphs/lists or leaked boilerplate), mis-paired image data, missing/incorrect
  `free_access` on a premium publisher, `VALID_UNTIL`/version-bump mistakes, an unreviewed
  `validate=False` attribute that's wrong.
- **Nits** — dropped trailers ("With files from …"), minor topic noise.

Then pick the review **event**:

- **Any blocker → `REQUEST_CHANGES`.**
- **No blockers → `COMMENT`.** Leave the actual `APPROVE` to a human — an agent reports findings, it
  doesn't sign off the merge gate.
- **It's your own PR → `COMMENT`** regardless — GitHub blocks `REQUEST_CHANGES` on your own PR anyway.

If a gap lives in a **base/parent parser** that other publishers inherit, say so — the fix likely
belongs there. When proposing a fix, prefer locking it in with a new test case.

## 5. Post the review

```bash
python "<skill>/scripts/review.py" payload <cc>.<Class>   # refuses while anything is pending
```

`payload` emits `findings.json` — the adjudicated blockers with your notes and the article URLs, plus
a suggested event. That's the mechanical half; your Tier-1 / layout / over-capture / image findings
join it. Submit **one review** via the GitHub API so the summary, the inline comments, and the verdict
land together.

### Write it to be read

A review nobody can skim doesn't get acted on. Two failure modes to avoid:

- **Stating the same evidence twice** — once in the summary and again in the inline comment.
- **Cataloguing what passed** — silence already says "checked, clean", so an inventory of working
  attributes only buries the finding that needs acting on.

Split the labor:

- **Summary body** — skimmable, no verbatim evidence. Lead with the verdict, then **one line per
  publisher** (clean, or the blocker named in a clause; include the not-machine-checked line: read N
  of M scanned, layouts covered, over-capture scanned), then a short **bulleted blocker list** where
  each bullet names the problem and **links to its inline thread** instead of restating the quote.
- **Inline comment** — where the evidence lives, one finding each, in this shape:
  - **Line 1:** `**Blocker — <one-line claim>.**` (or `**Nit — …**`).
  - **One** quoted snippet — the single most damning example, ellipsized to the few words that prove
    it. If it recurs, append `(also N more)` rather than quoting each.
  - `Fix:` one line naming the selector/change.
  - The article URL as an **anchored footnote** (`[[1]](https://…)`), never a bare inline URL.

  Aim for ~60–80 words. Keep the one claim, the one proof, the one fix.

> **Confirm before posting.** A review is outward-facing and hard to retract. Build `review.json`,
> show it to the user, and run the `gh api` POST only once they approve.

```bash
# commit_id is the PR head SHA:
gh pr view <PR> --json headRefOid -q .headRefOid

# Build the payload in the cache dir the driver printed, NOT the repo working dir.
# Valid JSON — no comments inside it. One entry per finding; each comment needs path + line + side + body.
cat > "$SCRATCH/review.json" <<'JSON'
{
  "commit_id": "<PR_HEAD_SHA>",
  "event": "REQUEST_CHANGES",
  "body": "<verdict; one line per publisher; bulleted blocker list linking to the inline threads>",
  "comments": [
    { "path": "src/fundus/publishers/<cc>/<file>.py", "line": 9, "side": "RIGHT",
      "body": "**Blocker — list items dropped.** \"…<ellipsized snippet>…\" Fix: <selector>. [[1]](<live article url>)" }
  ]
}
JSON
gh api repos/flairNLP/fundus/pulls/<PR>/reviews -X POST --input "$SCRATCH/review.json"
```

Notes:

- `event` is `REQUEST_CHANGES` or `COMMENT` per the rule in §4.
- `line` must fall inside the diff hunk (added or context lines are both fine); for a brand-new file
  every line qualifies. The `9` above is illustrative — use a real line from the diff.
- The review posts under the `gh`-authenticated user and, with `REQUEST_CHANGES`, blocks merge until
  resolved if the repo enforces review gating.

---

*Cleanup: with scratch kept in the cache/temp dir (see Rules), there's nothing to clean in the repo.
If anything of yours did land in the working dir, remove only that; never touch pre-existing untracked
files without asking.*
