# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the CLI: no default root, the bare call reads, and every mode's exit code."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest

from mikemol import pathsforward
from mikemol.pathsforward import cli, lock
from mikemol.pathsforward.digest import legacy_digests, v2

Rec = dict[str, object]

_OK = cli.EXIT_OK
_FAILED = cli.EXIT_FAILED
_REFUSED = cli.EXIT_REFUSED
_LOCKED = cli.EXIT_LOCKED
_DIVERGED = cli.EXIT_DIVERGED
_COUNTER = 3
_HUGE_STEP = 7000
_STALE = timedelta(minutes=45)
_LEGACY_WIDTH = 16
_HOME = re.compile(r"/home/")
_NEW_TITLE = "the title the waypoint's work now has"
_BAD_TITLES = ("", "   ", "first line\nsecond line", "first line\rsecond line")


def _wp(sym: str, status: str = "ready", **extra: object) -> Rec:
    """Build a waypoint.

    Returns:
        the waypoint.

    """
    w: Rec = {"symbol": sym, "title": f"t{sym}", "status": status, "blocked_on": [],
              "blocked_kind": None, "next_bounded_step": "s", "evidence": "",
              "ticks_blocked": 0}
    w.update(extra)
    return w


def _file(tmp_path: Path, waypoints: list[Rec] | None = None, **top: object) -> Path:
    """Write a state copy: W1, W2 live and W3 residue unless overridden.

    Returns:
        the state path.

    """
    doc: Rec = {"counter": _COUNTER, "project_root": str(tmp_path),
                "state_path": "/elsewhere/live/paths-forward.json",
                "waypoints": [_wp("W1"), _wp("W2")] if waypoints is None else waypoints,
                "residue": [{"symbol": "W3", "reason": "why"}]}
    doc.update(top)
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _run(path: Path, *args: str) -> int:
    """Run the CLI on a state copy.

    Returns:
        the exit code.

    """
    return cli.main(["--state", str(path), *args])


def _doc(path: Path) -> Rec:
    """Read a state file back.

    Returns:
        the document.

    """
    return cast("Rec", json.loads(path.read_text(encoding="utf-8")))


def _first(path: Path) -> Rec:
    """Read a state file's first waypoint back.

    Returns:
        the waypoint.

    """
    return cast("list[Rec]", _doc(path)["waypoints"])[0]


def _ledger(path: Path) -> str:
    """Read the ledger beside a state file.

    Returns:
        its text, or "" when absent.

    """
    led = path.with_suffix(".ledger")
    return led.read_text(encoding="utf-8") if led.exists() else ""


def _home_literals(source: str) -> list[str]:
    """Find `/home/` inside the string literals of a source text.

    Returns:
        the offending literals.

    """
    literals = (m.group(0) for m in re.finditer(r"\"[^\"\n]*\"", source))
    return [lit for lit in literals if _HOME.search(lit)]


def test_there_is_no_default_root(capsys: pytest.CaptureFixture[str]) -> None:
    """Without --state the CLI refuses and names why (sre and gabion hardcoded a root)."""
    assert (cli.main([]), "no default root" in capsys.readouterr().err) == (_REFUSED, True)


def test_no_module_hardcodes_a_home_path() -> None:
    """No module's string literals name /home/; the scanner finds one planted (positive control)."""
    package = Path(pathsforward.__file__).parent
    found = [lit for mod in sorted(package.glob("*.py"))
             for lit in _home_literals(mod.read_text(encoding="utf-8"))]
    assert (found, _home_literals('ROOT = "/home/mikemol/github/x"')) == (
        [], ['"/home/mikemol/github/x"'])


