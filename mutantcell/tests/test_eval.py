# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `eval`: one cell stages its counterfactual, runs the check, records the flip."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.mutantcell import cellcgroup, cellstage
from mikemol.mutantcell import eval as cell_eval

if TYPE_CHECKING:
    import pytest

_TAG = cellstage.cache_tag()
_PEAK = 4096
_SRC_ROOT = Path(cell_eval.__file__).parents[2]
_MIB = 1024 * 1024
_SPIN_CAP_S = 1
_MEM_CAP_MB = 300
_ALLOC_MB = 600
_RUN_TIMEOUT_S = 120
_KNOB = 7
_DEFAULT = 3
_CAP_CPU = 7
_CAP_MEM_MB = 4000
_WALL_S = 1
_LONG_WALL_S = 30
_SLEEP_FOREVER = "import time; time.sleep(60)"
_OOM_EVENTS = "oom 1\\noom_kill 1\\n"


def _check(tmp_path: Path, *lines: str) -> str:
    """Write a check script, the program one cell runs against a claim.

    Returns:
        The script's path.

    """
    path = tmp_path / "check.py"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def _cgroup(tmp_path: Path) -> cellcgroup.Cgroup:
    """Plant a fake cgroup `/job` with a peak and zeroed OOM counters.

    Returns:
        The `Cgroup` that points at it.

    """
    proc = tmp_path / "proc_cgroup"
    proc.write_text("0::/job\n", encoding="utf-8")
    job = tmp_path / "fs" / "job"
    job.mkdir(parents=True, exist_ok=True)
    (job / "memory.peak").write_text(f"{_PEAK}\n", encoding="utf-8")
    (job / "memory.events").write_text("oom 0\noom_kill 0\n", encoding="utf-8")
    return cellcgroup.Cgroup(proc=proc, root=str(tmp_path / "fs"))


def _no_caps() -> None:
    """Decline the real caps: they are irreversible, and would cap the test runner itself."""


def _argv(tmp_path: Path, check: str, site: str, *extra: str) -> list[str]:
    """Build one cell's argv, with the engine an empty staged directory.

    Returns:
        The argument vector.

    """
    engine = tmp_path / "engine"
    engine.mkdir(exist_ok=True)
    return [
        "--engine-dir",
        str(engine),
        "--check",
        check,
        "--claim",
        "claim-1",
        "--site",
        site,
        "--out",
        str(tmp_path / "out.json"),
        *extra,
    ]


def _cell(tmp_path: Path, check: str, site: str = "m.py::f", *extra: str) -> int:
    """Run one cell in-process against the planted cgroup, with no caps.

    Returns:
        The cell's exit status.

    """
    return cell_eval.main(
        _argv(tmp_path, check, site, *extra),
        cgroup=_cgroup(tmp_path),
        caps=_no_caps,
    )


def _record(tmp_path: Path) -> dict[str, object]:
    """Read the record a cell wrote.

    Returns:
        The `{claim, site, flipped, why}` object.

    """
    text = (tmp_path / "out.json").read_text(encoding="utf-8")
    return cast("dict[str, object]", json.loads(text))


def _subprocess_cell(
    tmp_path: Path,
    check: str,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    """Run one cell as `python -m mikemol.mutantcell.eval`, with the REAL caps.

    Returns:
        The finished process.

    """
    child_env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(_SRC_ROOT), os.environ.get("PYTHONPATH", "")]),
        **env,
    }
    return subprocess.run(
        [sys.executable, "-m", "mikemol.mutantcell.eval", *_argv(tmp_path, check, "m.py::f")],
        env=child_env,
        capture_output=True,
        text=True,
        check=False,
        timeout=_RUN_TIMEOUT_S,
    )


def _proc_entry(proc: Path, pid: int, stat: str) -> None:
    """Plant one fake `/proc/<pid>/stat`."""
    (proc / str(pid)).mkdir(parents=True)
    (proc / str(pid) / "stat").write_text(stat, encoding="utf-8")


