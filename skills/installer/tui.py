"""Textual dashboard for the skill installer.

A live list of *skills* for the selected agent. The **Installed** column shows both presence and
drift: ``✓`` in sync, ``↑`` repo moved on, ``≠`` copy edited in place, ``·`` absent. Move the
cursor to a skill and toggle it to install (if absent) or uninstall (if present) — in place, no
re-running.

This module owns everything textual/rich; all install logic lives in :mod:`installer.core`.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, RadioButton, RadioSet, RichLog, Static

from .core import Agent, InstallResult, InstallStatus, Skill, available_agents, discover_skills

_YES = Text("✓", style="bold green", justify="center")
_NO = Text("·", style="dim", justify="center")
# Kept apart because the fix differs: ↑ reinstall; ≠ the copy holds work a reinstall would lose.
_OUTDATED = Text("↑", style="bold yellow", justify="center")
_MODIFIED = Text("≠", style="bold magenta", justify="center")
# Pre-manifest install whose folders differ: real drift, direction unknown.
_UNKNOWN = Text("?", style="bold yellow", justify="center")
# Install failed and was rolled back: a transient marker, replaced by · on the next refresh
# (the rollback makes "not installed" the true steady state, so refresh doesn't lie).
_FAILED = Text("!", style="bold red", justify="center")
_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"  # braille "wheel": a busy cell cycles through these frames
_INSTALLED_COL = "installed"
_VERSION_COL = "version"


def _status(status: InstallStatus) -> Text:
    """One glyph for the row. Local edits outrank a stale repo: reinstalling would lose them."""
    if not status.installed:
        return _NO
    if status.in_sync:
        return _YES
    if not status.tracked:
        return _UNKNOWN  # differs, but nothing says which side moved
    return _MODIFIED if status.local_changed else _OUTDATED


def _version_cell(status: InstallStatus) -> Text:
    """The source version, prefixed with the installed one when they differ."""
    source = status.source_version or "—"
    if status.installed and status.installed_version and status.installed_version != status.source_version:
        return Text(f"{status.installed_version} → {source}", style="yellow")
    return Text(source, style="dim")


def _spinner_cell(frame: int) -> Text:
    return Text(_SPINNER[frame % len(_SPINNER)], style="bold yellow", justify="center")


class InstallerApp(App[None]):
    """Live list of skills, with install status, for the selected agent."""

    TITLE = "Fundus Skill Installer"

    # The skills table is the point of the screen: it gets the flexible space *and* a minimum,
    # so a short terminal shrinks the log, never the skills. The agent panel only exists
    # when there is an actual choice to make (see compose).
    CSS = """
    DataTable { height: 1fr; min-height: 6; margin: 1 1 0 1; border: round $primary; }
    #agent { height: auto; border: round $primary; padding: 0 1; margin: 1 1 0 1; }
    #agent > RadioButton { width: auto; }
    #desc { height: auto; border: round $panel; padding: 0 1; margin: 1 1 0 1; }
    RichLog { height: 10; border: round $panel; padding: 0 1; margin: 1; }
    """

    BINDINGS = [
        Binding("space", "toggle_skill", "Install / uninstall"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    skills: Dict[str, Skill]
    agents: Dict[str, Agent]
    table: DataTable[Text]
    detail: Static
    output: RichLog

    def __init__(self) -> None:
        super().__init__()
        self.skills = discover_skills()
        self.agents = available_agents()
        self._agent_names = sorted(self.agents)
        # Skills with an install in flight; the spinner timer animates their cells.
        self._busy: Set[str] = set()
        self._frame = 0

    def compose(self) -> ComposeResult:
        yield Header()
        if len(self._agent_names) > 1:
            with RadioSet(id="agent"):
                for i, name in enumerate(self._agent_names):
                    yield RadioButton(name, value=(i == 0))
        self.table = DataTable(cursor_type="row", zebra_stripes=True)
        yield self.table
        self.detail = Static(id="desc")
        yield self.detail
        self.output = RichLog(id="log", markup=True, wrap=True)
        yield self.output
        yield Footer()

    def on_mount(self) -> None:
        if len(self._agent_names) > 1:
            self.query_one("#agent", RadioSet).border_title = "Agent"
        else:
            self.sub_title = f"agent: {self._agent_names[0]}"
        self.table.border_title = (
            "Skills - ✓ in sync | ↑ repo newer | ≠ edited in place | ? unknown | ! failed | · absent"
        )
        self.table.border_subtitle = "↑/↓ pick a skill · space to (un)install"
        self.detail.border_title = "Description"
        self.output.border_title = "Log"
        self.table.add_column("Skill", key="skill")
        self.table.add_column("Installed", key=_INSTALLED_COL, width=12)
        self.table.add_column("Version", key=_VERSION_COL, width=16)
        self._rebuild()
        self.table.focus()
        self._show_description(self._highlighted_skill())
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
            status = agent.status(skill)
            self.table.add_row(
                Text(name, style="bold"),
                _status(status),
                _version_cell(status),
                key=name,
            )

    def _show_description(self, skill: Optional[Skill]) -> None:
        """Render the highlighted skill's full description in the detail panel.

        Shown in full (never truncated) and as literal ``Text`` so any ``[...]`` in a
        description isn't eaten as console markup."""
        if skill is not None and skill.description:
            self.detail.update(Text(skill.description))
        else:
            self.detail.update(Text("(no description)", style="dim"))

    def _refresh_row(self, name: str) -> None:
        agent = self._agent()
        status = agent.status(self.skills[name])
        self.table.update_cell(name, _INSTALLED_COL, _status(status))
        self.table.update_cell(name, _VERSION_COL, _version_cell(status))

    def _write_log(self, lines: List[str], style: str = "") -> None:
        """Write core-produced log lines as literal Text — styled, and safe against any
        ``[...]`` in pip output that a markup-parsing RichLog would otherwise eat."""
        for line in lines:
            self.output.write(Text(line, style=style))

    # --- actions ---

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        self._rebuild()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._show_description(self.skills.get(str(event.row_key.value)))

    def action_toggle_skill(self) -> None:
        skill = self._highlighted_skill()
        if skill is None:
            return
        if self._busy:
            return  # an install is in flight — ignore toggles until it finishes
        agent = self._agent()
        # Keyed on presence, not sync state: space on a ↑/≠ row uninstalls, same as on ✓.
        if agent.is_installed(skill):
            self._write_log(agent.uninstall(skill))
            self._refresh_row(skill.name)
            return
        # Install may pip-install requirements, which blocks for seconds. Run it in a worker
        # thread so the event loop stays free to animate the spinner; mark the cell busy and
        # show the first frame at once so there's no dead beat before the timer ticks.
        self._busy.add(skill.name)
        self.table.update_cell(skill.name, _INSTALLED_COL, _spinner_cell(self._frame))
        if skill.requirements is not None:
            self.output.write(f"[dim]installing '{skill.name}' — fetching requirements, please wait…[/]")
        self._do_install(agent, skill)

    @work(thread=True)
    def _do_install(self, agent: Agent, skill: Skill) -> None:
        try:
            result = agent.install(skill)
        except Exception as exc:  # never let a crashed worker leave the cell spinning forever
            result = InstallResult(False, [f"  ! install failed for '{skill.name}': {exc}"])
        self.call_from_thread(self._install_done, skill.name, result)

    def _install_done(self, name: str, result: InstallResult) -> None:
        self._busy.discard(name)
        self._write_log(result.log, "green" if result.ok else "red")  # mirrors the ✓ / !
        if result.ok:
            self._refresh_row(name)  # replaces the spinner with the final ✓
        else:
            # Rolled back: flag this attempt with ! now; a refresh will settle it to ·.
            self.table.update_cell(name, _INSTALLED_COL, _FAILED)

    def _tick(self) -> None:
        if not self._busy:
            return
        self._frame += 1
        cell = _spinner_cell(self._frame)
        for name in self._busy:
            self.table.update_cell(name, _INSTALLED_COL, cell)

    def action_refresh(self) -> None:
        self._rebuild()
        self.output.write("[dim]refreshed from disk[/]")


def run() -> None:
    """Launch the dashboard."""
    InstallerApp().run()
