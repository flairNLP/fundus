# Agent skills

Playbooks and skills meant to be **executed by AI coding agents**, not human contributors.

The repo stays **agent-neutral**: we track the skill *sources* here, but we do **not** commit any
agent's config directory (`.claude/` is gitignored). Each developer installs the skills they want into
their own agent with the installer below.

## Skills

| Skill | What it does |
|-------|--------------|
| [`review-publisher`](review-publisher/SKILL.md) | Reviews a publisher PR (new publisher or parser-version change): crawls live articles to verify the extracted `ArticleBody` mirrors the real article, checks `VALID_UNTIL` / version bumps / `validate=False` / `free_access`, and drafts a single GitHub review. |

`install.py` (the installer launcher) and the `installer/` package behind it, plus this
`README.md`, round out the folder.

## Layout

Each skill is a **self-contained folder** — a `SKILL.md`, the `PLAYBOOK.md` it points at, and any helper
scripts under `scripts/` — so the whole thing can be copied anywhere and still work. The installer copies
the **entire folder**, so anything you drop in ships automatically; if the folder has a `requirements.txt`
at its root, the installer also pip-installs it into your current interpreter. Install is **atomic**: if
that pip step fails, the copied folder is rolled back (the cell flashes `!`, then shows `·`) so an install
never half-lands — `✓` always means the skill *and* its deps are in.

Two path conventions keep a copied folder working:

- `SKILL.md` links to `PLAYBOOK.md` as a **sibling**, so the link survives being copied into `.claude/`.
- **`${CLAUDE_SKILL_DIR}` is substituted by Claude Code in `SKILL.md` content only** — it is *not* an
  environment variable, and other bundled files are read verbatim. So `SKILL.md` states the skill's own
  directory once (via the placeholder) and tells the agent to substitute it into the `<skill>` paths
  the `PLAYBOOK.md` commands use. A bare `scripts/…` path would wrongly assume the working dir is the
  skill dir; a `${CLAUDE_SKILL_DIR}` outside SKILL.md would expand to nothing in a shell.

References from `PLAYBOOK.md` to *other* repo docs use **repo-root-relative** links
(e.g. `/docs/attribute_guidelines.md`): they resolve on GitHub and from the repo root, which is where
the review skill runs anyway.

## Install

The installer is a full-screen **status dashboard**. Run it with no arguments:

```bash
python skills/install.py
```

It shows a live list of *skills* for the selected agent. Each row is a skill; the **Installed** column
shows whether it's installed (`✓`) or not (`·`). Move the cursor with `↑`/`↓`, then press `space` to act
on the highlighted skill — installing it if it's absent, uninstalling it if it's present. The list updates
in place, so you never have to re-run. `r` refreshes from disk and `q` quits.

Skills install to `./.claude/skills/`, scoped to this repo — where they're relevant (Fundus skills
reference repo files and run against the repo) — and never pushed (`.claude/` is in the committed
`.gitignore`). A skill's `requirements.txt` is installed into the interpreter you run the installer with
(a venv/conda env if one is active), *not* system-wide, so run the installer with the same Python your
agent uses.

The installer needs the `textual` package, which ships in the project's `dev` extra:

```bash
pip install -e .[dev]
```

Re-install (toggle off, then on) after editing a skill source to refresh the installed copy. Restart
your agent so it picks up a newly installed skill.

## Supported agents

| Agent | Status | Target |
|-------|--------|--------|
| **Claude Code** (`claude`) | supported | `.claude/skills/<name>/` |
| Codex, Cursor, … | not yet | no 1:1 `SKILL.md` concept; would be a best-effort mapping (e.g. a Codex prompt or a `.cursor/rules` file). Add to `available_agents()` in `installer/core.py` when wanted. |

## Adding a skill

Create a self-contained folder `skills/<name>/`. A typical one looks like this — only `SKILL.md` is
required; the rest are optional:

```
skills/
└── my-skill/
    ├── SKILL.md          # required: frontmatter (name/description) + instructions
    ├── PLAYBOOK.md       # the steps SKILL.md links to as a sibling
    ├── requirements.txt  # optional: extra pip deps, installed on install
    └── scripts/          # optional: helper scripts the playbook calls
        └── do_thing.py
```

A minimal `SKILL.md` looks like this — the block fenced by `---` at the top is the **YAML frontmatter**
(a small metadata header): the installer reads its one-line `description` for the dashboard, and your
agent reads `name`/`description` to decide when to invoke the skill. Everything after the closing `---`
is the instructions the agent follows.

```markdown
---
name: my-skill
description: One-line summary of what this skill does and, crucially, when the agent should use it.
---

# My skill

What to do, in prose the agent can follow. Point it at the sibling playbook and give it the skill's
own directory so bundled scripts resolve:

Follow the steps in [PLAYBOOK.md](PLAYBOOK.md); this skill's directory is `${CLAUDE_SKILL_DIR}`.
```

The installer **discovers skills from the folder layout** (any directory here containing a `SKILL.md`),
so there is nothing to register — run `python skills/install.py` and the new skill shows up as a row. If
the skill needs packages beyond Fundus, drop a `requirements.txt` at its root — the installer pip-installs
it on install (and leaves it in place on uninstall).

Keep the path conventions above: state the skill's own directory in `SKILL.md` via
`${CLAUDE_SKILL_DIR}` (it is substituted nowhere else), and point cross-doc links at repo-root paths
(`/docs/...`).
