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
    """Spool a line, then --drain: nothing sent, one left, exit 3 and the reason on stderr."""
    _run(tmp_path, "--no-drain", stdin="x\n")
    kept, sys.stderr = sys.stderr, io.StringIO()
    try:
        code, _spawned = _run(tmp_path, "--drain")
        said = sys.stderr.getvalue()
    finally:
        sys.stderr = kept
    assert code == vlogcli.EXIT_NO_DESTINATION
    assert "no destination" in said
    assert len(_spooled(tmp_path / "spool")) == 1


def test_a_drain_that_left_lines_names_its_class_as_the_exit_status() -> None:
    """W1214: no destination 3, an answered refusal 4, a busy spool 5, no reason at all 1."""
    assert vlogcli.drain_class("no destination: no service named") == vlogcli.EXIT_NO_DESTINATION
    assert vlogcli.drain_class("503 Service Unavailable") == vlogcli.EXIT_REFUSED
    assert vlogcli.drain_class("busy: another drainer holds it (moving)") == vlogcli.EXIT_BUSY
    assert vlogcli.drain_class("") == 1


def test_a_flag_overrides_the_config_file_and_the_file_overrides_the_default() -> None:
    """The file sets service and max_lines; a flag changes max_lines; the service stays."""
    table: Doc = {"service": "logs", "max_lines": 7, "resolver": ["q", "{name}"]}
    from_file = vlogconfig.build(table, vlogconfig.Flags())
    assert (from_file.service, from_file.max_lines) == ("logs", 7)
    assert from_file.resolver == ("q", "{name}")
    flagged = vlogconfig.build(table, vlogconfig.Flags(max_lines=9))
    assert (flagged.service, flagged.max_lines) == ("logs", 9)
    assert vlogconfig.build({}, vlogconfig.Flags()).max_lines == vlogconfig.DEFAULT_MAX_LINES


_STAMPS = (
    "[stamps.logfmt]\n"
    "pattern = '^time=\"([0-9T:.+\\-Z]+)\"'\n"
    'form = "iso"\n'
    "[stamps.epoch]\n"
    "pattern = '^(\\d{9,11}):'\n"
    'form = "epoch"\n'
)


def _stamped(tmp_path: Path, name: str, stdin: str) -> tuple[int, list[Doc]]:
    """Run main with a stamp kind from a config file declaring both of luthen's shapes.

    Returns:
        the exit code and the spooled records.

    """
    config = tmp_path / "stamps.toml"
    config.write_text(_STAMPS, encoding="utf-8")
    spool = ["--spool-dir", str(tmp_path / "spool"), "--no-drain", "--config", str(config)]
    code = vlogcli.main([*spool, "--stamp", name, "--stream", "k=v"], io.StringIO(stdin), print)
    return code, _spooled(tmp_path / "spool")


def test_a_logfmt_stamp_gives_old_lines_their_own_time_and_a_miss_says_so(tmp_path: Path) -> None:
    """The matched line keeps its time; the unmatched one is stamped now AND flagged."""
    code, records = _stamped(
        tmp_path, "logfmt", 'time="2026-10-13T20:11:40Z" level=info msg=x\nno stamp here\n'
    )
    assert code == 0
    assert records[0]["_time"] == "2026-10-13T20:11:40.000000Z"
    assert records[0]["parse_failure"] == "not-json"
    assert "time_unparsed" not in records[0]
    assert records[1]["time_unparsed"] == "true"
    assert records[1]["_time"] != records[0]["_time"]


def test_an_epoch_prefixed_stamp_reads_seconds(tmp_path: Path) -> None:
    """`1760400000:` is 2025-10-14T00:00:00Z; the rest of the line stays the message."""
    code, records = _stamped(tmp_path, "epoch", "1760400000: hello\n")
    assert code == 0
    assert records[0]["_time"] == "2025-10-14T00:00:00.000000Z"
    assert records[0]["_msg"] == "1760400000: hello"


def test_an_undeclared_stamp_is_a_usage_error_and_spools_nothing(tmp_path: Path) -> None:
    """A typo must not silently fall back to the ship time: exit 2, nothing spooled."""
    code, _records = _stamped(tmp_path, "logfnt", "x\n")
    assert code == _USAGE
    assert not (tmp_path / "spool").exists()


