"""Fundus skill installer.

:mod:`installer.core` is stdlib-only (discovery + install logic); :mod:`installer.tui` adds
the Textual dashboard. Importing this package pulls in only the core, so it stays usable
without textual installed.
"""

from __future__ import annotations

from .core import (
    REPO_ROOT,
    SKILLS_DIR,
    Agent,
    InstallResult,
    Skill,
    available_agents,
    discover_skills,
)

__all__ = [
    "REPO_ROOT",
    "SKILLS_DIR",
    "Agent",
    "InstallResult",
    "Skill",
    "available_agents",
    "discover_skills",
]