def _oom_check(tmp_path: Path, *, exit_code: int) -> str:
    """Write a check that raises the planted cgroup's OOM counters, then exits `exit_code`.

    Returns:
        The script's path.

    """
    events = tmp_path / "fs" / "job" / "memory.events"
    return _check(
        tmp_path,
        "import pathlib, sys",
        f"pathlib.Path({str(events)!r}).write_text('{_OOM_EVENTS}')",
        f"sys.exit({exit_code})",
    )


# --- env_int, last_line -------------------------------------------------------------------------


def test_env_int_reads_an_integer_knob_and_falls_back_to_the_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Set reads; empty, garbage and unset all fall back to the default."""
    monkeypatch.setenv("MUTANTCELL_KNOB", str(_KNOB))
    assert cell_eval.env_int("MUTANTCELL_KNOB", _DEFAULT) == _KNOB
    monkeypatch.setenv("MUTANTCELL_KNOB", "")
    assert cell_eval.env_int("MUTANTCELL_KNOB", _DEFAULT) == _DEFAULT
    monkeypatch.setenv("MUTANTCELL_KNOB", "seven")
    assert cell_eval.env_int("MUTANTCELL_KNOB", _DEFAULT) == _DEFAULT
    monkeypatch.delenv("MUTANTCELL_KNOB")
    assert cell_eval.env_int("MUTANTCELL_KNOB", _DEFAULT) == _DEFAULT


def test_last_line_is_the_final_non_empty_line_cut_to_the_why_limit() -> None:
    """Blank trailing lines are skipped; a long line is cut; no output reads empty."""
    assert cell_eval.last_line(b"first\nsecond\n\n  \n") == "second"
    assert cell_eval.last_line(b"x" * (cell_eval.WHY_CHARS + 50)) == "x" * cell_eval.WHY_CHARS
    assert not cell_eval.last_line(b"")
    assert not cell_eval.last_line(None)
    assert not cell_eval.last_line(b" \n \n")


def test_last_line_replaces_undecodable_bytes_instead_of_raising() -> None:
    """A check that wrote invalid UTF-8 still has its last line recorded."""
    assert cell_eval.last_line(b"ok \xff\xfe") == "ok ��"


# --- descendants, kill_tree, become_subreaper ---------------------------------------------------


def test_descendants_walks_ppid_counts_live_ones_and_skips_zombies(tmp_path: Path) -> None:
    """A planted /proc: children and grandchildren count; a zombie is walked, not counted."""
    proc = tmp_path / "proc"
    _proc_entry(proc, 10, "10 (a b) S 1 10 10 0")
    _proc_entry(proc, 11, "11 (c)) S 10 10 10 0")
    _proc_entry(proc, 12, "12 (d) Z 11 10 10 0")
    _proc_entry(proc, 13, "13 (e) S 12 10 10 0")
    _proc_entry(proc, 14, "14 (f) S 99 10 10 0")
    (proc / "self").mkdir()
    (proc / "15").mkdir()
    _proc_entry(proc, 16, "16")
    assert cell_eval.descendants(10, proc) == [11, 13]
    assert cell_eval.descendants(1, proc) == [10, 11, 13]
    assert cell_eval.descendants(99, proc) == [14]


def test_descendants_of_an_unlistable_proc_is_empty(tmp_path: Path) -> None:
    """A /proc that cannot be listed counts nothing, and does not raise."""
    assert cell_eval.descendants(1, tmp_path / "absent") == []


def test_a_grandchild_orphaned_by_its_parents_exit_is_adopted_once_this_is_a_subreaper() -> None:
    """After `become_subreaper`, a grandchild whose parent exited is OUR descendant."""
    cell_eval.become_subreaper()
    code = f"import subprocess, sys\nsubprocess.Popen([sys.executable, '-c', {_SLEEP_FOREVER!r}])\n"
    subprocess.run([sys.executable, "-c", code], check=True)
    orphans = cell_eval.descendants(os.getpid())
    try:
        assert orphans
    finally:
        for pid in orphans:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)


def test_kill_tree_kills_and_reaps_every_descendant() -> None:
    """A sleeping child is gone afterwards: no descendant survives, none is left a zombie."""
    child = subprocess.Popen([sys.executable, "-c", _SLEEP_FOREVER])
    assert child.pid in cell_eval.descendants(os.getpid())
    cell_eval.kill_tree(child)
    assert child.pid not in cell_eval.descendants(os.getpid())
    assert not Path(f"/proc/{child.pid}").exists()


# --- run, cap_note ------------------------------------------------------------------------------


def test_run_reports_a_passing_check_as_not_flipped_with_its_last_line(tmp_path: Path) -> None:
    """Exit 0: not flipped; `why` is the last line, and the claim reaches the check as argv[1]."""
    check = _check(tmp_path, "import sys", "print('noise')", "print(sys.argv[1])")
    assert cell_eval.run(check, "the-claim", _LONG_WALL_S) == (False, "the-claim")


def test_run_reports_a_failing_check_as_flipped_and_merges_stderr(tmp_path: Path) -> None:
    """Exit 1 is a flip; the last line comes from the merged stdout and stderr streams."""
    check = _check(
        tmp_path,
        "import sys",
        "print('out', flush=True)",
        "sys.stderr.write('red here\\n')",
        "sys.exit(1)",
    )
    assert cell_eval.run(check, "c", _LONG_WALL_S) == (True, "red here")


def test_run_folds_a_kill_without_a_cpu_cap_into_a_flip_with_no_reason(tmp_path: Path) -> None:
    """A SIGKILLed check (an OOM kill looks the same) is flipped; the cap note stays silent."""
    check = _check(tmp_path, "import os", "os.kill(os.getpid(), 9)")
    assert cell_eval.run(check, "c", _LONG_WALL_S) == (True, "")


def test_run_stops_a_check_that_outlives_the_wall_clock(tmp_path: Path) -> None:
    """A mutant that never answers HAS flipped the check: killed, with the reason recorded."""
    check = _check(tmp_path, _SLEEP_FOREVER)
    flipped, why = cell_eval.run(check, "c", _WALL_S)
    assert flipped
    assert why.startswith(f"did not terminate within {_WALL_S}s (killed)")


def test_run_stops_a_check_whose_process_tree_outgrows_its_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A check that forks past the tree bound is killed and read as a flip."""
    monkeypatch.setenv("PAPERKIT_CHECK_TREE", "1")
    check = _check(
        tmp_path,
        "import subprocess, sys",
        f"subprocess.run([sys.executable, '-c', {_SLEEP_FOREVER!r}], check=False)",
    )
    flipped, why = cell_eval.run(check, "c", _LONG_WALL_S)
    assert flipped
    assert why.startswith("process tree reached ")
    assert "> 1 (killed)" in why
    assert "recursed by forking" in why


