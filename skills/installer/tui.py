"""Textual dashboard for the skill installer.

A live matrix of *skills* × *scopes* for the selected agent. Each row is a skill; the
**Project** and **User** columns show whether it's installed (``✓``) or not (``·``). Move
the cursor to a skill and toggle a scope to install it (if absent) or uninstall it (if
present) — the matrix updates in place, no re-running.

This module owns everything textual/rich; all install logic lives in :mod:`installer.core`.
"""

from __future__ import annotations

import textwrap
from typing import Dict, List, Optional, Set, Tuple

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, RadioButton, RadioSet, RichLog

from .core import Agent, InstallResult, Skill, available_agents, discover_skills

_YES = Text("✓", style="bold green", justify="center")
_NO = Text("·", style="dim", justify="center")
# Install failed and was rolled back: a transient marker, replaced by · on the next refresh
# (the rollback makes "not installed" the true steady state, so refresh doesn't lie).
_FAILED = Text("!", style="bold red", justify="center")
_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"  # braille "wheel": a busy cell cycles through these frames


def _status(installed: bool) -> Text:
    return _YES if installed else _NO


def _spinner_cell(frame: int) -> Text:
    return Text(_SPINNER[frame % len(_SPINNER)], style="bold yellow", justify="center")


class InstallerApp(App[None]):
    """Live skills × scopes matrix for the selected agent."""

    TITLE = "Fundus Skill Installer"

    # The matrix is the point of the screen: it gets the flexible space *and* a minimum,
    # so a short terminal shrinks the log, never the skills. The agent panel only exists
    # when there is an actual choice to make (see compose).
    CSS = """
    DataTable { height: 1fr; min-height: 6; margin: 1 1 0 1; border: round $primary; }
    #agent { height: auto; border: round $primary; padding: 0 1; margin: 1 1 0 1; }
    #agent > RadioButton { width: auto; }
    RichLog { height: 5; border: round $panel; padding: 0 1; margin: 1; }
    """

    BINDINGS = [
        Binding("p", "toggle_scope('project')", "Toggle project"),
        Binding("u", "toggle_scope('user')", "Toggle user"),
        Binding("r", "refresh_matrix", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    skills: Dict[str, Skill]
    agents: Dict[str, Agent]
    table: DataTable[Text]
    output: RichLog

    def __init__(self) -> None:
        super().__init__()
        self.skills = discover_skills()
        self.agents = available_agents()
        self._agent_names = sorted(self.agents)
        # (skill, scope) cells with an install in flight; the spinner timer animates these.
        self._busy: Set[Tuple[str, str]] = set()
        self._frame = 0

    def compose(self) -> ComposeResult:
        yield Header()
        if len(self._agent_names) > 1:
            with RadioSet(id="agent"):
                for i, name in enumerate(self._agent_names):
                    yield RadioButton(name, value=(i == 0))
        self.table = DataTable(cursor_type="row", zebra_stripes=True)
        yield self.table
        self.output = RichLog(id="log", markup=True, wrap=True)
        yield self.output
        yield Footer()

    def on_mount(self) -> None:
        if len(self._agent_names) > 1:
            self.query_one("#agent", RadioSet).border_title = "Agent"
        else:
            self.sub_title = f"agent: {self._agent_names[0]}"
        self.table.border_title = "Skills - ✓ = installed in that scope"
        self.table.border_subtitle = "↑/↓ pick a skill · press p / u to (un)install"
        self.output.border_title = "Log"
        self.table.add_column("Skill", key="skill")
        self.table.add_column("Project (p)", key="project", width=12)
        self.table.add_column("User (u)", key="user", width=12)
        self.table.add_column("Description", key="desc")
        self._rebuild()
        self.table.focus()
        self.output.write("[dim]toggling installs if absent, uninstalls if present · r refresh · q quit[/]")
        self.set_interval(0.1, self._tick)  # animates the spinner in any busy cell

    # --- state readers ---

    def _agent(self) -> Agent:
        if len(self._agent_names) == 1:
            return self.agents[self._agent_names[0]]
        index = self.query_one("#agent", RadioSet).pressed_index
        return self.agents[self._agent_names[index if index >= 0 else 0]]

    def _highlighted_skill(self) -> Optional[Skill]:
        names = sorted(self.skills)
        row = self.table.cursor_row
        return self.skills[names[row]] if 0 <= row < len(names) else None

    # --- rendering ---

    def _rebuild(self) -> None:
        """Repopulate every row from disk for the current agent."""
        agent = self._agent()
        self.table.clear()
        for name in sorted(self.skills):
            skill = self.skills[name]
            self.table.add_row(
                Text(name, style="bold"),
                _status(agent.is_installed("project", skill)),
                _status(agent.is_installed("user", skill)),
                Text(textwrap.shorten(skill.description, width=70, placeholder="…")),
                key=name,
            )

    def _refresh_row(self, name: str) -> None:
        agent = self._agent()
        skill = self.skills[name]
        self.table.update_cell(name, "project", _status(agent.is_installed("project", skill)))
        self.table.update_cell(name, "user", _status(agent.is_installed("user", skill)))

    def _write_log(self, lines: List[str], style: str = "") -> None:
        """Write core-produced log lines as literal Text — styled, and safe against any
        ``[...]`` in pip output that a markup-parsing RichLog would otherwise eat."""
        for line in lines:
            self.output.write(Text(line, style=style))

    # --- actions ---

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        self._rebuild()

    def action_toggle_scope(self, scope: str) -> None:
        skill = self._highlighted_skill()
        if skill is None:
            return
        if self._busy:
            return  # an install is in flight — ignore toggles until it finishes
        agent = self._agent()
        if agent.is_installed(scope, skill):
            self._write_log(agent.uninstall(scope, skill))
            self._refresh_row(skill.name)
            return
        # Install may pip-install requirements, which blocks for seconds. Run it in a worker
        # thread so the event loop stays free to animate the spinner; mark the cell busy and
        # show the first frame at once so there's no dead beat before the timer ticks.
        self._busy.add((skill.name, scope))
        self.table.update_cell(skill.name, scope, _spinner_cell(self._frame))
        if skill.requirements is not None:
            self.output.write(f"[dim]installing '{skill.name}' ({scope}) — fetching requirements, please wait…[/]")
        self._do_install(agent, scope, skill)

    @work(thread=True)
    def _do_install(self, agent: Agent, scope: str, skill: Skill) -> None:
        try:
            result = agent.install(scope, skill)
        except Exception as exc:  # never let a crashed worker leave the cell spinning forever
            result = InstallResult(False, [f"  ! install failed for '{skill.name}': {exc}"])
        self.call_from_thread(self._install_done, skill.name, scope, result)

    def _install_done(self, name: str, scope: str, result: InstallResult) -> None:
        self._busy.discard((name, scope))
        self._write_log(result.log, "green" if result.ok else "red")  # mirrors the matrix ✓ / !
        if result.ok:
            self._refresh_row(name)  # replaces the spinner with the final ✓
        else:
            # Rolled back: flag this attempt with ! now; a refresh will settle it to · (the
            # only other cell, the sibling scope, is untouched so we don't disturb it).
            self.table.update_cell(name, scope, _FAILED)

    def _tick(self) -> None:
        if not self._busy:
            return
        self._frame += 1
        cell = _spinner_cell(self._frame)
        for name, scope in self._busy:
            self.table.update_cell(name, scope, cell)

    def action_refresh_matrix(self) -> None:
        self._rebuild()
        self.output.write("[dim]refreshed from disk[/]")


def run() -> None:
    """Launch the dashboard."""
    InstallerApp().run()
