"""Installer core: discover skill sources and copy them into an agent's config dir.

UI-agnostic and **stdlib-only** (no textual/rich), so it can back the dashboard, a
future plain CLI, or tests without dragging in the TUI stack. The two domain objects:

- :class:`Skill` — a self-contained source folder (``SKILL.md`` + ``PLAYBOOK.md`` + any
  bundled ``scripts/``/``requirements.txt``). Discovered from the folder layout, never
  registered by hand.
- :class:`Agent` — a coding agent we can install into: it knows where its skills live and
  owns the install/uninstall/is-installed operations for a given skill.

Installing copies the whole folder (``shutil.copytree``) into the agent's config dir (under
the repo's gitignored ``.claude/``); re-installing refreshes the copy in place.

Every install drops a :data:`MANIFEST_FILE` recording the declared ``version`` and a content
**fingerprint**, which is how :meth:`Agent.status` tells the two kinds of drift apart: the repo
moved on (reinstall), or the installed copy was edited in place (reinstalling discards it). A
version alone can't catch the second — whoever edits a copy has no reason to bump it.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Records what was installed; excluded from fingerprints so it isn't part of the skill.
MANIFEST_FILE = ".install-manifest.json"
# Bump whenever `fingerprint` changes: a digest written by an older algorithm is not comparable,
# and treating it as one would report an untouched copy as edited in place. A manifest at any
# other format reads as untracked until the skill is re-installed.
MANIFEST_FORMAT = 1
# Build artefacts a copied folder accumulates on use; never part of what was installed.
_IGNORED_NAMES = {"__pycache__", MANIFEST_FILE}
_IGNORED_SUFFIXES = {".pyc", ".pyo"}

INSTALLER_DIR = Path(__file__).resolve().parent  # skills/installer/
SKILLS_DIR = INSTALLER_DIR.parent  # skills/
REPO_ROOT = SKILLS_DIR.parent  # repo root


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
        return _frontmatter_field(self.skill_md, "description")

    @property
    def version(self) -> str:
        """The ``version`` from frontmatter (``""`` if none) — a hand-bumped label only; drift
        detection uses :func:`fingerprint`, so an unversioned skill is fine."""
        return _frontmatter_field(self.skill_md, "version")

    def fingerprint(self) -> str:
        """Content hash of this skill's source folder."""
        return fingerprint(self.source)


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


def fingerprint(root: Path) -> str:
    """Content hash of a skill folder: names and bytes, not folder state.

    Paths go in POSIX-relative so a rename registers and the digest matches across platforms;
    bytes are hashed raw, since normalising line endings would hide exactly the differences this
    exists to surface. Mode bits and empty directories are *not* covered — a `chmod -x` on an
    installed script still reads as in sync.
    """
    digest = hashlib.sha256()
    for path in sorted(_skill_files(root), key=lambda p: p.relative_to(root).as_posix()):
        data = path.read_bytes()
        # Both parts length-prefixed, so no arrangement of names and contents hashes the same
        # two ways (colons are legal in filenames, so prefixing only the content isn't enough).
        name = path.relative_to(root).as_posix()
        header = f"{len(name)}:{name}:{len(data)}:"
        digest.update(header.encode("utf-8"))
        digest.update(data)
    return digest.hexdigest()


def _skill_files(root: Path) -> List[Path]:
    """Every file that counts as part of a skill — build artefacts and the manifest excluded."""
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix not in _IGNORED_SUFFIXES
        and not any(part in _IGNORED_NAMES for part in path.relative_to(root).parts)
    ]


