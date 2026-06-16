---
name: review-publisher
description: >-
  Review a Fundus publisher PR — one that adds a new publisher or adds/changes a parser version.
  Crawls live articles to verify the extracted ArticleBody mirrors the real article (no missing or
  leaked content), checks VALID_UNTIL / version bumps / validate=False attributes / free_access, and
  drafts a single GitHub review. Use when asked to review a publisher or parser PR.
---

# Review a Publisher PR

**This skill's directory is `${CLAUDE_SKILL_DIR}`** — that placeholder is substituted *only here in
SKILL.md*, so note the literal path above now. The procedure lives in the sibling
[`PLAYBOOK.md`](PLAYBOOK.md); wherever its commands write `<skill>`, substitute the literal path.
The bundled driver — the only tool you need — is:

    python "<skill>/scripts/review.py" {crawl,sweep,show,adjudicate,status,payload} <cc>.<Class>

Open the PLAYBOOK and work through §1–§5; it's the source of truth. These are the guardrails to
hold onto even before you open it:

- **No PR named? Resolve it first** — read the current branch's PR (`gh pr view`), confirm it, or ask.
  Never guess or default to the latest.
- **Don't run `pytest` / `mypy` / `ruff`** — CI covers them; your value-add is live-article correctness.
- **The body must mirror the article** — no dropped paragraphs, no leaked boilerplate. The driver's
  crawl-once-then-sweep flow (§2) is a hard gate on **every** publisher: every candidate it surfaces
  must be explicitly adjudicated (`adjudicate <id> ok|blocker --note ...`), and `status` must report
  READY before any verdict. The judgment calls stay yours; skipping them silently does not.
- **Each publisher is its own review** — its own crawl, sweep, and `status READY`; a blocker on one
  does not discharge the checks on the rest.
- **Verdict:** any blocker → `REQUEST_CHANGES`, else `COMMENT`. Never `APPROVE`; your own PR → `COMMENT`.
- **Keep the review tight, and confirm before posting** — one skimmable review, no evidence stated
  twice (§5); show `review.json` to the user before the `gh api` POST.
