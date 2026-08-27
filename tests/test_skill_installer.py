"""Tests for the skill installer's drift detection (skills/installer/core.py).

`core` is stdlib-only by design, so these need no textual and no network. They build a synthetic
skill (no `requirements.txt`, so `install` never shells out to pip) and drive the real install.

What they pin is the distinction the manifest exists for: a version string cannot tell "the repo
moved on" from "someone edited the installed copy", because whoever edits a copy in place does not
bump a version. Those two have opposite fixes, so conflating them is the failure worth a test.
"""

import json
import os
import sys
from pathlib import Path

import pytest

_SKILLS = Path(__file__).resolve().parents[1] / "skills"
sys.path.insert(0, str(_SKILLS))

from installer.core import (  # noqa: E402
    MANIFEST_FILE,
    MANIFEST_FORMAT,
    Agent,
    InstallStatus,
    Skill,
    fingerprint,
)
from installer.tui import _status, _version_cell  # noqa: E402


def _skill(root: Path, version: str = "1.0.0") -> Skill:
    source = root / "src" / "my-skill"
    (source / "scripts").mkdir(parents=True, exist_ok=True)
    (source / "SKILL.md").write_text(
        f"---\nname: my-skill\nversion: {version}\ndescription: A test skill.\n---\n\ndo the thing\n",
        encoding="utf-8",
    )
    (source / "scripts" / "run.py").write_text("print('hi')\n", encoding="utf-8")
    return Skill("my-skill", source)


class TestFingerprint:
    def test_reflects_content_and_names_but_ignores_build_artefacts(self, tmp_path: Path) -> None:
        skill = _skill(tmp_path)
        baseline = fingerprint(skill.source)

        # __pycache__ and .pyc are what a *copied* skill accumulates simply by being run; counting
        # them would report drift on every installed skill the moment the agent used it.
        (skill.source / "scripts" / "__pycache__").mkdir()
        (skill.source / "scripts" / "__pycache__" / "run.cpython-38.pyc").write_bytes(b"\x00\x01")
        assert fingerprint(skill.source) == baseline

        (skill.source / "scripts" / "run.py").write_text("print('bye')\n", encoding="utf-8")
        assert fingerprint(skill.source) != baseline

    @pytest.mark.skipif(os.name == "nt", reason="`:` is not a legal filename character on Windows")
    def test_name_and_content_cannot_be_confused_for_one_another(self, tmp_path: Path) -> None:
        # Why *both* halves carry a length prefix: `:` is the field separator and is a legal
        # filename character on POSIX, so hashing "<name>:<len>:<bytes>" would let a colon in a
        # name reproduce another folder's byte stream. Unconstructible on Windows, hence the skip.
        def folder(case: str, name: str, content: str) -> str:
            root = tmp_path / case
            root.mkdir()
            (root / name).write_text(content, encoding="utf-8")
            return fingerprint(root)

        # Without the name prefix both stream as "a:5:b:1:c" — verified; with it they diverge.
        assert folder("one", "a", "b:1:c") != folder("two", "a:5:b", "c")

    def test_renaming_a_file_changes_the_digest(self, tmp_path: Path) -> None:
        skill = _skill(tmp_path)
        baseline = fingerprint(skill.source)
        (skill.source / "scripts" / "run.py").rename(skill.source / "scripts" / "main.py")
        assert fingerprint(skill.source) != baseline


