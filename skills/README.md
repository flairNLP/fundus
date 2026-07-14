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

It shows a live matrix of *skills* × *scopes* for the selected agent. Each row is a skill; the
**Project** and **User** columns show whether it's installed (`✓`) or not (`·`). Move the cursor with
`↑`/`↓`, then toggle a scope to act on the highlighted skill — `p` for project, `u` for user. Toggling
installs the skill if it's absent and uninstalls it if it's present; the matrix updates in place, so you
never have to re-run. `r` refreshes from disk and `q` quits.

The two scopes:

- **project** installs to `./.claude/skills/`. The skill is scoped to this repo, where it's relevant,
  and never pushed (`.claude/` is in the committed `.gitignore`).
- **user** installs to `~/.claude/skills/`, available in every project. Nothing touches the repo. (The
  review skill references repo files, so it only makes sense while your working directory is the Fundus
  repo regardless.)

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

Create `skills/<name>/` with a `SKILL.md` (frontmatter `name`/`description`) and a `PLAYBOOK.md`
it links to as a sibling; put helper scripts under `scripts/`. The installer **discovers skills from
the folder layout** (any directory here containing a `SKILL.md`), so there is nothing to register —
run `python skills/install.py` and the new skill shows up as a row. If the skill needs packages
beyond Fundus, drop a `requirements.txt` at its root — the installer pip-installs it on install (and
leaves it in place on uninstall).

Keep the path conventions above: state the skill's own directory in `SKILL.md` via
`${CLAUDE_SKILL_DIR}` (it is substituted nowhere else), and point cross-doc links at repo-root paths
(`/docs/...`).
