#!/usr/bin/env python3
"""Install Fundus agent skills into your coding agent's config directory.

The skill *sources* live under ``skills/``, tracked in the repo, so the repo itself stays
agent-neutral (we don't commit any agent's config dir). Each skill is a self-contained
folder (``SKILL.md`` + ``PLAYBOOK.md`` + any bundled ``scripts/``); installing copies the
whole folder into your agent's config dir, which is gitignored (project scope) or lives
outside the repo entirely (user scope). Re-install after editing a source to refresh the
installed copy.

Run it with no arguments for a full-screen status dashboard::

    python skills/install.py

The dashboard is a live matrix of *skills* × *scopes* for the selected agent — toggle a
scope on the highlighted skill to (un)install it in place. It needs the ``textual`` package
(it ships in the project's ``dev`` extra: ``pip install -e .[dev]``).

This file is a thin launcher; the install logic lives in the ``installer`` package next to
it (``installer/core.py`` is stdlib-only, ``installer/tui.py`` is the Textual dashboard).
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    # Allow `python skills/install.py` to find the sibling `installer` package regardless
    # of the current working directory.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from installer.tui import run
    except ModuleNotFoundError as exc:
        if exc.name in {"textual", "rich"}:
            print(
                "The skill installer dashboard needs the 'textual' package.\n"
                "Install the project's dev extra:  pip install -e .[dev]",
                file=sys.stderr,
            )
            return 1
        raise
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