def test_run_reads_a_check_that_cannot_be_spawned_as_a_flip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the fork or exec itself fails, the harness says so instead of dying."""
    monkeypatch.setattr(sys, "executable", str(tmp_path / "no-such-python"))
    flipped, why = cell_eval.run("check.py", "c", _WALL_S)
    assert flipped
    assert why.startswith("could not spawn the check (FileNotFoundError")
    assert "process budget" in why


def test_cap_note_is_silent_for_an_exit_that_was_not_a_cap_kill() -> None:
    """Exit 0, an ordinary failure and an uncapped SIGKILL carry no cap note."""
    assert not cell_eval.cap_note(0)
    assert not cell_eval.cap_note(1)
    assert not cell_eval.cap_note(-signal.SIGKILL)


# --- main, in process: the staging, the record, the baseline canary, the OOM deferral -----------


def test_a_passing_cell_writes_its_record_and_exits_zero(tmp_path: Path) -> None:
    """The record carries claim, site, flipped=false and the check's last line."""
    check = _check(tmp_path, "print('fine')")
    assert _cell(tmp_path, check) == 0
    assert _record(tmp_path) == {
        "claim": "claim-1",
        "site": "m.py::f",
        "flipped": False,
        "why": "fine",
    }


def test_a_failing_cell_records_the_flip_and_why_and_still_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A flip is a RESULT, not a harness failure: exit 0, flipped=true, quiet stderr."""
    check = _check(tmp_path, "print('caught it')", "raise SystemExit(1)")
    assert _cell(tmp_path, check) == 0
    record = _record(tmp_path)
    assert record["flipped"] is True
    assert record["why"] == "caught it"
    assert not capsys.readouterr().err


def test_a_flipped_baseline_says_so_on_stderr_but_still_records(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The empty-set cell is the canary: its flip is named on the spot, with the check's reason."""
    check = _check(tmp_path, "print('identity broke it')", "raise SystemExit(1)")
    assert _cell(tmp_path, check, cell_eval.BASELINE) == 0
    err = capsys.readouterr().err
    assert err.startswith("eval: BASELINE FLIPPED (the identity mutation broke the check)")
    assert err.endswith("identity broke it\n")
    assert _record(tmp_path)["flipped"] is True