@dataclass(frozen=True)
class InstallStatus:
    """How an installed skill relates to its source.

    ``source_changed`` and ``local_changed`` are independent because the fixes differ (see the
    module docstring). ``tracked`` is False for a pre-manifest install, where a difference can't
    be attributed to either side — both flags then carry the same "they differ".
    """

    installed: bool
    tracked: bool
    source_changed: bool
    local_changed: bool
    installed_version: str
    source_version: str

    @property
    def in_sync(self) -> bool:
        return self.installed and not self.source_changed and not self.local_changed


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
    skills_root: Path  # the agent's skills dir

    def destination(self, skill: Skill) -> Path:
        return self.skills_root / skill.name

    def is_installed(self, skill: Skill) -> bool:
        return self.destination(skill).exists()

    def install(self, skill: Skill) -> InstallResult:
        """Copy a skill source into this agent's config dir (refreshing in place), then
        install any requirements it bundles.

        The install is **atomic**: if the requirements step fails, the just-copied folder is
        rolled back, so ``is_installed`` only ever reports ``True`` for a skill whose deps are
        in too. Skills land under ``.claude/``, which the repo's committed ``.gitignore``
        covers — an installed copy can never show up in ``git status``.
        """
        dest = self.destination(skill)
        if dest.exists():
            shutil.rmtree(dest)  # refresh in place
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill.source, dest)
        req_ok, req_log = _install_requirements(skill)
        if not req_ok:
            shutil.rmtree(dest, ignore_errors=True)  # undo the copy — keep the status honest
            return InstallResult(
                False,
                [*req_log, f"  rolled back '{skill.name}' files — any packages pip already installed stay"],
            )
        # Last, so a manifest only ever describes a fully landed install.
        _write_manifest(dest, skill)
        version = f" v{skill.version}" if skill.version else ""
        head = f"installed '{skill.name}'{version} for {self.name} -> {dest / 'SKILL.md'}"
        return InstallResult(True, [head, *req_log])

    def status(self, skill: Skill) -> InstallStatus:
        """Where the installed copy stands relative to the source — see :class:`InstallStatus`."""
        dest = self.destination(skill)
        source_version = skill.version
        if not dest.exists():
            return InstallStatus(False, False, False, False, "", source_version)
        manifest = _read_manifest(dest) or {}
        source_now = skill.fingerprint()
        installed_now = fingerprint(dest)
        recorded = str(manifest.get("fingerprint") or "")
        # An unusable manifest is one we cannot compare against: absent (pre-manifest install),
        # truncated, or — the one that bites on upgrade — written by a different `fingerprint`
        # algorithm, whose digest would differ for a copy nobody touched. Each would otherwise
        # read as ≠ ("your local edits are about to be destroyed") for work that never happened.
        if not recorded or manifest.get("format") != MANIFEST_FORMAT:
            differs = installed_now != source_now
            return InstallStatus(True, False, differs, differs, "", source_version)
        return InstallStatus(
            installed=True,
            tracked=True,
            source_changed=source_now != recorded,
            local_changed=installed_now != recorded,
            installed_version=str(manifest.get("version", "")),
            source_version=source_version,
        )

    def uninstall(self, skill: Skill) -> List[str]:
        dest = self.destination(skill)
        if dest.exists():
            shutil.rmtree(dest)
            return [f"removed '{skill.name}' for {self.name} -> {dest}"]
        return [f"nothing installed at {dest}"]


def _claude_skills_root() -> Path:
    """Where Claude Code looks for skills: the repo's gitignored ``.claude/skills/``."""
    return REPO_ROOT / ".claude" / "skills"


def available_agents() -> Dict[str, Agent]:
    """Supported agents.

    Only ``claude`` (Claude Code) is supported today. Other agents (Codex, Cursor) have no
    1:1 ``SKILL.md`` concept; add them here when wanted.
    """
    return {"claude": Agent("claude", _claude_skills_root())}


# --- helpers ---


def _write_manifest(dest: Path, skill: Skill) -> None:
    """Record what was just installed, so a later run can detect drift on either side."""
    # `source` and `installed_at` have no reader — they are breadcrumbs for a human opening the
    # file to ask where a copy came from. `version` and `fingerprint` are what `status` uses.
    manifest = {
        "format": MANIFEST_FORMAT,
        "skill": skill.name,
        "version": skill.version,
        "fingerprint": fingerprint(dest),
        "source": str(skill.source),
        "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (dest / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _read_manifest(dest: Path) -> Optional[Dict[str, object]]:
    """The manifest, or None if absent/unreadable — a corrupt one degrades to "untracked"
    rather than crashing the dashboard."""
    path = dest / MANIFEST_FILE
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _install_requirements(skill: Skill) -> Tuple[bool, List[str]]:
    """If the skill bundles a ``requirements.txt``, pip-install it into the current interpreter.

    Deps go to the interpreter running the installer (``sys.executable``), so run the installer
    with the same Python your agent/Fundus uses; if that is a venv/conda env, the deps go there,
    not system-wide.

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
    drop that notice and, when pip emitted its own ``ERROR:``/``WARNING:`` lines, surface
    those (the warnings often explain the error — e.g. a "Retrying … name resolution" warning
    ahead of "No matching distribution"); otherwise we fall back to the last few non-empty
    lines. pip emits its warnings before the final errors, so the tail still ends on them.
    """
    noise = ("A new release of pip", "To update, run")
    lines = [ln.rstrip() for ln in f"{stdout}\n{stderr}".splitlines() if ln.strip()]
    lines = [ln for ln in lines if not any(n in ln for n in noise)]
    diagnostics = [ln for ln in lines if ln.lstrip().startswith(("ERROR", "WARNING"))]
    chosen = diagnostics or lines
    return chosen[-5:] if chosen else ["(pip produced no output)"]


def _frontmatter_field(skill_md: Path, field: str) -> str:
    """Pull one field from a SKILL.md's YAML frontmatter.

    Handles both inline (``description: foo``) and block-scalar (``description: >-``) forms;
    returns ``""`` when the file is missing or has no such field.
    """
    key = f"{field}:"
    try:
        text = skill_md.read_text(encoding="utf-8")
    except FileNotFoundError:
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
            if line.startswith(key):
                capturing = True
                rest = line[len(key) :].strip()
                # Skip block-scalar indicators (``>-``, ``|``, …); keep inline text.
                if rest and rest[0] not in "|>":
                    parts.append(rest)
            continue
        if line and not line[0].isspace():
            break  # next top-level frontmatter key
        parts.append(line.strip())
    return " ".join(p for p in parts if p)