def test_the_bare_call_reads_and_writes_nothing(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The bare call prints a summary and leaves the directory byte-for-byte as it was."""
    path = _file(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    code = _run(path)
    after = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert (code, after == before, f"counter={_COUNTER}" in capsys.readouterr().out) == (
        _OK, True, True)


def test_selftest_needs_no_state(capsys: pytest.CaptureFixture[str]) -> None:
    """The selftest runs without --state and reports every arm holding."""
    assert (cli.main(["--selftest"]), "7 of 7" in capsys.readouterr().out) == (_OK, True)


def test_hash_prints_v2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--hash prints the v2 hash."""
    path = _file(tmp_path)
    _run(path, "--hash")
    assert capsys.readouterr().out.strip() == v2(cast("list[Rec]", _doc(path)["waypoints"]))


def test_verify_matches_v2(tmp_path: Path) -> None:
    """--verify on the current v2 matches and ledgers nothing."""
    path = _file(tmp_path)
    claimed = v2([_wp("W1"), _wp("W2")])
    assert (_run(path, "--verify", claimed), _ledger(path)) == (_OK, "")


def test_verify_accepts_a_legacy_hash_as_a_transition(tmp_path: Path) -> None:
    """A legacy C/U prefix (mtools' form) exits 0 and is ledgered as a transition."""
    path = _file(tmp_path)
    claimed = legacy_digests([_wp("W1"), _wp("W2")])["C/U"][:_LEGACY_WIDTH]
    assert (_run(path, "--verify", claimed), "transition" in _ledger(path)) == (_OK, True)


def test_verify_diverges_on_a_foreign_hash(tmp_path: Path) -> None:
    """A foreign hash exits 4 and is ledgered as a divergence the file wins."""
    path = _file(tmp_path)
    assert (_run(path, "--verify", "f" * _LEGACY_WIDTH), "FILE wins" in _ledger(path)) == (
        _DIVERGED, True)


def test_verify_refuses_a_malformed_hash(tmp_path: Path) -> None:
    """A malformed claim is refused."""
    assert _run(_file(tmp_path), "--verify", "nope") == _REFUSED


def test_render_writes_the_mirror_beside_the_copy(tmp_path: Path) -> None:
    """--render writes the mirror beside the state copy."""
    path = _file(tmp_path)
    _run(path, "--render")
    assert path.with_suffix(".md").read_text(encoding="utf-8").startswith("<!-- DERIVED")


def test_payload_names_the_copy(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The payload built from a copy names the copy, never the file's state_path key."""
    path = _file(tmp_path)
    code = _run(path, "--payload")
    out = capsys.readouterr().out
    assert (code, f"state_path={path}" in out, "/elsewhere/live" in out) == (_OK, True, False)


def test_an_oversize_payload_exits_1_and_prints_nothing(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """An oversize payload is refused: exit 1, nothing on stdout, the reason on stderr."""
    path = _file(tmp_path, [_wp("W1", next_bounded_step="x" * _HUGE_STEP), _wp("W2")])
    code = _run(path, "--payload")
    got = capsys.readouterr()
    assert (code, got.out, "PayloadOverBudget" in got.err) == (_FAILED, "", True)


def test_queue_lists_the_waypoints(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--queue lists each waypoint."""
    _run(_file(tmp_path), "--queue")
    assert len(capsys.readouterr().out.splitlines()) == len(("W1", "W2"))


def test_check_passes_a_clean_copy(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--check exits 0 on a clean state (the positive control for the refusals below)."""
    assert (_run(_file(tmp_path), "--check"), "OK" in capsys.readouterr().out) == (_OK, True)


def test_check_refuses_a_malformed_symbol_without_crashing(tmp_path: Path) -> None:
    """`Wx` is refused with exit 2 (gabion crashed with rc 1 on it)."""
    assert _run(_file(tmp_path, [_wp("W1"), _wp("W2"), _wp("Wx")]), "--check") == _REFUSED


def test_check_admits_a_historical_residue_name_and_show_resolves_it(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A residue `W50b` with a reason passes --check, and --show resolves it with its reason."""
    residue = [{"symbol": "W3", "reason": "why"}, {"symbol": "W50b", "reason": "historical"}]
    path = _file(tmp_path, residue=residue)
    assert (_run(path, "--check"), _run(path, "--show", "W50b")) == (_OK, _OK)
    assert '"reason": "historical"' in capsys.readouterr().out


def test_check_refuses_a_duplicate(tmp_path: Path) -> None:
    """A duplicate symbol is refused (el-openglo passed it)."""
    assert _run(_file(tmp_path, [_wp("W1"), _wp("W1"), _wp("W2")]), "--check") == _REFUSED


def test_evidence_is_read_only_when_asked(tmp_path: Path) -> None:
    """--check passes a missing evidence path; --check-evidence refuses it."""
    path = _file(tmp_path, [_wp("W1", evidence=f"{tmp_path}/gone"), _wp("W2")])
    assert (_run(path, "--check"), _run(path, "--check-evidence")) == (_OK, _REFUSED)


def test_lock_is_taken_and_then_held(tmp_path: Path) -> None:
    """A lock is taken, then held against another holder with exit 3."""
    path = _file(tmp_path)
    assert (_run(path, "--lock", "A"), _run(path, "--lock", "B")) == (_OK, _LOCKED)


def test_a_takeover_is_ledgered(tmp_path: Path) -> None:
    """A stale lock is taken over and the takeover is written to the ledger (section 4.1)."""
    stale = lock.stamp(datetime.now(UTC) - _STALE)
    path = _file(tmp_path, lock={"holder": "dead", "taken_at": stale})
    code = _run(path, "--lock", "B")
    held = _doc(path)["lock"]
    assert (code, "takeover" in _ledger(path), isinstance(held, dict) and held["holder"]) == (
        _OK, True, "B")


def test_unlock_by_the_holder_and_not_by_another(tmp_path: Path) -> None:
    """Only the holder unlocks; another gets exit 3 and the lock stays."""
    path = _file(tmp_path)
    _run(path, "--lock", "A")
    assert (_run(path, "--unlock", "B"), _run(path, "--unlock", "A"), _doc(path)["lock"]) == (
        _LOCKED, _OK, None)


def test_armed_records_the_job(tmp_path: Path) -> None:
    """--armed records the job id."""
    path = _file(tmp_path)
    assert (_run(path, "--armed", "job-2"), _doc(path)["job_id"]) == (_OK, "job-2")


def test_a_bogus_status_is_refused_before_anything_is_read(tmp_path: Path) -> None:
    """`--status bogus` is refused by the parser (el-openglo's `--set` took it), file untouched."""
    path = _file(tmp_path)
    before = path.read_bytes()
    with pytest.raises(SystemExit) as exc:
        _run(path, "--update", "W1", "--status", "bogus")
    assert (exc.value.code, path.read_bytes() == before) == (_REFUSED, True)


def test_update_sets_typed_fields(tmp_path: Path) -> None:
    """--update blocks a waypoint with a party and a kind."""
    path = _file(tmp_path)
    code = _run(path, "--update", "W1", "--status", "blocked", "--blocked-on", "mikemol",
                "--blocked-kind", "human", "--next", "n", "--evidence-append", "e",
                "--ticks-blocked", "0")
    assert (code, _first(path)["blocked_on"]) == (_OK, ["mikemol"])


def test_a_refused_update_exits_2_and_saves_nothing(tmp_path: Path) -> None:
    """Blocking without a party is refused with exit 2 and nothing saved."""
    path = _file(tmp_path)
    before = path.read_bytes()
    assert (_run(path, "--update", "W1", "--status", "blocked"), path.read_bytes() == before) == (
        _REFUSED, True)


def _code(path: Path, *args: str) -> int:
    """Run the CLI, reading a parser refusal as its exit code rather than raising it.

    Returns:
        the exit code.

    """
    try:
        return _run(path, *args)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else _REFUSED


def test_update_replaces_a_stale_title(tmp_path: Path) -> None:
    """--update --title replaces the title, stamps last_worked, and leaves the step alone."""
    path = _file(tmp_path)
    code = _code(path, "--update", "W1", "--title", _NEW_TITLE)
    w = _first(path)
    assert (code, w["title"], w["next_bounded_step"], "last_worked" in w) == (
        _OK, _NEW_TITLE, "s", True)


@pytest.mark.parametrize("title", _BAD_TITLES)
def test_a_blank_or_multiline_title_is_refused(
        tmp_path: Path, capsys: pytest.CaptureFixture[str], title: str) -> None:
    """A blank or multi-line --title is refused by the tool, naming the title; nothing is saved."""
    path = _file(tmp_path)
    before = path.read_bytes()
    code = _code(path, "--update", "W1", "--title", title)
    err = capsys.readouterr().err
    assert (code, path.read_bytes() == before, "REFUSED: title" in err) == (_REFUSED, True, True)


def test_add_mints_and_saves(tmp_path: Path) -> None:
    """--add mints the next symbol and saves the counter."""
    path = _file(tmp_path)
    code = _run(path, "--add", "new", "--next", "go", "--enables", "W1", "--touches", "x")
    assert (code, _doc(path)["counter"]) == (_OK, _COUNTER + 1)


def test_drop_moves_to_residue(tmp_path: Path) -> None:
    """--drop moves a waypoint to residue."""
    path = _file(tmp_path)
    residue = _doc(path)["residue"]
    code = _run(path, "--drop", "W1", "superseded")
    after = _doc(path)["residue"]
    assert (code, isinstance(after, list) and isinstance(residue, list)
            and len(after) - len(residue)) == (_OK, 1)


def test_drop_without_a_reason_is_refused(tmp_path: Path) -> None:
    """--drop with a blank reason exits 2."""
    assert _run(_file(tmp_path), "--drop", "W1", " ") == _REFUSED


def test_bump_blocked_says_who_is_owed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--bump-blocked prints NUDGE on the first blocked tick, and honours --except."""
    blocked = {"blocked_on": ["agent-2"], "blocked_kind": "agent"}
    path = _file(tmp_path, [_wp("W1", "blocked", **blocked), _wp("W2", "blocked", **blocked)])
    code = _run(path, "--bump-blocked", "--except", "W2")
    out = capsys.readouterr().out
    assert (code, "W1 ticks_blocked=1 on=agent-2(agent)  NUDGE" in out, "W2" in out) == (
        _OK, True, False)


def test_ledger_appends_a_structured_line(tmp_path: Path) -> None:
    """--ledger appends a structured line with evidence."""
    path = _file(tmp_path)
    code = _run(path, "--ledger", "W1", "advanced", "unblock", "did it", "--evidence", "c1")
    assert (code, _ledger(path).rstrip().endswith('"did it"  evidence=c1')) == (_OK, True)


def test_a_malformed_ledger_line_is_refused(tmp_path: Path) -> None:
    """A ledger line with a spaced column exits 2."""
    assert _run(_file(tmp_path), "--ledger", "W1", "two words", "sweep", "n") == _REFUSED


def test_show_resolves_live_and_residue(tmp_path: Path) -> None:
    """--show resolves a live symbol and a residue one, and refuses an unissued one."""
    path = _file(tmp_path)
    assert (_run(path, "--show", "W1"), _run(path, "--show", "W3"), _run(path, "--show", "W9")) == (
        _OK, _OK, _REFUSED)


def test_the_preamble_is_set_and_cleared(tmp_path: Path) -> None:
    """--preamble-set stores a file's lines; --preamble-clear removes them."""
    path = _file(tmp_path)
    rules = tmp_path / "rules.txt"
    rules.write_text("rule one\nrule two\n", encoding="utf-8")
    first = (_run(path, "--preamble-set", str(rules)), _doc(path).get("preamble"))
    assert (first, _run(path, "--preamble-clear"), "preamble" in _doc(path)) == (
        (_OK, ["rule one", "rule two"]), _OK, False)


def test_a_blank_preamble_file_is_refused(tmp_path: Path) -> None:
    """A preamble file of blank lines exits 2."""
    rules = tmp_path / "rules.txt"
    rules.write_text("\n\n", encoding="utf-8")
    assert _run(_file(tmp_path), "--preamble-set", str(rules)) == _REFUSED


def test_an_unreadable_state_is_refused(tmp_path: Path) -> None:
    """A missing state file exits 2 rather than raising."""
    assert _run(tmp_path / "absent.json", "--hash") == _REFUSED


def test_an_unknown_flag_is_refused(tmp_path: Path) -> None:
    """An unknown flag beside a valid mode exits 2, not run."""
    with pytest.raises(SystemExit) as exc:
        _run(_file(tmp_path), "--hash", "--queit")
    assert exc.value.code == _REFUSED


def test_main_reads_sys_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The console script reads sys.argv when called with no arguments."""
    monkeypatch.setattr("sys.argv", ["mikemol-paths-forward", "--state", str(_file(tmp_path))])
    assert cli.main() == _OK


def test_the_mode_defaults_to_the_summary() -> None:
    """With no mode the summary is selected; a flag or a value selects its mode."""
    got = (cli.mode_of({}), cli.mode_of({"hash": True}), cli.mode_of({"verify": "x"}))
    assert got == ("summary", "hash", "verify")
