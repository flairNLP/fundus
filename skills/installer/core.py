"""Installer core: discover skill sources and copy them into an agent's config dir.

UI-agnostic and **stdlib-only** (no textual/rich), so it can back the dashboard, a
future plain CLI, or tests without dragging in the TUI stack. The two domain objects:

- :class:`Skill` — a self-contained source folder (``SKILL.md`` + ``PLAYBOOK.md`` + any
  bundled ``scripts/``/``requirements.txt``). Discovered from the folder layout, never
  registered by hand.
- :class:`Agent` — a coding agent we can install into: it knows where its skills live per
  scope, and owns the install/uninstall/is-installed operations for a given skill.

Installing copies the whole folder (``shutil.copytree``) into the agent's config dir,
which is gitignored (project scope) or lives outside the repo (user scope); re-installing
refreshes the copy in place.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

INSTALLER_DIR = Path(__file__).resolve().parent  # skills/installer/
SKILLS_DIR = INSTALLER_DIR.parent  # skills/
REPO_ROOT = SKILLS_DIR.parent  # repo root

# The scopes a skill can be installed into, in display order.
SCOPES: Tuple[str, ...] = ("project", "user")


# --- skills (the sources we install) ---


@dataclass(frozen=True)
class Skill:
    """A self-contained skill source folder living under ``skills/``."""

    name: str
    source: Path

    @property
    def skill_md(self) -> Path:
        return self.source / "SKILL.md"

    @property
    def requirements(self) -> Optional[Path]:
        """The skill's ``requirements.txt`` if it bundles one, else ``None``."""
        req = self.source / "requirements.txt"
        return req if req.is_file() else None

    @property
    def description(self) -> str:
        """The one-line ``description`` from this skill's SKILL.md frontmatter (``""`` if none)."""
        return _frontmatter_description(self.skill_md)


def discover_skills() -> Dict[str, Skill]:
    """A skill is self-identifying: any folder under ``skills/`` with a ``SKILL.md``.

    Nothing to register — drop a folder in and it shows up. (This package has no
    ``SKILL.md``, so it is skipped.)
    """
    return {
        path.name: Skill(path.name, path)
        for path in sorted(SKILLS_DIR.iterdir())
        if path.is_dir() and (path / "SKILL.md").is_file()
    }


# --- agents (where skills get installed) ---


@dataclass(frozen=True)
class InstallResult:
    """Outcome of an install attempt: whether it ended fully installed, plus log lines."""

    ok: bool
    log: List[str]


@dataclass(frozen=True)
class Agent:
    """A coding agent we can install skills into."""

    name: str
    skills_root: Callable[[str], Path]  # scope -> the agent's skills dir for that scope

    def destination(self, scope: str, skill: Skill) -> Path:
        return self.skills_root(scope) / skill.name

    def is_installed(self, scope: str, skill: Skill) -> bool:
        return self.destination(scope, skill).exists()

    def install(self, scope: str, skill: Skill) -> InstallResult:
        """Copy a skill source into this agent's config dir (refreshing in place), then
        install any requirements it bundles.

        The install is **atomic**: if the requirements step fails, the just-copied folder is
        rolled back, so ``is_installed`` only ever reports ``True`` for a skill whose deps are
        in too. Project scope lands under ``.claude/``, which the repo's committed
        ``.gitignore`` covers — an installed copy can never show up in ``git status``.
        """
        dest = self.destination(scope, skill)
        if dest.exists():
            shutil.rmtree(dest)  # refresh in place
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill.source, dest)
        req_ok, req_log = _install_requirements(skill)
        if not req_ok:
            shutil.rmtree(dest, ignore_errors=True)  # undo the copy — keep the matrix honest
            return InstallResult(False, [*req_log, f"  rolled back '{skill.name}' ({scope}) — nothing left installed"])
        head = f"installed '{skill.name}' for {self.name} ({scope}) -> {dest / 'SKILL.md'}"
        return InstallResult(True, [head, *req_log])

    def uninstall(self, scope: str, skill: Skill) -> List[str]:
        dest = self.destination(scope, skill)
        if dest.exists():
            shutil.rmtree(dest)
            return [f"removed '{skill.name}' for {self.name} ({scope}) -> {dest}"]
        return [f"nothing installed at {dest}"]


def _claude_skills_root(scope: str) -> Path:
    """Where Claude Code looks for skills, per scope."""
    base = REPO_ROOT if scope == "project" else Path.home()
    return base / ".claude" / "skills"


def available_agents() -> Dict[str, Agent]:
    """Supported agents.

    Only ``claude`` (Claude Code) is supported today. Other agents (Codex, Cursor) have no
    1:1 ``SKILL.md`` concept; add them here when wanted.
    """
    return {"claude": Agent("claude", _claude_skills_root)}


# --- helpers ---


def _install_requirements(skill: Skill) -> Tuple[bool, List[str]]:
    """If the skill bundles a ``requirements.txt``, pip-install it into the current interpreter.

    Returns ``(ok, log_lines)``; the caller rolls back the copy when ``ok`` is ``False``.
    Runs on install only — uninstall leaves any deps in place, since we don't track which
    packages a skill brought in. A skill with no ``requirements.txt`` trivially succeeds.
    """
    req = skill.requirements
    if req is None:
        return True, []
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req)],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return False, [f"  ! could not run pip for '{skill.name}' requirements: {exc}"]
    if proc.returncode == 0:
        return True, [f"  installed requirements for '{skill.name}' ({req.name})"]
    tail = _pip_error_tail(proc.stdout, proc.stderr)
    return False, [
        f"  ! pip failed for '{skill.name}' requirements (exit {proc.returncode}):",
        *(f"    {line}" for line in tail),
    ]


def _pip_error_tail(stdout: str, stderr: str) -> List[str]:
    """Pull the lines that actually explain a pip failure out of its combined output.

    pip prints its "A new release of pip is available / To update, run …" upgrade notice
    *last*, so a naive last-N-lines tail shows that noise instead of the real failure. We
    drop that notice and, when pip emitted its own ``ERROR:`` lines, surface those; otherwise
    we fall back to the last few non-empty lines.
    """
    noise = ("A new release of pip", "To update, run")
    lines = [ln.rstrip() for ln in f"{stdout}\n{stderr}".splitlines() if ln.strip()]
    lines = [ln for ln in lines if not any(n in ln for n in noise)]
    errors = [ln for ln in lines if ln.lstrip().startswith("ERROR")]
    chosen = errors or lines
    return chosen[-3:] if chosen else ["(pip produced no output)"]


def _frontmatter_description(skill_md: Path) -> str:
    """Pull the one-line ``description`` from a SKILL.md's YAML frontmatter.

    Handles both inline (``description: foo``) and block-scalar (``description: >-``) forms;
    returns ``""`` when the file is missing or has no frontmatter description.
    """
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return ""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return ""

    parts: List[str] = []
    capturing = False
    for line in lines[1:end]:
        if not capturing:
            if line.startswith("description:"):
                capturing = True
                rest = line[len("description:") :].strip()
                # Skip block-scalar indicators (``>-``, ``|``, …); keep inline text.
                if rest and rest[0] not in "|>":
                    parts.append(rest)
            continue
        if line and not line[0].isspace():
            break  # next top-level frontmatter key
        parts.append(line.strip())
    return " ".join(p for p in parts if p)