def test_an_undeclared_stamp_names_what_is_declared() -> None:
    """The refusal lists the kinds that are declared, so the typo is findable."""
    table: Doc = {"stamps": {"logfmt": {"pattern": "(a)"}, "epoch": {"pattern": "(b)"}}}
    reason = str(vlogconfig.stamp_named(table, "logfnt"))
    assert "logfnt" in reason
    assert "epoch, logfmt" in reason


def test_a_stamp_that_cannot_be_used_is_refused_with_its_reason() -> None:
    """Two groups, an uncompilable pattern and an unknown form each say which they are."""
    bad: Doc = {
        "stamps": {
            "two": {"pattern": "(a)(b)"},
            "broken": {"pattern": "("},
            "odd": {"pattern": "(a)", "form": "julian"},
        }
    }
    assert "exactly one capture group" in str(vlogconfig.stamp_named(bad, "two"))
    assert "does not compile" in str(vlogconfig.stamp_named(bad, "broken"))
    assert "form of iso or epoch" in str(vlogconfig.stamp_named(bad, "odd"))


_THREE = 3
_HUNDRED = 100
_SOURCES = (
    "max_lines = 100\n"
    "[source.app]\n"
    "max_lines = 2\n"
    'on_full = "hold"\n'
    "[source.loose]\n"
    "max_lines = 2\n"
    'on_full = "drop-oldest"\n'
    "[source.typo]\n"
    'on_full = "hodl"\n'
)


def _sourced(tmp_path: Path, source: str, *extra: str, stdin: str = "") -> int:
    """Run main against a config whose [source.NAME] tables declare three policies.

    Returns:
        the exit code.

    """
    config = tmp_path / "sources.toml"
    config.write_text(_SOURCES, encoding="utf-8")
    base = ["--spool-dir", str(tmp_path / "spool"), "--no-drain", "--config", str(config)]
    argv = [*base, "--source", source, "--stream", "k=v", *extra]
    return vlogcli.main(argv, io.StringIO(stdin), print)


def _forget_the_spool(tmp_path: Path) -> list[str]:
    """Take what the spool holds and empty it, as a successful drain would.

    Returns:
        the `_msg` of each record that was in it.

    """
    taken = [str(r["_msg"]) for r in _spooled(tmp_path / "spool")]
    for path in (tmp_path / "spool").glob("vlog-*.spool"):
        path.write_text("", encoding="utf-8")
    return taken


def test_hold_reads_only_what_fits_and_the_tail_comes_back_on_the_next_runs(
    tmp_path: Path,
) -> None:
    """Five lines, room for two: each run spools two, the rest stays in the file, none is lost."""
    log = tmp_path / "app.log"
    log.write_text("1\n2\n3\n4\n5\n", encoding="utf-8")
    args = ("--from-file", str(log), "--state", str(tmp_path / "app.state"))
    delivered: list[str] = []
    for _ in range(_THREE):
        assert _sourced(tmp_path, "app", *args) == 0
        delivered += _forget_the_spool(tmp_path)
    assert delivered == ["1", "2", "3", "4", "5"]


def test_exit_classes_make_a_held_tail_exit_six_and_the_default_stays_zero(tmp_path: Path) -> None:
    """W1214: five lines, room for two. Without the flag the run is 0 as ever; with it, 6."""
    log = tmp_path / "app.log"
    log.write_text("1\n2\n3\n4\n5\n", encoding="utf-8")
    args = ("--from-file", str(log), "--state", str(tmp_path / "app.state"))
    assert _sourced(tmp_path, "app", *args) == 0
    _forget_the_spool(tmp_path)
    kept, sys.stderr = sys.stderr, io.StringIO()
    try:
        status = _sourced(tmp_path, "app", *args, "--exit-classes")
        said = sys.stderr.getvalue()
    finally:
        sys.stderr = kept
    assert status == vlogcli.EXIT_HELD
    assert "ceiling" in said
    _forget_the_spool(tmp_path)
    log.write_text("6\n", encoding="utf-8")
    assert _sourced(tmp_path, "loose", *args, "--exit-classes") == 0


def test_hold_into_a_spool_that_is_still_full_consumes_nothing(tmp_path: Path) -> None:
    """Nobody drained: the second run spools nothing and the offset has not moved past the held."""
    log = tmp_path / "app.log"
    log.write_text("1\n2\n3\n4\n", encoding="utf-8")
    args = ("--from-file", str(log), "--state", str(tmp_path / "app.state"))
    assert _sourced(tmp_path, "app", *args) == 0
    assert [r["_msg"] for r in _spooled(tmp_path / "spool")] == ["1", "2"]
    assert _sourced(tmp_path, "app", *args) == 0
    assert [r["_msg"] for r in _spooled(tmp_path / "spool")] == ["1", "2"]