def test_a_flipped_baseline_with_no_output_says_no_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A canary that died silently is named as such."""
    check = _check(tmp_path, "raise SystemExit(1)")
    assert _cell(tmp_path, check, cell_eval.BASELINE) == 0
    assert capsys.readouterr().err.endswith("no output\n")


def test_a_passing_baseline_is_silent(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The canary only sings when it flips."""
    assert _cell(tmp_path, _check(tmp_path, "pass"), cell_eval.BASELINE) == 0
    assert not capsys.readouterr().err


def test_a_cell_stages_the_engine_bytecode_and_delivers_the_module_swap(tmp_path: Path) -> None:
    """The check sees the staged .pyc in its slot and the mutant source over the module."""
    engine = tmp_path / "engine" / "pkg"
    engine.mkdir(parents=True)
    (engine / "a.pyc").write_text("staged", encoding="utf-8")
    module = engine / "a.py"
    module.write_text("original", encoding="utf-8")
    mutant_py = tmp_path / "mutant.py"
    mutant_py.write_text("mutant", encoding="utf-8")
    mutant_pyc = tmp_path / "mutant.pyc"
    mutant_pyc.write_text("mutant bytecode", encoding="utf-8")
    slot = engine / "__pycache__" / f"a.{_TAG}.pyc"
    check = _check(
        tmp_path,
        "import pathlib",
        f"assert pathlib.Path({str(module)!r}).read_text() == 'mutant'",
        f"assert pathlib.Path({str(slot)!r}).read_text() == 'mutant bytecode'",
        "print('swapped')",
    )
    extra = [
        "--module",
        str(module),
        "--mutant-py",
        str(mutant_py),
        "--mutant-pyc",
        str(mutant_pyc),
    ]
    assert _cell(tmp_path, check, "pkg/a.py::f", *extra) == 0
    assert _record(tmp_path)["why"] == "swapped"
    assert not (engine / "a.pyc").exists()


def test_the_caps_are_applied_once_before_the_check_runs(tmp_path: Path) -> None:
    """`main` calls its `caps` exactly once, and before the check is spawned."""
    ran = tmp_path / "check-ran"
    seen: list[bool] = []

    def caps() -> None:
        """Record whether the check had already run when the caps were applied."""
        seen.append(ran.exists())

    check = _check(tmp_path, "import pathlib", f"pathlib.Path({str(ran)!r}).write_text('x')")
    argv = _argv(tmp_path, check, "m.py::f")
    assert cell_eval.main(argv, cgroup=_cgroup(tmp_path), caps=caps) == 0
    assert seen == [False]
    assert ran.exists()