class TestInstallStatus:
    def test_tracks_a_fresh_install_then_both_directions_of_drift(self, tmp_path: Path) -> None:
        skill = _skill(tmp_path)
        agent = Agent("test", tmp_path / "agent" / "skills")

        absent = agent.status(skill)
        assert not absent.installed and absent.source_version == "1.0.0"

        assert agent.install(skill).ok
        dest = agent.destination(skill)
        assert (dest / MANIFEST_FILE).is_file()
        fresh = agent.status(skill)
        assert fresh.in_sync and fresh.tracked
        assert fresh.installed_version == "1.0.0" and fresh.source_version == "1.0.0"

        # The agent ran the installed skill: cache files must not read as an edit.
        (dest / "scripts" / "__pycache__").mkdir()
        (dest / "scripts" / "__pycache__" / "run.cpython-38.pyc").write_bytes(b"\x00\x01")
        assert agent.status(skill).in_sync

        # Repo moves on -> reinstall to update. Not "edited locally".
        (skill.source / "SKILL.md").write_text(
            "---\nname: my-skill\nversion: 1.1.0\ndescription: A test skill.\n---\n\nnew steps\n",
            encoding="utf-8",
        )
        outdated = agent.status(skill)
        assert outdated.source_changed and not outdated.local_changed
        assert outdated.installed_version == "1.0.0" and outdated.source_version == "1.1.0"

        # Someone edits the installed copy too: now both sides moved, and the local edit is the
        # one that matters — reinstalling would silently discard it.
        (dest / "scripts" / "run.py").write_text("print('patched in place')\n", encoding="utf-8")
        diverged = agent.status(skill)
        assert diverged.source_changed and diverged.local_changed

        # Reinstalling settles both and rewrites the manifest at the new version.
        assert agent.install(skill).ok
        assert agent.status(skill).in_sync
        assert agent.status(skill).installed_version == "1.1.0"

    def test_local_edit_alone_is_not_reported_as_the_repo_moving_on(self, tmp_path: Path) -> None:
        skill = _skill(tmp_path)
        agent = Agent("test", tmp_path / "agent" / "skills")
        assert agent.install(skill).ok

        (agent.destination(skill) / "scripts" / "run.py").write_text("print('local')\n", encoding="utf-8")
        status = agent.status(skill)
        assert status.local_changed and not status.source_changed

    def test_a_copy_installed_before_manifests_reads_as_untracked(self, tmp_path: Path) -> None:
        # The real case this shipped into: copies already under .claude/ have no manifest, so the
        # difference is visible but cannot be attributed to either side. Say so, don't guess.
        skill = _skill(tmp_path)
        agent = Agent("test", tmp_path / "agent" / "skills")
        assert agent.install(skill).ok
        (agent.destination(skill) / MANIFEST_FILE).unlink()

        assert agent.status(skill).tracked is False
        assert agent.status(skill).in_sync  # identical folders still read as in sync

        (agent.destination(skill) / "scripts" / "run.py").write_text("print('drifted')\n", encoding="utf-8")
        untracked = agent.status(skill)
        assert not untracked.tracked and not untracked.in_sync
        assert untracked.source_changed and untracked.local_changed  # differs, direction unknown

    def test_a_manifest_without_a_fingerprint_is_untracked_not_edited_in_place(self, tmp_path: Path) -> None:
        # A truncated or foreign-schema manifest knows nothing; reporting it as a local edit would
        # tell the user to rescue work that does not exist.
        skill = _skill(tmp_path)
        agent = Agent("test", tmp_path / "agent" / "skills")
        assert agent.install(skill).ok
        (agent.destination(skill) / MANIFEST_FILE).write_text('{"skill": "my-skill"}', encoding="utf-8")

        status = agent.status(skill)
        assert not status.tracked and status.in_sync  # folders still match, so: no drift claimed

    def test_a_manifest_from_another_fingerprint_algorithm_is_untracked_not_edited_in_place(
        self, tmp_path: Path
    ) -> None:
        # The upgrade case: `fingerprint` changes, so every existing manifest's digest no longer
        # matches a copy nobody touched. Without the format check that reads as ≠ - "rescue your
        # local edits" for edits that never happened. Caught for real on this repo's own install.
        skill = _skill(tmp_path)
        agent = Agent("test", tmp_path / "agent" / "skills")
        assert agent.install(skill).ok
        manifest_path = agent.destination(skill) / MANIFEST_FILE
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["format"] == MANIFEST_FORMAT  # a fresh install is always current

        manifest["format"] = MANIFEST_FORMAT + 1
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        status = agent.status(skill)
        assert not status.tracked and status.in_sync  # folders match, so claim no drift at all

    def test_a_corrupt_manifest_degrades_to_untracked_rather_than_crashing(self, tmp_path: Path) -> None:
        skill = _skill(tmp_path)
        agent = Agent("test", tmp_path / "agent" / "skills")
        assert agent.install(skill).ok
        (agent.destination(skill) / MANIFEST_FILE).write_text("{not json", encoding="utf-8")

        assert agent.status(skill).tracked is False

    def test_uninstall_takes_the_manifest_with_it(self, tmp_path: Path) -> None:
        skill = _skill(tmp_path)
        agent = Agent("test", tmp_path / "agent" / "skills")
        assert agent.install(skill).ok
        agent.uninstall(skill)

        assert not agent.destination(skill).exists()
        assert not agent.status(skill).installed


class TestGlyphs:
    """`_status` is where "local edits outrank a stale repo" is decided — swapping those two
    branches turns "your work is about to be destroyed" into "just reinstall"."""

    @staticmethod
    def _status_of(installed: bool, tracked: bool, source: bool, local: bool) -> str:
        return str(_status(InstallStatus(installed, tracked, source, local, "1.0.0", "1.1.0")))

    def test_every_state_maps_to_its_documented_glyph(self) -> None:
        assert self._status_of(False, False, False, False) == "·"
        assert self._status_of(True, True, False, False) == "✓"
        assert self._status_of(True, True, True, False) == "↑"
        assert self._status_of(True, True, False, True) == "≠"
        assert self._status_of(True, True, True, True) == "≠"  # local edits outrank a stale repo
        assert self._status_of(True, False, False, False) == "✓"
        assert self._status_of(True, False, True, True) == "?"  # differs, direction unknown

    def test_version_cell_shows_the_move_only_when_there_is_one(self) -> None:
        same = InstallStatus(True, True, False, False, "1.0.0", "1.0.0")
        moved = InstallStatus(True, True, True, False, "1.0.0", "1.1.0")
        assert str(_version_cell(same)) == "1.0.0"
        assert str(_version_cell(moved)) == "1.0.0 → 1.1.0"
        assert str(_version_cell(InstallStatus(False, False, False, False, "", ""))) == "—"