def test_drop_oldest_with_the_same_ceiling_takes_every_line_and_drops_the_oldest(
    tmp_path: Path,
) -> None:
    """The control: the other policy consumes all five lines at once and keeps the newest two."""
    log = tmp_path / "app.log"
    log.write_text("1\n2\n3\n4\n5\n", encoding="utf-8")
    args = ("--from-file", str(log), "--state", str(tmp_path / "app.state"))
    assert _sourced(tmp_path, "loose", *args) == 0
    messages = [str(r["_msg"]) for r in _spooled(tmp_path / "spool")]
    assert "5" in messages
    assert "1" not in messages
    assert _sourced(tmp_path, "loose", *args) == 0


def test_hold_with_stdin_is_refused_because_stdin_cannot_be_read_again(tmp_path: Path) -> None:
    """Exit 2 and nothing spooled: a stream that is consumed has no tail to leave."""
    assert _sourced(tmp_path, "app", stdin="x\n") == _USAGE
    assert not (tmp_path / "spool").exists()


def test_an_undeclared_source_and_a_mistyped_policy_are_usage_errors(tmp_path: Path) -> None:
    """Neither falls back to a default: exit 2 for `nope` and for `on_full = "hodl"`."""
    assert _sourced(tmp_path, "nope", stdin="x\n") == _USAGE
    assert _sourced(tmp_path, "typo", stdin="x\n") == _USAGE


def test_a_source_table_overrides_the_top_level_and_the_top_level_is_the_default() -> None:
    """`app` sets max_lines 2 and hold; the top-level 100 stays for a source that sets none."""
    table: Doc = {"max_lines": 100, "source": {"app": {"max_lines": 2, "on_full": "hold"}}}
    app = vlogconfig.merged_table(table, "app")
    assert isinstance(app, dict)
    assert (app["max_lines"], app["on_full"]) == (2, "hold")
    assert vlogconfig.build(app, vlogconfig.Flags()).on_full == "hold"
    plain = vlogconfig.merged_table(table, None)
    assert isinstance(plain, dict)
    assert plain["max_lines"] == _HUNDRED
    assert vlogconfig.build(plain, vlogconfig.Flags()).on_full == "drop-oldest"
    assert "not declared" in str(vlogconfig.merged_table(table, "nope"))


def test_per_source_caps_that_add_up_to_more_than_the_total_are_refused_by_name() -> None:
    """W1213: `a` 6 and `b` 6 against a total of 10 is refused, naming the caps and the total."""
    table: Doc = {"max_lines": 10, "source": {"a": {"max_lines": 6}, "b": {"max_lines": 6}}}
    reason = vlogconfig.merged_table(table, "a")
    assert isinstance(reason, str)
    assert "max_lines" in reason
    assert "a=6, b=6" in reason
    assert "total 10" in reason


def test_caps_that_fit_an_uncapped_source_and_a_bytes_overrun_are_judged_apart() -> None:
    """The controls: 4 + 6 fits 10; a source with no cap is not counted; bytes are checked too."""
    fits: Doc = {"max_lines": 10, "source": {"a": {"max_lines": 4}, "b": {"max_lines": 6}, "c": {}}}
    assert isinstance(vlogconfig.merged_table(fits, "c"), dict)
    over: Doc = {"max_bytes": 100, "source": {"a": {"max_bytes": 60}, "b": {"max_bytes": 60}}}
    assert "max_bytes" in str(vlogconfig.merged_table(over, None))


def test_the_chosen_source_reaches_the_shipper_config_and_an_uncapped_one_keeps_the_total() -> None:
    """`--source a` names the spool; `c` declares nothing, so its bound is the top-level pair."""
    table: Doc = {"max_lines": 10, "source": {"a": {"max_lines": 4}, "c": {}}}
    capped = vlogconfig.merged_table(table, "a")
    free = vlogconfig.merged_table(table, "c")
    assert isinstance(capped, dict)
    assert isinstance(free, dict)
    one = vlogconfig.build(capped, vlogconfig.Flags(source="a"))
    two = vlogconfig.build(free, vlogconfig.Flags(source="c"))
    assert (one.source, one.max_lines) == ("a", 4)
    assert (two.source, two.max_lines) == ("c", 10)


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
