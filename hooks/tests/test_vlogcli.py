# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses of `mikemol-vlog` through `main`: lines spool, the producer's status passes.

W1179. ⚑ THE DETACHED DRAINER IS A SEAM, NOT A PROCESS: `spawn` records the argv it was given, so
"the caller starts a drainer and returns" is read from what was passed, and no process is left
running. ⚑ THE FILE FORM IS RUN THREE TIMES to show the offset: everything, nothing new, then only
the line appended. ⚑ THE WRAPPER'S EXIT STATUS (5) IS A NUMBER NO OTHER PART OF THE PATH PRODUCES.
"""

from __future__ import annotations

import io
import json
import sys
from typing import TYPE_CHECKING, cast

from mikemol.hooks import vlogcli, vlogconfig, vlogdetach, vlogship

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_USAGE = 2
_FIVE = 5
_TWO = 2
Doc = dict[str, object]


def _spooled(spool_dir: Path) -> list[Doc]:
    """Read every record in every spool under `spool_dir`.

    Returns:
        the records, spool by spool.

    """
    found: list[Doc] = []
    for path in sorted(spool_dir.glob("vlog-*.spool")):
        found.extend(
            cast("Doc", json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines()
        )
    return found


def _run(tmp_path: Path, *extra: str, stdin: str = "") -> tuple[int, list[Sequence[str]]]:
    """Run main against a spool in `tmp_path`, with a recording spawn.

    Returns:
        the exit code and the argvs handed to spawn.

    """
    spawned: list[Sequence[str]] = []
    base = ["--spool-dir", str(tmp_path / "spool"), "--config", str(tmp_path / "none.toml")]
    code = vlogcli.main([*base, *extra], io.StringIO(stdin), spawned.append)
    return code, spawned


def test_stdin_lines_are_spooled_with_the_stream_fields_and_a_drainer_is_started(
    tmp_path: Path,
) -> None:
    """Two lines become two records; exit 0; exactly one detached drain argv, naming the spool."""
    code, spawned = _run(tmp_path, "--stream", "tool=commit", stdin='{"message": "a"}\nplain\n')
    assert code == 0
    records = _spooled(tmp_path / "spool")
    assert [r["_msg"] for r in records] == ["a", "plain"]
    assert records[0]["tool"] == "commit"
    assert records[1]["parse_failure"] == "not-json"
    assert len(spawned) == 1
    assert "--drain" in spawned[0]
    assert str(tmp_path / "spool") in spawned[0]


def test_no_drain_spools_and_starts_nothing(tmp_path: Path) -> None:
    """The control for the spawn above: with --no-drain the seam is never called."""
    code, spawned = _run(tmp_path, "--no-drain", stdin="x\n")
    assert code == 0
    assert not spawned
    assert len(_spooled(tmp_path / "spool")) == 1


def test_the_wrapper_returns_the_commands_own_status_and_spools_its_lines(tmp_path: Path) -> None:
    """The command prints a record and exits 5: 5 comes back, the record is in the spool."""
    code, _spawned = _run(
        tmp_path,
        "--no-drain",
        "--stream",
        "tool=gate",
        "--",
        sys.executable,
        "-c",
        'print(\'{"message": "ran"}\'); raise SystemExit(5)',
    )
    assert code == _FIVE
    assert [r["_msg"] for r in _spooled(tmp_path / "spool")] == ["ran"]


def test_the_file_form_spools_each_line_once_across_three_runs(tmp_path: Path) -> None:
    """All lines, then none, then only the one appended; the state file is the only memory."""
    log = tmp_path / "app.log"
    state = tmp_path / "app.state"
    log.write_text("one\ntwo\n", encoding="utf-8")
    args = ("--no-drain", "--from-file", str(log), "--state", str(state))
    assert _run(tmp_path, *args)[0] == 0
    assert [r["_msg"] for r in _spooled(tmp_path / "spool")] == ["one", "two"]
    assert _run(tmp_path, *args)[0] == 0
    assert len(_spooled(tmp_path / "spool")) == _TWO
    with log.open("a", encoding="utf-8") as handle:
        handle.write("three\n")
    assert _run(tmp_path, *args)[0] == 0
    assert [r["_msg"] for r in _spooled(tmp_path / "spool")] == ["one", "two", "three"]


def test_a_stream_without_an_equals_sign_is_a_usage_error_and_spools_nothing(
    tmp_path: Path,
) -> None:
    """`--stream bad` exits 2 and creates no spool."""
    code, spawned = _run(tmp_path, "--stream", "bad", stdin="x\n")
    assert code == _USAGE
    assert not spawned
    assert not (tmp_path / "spool").exists()


def test_drain_in_front_with_no_service_says_there_is_no_destination(tmp_path: Path) -> None:
    """Spool a line, then --drain: nothing sent, one left, exit 1."""
    _run(tmp_path, "--no-drain", stdin="x\n")
    code, _spawned = _run(tmp_path, "--drain")
    assert code == 1
    assert len(_spooled(tmp_path / "spool")) == 1


def test_a_flag_overrides_the_config_file_and_the_file_overrides_the_default() -> None:
    """The file sets service and max_lines; a flag changes max_lines; the service stays."""
    table: Doc = {"service": "logs", "max_lines": 7, "resolver": ["q", "{name}"]}
    from_file = vlogconfig.build(table, vlogconfig.Flags())
    assert (from_file.service, from_file.max_lines) == ("logs", 7)
    assert from_file.resolver == ("q", "{name}")
    flagged = vlogconfig.build(table, vlogconfig.Flags(max_lines=9))
    assert (flagged.service, flagged.max_lines) == ("logs", 9)
    assert vlogconfig.build({}, vlogconfig.Flags()).max_lines == vlogconfig.DEFAULT_MAX_LINES


def test_the_drainer_argv_carries_the_same_settings(tmp_path: Path) -> None:
    """Spool directory, bounds, service and every resolver argument reach the detached process."""
    config = vlogship.Config(tmp_path, "logs", ("q", "{name}"), 11, 22)
    argv = vlogdetach.drain_argv(config)
    assert argv[1:4] == ["-m", "mikemol.hooks.vlogcli", "--drain"]
    assert argv[argv.index("--spool-dir") + 1] == str(tmp_path)
    assert argv[argv.index("--max-lines") + 1] == "11"
    assert argv[argv.index("--max-bytes") + 1] == "22"
    assert argv[argv.index("--service") + 1] == "logs"
    assert argv.count("--resolver-arg") == _TWO