def test_main_reads_sys_argv_when_given_no_argument(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The `-m` path: `main()` takes the cell's operands from `sys.argv[1:]`."""
    check = _check(tmp_path, "print('from argv')")
    monkeypatch.setattr(sys, "argv", ["eval", *_argv(tmp_path, check, "m.py::f")])
    assert cell_eval.main(cgroup=_cgroup(tmp_path), caps=_no_caps) == 0
    assert _record(tmp_path)["why"] == "from argv"


def test_a_cell_asked_to_observe_deposits_the_peak_of_its_own_cgroup(tmp_path: Path) -> None:
    """With `--peak`, the in-scope peak lands at that path in the vocabulary mem_harvest parses."""
    peak = tmp_path / "cell.peak"
    assert _cell(tmp_path, _check(tmp_path, "pass"), "m.py::f", "--peak", str(peak)) == 0
    assert peak.read_text(encoding="utf-8") == str(_PEAK)


def test_a_cell_not_asked_to_observe_writes_no_peak(tmp_path: Path) -> None:
    """Without `--peak`, nothing but the record is written."""
    assert _cell(tmp_path, _check(tmp_path, "pass")) == 0
    names = sorted(p.name for p in tmp_path.iterdir())
    assert "cell.peak" not in names
    assert "out.json" in names


def test_a_flip_that_coincides_with_an_oom_is_deferred_not_recorded(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The kernel's OOM kill is a verdict about the HARNESS: exit CANNOT_RUN, no record."""
    peak = tmp_path / "cell.peak"
    check = _oom_check(tmp_path, exit_code=1)
    assert _cell(tmp_path, check, "m.py::f", "--peak", str(peak)) == cell_eval.CANNOT_RUN
    assert not (tmp_path / "out.json").exists()
    assert "eval: OOM-KILLED at this cell's cap (not a flip)" in capsys.readouterr().err
    assert peak.read_text(encoding="utf-8") == str(_PEAK)


def test_an_oom_counter_rise_without_a_flip_is_not_a_deferral(tmp_path: Path) -> None:
    """A passing check that merely saw the counters rise is a result like any other."""
    assert _cell(tmp_path, _oom_check(tmp_path, exit_code=0)) == 0
    assert _record(tmp_path)["flipped"] is False


# --- main, as `python -m`: the REAL caps bind the check -----------------------------------------


def test_the_real_caps_bind_the_check_and_the_core_dump_is_off(tmp_path: Path) -> None:
    """The check inherits soft==hard CPU and address-space caps from the env knobs, core 0."""
    check = _check(
        tmp_path,
        "import resource",
        "print(resource.getrlimit(resource.RLIMIT_CPU),",
        "      resource.getrlimit(resource.RLIMIT_AS),",
        "      resource.getrlimit(resource.RLIMIT_CORE))",
    )
    done = _subprocess_cell(
        tmp_path,
        check,
        {"PAPERKIT_CHECK_CPU": str(_CAP_CPU), "PAPERKIT_CHECK_MEM_MB": str(_CAP_MEM_MB)},
    )
    assert done.returncode == 0, done.stderr
    cap_bytes = _CAP_MEM_MB * _MIB
    expected = f"({_CAP_CPU}, {_CAP_CPU}) ({cap_bytes}, {cap_bytes}) (0, 0)"
    assert _record(tmp_path)["why"] == expected


def test_a_check_that_allocates_past_the_address_space_cap_is_a_flip(tmp_path: Path) -> None:
    """A runaway single-process allocation raises MemoryError under the cap: flipped."""
    check = _check(tmp_path, f"x = bytearray({_ALLOC_MB} * 1024 * 1024)")
    done = _subprocess_cell(tmp_path, check, {"PAPERKIT_CHECK_MEM_MB": str(_MEM_CAP_MB)})
    assert done.returncode == 0, done.stderr
    record = _record(tmp_path)
    assert record["flipped"] is True
    assert record["why"] == "MemoryError"


def test_a_check_that_spins_is_killed_at_the_cpu_cap_and_the_note_says_so(tmp_path: Path) -> None:
    """The cap kill is a flip, and the recorded reason names the cap and the signal."""
    check = _check(tmp_path, "while True:", "    pass")
    done = _subprocess_cell(tmp_path, check, {"PAPERKIT_CHECK_CPU": str(_SPIN_CAP_S)})
    assert done.returncode == 0, done.stderr
    record = _record(tmp_path)
    assert record["flipped"] is True
    why = str(record["why"])
    assert why.startswith(f"exceeded its {_SPIN_CAP_S}s CPU cap (")
    assert "killed by SIGKILL" in why
    assert why.endswith("the mutation made it spin, which is a flip")
