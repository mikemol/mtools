# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `pulse`: the fleet view, standing warnings hidden, the top of the ranking."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.procrun.proc import capture

from mikemol.katas import fleet, pulse

if TYPE_CHECKING:
    from pathlib import Path

_EXECUTABLE = 0o755
_CHECK_OUTPUT = (
    "OK        alpha\n"
    "  Warning   --     no working card while items are ready\n"
    "  Warning   W9     title over 150 chars\n"
    "  Warning   W7     blocked_on names a waypoint that has already landed\n"
    "  VIOLATES  W3     enables names nothing\n"
)
_RANK_LINES = 20


def _tool(directory: Path, name: str, body: str) -> None:
    """Write a stand-in nemik tool that prints `body`."""
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / name
    script.write_text(f"#!/bin/sh\ncat <<'EOF'\n{body}EOF\n", encoding="utf-8")
    script.chmod(_EXECUTABLE)


def _nemik(tmp_path: Path, check: str = _CHECK_OUTPUT) -> Path:
    """Write fake nemik-check and nemik-rank tools.

    Returns:
        the directory holding them.

    """
    directory = tmp_path / "nemik"
    _tool(directory, "nemik-check", check)
    ranking = "".join(f"rank {n}\n" for n in range(_RANK_LINES))
    _tool(directory, "nemik-rank", ranking)
    return directory


def _host(tmp_path: Path) -> fleet.Fleet:
    """Build a fleet with one workstream, so status has a row.

    Returns:
        the fleet.

    """
    host = fleet.Fleet(tmp_path / "hosts", tmp_path / "logs")
    repo = host.root / "alpha"
    (repo / ".claude").mkdir(parents=True)
    (repo / ".claude" / "paths-forward.json").write_text("{}", encoding="utf-8")
    capture(("git", "init", "-q", str(repo)))
    return host


def test_only_warnings_and_violations_are_picked() -> None:
    """The OK line and anything else is not shown."""
    got = pulse.warning_lines(_CHECK_OUTPUT)
    assert len(got) == len(_CHECK_OUTPUT.splitlines()) - 1


def test_a_standing_substring_hides_its_warning() -> None:
    """The operator has accepted these, so they do not page again."""
    got = pulse.warning_lines(_CHECK_OUTPUT, ["no working card", "title over 150"])
    assert [line.split()[1] for line in got] == ["W7", "W3"]


def test_a_violation_is_never_hidden_by_a_warning_substring() -> None:
    """A VIOLATES line still shows when the standing list names only warnings' words."""
    got = pulse.warning_lines(_CHECK_OUTPUT, ["no working card"])
    assert any("VIOLATES" in line for line in got)


def test_the_pulse_has_status_then_warnings_then_the_top_of_the_ranking(tmp_path: Path) -> None:
    """Three sections in that order, with the ranking cut to its first rows."""
    lines = pulse.pulse(_host(tmp_path), _nemik(tmp_path), ["no working card", "title over 150"])
    assert lines[0].startswith("alpha")
    heading = lines.index("-- nemik-check (warnings other than the standing ones)")
    rank = lines.index(f"-- nemik-rank --all, top {pulse.RANK_ROWS}")
    assert heading < rank
    assert lines[rank + 1 :] == [f"rank {n}" for n in range(pulse.RANK_ROWS)]


def test_no_unhidden_warning_reads_none(tmp_path: Path) -> None:
    """A clean check shows (none) rather than an empty section."""
    lines = pulse.pulse(_host(tmp_path), _nemik(tmp_path, "OK        alpha\n"))
    heading = lines.index("-- nemik-check (warnings other than the standing ones)")
    assert lines[heading + 1] == pulse.NONE_SHOWN
