# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The mutation grid addresses each def-site by a qualified path, so same-named defs are distinct.

⚑⚑⚑ WRITTEN AGAINST A MEASURED DEFECT. `mutate(source, name)` mutated the FIRST def carrying a
bare name, so every same-named def in a module was reported as its own site and mutated the same
node. On ratchet a Protocol stub `parse` came back SURVIVED three times: each `parse` mutated the
stub. Every test here fails on the bare-name runner by assertion, not by an error.

⚑ AND THE ENVIRONMENT A MUTANT'S SUITE RECEIVES CARRIES NO `GIT_*`: the last case fails by
assertion on a runner that copies `os.environ` whole, with its decoy repository holding a commit.
"""

from __future__ import annotations

import ast
import concurrent.futures
import json
import os
import pathlib
import subprocess
import sys
import threading

import mutants_gen
import mutate_runner
import pytest
from mikemol.mutation.declarations import Declared
from mikemol.mutation.regexop import RegexSpec

_MUTANT = "raise AssertionError('mutant')"

_TWO_CLASSES = """\
class First:
    def run(self):
        return 1


class Second:
    def run(self):
        return 2
"""

_PROTOCOL_AND_IMPL = """\
from typing import Protocol


class Parser(Protocol):
    def parse(self, text: str) -> str: ...


def parse(text: str) -> str:
    return text.strip()
"""

_NESTED = """\
def outer():
    def inner():
        return 1
    return inner()


def inner():
    return 2
"""

_UNIQUE = """\
def alpha():
    \"\"\"Doc.\"\"\"
    return 1


def beta():
    return 2
"""


def _paths(source: str) -> list[str]:
    """Return each site's address, asserting first that a site carries one at all.

    Returns:
        the qualified paths `sites` reports, in its order.

    """
    found = mutate_runner.sites(ast.parse(source))
    assert all(isinstance(site, tuple) for site in found), "a site must carry its qualified path"
    return [path for path, _node in found]


def _body_of(source: str, path: str) -> str:
    """Return the unparsed body of the def at `path` in `source`.

    Returns:
        the body's statements, unparsed, one per line.

    Raises:
        LookupError: when no def-site carries that path.

    """
    for got, node in mutate_runner.sites(ast.parse(source)):
        if got == path:
            return "\n".join(ast.unparse(stmt) for stmt in node.body)
    raise LookupError(path)


def test_methods_of_two_classes_are_two_sites_and_the_second_mutates_the_second() -> None:
    """Two classes' `run` methods are distinct sites, and mutating one leaves the other alone."""
    assert _paths(_TWO_CLASSES) == ["First.run", "Second.run"]
    mutant = mutate_runner.mutate(_TWO_CLASSES, "Second.run")
    assert _body_of(mutant, "Second.run") == _MUTANT
    assert _body_of(mutant, "First.run") == "return 1"


def test_a_protocol_stub_is_no_site_and_a_function_of_its_name_is_one() -> None:
    """A Protocol's stub is not a site; the same-named function is one and mutates itself."""
    assert _paths(_PROTOCOL_AND_IMPL) == ["parse"]
    mutant = mutate_runner.mutate(_PROTOCOL_AND_IMPL, "parse")
    assert _body_of(mutant, "parse") == _MUTANT


def test_no_protocol_member_is_a_site_whatever_its_body_or_its_base_spelling() -> None:
    """Docstring-bodied, subscripted and qualified Protocols are skipped; a plain class is kept."""
    source = (
        "import typing\n"
        "from typing import Protocol\n\n\n"
        "class Shape(Protocol):\n"
        '    def area(self) -> int:\n        """The area."""\n        ...\n\n\n'
        "class Generic(Protocol[int]):\n"
        '    def side(self) -> int:\n        """The side."""\n        ...\n\n\n'
        "class Qualified(typing.Protocol):\n"
        '    def edge(self) -> int:\n        """The edge."""\n        ...\n\n\n'
        "class Plain:\n"
        "    def real(self) -> int:\n        return 1\n"
    )
    assert _paths(source) == ["Plain.real"]


def test_a_nested_def_is_addressed_through_its_enclosing_function() -> None:
    """A nested def is `outer.<locals>.inner`, distinct from a module-level `inner`."""
    assert _paths(_NESTED) == ["outer", "outer.<locals>.inner", "inner"]
    mutant = mutate_runner.mutate(_NESTED, "inner")
    assert _body_of(mutant, "inner") == _MUTANT
    assert _body_of(mutant, "outer.<locals>.inner") == "return 1"


def test_a_module_of_unique_names_is_addressed_and_mutated_as_before() -> None:
    """Positive control: unique top-level names keep their bare paths and the same mutant."""
    assert _paths(_UNIQUE) == ["alpha", "beta"]
    mutant = mutate_runner.mutate(_UNIQUE, "alpha")
    assert _body_of(mutant, "alpha") == f"'Doc.'\n{_MUTANT}"
    assert _body_of(mutant, "beta") == "return 2"


_GIT_ID = ("-c", "user.name=fixture", "-c", "user.email=fixture@invalid")
_SITE_SOURCE = "def f():\n    return 1\n"
_SITE = "f"
_PASSED = "1 passed in 0.01s\n"


def _git(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run git with exactly `env`, carrying its stderr into any failure.

    Returns:
        the completed process.

    """
    proc = subprocess.run(
        ["git", *_GIT_ID, *args], capture_output=True, text=True, check=False, env=env
    )
    assert proc.returncode == 0, f"git {' '.join(args)} failed: {proc.stderr.strip()}"
    return proc


def test_a_mutant_suite_cannot_commit_into_the_repository_the_caller_names(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A suite committing in its own dir lands there, not in the repo the caller's GIT_DIR names.

    ⚑⚑⚑ THE DECOY STANDS IN FOR THE REAL REPOSITORY A HOOK EXPORTS. Measured 2026-09-23: a fixture
    running `git commit` under a pre-commit hook wrote nine commits into the calling repo. The
    fake suite below does what that fixture did, with whatever environment `run` hands it.
    """
    clean = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    decoy = tmp_path / "decoy"
    _git("init", "-q", str(decoy), env=clean)
    dist = tmp_path / "dist"
    (dist / "tests").mkdir(parents=True)
    (dist / "mod.py").write_text(_SITE_SOURCE, encoding="utf-8")
    (dist / "pyproject.toml").write_text("", encoding="utf-8")
    seen: list[dict[str, str]] = []

    def suite(
        argv: list[str],
        cwd: pathlib.Path,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        seen.append(env)
        _git("init", "-q", str(cwd), env=env)
        _git("-C", str(cwd), "commit", "-q", "--allow-empty", "-m", "fixture", env=env)
        return subprocess.CompletedProcess(argv, 0, _PASSED, "")

    monkeypatch.setenv("GIT_DIR", str(decoy / ".git"))
    # ⚑ THE RUNNER'S ONE SEAM, NOT `subprocess.run`: patching the module attribute replaced it for
    # the whole interpreter, so `_git` had to hoard the real one before the patch landed.
    monkeypatch.setattr(mutate_runner, "launch", suite)
    grid = mutate_runner.Grid(pathlib.Path(sys.executable), dist, dist / "pyproject.toml")
    mutate_runner.run(grid, mutate_runner.Mutant(pathlib.Path("mod.py"), _SITE_SOURCE, _SITE))
    refs = _git("-C", str(decoy), "for-each-ref", env=clean).stdout
    assert not refs, f"the suite committed into the decoy: {refs.strip()}"
    # ⚑ THE CALLER'S GIT_* NEVER REACHES THE SUITE; THE RUNNER'S OWN CONFIG INJECTION DOES (W2724):
    # GIT_DIR and its kin point git at the real repository, GIT_CONFIG_* is what `quiet_git` sets.
    own = {k for k in seen[0] if k.startswith("GIT_")}
    assert own == {k for k in mutate_runner.quiet_git({}) if k.startswith("GIT_")}, (
        "a caller's GIT_* variable reached the suite"
    )


# ⚑ THE SUITE WAITS FOR `f` TO SUCCEED: unmutated it passes at once, mutated it retries far past
# the runner's limit. That is the shape that hung //gmailstruct:mutants (W356).
# ⚑ ITS OWN 120s BOUND IS CLEANUP ONLY: a runner without the limit still fails the 30s join below
# by assertion, and the orphaned suite then exits instead of spinning forever (measured
# 2026-10-02: the unbounded form left three orphans behind F-arm runs).
_WAITING_SUITE = """\
import time

import mod


def test_waits_for_f() -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            assert mod.f() == 1
        except AssertionError:
            time.sleep(0.05)
        else:
            return
    raise AssertionError("f never returned 1")
"""


def test_a_mutant_that_makes_a_wait_unbounded_is_killed_as_hung(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutant whose suite waits forever is recorded as KILLED once it shows no progress (W1376).

    ⚑⚑ RUN ON A WORKER THREAD AND JOINED WITH A BOUND, so a runner without the limit fails this
    test by ASSERTION (the verdict never arrives) rather than hanging the suite that tests it.
    """
    dist = tmp_path / "dist"
    (dist / "src").mkdir(parents=True)
    (dist / "tests").mkdir()
    (dist / "src" / "mod.py").write_text(_SITE_SOURCE, encoding="utf-8")
    (dist / "tests" / "test_wait.py").write_text(_WAITING_SUITE, encoding="utf-8")
    (dist / "pyproject.toml").write_text("", encoding="utf-8")
    monkeypatch.setenv("MUTATE_POLL_S", "0.2")
    monkeypatch.setenv("MUTATE_PATIENCE", "5")
    grid = mutate_runner.Grid(pathlib.Path(sys.executable), dist, dist / "pyproject.toml")
    mutant = mutate_runner.Mutant(pathlib.Path("src/mod.py"), _SITE_SOURCE, _SITE)
    got: list[str] = []
    worker = threading.Thread(
        target=lambda: got.append(mutate_runner.run(grid, mutant)), daemon=True
    )
    worker.start()
    worker.join(timeout=30)
    assert got == ["killed"], "the unbounded mutant produced no verdict within 30s"


# ⚑ THE SPINNING SUITE: a mutant that turns the wait into a BUSY loop keeps its tree's CPU
# advancing, so the hang witness never fires; the CPU limit is what ends it. Unmutated it passes
# at once.
_SPINNING_SUITE = """\
import mod


def test_spins_for_f() -> None:
    while True:
        try:
            assert mod.f() == 1
        except AssertionError:
            continue
        else:
            return
"""


def test_a_mutant_that_turns_the_wait_into_a_busy_loop_is_killed_by_the_cpu_limit(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A suite that spins is KILLED when its CPU seconds reach `MUTATE_CPU_S`, not by a timer."""
    dist = tmp_path / "dist"
    (dist / "src").mkdir(parents=True)
    (dist / "tests").mkdir()
    (dist / "src" / "mod.py").write_text(_SITE_SOURCE, encoding="utf-8")
    (dist / "tests" / "test_spin.py").write_text(_SPINNING_SUITE, encoding="utf-8")
    (dist / "pyproject.toml").write_text("", encoding="utf-8")
    monkeypatch.setenv("MUTATE_CPU_S", "1")
    grid = mutate_runner.Grid(pathlib.Path(sys.executable), dist, dist / "pyproject.toml")
    mutant = mutate_runner.Mutant(pathlib.Path("src/mod.py"), _SITE_SOURCE, _SITE)
    got: list[str] = []
    worker = threading.Thread(
        target=lambda: got.append(mutate_runner.run(grid, mutant)), daemon=True
    )
    worker.start()
    worker.join(timeout=60)
    assert got == ["killed"], "the spinning mutant produced no verdict within 60s"


# ⚑ THE CONTROLS FOR THE WITNESS: a child that is SLOW but progressing (burning CPU, or printing
# while idle) must never be ended, and a child that is silent and idle must be. Each runs `launch`
# itself, the seam, with a patience of a few short polls.
_BUSY = """\
import time

start = time.process_time()
while time.process_time() - start < 1.0:
    pass
print('done')
"""
_CHATTY = """\
import time

for _ in range(30):
    print('tick', flush=True)
    time.sleep(0.005)
print('done')
"""
_SILENT = "import time\ntime.sleep(60)\n"
_SHORT_POLLS = (("MUTATE_POLL_S", "0.1"), ("MUTATE_PATIENCE", "4"))


def _launch(code: str, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> str:
    for name, value in _SHORT_POLLS:
        monkeypatch.setenv(name, value)
    done = mutate_runner.launch([sys.executable, "-c", code], tmp_path, dict(os.environ))
    return done.stdout.strip()


def test_a_suite_burning_cpu_is_never_ended_as_hung(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: one CPU second across many short polls advances every poll, so it finishes."""
    assert _launch(_BUSY, monkeypatch, tmp_path) == "done"


def test_a_suite_that_prints_while_idle_is_never_ended_as_hung(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Output growth is progress even when the CPU is flat, so a chatty idle suite finishes."""
    assert _launch(_CHATTY, monkeypatch, tmp_path) == "tick\n" * 30 + "done"


def test_a_silent_idle_suite_is_ended_after_the_patience_not_a_deadline(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive control: no output and no CPU for the patience raises TimeoutExpired."""
    with pytest.raises(subprocess.TimeoutExpired):
        _launch(_SILENT, monkeypatch, tmp_path)


_SLOW_SILENT = "import time\ntime.sleep(1.2)\nprint('done')\n"


def _frozen_cpu(_pid: int) -> float:
    return 1.0


def _yes(_root: int) -> bool:
    return True


def _no(_root: int) -> bool:
    return False


def test_a_suite_waiting_on_the_host_that_got_no_cpu_is_never_ended_as_hung(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2642, forced: the CPU reads frozen and nothing is printed, but a process is runnable.

    The poll is 0.1 s and the patience 4, so the old rule (bytes and CPU unchanged for 4 polls)
    ended this suite at about 0.4 s while it was due to finish at 1.2 s: a live suite the
    scheduler had not yet run, killed as hung. A runnable process is never a stall, so it finishes.
    """
    monkeypatch.setattr(mutate_runner, "_cpu", _frozen_cpu)
    monkeypatch.setattr(mutate_runner, "waiting_on_host", _yes)
    assert _launch(_SLOW_SILENT, monkeypatch, tmp_path) == "done"


def test_a_frozen_cpu_with_nothing_runnable_is_still_ended_as_hung(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive control for the test above: a frozen CPU and nothing runnable is a stall."""
    monkeypatch.setattr(mutate_runner, "_cpu", _frozen_cpu)
    monkeypatch.setattr(mutate_runner, "waiting_on_host", _no)
    with pytest.raises(subprocess.TimeoutExpired):
        _launch(_SLOW_SILENT, monkeypatch, tmp_path)


def _fake_proc(root: pathlib.Path, rows: tuple[tuple[int, int, int, str], ...]) -> pathlib.Path:
    """Write a `/proc` of `(pid, parent, group, state)` rows, one `stat` file each.

    Returns:
        the directory, which `waiting_on_host` reads in place of `/proc`.

    """
    root.mkdir(exist_ok=True)
    for pid, ppid, group, state in rows:
        entry = root / str(pid)
        entry.mkdir()
        text = f"{pid} (a (b)) {state} {ppid} {group} " + "0 " * 20
        (entry / "stat").write_text(text, encoding="utf-8")
    return root


def test_waiting_on_host_finds_a_running_descendant_anywhere(tmp_path: pathlib.Path) -> None:
    """The leader sleeps, its grandchild runs: the tree is waiting on the host."""
    proc = _fake_proc(tmp_path, ((10, 1, 10, "S"), (11, 10, 10, "S"), (12, 11, 12, "R")))
    assert mutate_runner.waiting_on_host(10, proc)


def test_waiting_on_host_finds_a_descendant_blocked_on_disk_io(tmp_path: pathlib.Path) -> None:
    """A grandchild in uninterruptible sleep (`D`) is waiting on the host too (github-cb)."""
    proc = _fake_proc(tmp_path, ((10, 1, 10, "S"), (11, 10, 10, "S"), (12, 11, 12, "D")))
    assert mutate_runner.waiting_on_host(10, proc)


def test_waiting_on_host_is_false_when_the_whole_tree_sleeps_on_its_own(
    tmp_path: pathlib.Path,
) -> None:
    """A tree that is all `S` is the absence the hang watch exists to count, runners outside it."""
    proc = _fake_proc(tmp_path, ((10, 1, 10, "S"), (11, 10, 10, "S"), (99, 1, 99, "R")))
    assert not mutate_runner.waiting_on_host(10, proc)


def test_a_suite_blocked_on_disk_io_is_never_ended_as_hung(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2642 review, forced: CPU frozen, nothing printed, a descendant in `D` throughout.

    The I/O scheduler, not the CPU scheduler, holds this suite; the old rule and an R-only rule
    both ended it at about 0.4 s of a 1.2 s run. Waiting on the host is not a stall.
    """
    proc = _fake_proc(tmp_path / "proc", ((10, 1, 10, "S"), (11, 10, 10, "D")))
    real = mutate_runner.waiting_on_host

    def blocked(_root: int) -> bool:
        return real(10, proc)

    monkeypatch.setattr(mutate_runner, "_cpu", _frozen_cpu)
    monkeypatch.setattr(mutate_runner, "waiting_on_host", blocked)
    assert _launch(_SLOW_SILENT, monkeypatch, tmp_path) == "done"


def test_a_frozen_suite_asleep_on_its_own_is_ended_as_hung(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive control for the `D` case: the same tree with every process in `S` is a stall."""
    proc = _fake_proc(tmp_path / "proc", ((10, 1, 10, "S"), (11, 10, 10, "S")))
    real = mutate_runner.waiting_on_host

    def asleep(_root: int) -> bool:
        return real(10, proc)

    monkeypatch.setattr(mutate_runner, "_cpu", _frozen_cpu)
    monkeypatch.setattr(mutate_runner, "waiting_on_host", asleep)
    with pytest.raises(subprocess.TimeoutExpired):
        _launch(_SLOW_SILENT, monkeypatch, tmp_path)


def test_waiting_on_host_reads_the_group_once_the_leader_has_gone(tmp_path: pathlib.Path) -> None:
    """A leaked child in the suite's group still counts after the leader exits."""
    proc = _fake_proc(tmp_path, ((20, 1, 10, "R"),))
    assert mutate_runner.waiting_on_host(10, proc)


def test_waiting_on_host_ignores_a_process_it_cannot_read(tmp_path: pathlib.Path) -> None:
    """An entry that vanished or has no parseable `stat` is no process, never a runnable one."""
    proc = _fake_proc(tmp_path, ((10, 1, 10, "S"),))
    (tmp_path / "11").mkdir()
    (tmp_path / "11" / "stat").write_text("garbage", encoding="utf-8")
    assert not mutate_runner.waiting_on_host(10, proc)


def test_the_tree_cpu_of_a_live_process_is_a_number_and_of_a_gone_one_is_none() -> None:
    """A gone root is None, never 0.0: a finished suite and an idle one are different answers."""
    mine = mutate_runner.tree_cpu(os.getpid())
    assert mine is not None
    assert mine >= 0.0
    assert mutate_runner.tree_cpu(2**22 + 7) is None


def test_the_limits_read_their_environment_and_default_without_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Poll, patience and CPU seconds come from the environment, with defaults when it is empty."""
    for name in ("MUTATE_POLL_S", "MUTATE_PATIENCE", "MUTATE_CPU_S"):
        monkeypatch.delenv(name, raising=False)
    assert mutate_runner.limits() == (5.0, 24, 120.0)
    monkeypatch.setenv("MUTATE_POLL_S", "0.5")
    monkeypatch.setenv("MUTATE_PATIENCE", "3")
    monkeypatch.setenv("MUTATE_CPU_S", "7")
    assert mutate_runner.limits() == (0.5, 3, 7.0)


# ⚑ THE LEAKED CHILD: a suite that exits but leaves a grandchild in its group. Under pipes the read
# waited on that child until a wall timer killed it, and the katas mutants that plant exactly this
# were recorded KILLED that way; with files the suite exits at once, so the runner must wait for the
# GROUP and end it by the same absence. The control is a suite that leaves nothing behind.
_LEAKS = """\
import subprocess
import sys

subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
print("suite done")
"""


def test_a_suite_that_leaves_a_child_in_its_group_is_ended_as_hung(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The suite exits 0, but its leaked sleeper is silent and idle, so the group is killed."""
    with pytest.raises(subprocess.TimeoutExpired):
        _launch(_LEAKS, monkeypatch, tmp_path)


_LEAKS_DETACHED = """\
import subprocess
import sys

subprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)"], start_new_session=True)
print("suite done")
"""


def test_a_child_in_its_own_session_holding_the_pipe_ends_as_hung_without_a_crash(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The group is empty when the kill comes, so it raised ProcessLookupError out of the pool."""
    with pytest.raises(subprocess.TimeoutExpired):
        _launch(_LEAKS_DETACHED, monkeypatch, tmp_path)


def _fake_environs(root: pathlib.Path, entries: dict[int, bytes | None]) -> pathlib.Path:
    """Write a `/proc` of `pid -> environ bytes` (None writes no file), one directory each.

    Returns:
        the directory, which `holders` reads in place of `/proc`.

    """
    root.mkdir(exist_ok=True)
    for pid, environ in entries.items():
        entry = root / str(pid)
        entry.mkdir()
        if environ is not None:
            (entry / "environ").write_bytes(environ)
    return root


def test_holders_names_the_processes_whose_environment_carries_the_tree(
    tmp_path: pathlib.Path,
) -> None:
    """W2694: HOME, a PYTHONPATH entry and a bare final entry all name the tree; lookalikes do not.

    Not holders: a sibling whose name merely begins the same, another tree, a process with no
    readable environment, and this process itself.
    """
    tree = tmp_path / "tmpab12cd34"
    named = os.fsencode(tree)
    # ⚑ THE FAKE PIDS ARE RELATIVE TO THIS PROCESS'S OWN: under bazel's sandbox the test runs in a
    # pid namespace where its own pid is small, and a fixed `12` collided with it (the first bazel
    # run of this test named two holders, not three, because `holders` rightly skipped itself).
    me = os.getpid()
    proc = _fake_environs(
        tmp_path / "proc",
        {
            me + 1: b"PATH=/usr/bin\x00HOME=" + named + b"\x00LANG=C",
            me + 2: b"PYTHONPATH=" + named + b"/katas/src:/elsewhere\x00",
            me + 3: b"HOME=" + named + b"5\x00",
            me + 4: None,
            me + 5: b"HOME=/somewhere/else\x00",
            me + 6: b"HOME=" + named,
            me: b"HOME=" + named + b"\x00",
        },
    )
    assert mutate_runner.holders(tree, proc) == [me + 1, me + 2, me + 6]


def test_discard_removes_the_tree_with_one_rmtree(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2694: there is no concurrent writer, so the removal is one call and no retry."""
    tree = tmp_path / "tree"
    (tree / "src").mkdir(parents=True)
    calls: list[pathlib.Path] = []

    def counted(path: pathlib.Path) -> None:
        calls.append(path)

    monkeypatch.setattr("shutil.rmtree", counted)
    mutate_runner.discard(tree)
    assert calls == [tree]


def test_discard_raises_a_named_error_when_the_tree_cannot_be_removed(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2694: a failed removal is a fact, not a race: one try, then an error naming the tree."""
    tree = tmp_path / "stuck"
    tree.mkdir()
    calls: list[int] = []

    def refuses(_path: pathlib.Path) -> None:
        calls.append(1)
        message = "Directory not empty"
        raise OSError(39, message)

    monkeypatch.setattr("shutil.rmtree", refuses)
    proc = _fake_environs(tmp_path / "proc", {})
    with pytest.raises(mutate_runner.ScratchTreeHeldError) as held:
        mutate_runner.discard(tree, proc)
    assert calls == [1]
    assert held.value.root == tree
    assert held.value.remaining == []
    assert str(tree) in str(held.value)


def test_the_held_error_names_the_processes_that_still_hold_the_tree(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2694: the error carries the pids still naming the tree, read when the removal failed."""
    tree = tmp_path / "stuck"
    tree.mkdir()
    me = os.getpid()
    proc = _fake_environs(tmp_path / "proc", {me + 1: b"HOME=" + os.fsencode(tree) + b"\x00"})

    def refuses(_path: pathlib.Path) -> None:
        message = "Directory not empty"
        raise OSError(39, message)

    monkeypatch.setattr("shutil.rmtree", refuses)
    with pytest.raises(mutate_runner.ScratchTreeHeldError) as held:
        mutate_runner.discard(tree, proc)
    assert held.value.remaining == [me + 1]


def test_a_sibling_tree_with_the_same_name_prefix_is_not_a_holder(tmp_path: pathlib.Path) -> None:
    """W2694: a path that merely begins the same is another cell's tree and is never killed."""
    tree = tmp_path / "tmpab12"
    named = os.fsencode(tree)
    me = os.getpid()
    proc = _fake_environs(
        tmp_path / "proc",
        {
            me + 1: b"HOME=" + named + b"-sibling\x00",
            me + 2: b"HOME=" + named + b"2/src\x00",
            me + 3: b"PYTHONPATH=/x:" + named + b"3:/y\x00",
        },
    )
    assert mutate_runner.holders(tree, proc) == []


_KILLED_BY_SIGKILL = -9  # a child's exit status when SIGKILL ended it

_STUBBORN = """\
import pathlib
import signal
import sys
import threading

for name in ("SIGTERM", "SIGINT", "SIGHUP"):
    signal.signal(getattr(signal, name), signal.SIG_IGN)
pathlib.Path(sys.argv[1]).write_text("up", encoding="utf-8")
threading.Event().wait()
"""


def _stubborn_holder(tmp_path: pathlib.Path, tree: pathlib.Path) -> subprocess.Popen[bytes]:
    """Start a process in its own session that names `tree` in HOME and ignores soft signals.

    Returns:
        the running child, after it has said it is up.

    """
    script = tmp_path / "stubborn.py"
    script.write_text(_STUBBORN, encoding="utf-8")
    ready = tmp_path / "ready"
    child = subprocess.Popen(
        [sys.executable, str(script), str(ready)],
        env={**os.environ, "HOME": str(tree)},
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(1000):
        if ready.exists():
            break
        threading.Event().wait(0.01)
    assert ready.exists()
    return child


def test_end_holders_returns_only_after_a_stubborn_holder_has_exited(
    tmp_path: pathlib.Path,
) -> None:
    """W2694: a holder that ignores soft signals is gone, not merely signalled, when it returns.

    The assertion reads no clock and polls nothing: the process table is read once, right after
    the call, and a holder still running at that instant fails it.
    """
    tree = tmp_path / "cell"
    tree.mkdir()
    child = _stubborn_holder(tmp_path, tree)
    mutate_runner.end_holders(tree)
    assert not _alive(child.pid)
    assert child.wait() == _KILLED_BY_SIGKILL
    assert mutate_runner.holders(tree) == []


class _ReachedWaitError(Exception):
    """Raised by the seam to show that `end_holders` reached its wait on a live holder."""


def test_end_holders_waits_on_the_holder_after_signalling_it(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2694: the kill is followed by a wait on the pidfd; a kill-and-move-on never reaches it."""
    tree = tmp_path / "cell"
    tree.mkdir()
    child = _stubborn_holder(tmp_path, tree)

    def reached(
        _read: list[int], _write: list[int], _err: list[int]
    ) -> tuple[list[int], list[int], list[int]]:
        raise _ReachedWaitError

    monkeypatch.setattr(mutate_runner, "wait_readable", reached)
    with pytest.raises(_ReachedWaitError):
        mutate_runner.end_holders(tree)
    child.kill()
    child.wait()


def test_a_held_tree_is_recorded_against_its_cell_and_is_not_a_verdict(
    tmp_path: pathlib.Path,
) -> None:
    """W2694: the cell is named, the verdict is `held`, and no mutant outcome is invented."""
    future: concurrent.futures.Future[str] = concurrent.futures.Future()
    future.set_exception(mutate_runner.ScratchTreeHeldError(tmp_path / "cell", [7]))
    held: list[str] = []
    assert mutate_runner.settle_verdict(future, "mod.py::f", held) == "held"
    assert len(held) == 1
    assert held[0].startswith("mod.py::f: ")
    assert "[7]" in held[0]


def test_a_settled_verdict_passes_through_untouched() -> None:
    """W2694: a cell that finished normally keeps its own verdict and records nothing."""
    future: concurrent.futures.Future[str] = concurrent.futures.Future()
    future.set_result("killed")
    held: list[str] = []
    assert mutate_runner.settle_verdict(future, "mod.py::f", held) == "killed"
    assert held == []


def test_the_shard_is_refused_by_cell_when_any_tree_was_held(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W2694: an infrastructure failure ends the shard loudly, naming every cell it hit."""
    mutate_runner.refuse_held([])
    with pytest.raises(SystemExit) as exit_info:
        mutate_runner.refuse_held(["a.py::f: tree held", "b.py::g: tree held"])
    assert exit_info.value.code == 1
    said = capsys.readouterr().err
    assert "2 cell(s)" in said
    assert "a.py::f" in said
    assert "b.py::g" in said


# ⚑ THE DETACHED DESCENDANT (W2694): the suite starts a child in a session of its own that holds
# no pipe and keeps recreating an entry in the cell's tree for 15 s, as a katas mutant that leaves
# the waiter's tree alive does. The leader exits, `launch` returns, and the child is still running
# while the tree is removed: b89's `//katas:mutants_4` died of ENOTEMPTY on exactly that race.
_LEAKER = """\
import os
import pathlib
import sys
import threading

pathlib.Path(sys.argv[1], str(os.getpid())).write_text("", encoding="utf-8")
for _ in range(1500):
    try:
        os.makedirs("leak/deeper", exist_ok=True)
    except OSError:
        pass
    threading.Event().wait(0.01)
"""

_LEAKING_SUITE = """\
import pathlib
import subprocess
import sys
import threading

import mod


def test_f_while_a_detached_child_runs() -> None:
    pids = pathlib.Path("@PIDS@")
    before = len(list(pids.iterdir()))
    subprocess.Popen(
        [sys.executable, "@LEAKER@", str(pids)],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(500):
        if len(list(pids.iterdir())) > before:
            break
        threading.Event().wait(0.01)
    assert mod.f() == 1
"""


def _alive(pid: int) -> bool:
    try:
        text = pathlib.Path("/proc", str(pid), "stat").read_text(encoding="utf-8")
    except OSError:
        return False
    return text[text.rindex(")") + 2] != "Z"


def _gone(pid: int) -> bool:
    for _ in range(100):
        if not _alive(pid):
            return True
        threading.Event().wait(0.05)
    return False


def test_a_descendant_in_its_own_session_is_dead_when_its_cell_ends(
    tmp_path: pathlib.Path,
) -> None:
    """W2694: every child the suite started, in any session, is gone when `run` returns.

    The test waits up to 5 s per child for a process that was sent SIGKILL to leave the process
    table; that bound belongs to this assertion, not to the runner, which reads no clock.
    """
    pids = tmp_path / "pids"
    pids.mkdir()
    leaker = tmp_path / "leaker.py"
    leaker.write_text(_LEAKER, encoding="utf-8")
    dist = tmp_path / "dist"
    (dist / "src").mkdir(parents=True)
    (dist / "tests").mkdir()
    (dist / "src" / "mod.py").write_text(_SITE_SOURCE, encoding="utf-8")
    suite = _LEAKING_SUITE.replace("@PIDS@", str(pids)).replace("@LEAKER@", str(leaker))
    (dist / "tests" / "test_leak.py").write_text(suite, encoding="utf-8")
    (dist / "pyproject.toml").write_text("", encoding="utf-8")
    grid = mutate_runner.Grid(pathlib.Path(sys.executable), dist, dist / "pyproject.toml")
    mutant = mutate_runner.Mutant(pathlib.Path("src/mod.py"), _SITE_SOURCE, _SITE)
    assert mutate_runner.run(grid, mutant) == "killed"
    started = sorted(int(entry.name) for entry in pids.iterdir())
    assert started, "the suite never started its child"
    assert [pid for pid in started if not _gone(pid)] == []


_GRAPH = """\
{
  "modules": {
    "src/p/a.py": {"imports": [], "reads": []},
    "src/p/b.py": {"imports": ["src/p/a.py"], "reads": []},
    "src/p/c.py": {"imports": [], "reads": []}
  },
  "tests": {
    "tests/test_a.py": {"imports": ["src/p/a.py"], "reads": []},
    "tests/test_b.py": {"imports": ["src/p/b.py"], "reads": []},
    "tests/test_c.py": {"imports": ["src/p/c.py"], "reads": []},
    "tests/test_data.py": {"imports": [], "reads": ["src/p/c.py"]}
  }
}
"""


def _graph_dist(tmp_path: pathlib.Path, text: str = _GRAPH) -> pathlib.Path:
    (tmp_path / "graph.json").write_text(text, encoding="utf-8")
    return tmp_path


def test_a_mutant_runs_only_the_tests_whose_import_cone_holds_its_module(
    tmp_path: pathlib.Path,
) -> None:
    """Module a is imported by test_a directly and by test_b through b; test_c never sees it."""
    got = mutate_runner.selected_tests(_graph_dist(tmp_path), pathlib.Path("src/p/a.py"))
    assert got == ["tests/test_a.py", "tests/test_b.py"]


def test_a_test_that_declares_it_reads_the_module_is_run_for_it(tmp_path: pathlib.Path) -> None:
    """A read that is not an import is still a way for a test to see a mutation."""
    got = mutate_runner.selected_tests(_graph_dist(tmp_path), pathlib.Path("src/p/c.py"))
    assert got == ["tests/test_c.py", "tests/test_data.py"]


def test_no_graph_or_a_module_it_does_not_name_runs_everything(tmp_path: pathlib.Path) -> None:
    """An unknown is never read as no test needs this: the empty list means the whole directory."""
    assert mutate_runner.selected_tests(tmp_path, pathlib.Path("src/p/a.py")) == []
    dist = _graph_dist(tmp_path)
    assert mutate_runner.selected_tests(dist, pathlib.Path("src/p/new.py")) == []


def test_a_graph_that_is_not_json_or_not_a_mapping_runs_everything(tmp_path: pathlib.Path) -> None:
    """A torn or wrongly shaped file is a missing graph, never a narrowing."""
    dist = _graph_dist(tmp_path, "{not json")
    assert mutate_runner.selected_tests(dist, pathlib.Path("src/p/a.py")) == []
    dist = _graph_dist(tmp_path, "[1, 2]")
    assert mutate_runner.selected_tests(dist, pathlib.Path("src/p/a.py")) == []


def test_the_files_a_site_stages_are_its_module_the_cone_of_its_tests_and_those_tests(
    tmp_path: pathlib.Path,
) -> None:
    """W1883: module a is seen by test_a and test_b (through b), so b's cone joins the files."""
    got = mutate_runner.staged_files(_graph_dist(tmp_path), pathlib.Path("src/p/a.py"))
    assert got == (["src/p/a.py", "src/p/b.py"], ["tests/test_a.py", "tests/test_b.py"])
    only = mutate_runner.staged_files(_graph_dist(tmp_path), pathlib.Path("src/p/c.py"))
    assert only == (["src/p/c.py"], ["tests/test_c.py", "tests/test_data.py"])


def test_a_site_the_graph_cannot_narrow_stages_the_whole_distribution(
    tmp_path: pathlib.Path,
) -> None:
    """W1883: no graph, an unknown module, or a module no test sees is None, never a narrowing."""
    assert mutate_runner.staged_files(tmp_path, pathlib.Path("src/p/a.py")) is None
    dist = _graph_dist(tmp_path)
    assert mutate_runner.staged_files(dist, pathlib.Path("src/p/new.py")) is None


def test_a_declared_test_list_wins_over_the_graph_and_blank_means_the_graph(
    tmp_path: pathlib.Path,
) -> None:
    """W1883: MUTATE_TESTS is space-separated paths; unset or blank is the graph's answer."""
    dist = _graph_dist(tmp_path)
    rel = pathlib.Path("src/p/a.py")
    assert mutate_runner.chosen_tests(dist, rel, "tests/x.py  tests/y.py") == [
        "tests/x.py",
        "tests/y.py",
    ]
    assert mutate_runner.chosen_tests(dist, rel, "") == ["tests/test_a.py", "tests/test_b.py"]
    assert mutate_runner.chosen_tests(dist, rel, "   ") == ["tests/test_a.py", "tests/test_b.py"]


def test_a_suite_that_leaves_nothing_behind_returns_when_it_exits(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: no leaked child, so the wait ends with the suite and its output is kept."""
    assert _launch("print('clean')\n", monkeypatch, tmp_path) == "clean"


def test_the_group_cpu_of_a_live_group_is_a_number_and_of_an_empty_one_is_none() -> None:
    """A group with a member reads a number, and a group with none reads None, never 0.0."""
    mine = mutate_runner.group_cpu(os.getpgrp())
    assert mine is not None
    assert mine >= 0.0
    assert mutate_runner.group_cpu(2**22 + 7) is None


# ⚑ THE DECLARED-DEFECT PATH (W629, tests W669). A distribution declares a defect in `mutants.regex`
# and the runner plants it through the SAME temp-copy and suite path as a def-site mutant, so these
# replace the same one seam. What reaches the suite is read back from the temp tree, because a
# runner that planted nothing would still hand the suite a green. Declarations are read through
# `read_declared` from a written file, the runner's own path, so no test names a type it imports.
_FAILED = "1 failed in 0.01s\n"
_DECLARATION = "src/mod.py|returns-two|return 1|return 2|\n"


def _declared_grid(tmp_path: pathlib.Path, declaration: str = "") -> mutate_runner.Grid:
    dist = tmp_path / "dist"
    (dist / "src").mkdir(parents=True)
    (dist / "tests").mkdir()
    (dist / "src" / "mod.py").write_text(_SITE_SOURCE, encoding="utf-8")
    (dist / "pyproject.toml").write_text("", encoding="utf-8")
    if declaration:
        (dist / "mutants.regex").write_text(declaration, encoding="utf-8")
    return mutate_runner.Grid(pathlib.Path(sys.executable), dist, dist / "pyproject.toml")


def _seam(monkeypatch: pytest.MonkeyPatch, declared_rc: int, declared_out: str) -> list[str]:
    """Replace `launch` with a suite that kills def-site mutants and answers a planted defect.

    A module carrying the def-site raise is killed, as the real suite would; any other text is the
    declared defect, answered with `declared_rc` and `declared_out`.

    Returns:
        the list each run's `src/mod.py` text is appended to.

    """
    seen: list[str] = []

    def suite(
        argv: list[str],
        cwd: pathlib.Path,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        text = (cwd / "src" / "mod.py").read_text(encoding="utf-8")
        seen.append(text)
        pathlib.Path(env["MUTATE_NODES"]).write_text("", encoding="utf-8")  # the plugin's start
        if "AssertionError" in text:
            return subprocess.CompletedProcess(argv, 1, f"{_FAILED}AssertionError: mutant\n", "")
        return subprocess.CompletedProcess(argv, declared_rc, declared_out, "")

    monkeypatch.setattr(mutate_runner, "launch", suite)
    return seen


def test_a_declared_defect_the_suite_fails_on_is_killed_and_the_planted_text_reached_it(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W629: a failing suite KILLS the declared defect, and it ran against the rewritten module."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    seen = _seam(monkeypatch, 1, _FAILED)
    (declared,) = mutate_runner.read_declared(grid.dist)
    assert mutate_runner.run_declared(grid, declared) == "killed"
    assert seen == ["def f():\n    return 2\n"]


def test_a_declared_defect_the_suite_passes_on_survived(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W629: a green suite over the planted defect is SURVIVED: it is blind to what was named."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    _seam(monkeypatch, 0, _PASSED)
    (declared,) = mutate_runner.read_declared(grid.dist)
    assert mutate_runner.run_declared(grid, declared) == "survived"


def test_a_stale_declaration_is_unapplied_and_no_suite_runs(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W629: a pattern matching nothing plants nothing: UNAPPLIED, and the suite is never asked."""
    grid = _declared_grid(tmp_path, "src/mod.py|stale|nothing-here|x|\n")
    seen = _seam(monkeypatch, 0, _PASSED)
    (declared,) = mutate_runner.read_declared(grid.dist)
    assert mutate_runner.run_declared(grid, declared) == "unapplied"
    assert seen == []


def test_a_missing_module_or_a_rewrite_that_does_not_parse_is_errored_and_runs_nothing(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W629: a declaration naming no file, or breaking the source, is ERRORED, never a green."""
    both = "src/ghost.py|returns-two|return 1|return 2|\nsrc/mod.py|breaks|return|return (|\n"
    grid = _declared_grid(tmp_path, both)
    seen = _seam(monkeypatch, 0, _PASSED)
    ghost, broken = mutate_runner.read_declared(grid.dist)
    assert mutate_runner.run_declared(grid, ghost) == "errored"
    assert mutate_runner.run_declared(grid, broken) == "errored"
    assert seen == []


def test_a_distribution_with_no_declaration_file_declares_nothing(tmp_path: pathlib.Path) -> None:
    """W629: none by default: no `mutants.regex` is an empty list, not an error."""
    assert mutate_runner.read_declared(_declared_grid(tmp_path).dist) == []


def _run_main(grid: mutate_runner.Grid) -> int:
    return mutate_runner.main(["mutate_runner", str(grid.py), str(grid.config)])


def test_the_grid_reports_none_declared_and_passes_when_a_distribution_declares_nothing(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W629: an empty REGEX section is NAMED, and a distribution with no file passes as before."""
    grid = _declared_grid(tmp_path)
    _seam(monkeypatch, 0, _PASSED)
    assert _run_main(grid) == 0
    out = capsys.readouterr().out
    assert "REGEX (0)" in out
    assert "none declared" in out


def test_the_grid_passes_only_when_every_declared_defect_is_killed(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W629: a killed declared defect passes (0); the same defect surviving fails the grid (1)."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    _seam(monkeypatch, 1, _FAILED)
    assert _run_main(grid) == 0
    assert "src/mod.py::returns-two -> killed" in capsys.readouterr().out
    _seam(monkeypatch, 0, _PASSED)
    assert _run_main(grid) == 1
    captured = capsys.readouterr()
    assert "src/mod.py::returns-two -> survived" in captured.out
    assert "1 declared defect(s) NOT killed" in captured.err


def test_a_stale_declaration_fails_the_grid_as_unapplied(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W629: a declaration the code moved away from FAILS, reading as a defect nobody can plant."""
    grid = _declared_grid(tmp_path, "src/mod.py|stale|nothing-here|x|\n")
    _seam(monkeypatch, 1, _FAILED)
    assert _run_main(grid) == 1
    assert "src/mod.py::stale -> unapplied" in capsys.readouterr().out


def test_a_malformed_declaration_file_refuses_the_whole_grid_naming_the_line(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W629: a bad line is exit 1 with `mutants.regex: line 2`, never read as declared-nothing."""
    grid = _declared_grid(tmp_path, "# ok\nnot-a-declaration\n")
    seen = _seam(monkeypatch, 1, _FAILED)
    assert _run_main(grid) == 1
    assert "mutants.regex: line 2: " in capsys.readouterr().err
    assert seen == []


_KEYS = [f"src/m{n}.py::f{k}" for n in range(8) for k in range(5)]
_SHARDS = 4
_CPUS = 12
_SIX = 6
THREE_JOBS = 3


def _refused(raw: str) -> bool:
    try:
        mutate_runner.shard_spec(raw)
    except ValueError as fault:
        return "MUTATE_SHARD" in str(fault)
    return False


def test_a_shard_spec_is_index_slash_count_and_unset_means_the_whole_grid() -> None:
    """W970: `i/N` parses and unset is None; anything else, or an index past the count, fails."""
    assert mutate_runner.shard_spec("") is None
    assert mutate_runner.shard_spec("2/6") == (2, 6)
    assert all(_refused(bad) for bad in ("6/6", "a/3", "1", "1/0", "-1/3", "1/2/3"))


def test_every_key_is_in_exactly_one_shard_and_every_shard_has_some() -> None:
    """W970: the union of the N shards is the whole grid, with no overlap and no empty shard."""
    homes = [
        [i for i in range(_SHARDS) if mutate_runner.in_shard(key, (i, _SHARDS))] for key in _KEYS
    ]
    assert all(len(h) == 1 for h in homes)
    assert {h[0] for h in homes} == set(range(_SHARDS))
    assert all(mutate_runner.in_shard(key, None) for key in _KEYS)


def test_two_shards_between_them_run_the_declared_defect_once(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W970: a declared defect belongs to one shard, and the header names the shard."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    _seam(monkeypatch, 1, _FAILED)
    outs = []
    for index in range(2):
        monkeypatch.setenv("MUTATE_SHARD", f"{index}/2")
        assert _run_main(grid) == 0
        outs.append(capsys.readouterr().out)
    assert [f"shard {i}/2" in out for i, out in enumerate(outs)] == [True, True]
    assert sum("src/mod.py::returns-two -> killed" in out for out in outs) == 1


def test_a_malformed_shard_refuses_the_grid_before_running_anything(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W970: a bad `MUTATE_SHARD` is exit 1 naming the variable, and no suite runs."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    seen = _seam(monkeypatch, 1, _FAILED)
    monkeypatch.setenv("MUTATE_SHARD", "9/3")
    assert _run_main(grid) == 1
    assert "MUTATE_SHARD" in capsys.readouterr().err
    assert seen == []


def test_a_selection_is_the_whole_grid_a_shard_or_one_named_site_and_never_two_of_them() -> None:
    """W1881: unset is everything, a site is exactly its own key, a site and a shard is refused."""
    whole = mutate_runner.select("", "")
    assert (whole.keep("src/mod.py::f"), whole.share) == (True, 1)
    assert whole.label("dist") == "dist"
    shard = mutate_runner.select("1/2", "")
    assert (shard.share, shard.label("dist")) == (2, "dist shard 1/2")
    one = mutate_runner.select("", "src/mod.py::f")
    assert (one.keep("src/mod.py::f"), one.keep("src/mod.py::g"), one.share) == (True, False, 1)
    assert one.label("dist") == "dist site src/mod.py::f"
    with pytest.raises(ValueError, match="two ways"):
        mutate_runner.select("0/2", "src/mod.py::f")


def test_one_named_declared_defect_is_the_only_cell_a_site_run_runs(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W1881: MUTATE_SITE names the cell, the header names it, and no def-site suite runs."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    seen = _seam(monkeypatch, 1, _FAILED)
    monkeypatch.setenv("MUTATE_SITE", "src/mod.py::returns-two")
    assert _run_main(grid) == 0
    out = capsys.readouterr().out
    assert "site src/mod.py::returns-two" in out
    assert "src/mod.py::returns-two -> killed" in out
    assert len(seen) == 1


def test_a_site_that_names_nothing_refuses_the_grid_rather_than_passing_an_empty_one(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W1881: a typo in MUTATE_SITE must not run nothing and succeed."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    seen = _seam(monkeypatch, 1, _FAILED)
    monkeypatch.setenv("MUTATE_SITE", "src/mod.py::no-such-site")
    assert _run_main(grid) == 1
    assert "names no site or defect" in capsys.readouterr().err
    assert seen == []
    monkeypatch.setenv("MUTATE_SHARD", "0/2")
    assert _run_main(grid) == 1
    assert "two ways" in capsys.readouterr().err
    assert seen == []


def test_an_unsharded_runner_uses_every_cpu_and_a_shard_takes_its_share() -> None:
    """W970: six shards of one distribution must not each start a full machine's worth of suites.

    A cap on the unsharded runners was tried and withdrawn on 2026-10-11: four suites made the
    big unsharded grids (fence, katas, mdstruct, treeio) time out. They shard first, then narrow.
    """
    assert mutate_runner.pool_size("", _CPUS, 1) == _CPUS
    assert mutate_runner.pool_size("", _CPUS, _SIX) == _CPUS // _SIX
    assert mutate_runner.pool_size("", 2, _SIX) == 1


def test_an_explicit_job_count_wins_over_the_share() -> None:
    """MUTATE_JOBS is the operator's bound; `1` restores the serial run."""
    assert mutate_runner.pool_size("3", 12, 6) == THREE_JOBS
    assert mutate_runner.pool_size("1", 12, 1) == 1
    assert mutate_runner.pool_size("0", 12, 1) == 1


def test_the_declared_job_count_is_a_ceiling_the_free_cores_can_lower() -> None:
    """W1764: a shard declaring K children starts fewer on a busy host and never more than K.

    The idle host is the control: free cores above K leave K alone. A host loaded past its cores
    still gets one child, so a shard slows under load and is never stopped.
    """
    ceiling = str(THREE_JOBS)
    assert mutate_runner.pool_size(ceiling, _CPUS, 1, 0.0) == THREE_JOBS
    assert mutate_runner.pool_size(ceiling, _CPUS, 1, _CPUS - 1.0) == 1
    assert mutate_runner.pool_size(ceiling, _CPUS, 1, _CPUS * _SIX) == 1
    assert mutate_runner.free_cores(_CPUS, _CPUS - THREE_JOBS) == THREE_JOBS
    assert mutate_runner.pool_size(ceiling, _CPUS, 1, _CPUS - THREE_JOBS + 1.0) == THREE_JOBS - 1


def test_the_cpu_line_states_the_idle_host_wall_time_from_cpu_and_children() -> None:
    """W1769: 120 CPU seconds over 4 children is a 30 s shard on an idle host, whatever the load."""
    line = mutate_runner.cpu_line(120.0, 4)
    assert line == "shard cpu=120.0s children=4 idle_wall=30.0s\n"
    assert "children=1 idle_wall=5.0s" in mutate_runner.cpu_line(5.0, 0)


def test_a_shard_over_its_declared_cpu_budget_is_refused_and_one_under_it_is_not() -> None:
    """W1772: the verdict is CPU seconds against the declared budget, whatever the host load."""
    over = mutate_runner.budget_verdict(THREE_JOBS + 1.0, str(THREE_JOBS))
    assert over is not None
    assert "BUDGET EXCEEDED" in over
    assert mutate_runner.budget_verdict(float(THREE_JOBS), str(THREE_JOBS)) is None


def test_an_unset_or_malformed_cpu_budget_judges_nothing() -> None:
    """The control: no declaration, a garbled one, and a non-positive one never refuse a shard."""
    assert mutate_runner.budget_verdict(_CPUS * _SIX, "") is None
    assert mutate_runner.budget_verdict(_CPUS * _SIX, "soon") is None
    assert mutate_runner.budget_verdict(_CPUS * _SIX, "0") is None


def test_an_unreadable_load_reads_as_an_idle_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """The fallback is today's behaviour: the declared count, not a throttle."""

    def refuse(_self: pathlib.Path, *, encoding: str) -> str:
        raise OSError(encoding)

    monkeypatch.setattr(pathlib.Path, "read_text", refuse)
    assert not mutate_runner.load_one()


def test_plan_mode_prints_the_grid_size_and_runs_no_suite(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W981: MUTATE_PLAN=1 says how many sites a grid has and starts nothing."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    seen = _seam(monkeypatch, 1, _FAILED)
    monkeypatch.setenv("MUTATE_PLAN", "1")
    assert _run_main(grid) == 0
    out = capsys.readouterr().out
    assert out.startswith("dist: sites=")
    assert "declared=1" in out
    assert seen == []


def test_lint_mode_admits_a_declaration_that_plants_and_runs_no_suite(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W1176: MUTATE_LINT=1 on a clean declaration says nothing, exits 0 and starts no suite."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    seen = _seam(monkeypatch, 1, _FAILED)
    monkeypatch.setenv("MUTATE_LINT", "1")
    assert _run_main(grid) == 0
    assert not capsys.readouterr().err
    assert seen == []


def test_lint_mode_names_each_declaration_the_grid_would_error_or_leave_unapplied(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W1176: a missing module, a stale pattern and an unparsable rewrite are each named."""
    bad = (
        "src/ghost.py|no-module|return 1|return 2|\n"
        "src/mod.py|stale|nothing-here|x|\n"
        "src/mod.py|breaks|return|return (|\n"
    )
    grid = _declared_grid(tmp_path, bad)
    seen = _seam(monkeypatch, 0, _PASSED)
    monkeypatch.setenv("MUTATE_LINT", "1")
    assert _run_main(grid) == 1
    err = capsys.readouterr().err
    assert "no-module: src/ghost.py is not a file" in err
    assert "stale: the pattern matches nothing in its scope" in err
    assert "breaks:" in err
    assert seen == []


def test_plan_line_counts_mutable_sites_without_the_unreachable_ones() -> None:
    """Sites that cannot be mutated do not count toward the cost of a grid."""
    line = mutate_runner.plan_line("d", ["a", "b", "c"], ["c"], 2)
    assert line == "d: sites=2 unreachable=1 declared=2\n"


_GEN_SOURCE = "def f() -> int:\n    return 1\n\n\ndef g() -> int:\n    return 2\n"
_GEN_GRAPH = (
    '{"modules": {"src/p/__init__.py": {"imports": [], "reads": []},'
    ' "src/p/a.py": {"imports": [], "reads": []},'
    ' "src/p/b.py": {"imports": ["src/p/a.py"], "reads": []}},'
    ' "tests": {"tests/test_a.py": {"imports": ["src/p/a.py"], "reads": []},'
    ' "tests/test_b.py": {"imports": ["src/p/b.py"], "reads": []}}}'
)


def _gen_dist(tmp_path: pathlib.Path, declaration: str = "") -> pathlib.Path:
    dist = tmp_path / "d"
    (dist / "src" / "p").mkdir(parents=True)
    (dist / "tests").mkdir()
    for name in ("a", "b"):
        (dist / "src" / "p" / f"{name}.py").write_text(_GEN_SOURCE, encoding="utf-8")
        (dist / "tests" / f"test_{name}.py").write_text("", encoding="utf-8")
    (dist / "src" / "p" / "__init__.py").write_text("", encoding="utf-8")
    (dist / "graph.json").write_text(_GEN_GRAPH, encoding="utf-8")
    (dist / "pyproject.toml").write_text("", encoding="utf-8")
    if declaration:
        (dist / "mutants.regex").write_text(declaration, encoding="utf-8")
    return dist


def test_a_cell_names_its_target_after_its_own_key_and_a_declared_one_is_prefixed() -> None:
    """W1883: the name is the key's part after `::`, made safe, never an index."""
    plain = mutants_gen.Cell("src/p/a.py::K.m", "src/p/a.py", (), ())
    declared = mutants_gen.Cell("src/p/a.py::a b", "src/p/a.py", (), (), declared=True)
    assert plain.name == "K.m"
    assert declared.name == "declared_a_b"
    assert mutants_gen.package_of("d", "src/p/a.py") == "d/sites/src/p/a"
    assert mutants_gen.label("d", "src/p/a.py") == "//d:src/p/a.py"


def test_a_site_stages_its_module_the_cone_of_its_tests_and_those_tests(
    tmp_path: pathlib.Path,
) -> None:
    """W1883: a is seen by test_a and, through b, test_b; the cone and the inits are staged."""
    dist = _gen_dist(tmp_path)
    cells = {c.key: c for c in mutants_gen.cells_of(dist)}
    only_a = cells["src/p/a.py::f"]
    assert only_a.tests == ("tests/test_a.py", "tests/test_b.py")
    assert only_a.sources == ("src/p/__init__.py", "src/p/a.py", "src/p/b.py")
    assert cells["src/p/b.py::f"].tests == ("tests/test_b.py",)


def test_the_generated_package_carries_the_site_its_tests_and_a_suite(
    tmp_path: pathlib.Path,
) -> None:
    """W1883: one `mutant_site` per cell with MUTATE_TESTS spelled out, and a visible suite."""
    files = mutants_gen.generate(_gen_dist(tmp_path))
    text = files["d/sites/src/p/a/BUILD.bazel"]
    assert 'site = "src/p/a.py::f"' in text
    assert 'tests = "tests/test_a.py tests/test_b.py"' in text
    assert '"//d:src/p/b.py",' in text
    assert 'visibility = ["//d/sites:__pkg__"]' in text
    root = files["d/sites/BUILD.bazel"]
    assert '"//d/sites/src/p/a:suite",' in root
    assert '"//d/sites/src/p/b:suite",' in root
    assert sorted(files) == [
        "d/sites/BUILD.bazel",
        "d/sites/src/p/a/BUILD.bazel",
        "d/sites/src/p/b/BUILD.bazel",
    ]


def test_every_generated_suite_is_manual_so_a_wildcard_never_runs_the_sites(
    tmp_path: pathlib.Path,
) -> None:
    """W1989: both levels of suite carry `manual`, because a suite lists its tests explicitly.

    A `manual` site named by an un-tagged `test_suite` is still run by `//...`.
    """
    files = mutants_gen.generate(_gen_dist(tmp_path))
    for name in ("d/sites/BUILD.bazel", "d/sites/src/p/a/BUILD.bazel"):
        assert 'tags = ["manual"]' in files[name].split("test_suite(")[1]


def test_a_def_site_omits_mutants_regex_and_a_declared_defect_stages_it(
    tmp_path: pathlib.Path,
) -> None:
    """W1883: editing a declaration must rerun no def-site."""
    dist = _gen_dist(tmp_path, "src/p/a.py|f-two|return 1|return 2|def=f\n")
    text = mutants_gen.generate(dist)["d/sites/src/p/a/BUILD.bazel"]
    sites = text.split("mutant_site(")[1:]
    declared = [s for s in sites if "declared_" in s.split(",")[0]]
    plain = [s for s in sites if "declared_" not in s.split(",")[0]]
    assert declared
    assert all('"//d:mutants.regex"' in s for s in declared)
    assert not any("mutants.regex" in s for s in plain)


def test_a_module_the_graph_cannot_narrow_stages_the_whole_distribution(
    tmp_path: pathlib.Path,
) -> None:
    """W1883: no graph means every source and the whole tests directory, never a guess."""
    dist = _gen_dist(tmp_path)
    (dist / "graph.json").unlink()
    text = mutants_gen.generate(dist)["d/sites/src/p/a/BUILD.bazel"]
    assert 'tests = ""' in text
    assert '"//d:tests/test_a.py",' in text
    assert '"//d:tests/test_b.py",' in text


def test_check_names_a_stale_or_orphaned_package_and_write_makes_it_fresh(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W1883: --check exits 1 on a missing file and on one whose module is gone; --write heals."""
    _gen_dist(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert mutants_gen.main(["--dist", "d", "--check"]) == 1
    assert "stale d/sites/BUILD.bazel" in capsys.readouterr().out
    assert mutants_gen.main(["--dist", "d", "--write"]) == 0
    assert mutants_gen.main(["--dist", "d", "--check"]) == 0
    orphan = tmp_path / "d" / "sites" / "src" / "p" / "gone" / "BUILD.bazel"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("", encoding="utf-8")
    assert mutants_gen.main(["--dist", "d", "--check"]) == 1
    assert "stale d/sites/src/p/gone/BUILD.bazel" in capsys.readouterr().out
    assert mutants_gen.main(["--dist", "nope", "--check"]) == mutants_gen.EXIT_USAGE


_NINE = 9


class _Ledger:
    """A fake non-blocking claim table shared by every pool in a test."""

    def __init__(self) -> None:
        self.held: set[str] = set()

    def take(self, label: str) -> bool:
        if label in self.held:
            return False
        self.held.add(label)
        return True


def test_two_pools_sharing_one_taker_take_at_most_the_cpus_between_them() -> None:
    """W1765: the first pool takes its ceiling, the second gets only what is left."""
    ledger = _Ledger()
    ceiling = str(_NINE)
    first = mutate_runner.pool_size(ceiling, _CPUS, 1, take=ledger.take)
    second = mutate_runner.pool_size(ceiling, _CPUS, 1, take=ledger.take)
    assert first == _NINE
    assert first + second <= _CPUS
    assert second == _CPUS - _NINE


def test_a_pool_with_no_free_core_still_runs_one_worker_and_never_waits() -> None:
    """The control: every label held, the pool is one worker rather than none or a wait."""
    ledger = _Ledger()
    ledger.held.update(f"{mutate_runner.CORE_LABEL}:{k}" for k in range(_CPUS))
    assert mutate_runner.pool_size("3", _CPUS, 1, take=ledger.take) == 1


def test_claim_cores_stops_at_the_wanted_count_and_takes_labels_in_order() -> None:
    """A pool never hoards: it takes `wanted` labels, lowest first."""
    ledger = _Ledger()
    got = mutate_runner.claim_cores(2, _CPUS, ledger.take)
    assert got == [f"{mutate_runner.CORE_LABEL}:0", f"{mutate_runner.CORE_LABEL}:1"]
    assert ledger.held == set(got)


_NAMED_NODE = "tests/test_env.py::test_the_checker"
_NAMED_FAILURE = f"FAILED {_NAMED_NODE} - AssertionError\n1 failed in 0.01s\n"
_TWO = "src/mod.py|returns-two|return 1|return 2|\nsrc/mod.py|returns-three|return 1|return 3|\n"


def _controlled(
    monkeypatch: pytest.MonkeyPatch,
    *,
    clean_fails: bool,
    named: str = _NAMED_FAILURE,
    no_tests: bool = False,
    times_out: bool = False,
) -> list[tuple[str, str]]:
    """Replace `launch` with a suite that fails on every mutant, naming a failing test.

    The UNMUTATED module passes unless `clean_fails`, as a test broken by the environment would not.

    Returns:
        each run's (module text, last argument), the last argument being what was run.

    """
    monkeypatch.setattr(mutate_runner, "_CONTROLS", {})
    runs: list[tuple[str, str]] = []

    def suite(
        argv: list[str], cwd: pathlib.Path, env: dict[str, str]
    ) -> subprocess.CompletedProcess[str]:
        text = (cwd / "src" / "mod.py").read_text(encoding="utf-8")
        runs.append((text, [a for a in argv if not a.startswith("-")][-1]))
        # The plugin's report: the Python test ids the failure text names, as pytest would write.
        failed = [
            ln.removeprefix("FAILED ").split(" - ")[0]
            for ln in named.splitlines()
            if ln.startswith("FAILED ") and ".py::" in ln
        ]
        if text != _SITE_SOURCE and "MUTATE_NODES" in env:
            report = pathlib.Path(env["MUTATE_NODES"])
            lines = [json.dumps(node) + "\n" for node in failed]
            report.write_text("".join(lines), encoding="utf-8")
        if text == _SITE_SOURCE and times_out:
            raise subprocess.TimeoutExpired(argv, 1)
        if text == _SITE_SOURCE and no_tests:
            return subprocess.CompletedProcess(argv, 5, "no tests ran\n", "")
        if text == _SITE_SOURCE and not clean_fails:
            return subprocess.CompletedProcess(argv, 0, _PASSED, "")
        return subprocess.CompletedProcess(argv, 1, named, "")

    monkeypatch.setattr(mutate_runner, "launch", suite)
    return runs


def test_a_kill_by_a_test_that_also_fails_on_the_clean_module_is_errored(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2340: the named failing test is put against the original module; failing there, no kill."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    runs = _controlled(monkeypatch, clean_fails=True)
    (declared,) = mutate_runner.read_declared(grid.dist)
    assert mutate_runner.run_declared(grid, declared) == "errored"
    assert runs == [
        ("def f():\n    return 2\n", "tests"),
        (_SITE_SOURCE, "tests/test_env.py::test_the_checker"),
    ]


def test_a_kill_by_a_test_that_passes_on_the_clean_module_stays_a_kill(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2340: the control is no veto; a test that holds on the original module killed it."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    _controlled(monkeypatch, clean_fails=False)
    (declared,) = mutate_runner.read_declared(grid.dist)
    assert mutate_runner.run_declared(grid, declared) == "killed"


def _noted(grid: mutate_runner.Grid, declared: Declared) -> tuple[str, dict[str, str]]:
    notes: dict[str, str] = {}
    got = mutate_runner.timed(
        {}, declared.label, lambda: mutate_runner.run_declared(grid, declared), notes
    )
    return got, notes


def test_a_vouched_kill_names_its_killer_and_that_it_passed_in_the_control(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2818: 'failed under the mutant, passed in the control' is what a flaky neighbour looks like.

    github-00's condition 2 on the revised b108: the log names the test and the control's pass.
    """
    grid = _declared_grid(tmp_path, _DECLARATION)
    _controlled(monkeypatch, clean_fails=False)
    (declared,) = mutate_runner.read_declared(grid.dist)
    got, notes = _noted(grid, declared)
    assert got == "killed"
    assert notes[declared.label] == (
        f"killed by {_NAMED_NODE} (control: passed on the unmutated module)"
    )


def test_a_kill_the_control_could_not_vouch_for_names_no_killer(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The other case: the named test also fails on the clean module, so errored and no note."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    _controlled(monkeypatch, clean_fails=True)
    (declared,) = mutate_runner.read_declared(grid.dist)
    got, notes = _noted(grid, declared)
    assert got == "errored"
    assert notes == {}


def test_a_kill_by_several_failing_tests_names_the_first_and_counts_the_rest(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The first failing node is named, so the control's choice is visible, and the rest counted."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    named = (
        "FAILED tests/test_a.py::test_one - AssertionError\n"
        "FAILED tests/test_b.py::test_two - AssertionError\n2 failed in 0.01s\n"
    )
    _controlled(monkeypatch, clean_fails=False, named=named)
    (declared,) = mutate_runner.read_declared(grid.dist)
    _got, notes = _noted(grid, declared)
    assert notes[declared.label] == (
        "killed by tests/test_a.py::test_one and 1 more (control: passed on the unmutated module)"
    )


def test_a_suite_ended_by_the_cpu_limit_is_a_kill_that_names_no_test(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A hang killed by the limit names no test, and says so, so it is not read as a test's kill."""
    grid = _declared_grid(tmp_path, _DECLARATION)

    def hangs(
        argv: list[str], _cwd: pathlib.Path, _env: dict[str, str]
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(argv, 1)

    monkeypatch.setattr(mutate_runner, "launch", hangs)
    (declared,) = mutate_runner.read_declared(grid.dist)
    got, notes = _noted(grid, declared)
    assert got == "killed"
    assert notes[declared.label].startswith("killed by no test: the suite ended")


def test_the_cell_line_carries_the_note_after_the_id_and_a_cell_without_one_is_unchanged() -> None:
    """W2818: the note follows the id on the same line; other cells print exactly as before."""
    lines = mutate_runner.cell_lines(
        {"a": 1.0}, ["a", "b"], {"a": "killed by t.py::x (control: passed on the unmutated module)"}
    )
    assert lines == (
        "cell cpu=1.0s a killed by t.py::x (control: passed on the unmutated module)\n"
        "cell cpu=0.0s b\n"
    )
    assert mutate_runner.cell_lines({"a": 1.0}, ["a"]) == "cell cpu=1.0s a\n"


def test_the_suite_is_launched_without_the_callers_pythonhome(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2340: bazel's launcher exports PYTHONHOME; a host python3 a suite starts dies under it.

    fence's payload is the host interpreter (3.14) and exited 1 at startup under the hermetic 3.13
    home, so a cap test never allocated and its control read as a failure of the clean module.
    """
    grid = _declared_grid(tmp_path, _DECLARATION)
    monkeypatch.setenv("PYTHONHOME", "/not/the/hosts/python")
    seen: list[dict[str, str]] = []

    def suite(
        argv: list[str], _cwd: pathlib.Path, env: dict[str, str]
    ) -> subprocess.CompletedProcess[str]:
        seen.append(dict(env))
        return subprocess.CompletedProcess(argv, 0, _PASSED, "")

    monkeypatch.setattr(mutate_runner, "launch", suite)
    (declared,) = mutate_runner.read_declared(grid.dist)
    mutate_runner.run_declared(grid, declared)
    assert seen
    assert all("PYTHONHOME" not in env for env in seen)


def test_the_control_is_asked_once_per_failing_test_across_mutants(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2340: two mutants killed by one test cost one control run, not two."""
    grid = _declared_grid(tmp_path, _TWO)
    runs = _controlled(monkeypatch, clean_fails=False)
    verdicts = [mutate_runner.run_declared(grid, d) for d in mutate_runner.read_declared(grid.dist)]
    assert verdicts == ["killed", "killed"]
    assert sum(1 for text, _ in runs if text == _SITE_SOURCE) == 1


def test_a_parametrized_id_with_spaces_is_run_whole_by_the_control(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2340: the id ends at ' - ', not at its first space; the whole id reaches pytest."""
    spaced = "tests/test_w.py::test_cp[cp -r a b]"
    named = f"FAILED {spaced} - AssertionError\n1 failed in 0.01s\n"
    grid = _declared_grid(tmp_path, _DECLARATION)
    runs = _controlled(monkeypatch, clean_fails=False, named=named)
    (declared,) = mutate_runner.read_declared(grid.dist)
    assert mutate_runner.run_declared(grid, declared) == "killed"
    assert runs[1] == (_SITE_SOURCE, spaced)


def test_a_control_that_collects_no_test_cannot_vouch_so_the_cell_is_errored(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B2 (github-cb): exit code 5 proves nothing about the baseline, so no kill is vouched for."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    _controlled(monkeypatch, clean_fails=False, no_tests=True)
    (declared,) = mutate_runner.read_declared(grid.dist)
    assert mutate_runner.run_declared(grid, declared) == "errored"


def test_a_control_that_times_out_errors_the_cell_and_is_asked_again_for_the_next_mutant(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B2: a control that cannot run is not a pass and is not cached, so each mutant asks again."""
    grid = _declared_grid(tmp_path, _TWO)
    runs = _controlled(monkeypatch, clean_fails=False, times_out=True)
    verdicts = [mutate_runner.run_declared(grid, d) for d in mutate_runner.read_declared(grid.dist)]
    assert verdicts == ["errored", "errored"]
    assert sum(1 for text, _ in runs if text == _SITE_SOURCE) == len(verdicts)


def test_a_failed_line_for_a_non_test_item_does_not_become_the_controls_id(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2769: the control runs the node pytest reported, not the first `FAILED` line of the text.

    pytestspec prints `FAILED spec.rego::p` for a spec item, ahead of the real test's line. That id
    collects nothing, so the cell read ERRORED; it must read the true verdict.
    """
    noisy = (
        f"FAILED spec.rego::p - AssertionError\nFAILED {_NAMED_NODE} - AssertionError\n1 failed\n"
    )
    grid = _declared_grid(tmp_path, _DECLARATION)
    runs = _controlled(monkeypatch, clean_fails=False, named=noisy)
    (declared,) = mutate_runner.read_declared(grid.dist)
    assert mutate_runner.run_declared(grid, declared) == "killed"
    assert runs[1] == (_SITE_SOURCE, _NAMED_NODE)


def test_a_suite_that_reports_no_failed_python_test_gets_no_control(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2769: only a spec item failed, so there is no test to put against the clean module."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    spec_only = "FAILED spec.rego::p - AssertionError\n1 failed\n"
    runs = _controlled(monkeypatch, clean_fails=False, named=spec_only)
    (declared,) = mutate_runner.read_declared(grid.dist)
    assert mutate_runner.run_declared(grid, declared) == "killed"
    assert [text for text, _ in runs] == ["def f():\n    return 2\n"]


def test_failing_nodes_keeps_python_test_ids_and_skips_well_formed_spec_ids(
    tmp_path: pathlib.Path,
) -> None:
    """W2769: a well-formed spec id is a declared non-test; an empty report names no test."""
    report = tmp_path / "nodes.jsonl"
    report.write_text('"spec.rego::p"\n"tests/test_a.py::test_x[a b]"\n', encoding="utf-8")
    assert mutate_runner.failing_nodes(report) == ["tests/test_a.py::test_x[a b]"]
    report.write_text("", encoding="utf-8")
    assert mutate_runner.failing_nodes(report) == []


def test_a_missing_node_report_is_a_typed_error_and_never_an_empty_list(
    tmp_path: pathlib.Path,
) -> None:
    """W2769 R1: absence means the plugin did not run, so it cannot read as no failing test."""
    with pytest.raises(mutate_runner.NodeReportMissingError):
        mutate_runner.failing_nodes(tmp_path / "absent.jsonl")


@pytest.mark.parametrize("bad", ["not json\n", "42\n", "[1]\n"])
def test_a_line_the_plugin_wrote_that_is_not_a_node_id_is_a_typed_error(
    tmp_path: pathlib.Path, bad: str
) -> None:
    """W2769 R2: an unparseable line is a broken instrument, refused rather than skipped."""
    report = tmp_path / "nodes.jsonl"
    report.write_text(bad, encoding="utf-8")
    with pytest.raises(mutate_runner.NodeReportMalformedError):
        mutate_runner.failing_nodes(report)


def test_a_suite_whose_plugin_never_loaded_errors_the_cell_and_names_the_reason(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W2769 R1: a suite launched without the plugin writes no report, and the cell is ERRORED."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    monkeypatch.setattr(mutate_runner, "_CONTROLS", {})

    def suite(
        argv: list[str], _cwd: pathlib.Path, _env: dict[str, str]
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, _NAMED_FAILURE, "")

    monkeypatch.setattr(mutate_runner, "launch", suite)
    (declared,) = mutate_runner.read_declared(grid.dist)
    assert mutate_runner.run_declared(grid, declared) == "errored"
    assert "the plugin did not run" in capsys.readouterr().out


_SPEC_CONFTEST = """\
import pytest


class SpecItem(pytest.Item):
    def runtest(self):
        raise AssertionError("the spec item fails")

    def reportinfo(self):
        return self.path, 0, "spec"


class SpecFile(pytest.File):
    def collect(self):
        yield SpecItem.from_parent(self, name="p")


def pytest_collect_file(parent, file_path):
    if file_path.suffix == ".rego":
        return SpecFile.from_parent(parent, path=file_path)
    return None
"""


def _pytest_with_plugin(
    root: pathlib.Path, report: pathlib.Path
) -> subprocess.CompletedProcess[str]:
    """Run real pytest in `root` with the runner's node plugin written beside the tests.

    Returns:
        the completed pytest process.

    """
    (root / mutate_runner.PLUGIN_FILE).write_text(mutate_runner.NODE_PLUGIN, encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "_mutate_nodes"],
        cwd=root,
        env={**os.environ, "MUTATE_NODES": str(report), "PYTHONPATH": str(root)},
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_node_plugin_creates_an_empty_report_when_no_test_fails(
    tmp_path: pathlib.Path,
) -> None:
    """W2769 R1: a suite that ran and failed nothing leaves an EMPTY file, not a missing one."""
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    pass\n", encoding="utf-8")
    report = tmp_path / mutate_runner.REPORT_FILE
    _pytest_with_plugin(tmp_path, report)
    assert report.is_file()
    assert mutate_runner.failing_nodes(report) == []


def test_the_node_plugin_names_the_real_test_when_a_spec_item_fails_ahead_of_it(
    tmp_path: pathlib.Path,
) -> None:
    """W2769: real pytest, a spec item whose `FAILED` line precedes the real test's.

    The text's first `FAILED` line names `spec.rego::p`, which pytest cannot collect; the plugin's
    report names only the test.
    """
    (tmp_path / "conftest.py").write_text(_SPEC_CONFTEST, encoding="utf-8")
    (tmp_path / "spec.rego").write_text("p\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_real.py").write_text(
        "def test_real():\n    raise AssertionError('real')\n", encoding="utf-8"
    )
    report = tmp_path / mutate_runner.REPORT_FILE
    done = _pytest_with_plugin(tmp_path, report)
    spec_line = done.stdout.index("FAILED spec.rego::p")
    assert spec_line < done.stdout.index("FAILED tests/test_real.py::test_real")
    assert mutate_runner.failing_nodes(report) == ["tests/test_real.py::test_real"]


_REGEN_REPORT = (
    "KILLED (1) \N{EM DASH} the suite RAN and a test FAILED:\n    src/m.py::f\n\n"
    "SURVIVED (1) \N{EM DASH} the suite ran and noticed nothing:\n    src/m.py::g\n\n"
    "ERRORED (0) \N{EM DASH} the suite did NOT run, so it noticed nothing:\n\n"
    "REGEX (0) \N{EM DASH} defects the distribution DECLARED:\n"
)


def _dist_with_logs(
    root: pathlib.Path, baseline: str, shard: str
) -> tuple[pathlib.Path, pathlib.Path]:
    dist = root / "d"
    dist.mkdir()
    (dist / "mutants-baseline.txt").write_text(baseline, encoding="utf-8")
    log = root / "logs" / "d" / shard / "test.log"
    log.parent.mkdir(parents=True)
    log.write_text(_REGEN_REPORT, encoding="utf-8")
    return dist, root / "logs"


def test_regen_takes_a_cell_off_that_now_reads_killed_and_says_so(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2777: the stale errored cell is paid down and the surviving one stays."""
    old = "errored src/m.py::f\nsurvived src/m.py::g\n"
    dist, logs = _dist_with_logs(tmp_path, old, "mutants_1")
    assert mutate_runner.regen_baseline(dist, logs) == 0
    out = capsys.readouterr().out
    assert "OFF errored src/m.py::f" in out
    assert "paydown: 1 cell(s) off" in out
    written = (dist / "mutants-baseline.txt").read_text(encoding="utf-8")
    assert written.endswith("survived src/m.py::g\n")
    assert "src/m.py::f" not in written


def test_regen_reads_a_new_cell_as_debt_and_exits_one(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2777: a cell the baseline never listed is NEW debt, named, and the exit is 1."""
    dist, logs = _dist_with_logs(tmp_path, "", "mutants_1")
    assert mutate_runner.regen_baseline(dist, logs) == 1
    out = capsys.readouterr().out
    assert "NEW survived src/m.py::g" in out
    assert "the debt may only fall" in out


def test_regen_finds_a_plain_targets_log_and_refuses_a_dist_with_none(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2777: `mutants/test.log` serves a plain sh_test; no log at all is refused, named."""
    dist, logs = _dist_with_logs(tmp_path, "survived src/m.py::g\n", "mutants")
    assert mutate_runner.regen_baseline(dist, logs) == 0
    capsys.readouterr()
    assert mutate_runner.regen_baseline(dist, tmp_path / "nowhere") == 1
    assert "no mutation test logs for d" in capsys.readouterr().err


def _shard_log(root: pathlib.Path, shard: int, total: int) -> None:
    """Write one shard's log, stating `shard i/N` the way the runner's report does."""
    log = root / "logs" / "d" / f"mutants_{shard}" / "test.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(f"d shard {shard}/{total}: ATTEMPTED 1 def-site(s)\n" + _REGEN_REPORT, "utf-8")


def test_regen_names_a_malformed_old_baseline_and_changes_nothing(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2777 R1: an unreadable old baseline is refused with its problem, never read as empty."""
    dist, logs = _dist_with_logs(tmp_path, "not a baseline line\n", "mutants_1")
    assert mutate_runner.regen_baseline(dist, logs) == 1
    assert "not '<verdict> <cell>'" in capsys.readouterr().err
    assert (dist / "mutants-baseline.txt").read_text(encoding="utf-8") == "not a baseline line\n"


def test_regen_with_a_new_cell_leaves_the_baseline_file_untouched(tmp_path: pathlib.Path) -> None:
    """W2777 R2: debt is written only when nothing is NEW; a NEW cell exits 1 and writes nothing."""
    dist, logs = _dist_with_logs(tmp_path, "", "mutants_1")
    before = (dist / "mutants-baseline.txt").read_bytes()
    assert mutate_runner.regen_baseline(dist, logs) == 1
    assert (dist / "mutants-baseline.txt").read_bytes() == before


def test_a_complete_shard_set_is_accepted_and_a_leftover_beyond_the_count_is_refused(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2777 R3: shards 0 and 1 of 2 regenerate; a leftover mutants_9 of another layout refuses."""
    dist = tmp_path / "d"
    dist.mkdir()
    (dist / "mutants-baseline.txt").write_text("survived src/m.py::g\n", encoding="utf-8")
    _shard_log(tmp_path, 0, 2)
    _shard_log(tmp_path, 1, 2)
    assert mutate_runner.regen_baseline(dist, tmp_path / "logs") == 0
    capsys.readouterr()
    _shard_log(tmp_path, 9, 433)
    assert mutate_runner.regen_baseline(dist, tmp_path / "logs") == 1
    assert "leftover" in capsys.readouterr().err


def test_a_missing_shard_in_the_set_is_refused(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2777 R3: only shard 0 of 2 is present, so the set is incomplete and refuses."""
    dist = tmp_path / "d"
    dist.mkdir()
    _shard_log(tmp_path, 0, 2)
    assert mutate_runner.regen_baseline(dist, tmp_path / "logs") == 1
    assert "not exactly shards 0..1" in capsys.readouterr().err


def _fake_venv(root: pathlib.Path, home: str) -> pathlib.Path:
    # A venv shaped like bazel's: a pyvenv.cfg, a bin/python3 entry and one package of its own.
    (root / "bin").mkdir(parents=True)
    interpreter = root / "bin" / "python3"
    interpreter.write_text("#!/bin/sh\n", encoding="utf-8")
    (root / "pyvenv.cfg").write_text(f"home = {home}\nversion = 3.13.0\n", encoding="utf-8")
    site = root / "lib" / "python3.13" / "site-packages"
    site.mkdir(parents=True)
    (site / "zz_marker.py").write_text("VALUE = 'from the venv'\n", encoding="utf-8")
    return interpreter


def test_a_relative_home_venv_runs_through_a_private_venv_whose_children_find_the_packages(
    tmp_path: pathlib.Path,
) -> None:
    """W2340: a child started from another directory with NO environment still imports the venv."""
    interpreter = _fake_venv(tmp_path / "venv", "bin")
    chosen, extra = mutate_runner.portable_python(interpreter)
    assert not extra
    assert chosen != str(interpreter)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    code = "import zz_marker; print(zz_marker.VALUE)"
    done = subprocess.run(
        [chosen, "-c", code], cwd=elsewhere, env={}, capture_output=True, text=True, check=False
    )
    assert (done.returncode, done.stdout.strip()) == (0, "from the venv")


def test_an_absolute_home_or_no_config_keeps_the_interpreter_as_given(
    tmp_path: pathlib.Path,
) -> None:
    """W2340: only a relative home needs the private venv; the rest run as they always did."""
    absolute = _fake_venv(tmp_path / "absolute", str(tmp_path))
    assert mutate_runner.portable_python(absolute) == (str(absolute), "")
    bare = tmp_path / "bare" / "bin" / "python3"
    bare.parent.mkdir(parents=True)
    assert mutate_runner.portable_python(bare) == (str(bare), "")


def test_an_env_value_naming_a_file_under_the_base_is_made_absolute_and_nothing_else_is(
    tmp_path: pathlib.Path,
) -> None:
    """W2340: a relative path to a staged file points at the real file; prose and gaps stay."""
    (tmp_path / "tool").mkdir()
    (tmp_path / "tool" / "ruff").write_text("", encoding="utf-8")
    huge = "a" * 5000
    env = {
        "RUFF_BIN": "tool/ruff",
        "CONTROL_RUFF": "tool/ruff",
        "NOTE": "two words",
        "GONE": "tool/missing",
        "DIR": "tool",
        "ABS": "/usr/bin/env",
        "LONG": huge,
    }
    mutate_runner.absolute_tools(env, tmp_path)
    real = str((tmp_path / "tool" / "ruff").resolve())
    assert (env["RUFF_BIN"], env["CONTROL_RUFF"]) == (real, real)
    assert (env["NOTE"], env["GONE"], env["DIR"], env["ABS"], env["LONG"]) == (
        "two words",
        "tool/missing",
        "tool",
        "/usr/bin/env",
        huge,
    )


def _runfiles_root(tmp_path: pathlib.Path) -> pathlib.Path:
    # A runfiles root: the dist under test, a sibling dist with a file, and a root script.
    root = tmp_path / "runfiles"
    (root / "dist").mkdir(parents=True)
    (root / "sibling").mkdir()
    (root / "sibling" / "BUILD.bazel").write_text("one\n", encoding="utf-8")
    (root / "tool.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    return root


def test_the_siblings_are_copied_once_per_process_and_hard_linked_into_each_tree(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B3 (github-cb): two mutants cost one copy and share its bytes, not two copies."""
    root = _runfiles_root(tmp_path)
    monkeypatch.setenv("TEST_SRCDIR", str(root))
    monkeypatch.setattr(mutate_runner, "_MIRRORS", {})
    first, second = tmp_path / "one", tmp_path / "two"
    first.mkdir()
    second.mkdir()
    mutate_runner.mirror_siblings(root / "dist", first)
    (root / "sibling" / "BUILD.bazel").write_text("changed after the copy\n", encoding="utf-8")
    mutate_runner.mirror_siblings(root / "dist", second)
    assert (first / "sibling" / "BUILD.bazel").read_text(encoding="utf-8") == "one\n"
    assert (second / "sibling" / "BUILD.bazel").read_text(encoding="utf-8") == "one\n"
    assert (second / "tool.sh").is_file()
    assert not (second / "dist").exists()
    ino = (first / "sibling" / "BUILD.bazel").stat().st_ino
    assert ino == (second / "sibling" / "BUILD.bazel").stat().st_ino


def test_a_link_that_cannot_be_made_falls_back_to_a_copy_and_no_symlink_is_made(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B3: os.link refused (another device) leaves a real copy, and no symlink is ever made."""
    root = _runfiles_root(tmp_path)
    monkeypatch.setenv("TEST_SRCDIR", str(root))
    monkeypatch.setattr(mutate_runner, "_MIRRORS", {})

    def refuse(_src: str, _dst: str) -> None:
        raise OSError

    monkeypatch.setattr(os, "link", refuse)
    into = tmp_path / "into"
    into.mkdir()
    mutate_runner.mirror_siblings(root / "dist", into)
    copied = into / "sibling" / "BUILD.bazel"
    assert copied.read_text(encoding="utf-8") == "one\n"
    assert not copied.is_symlink()


def test_outside_bazel_nothing_is_mirrored(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The parent of a dist in a whole checkout already holds its siblings, so none are copied."""
    root = _runfiles_root(tmp_path)
    monkeypatch.delenv("TEST_SRCDIR", raising=False)
    monkeypatch.setattr(mutate_runner, "_MIRRORS", {})
    into = tmp_path / "into"
    into.mkdir()
    mutate_runner.mirror_siblings(root / "dist", into)
    assert list(into.iterdir()) == []


def test_the_private_interpreter_is_built_before_the_first_worker_runs(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The copy of the interpreter is made on one thread, so no fork can hold it open (W2340).

    ⚑ THE ORDER IS THE WITNESS: a worker that built it lazily would record `run` first, and two
    workers forking around the copy gave `Text file busy` on //bibparse:mutants.
    """
    order: list[str] = []

    def prime(py: pathlib.Path) -> tuple[str, str]:
        order.append("prime")
        return str(py), ""

    def worker(_grid: mutate_runner.Grid, _mutant: mutate_runner.Mutant, *, debug: bool) -> str:
        assert not debug
        order.append("run")
        return "killed"

    monkeypatch.setattr(mutate_runner, "portable_python", prime)
    monkeypatch.setattr(mutate_runner, "run", worker)
    grid = mutate_runner.Grid(pathlib.Path(sys.executable), tmp_path, tmp_path / "pyproject.toml")
    mutant = mutate_runner.Mutant(pathlib.Path("mod.py"), "", "mod")
    verdicts, _regex = mutate_runner.run_all(grid, [mutant], [], debug=False)
    assert verdicts == ["killed"]
    assert order == ["prime", "run"]


_GRANDCHILD = r"""
import subprocess, sys
burn = "import time\nt = time.process_time()\nwhile time.process_time() - t < 0.6: pass"
subprocess.run([sys.executable, "-c", burn])
"""


_FLOOR = 0.5
_CEILING = 5.0
_CHARGED = 2.0


def _same_python(py: pathlib.Path) -> tuple[str, str]:
    return str(py), ""


def _spent_by(code: str, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> float:
    spent: dict[str, float] = {}
    mutate_runner.timed(spent, "cell", lambda: _launch(code, monkeypatch, tmp_path))
    return spent["cell"]


def test_a_cell_is_charged_the_cpu_its_suite_burned(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2805: about one CPU second burned by a suite is charged to its cell."""
    assert _FLOOR <= _spent_by(_BUSY, monkeypatch, tmp_path) <= _CEILING


def test_the_cpu_of_a_child_that_has_already_exited_is_still_charged(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The red case of a live-only sum: a child that exited is not lost.

    A suite that spawns short processes (git, bazel) is not undercounted, because the reaped
    child's CPU is in its parent's waited-for time.
    """
    assert _spent_by(_GRANDCHILD, monkeypatch, tmp_path) >= _FLOOR


_BURN_AND_EXIT = "import time\nt = time.process_time()\nwhile time.process_time() - t < 0.6: pass\n"


def test_cpu_burned_and_gone_before_the_first_poll_is_still_charged(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """github-00's plant: a child that burns CPU and exits between polls is charged exactly.

    The poll interval is forced to 30 s, so the progress loop never reads the suite's CPU: a polled
    peak would charge this cell 0.0, and the kernel's own accounting at the reap charges 0.6 s.
    """
    monkeypatch.setenv("MUTATE_POLL_S", "30")
    spent: dict[str, float] = {}

    def job() -> str:
        argv = [sys.executable, "-c", _BURN_AND_EXIT]
        return mutate_runner.launch(argv, tmp_path, dict(os.environ)).stdout

    mutate_runner.timed(spent, "cell", job)
    assert _FLOOR <= spent["cell"] <= _CEILING


def test_a_cell_that_runs_nothing_is_charged_nothing_and_a_raising_cell_is_still_recorded() -> None:
    """The controls: no launch is 0.0, and the CPU is recorded when the job raises."""
    spent: dict[str, float] = {}
    assert mutate_runner.timed(spent, "idle", lambda: "killed") == "killed"
    assert spent == {"idle": 0.0}

    class JobRaisedError(Exception):
        """The job's own failure."""

    def broken() -> str:
        mutate_runner.charge(_CHARGED)
        raise JobRaisedError

    with pytest.raises(JobRaisedError):
        mutate_runner.timed(spent, "broken", broken)
    assert spent["broken"] >= _CHARGED


def test_charge_outside_a_timed_cell_is_ignored() -> None:
    """A launch made by no cell (the control of nothing) charges nothing and raises nothing."""
    mutate_runner.charge(3.0)


def test_the_cell_lines_name_each_cell_in_run_order_and_an_absent_one_reads_zero() -> None:
    """One line per cell, in the given order, one decimal; a cell never timed is 0.0."""
    lines = mutate_runner.cell_lines({"b": 12.34, "a": 0.04}, ["a", "b", "c"])
    assert lines == "cell cpu=0.0s a\ncell cpu=12.3s b\ncell cpu=0.0s c\n"


def test_the_reconciliation_line_says_how_much_of_the_shard_the_cells_account_for() -> None:
    """The witness the instrument needs: the cells' sum, the shard's total and what is left."""
    line = mutate_runner.reconcile_line({"a": 10.0, "b": 5.0}, 20.0)
    assert line == "cells cpu=15.0s shard cpu=20.0s unattributed=5.0s\n"


def test_a_shard_log_carries_a_cell_line_for_each_def_site_and_each_declared_cell(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W2805: after the shard total, def-sites first and declared cells after, each with its CPU."""

    def site(_grid: mutate_runner.Grid, _mutant: mutate_runner.Mutant, *, debug: bool) -> str:
        assert not debug
        mutate_runner.charge(2.5)
        return "killed"

    def planted(_grid: mutate_runner.Grid, _declared: Declared, *, debug: bool) -> str:
        assert not debug
        mutate_runner.charge(40.0)
        return "killed"

    monkeypatch.setattr(mutate_runner, "portable_python", _same_python)
    monkeypatch.setattr(mutate_runner, "run", site)
    monkeypatch.setattr(mutate_runner, "run_declared", planted)
    grid = mutate_runner.Grid(pathlib.Path(sys.executable), tmp_path, tmp_path / "pyproject.toml")
    mutant = mutate_runner.Mutant(pathlib.Path("mod.py"), "", "mod")
    spec = Declared("src/other.py", RegexSpec("watch-never-gives-up", "a", "b"))
    mutate_runner.run_all(grid, [mutant], [spec], debug=False)
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("shard cpu=")
    assert lines[1:3] == [
        "cell cpu=2.5s mod.py::mod",
        "cell cpu=40.0s src/other.py::watch-never-gives-up",
    ]
    assert lines[3].startswith("cells cpu=42.5s shard cpu=")


_EXCLUDED_CELL = "src/mod.py::returns-two"
_OTHER_CELL = "src/other.py::kept"
_PAIR = 2


_Cells = tuple[list[str], list[str], list[tuple[str, mutate_runner.Mutant]], list[Declared]]


def _cells(attempted: list[str], unreachable: list[str]) -> _Cells:
    named, kept = _two_declared()
    return (attempted, unreachable, [], [named, kept])


def _two_declared() -> tuple[Declared, Declared]:
    return (
        Declared("src/mod.py", RegexSpec("returns-two", "a", "b")),
        Declared("src/other.py", RegexSpec("kept", "a", "b")),
    )


def test_the_exclusion_drops_exactly_the_named_cell_and_nothing_else() -> None:
    """W2816: the named declared cell leaves the run; every other cell is untouched."""
    _named, kept = _two_declared()
    cells = _cells(["src/a.py::f"], ["src/a.py::g"])
    attempted, unreachable, jobs, declared = mutate_runner.drop_excluded(_EXCLUDED_CELL, cells)
    assert declared == [kept]
    assert (attempted, unreachable, jobs) == (["src/a.py::f"], ["src/a.py::g"], [])


def test_an_unset_exclusion_drops_nothing() -> None:
    """The control: no MUTATE_EXCLUDE is the run as it was."""
    cells = _cells(["src/a.py::f"], [])
    assert mutate_runner.drop_excluded("", cells) == cells


def test_an_excluded_label_that_is_no_cell_of_the_run_is_refused_by_name() -> None:
    """A stale or misdirected label raises, naming each such label, never ignored."""
    cells = _cells(["src/a.py::f"], [])
    with pytest.raises(ValueError, match=r"src/gone\.py::old") as caught:
        mutate_runner.drop_excluded(f"{_EXCLUDED_CELL} src/gone.py::old", cells)
    assert _EXCLUDED_CELL not in str(caught.value)


def test_the_header_line_names_every_effective_exclusion_or_none() -> None:
    """W2812's lesson: an exclusion that did not take is visible in the log header."""
    assert mutate_runner.excluded_line("") == "excluded (MUTATE_EXCLUDE): none\n"
    both = mutate_runner.excluded_line(f"{_OTHER_CELL} {_EXCLUDED_CELL}")
    assert both == f"excluded (MUTATE_EXCLUDE): {_PAIR} cell(s): {_EXCLUDED_CELL}, {_OTHER_CELL}\n"


def test_a_grid_run_prints_the_exclusion_and_does_not_plant_the_excluded_defect(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Through main: the header names it, REGEX lists no cell, and a stale label exits 1 by name."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    _seam(monkeypatch, 0, _PASSED)
    monkeypatch.setenv("MUTATE_EXCLUDE", _EXCLUDED_CELL)
    assert _run_main(grid) == 0
    out = capsys.readouterr().out
    assert f"excluded (MUTATE_EXCLUDE): 1 cell(s): {_EXCLUDED_CELL}" in out
    assert "REGEX (0)" in out
    monkeypatch.setenv("MUTATE_EXCLUDE", "src/gone.py::old")
    assert _run_main(grid) == 1
    assert "src/gone.py::old" in capsys.readouterr().err


def test_an_exclusion_changes_only_the_shard_that_holds_the_cell(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Both directions: the holder drops exactly that cell, the other shard's plan is identical."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    holder = 0 if mutate_runner.in_shard(_EXCLUDED_CELL, (0, _PAIR)) else 1
    other = 1 - holder
    monkeypatch.setenv("MUTATE_PLAN", "1")

    def plan(shard: int, exclude: str) -> str:
        monkeypatch.setenv("MUTATE_SHARD", f"{shard}/{_PAIR}")
        monkeypatch.setenv("MUTATE_EXCLUDE", exclude)
        assert _run_main(grid) == 0
        return capsys.readouterr().out

    before_other = plan(other, "")
    assert "declared=1" in plan(holder, "")
    assert "declared=0" in plan(holder, _EXCLUDED_CELL)
    assert plan(other, "") == before_other


_CELL = "src/mod.py::returns-two"


def _baselined(grid: mutate_runner.Grid, text: str) -> None:
    (grid.dist / mutate_runner.BASELINE_FILE).write_text(text, encoding="utf-8")


def test_a_baselined_survivor_passes_and_the_same_cell_killed_is_a_stale_entry(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W2340: debt on record passes, and a recorded cell that is now killed fails as STALE."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    _baselined(grid, f"survived {_CELL}\n")
    _seam(monkeypatch, 0, _PASSED)
    assert _run_main(grid) == 0
    assert "0 rise(s), 0 stale" in capsys.readouterr().out
    _seam(monkeypatch, 1, _FAILED)
    assert _run_main(grid) == 1
    assert f"STALE survived {_CELL}" in capsys.readouterr().out


def test_a_survivor_the_baseline_does_not_list_is_a_rise_and_fails(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W2340: a cell in debt that the baseline lacks, or lists under another verdict, is a RISE."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    _seam(monkeypatch, 0, _PASSED)
    assert _run_main(grid) == 1
    assert f"RISE survived {_CELL}" in capsys.readouterr().out
    _baselined(grid, f"errored {_CELL}\n")
    assert _run_main(grid) == 1
    assert f"RISE survived {_CELL}" in capsys.readouterr().out


def test_a_baseline_entry_for_a_cell_this_shard_did_not_run_is_not_judged(
    tmp_path: pathlib.Path,
) -> None:
    """W2340: only the cells a run ran are judged, so a shard never refuses another shard's debt."""
    grid = _declared_grid(tmp_path, _DECLARATION)
    _baselined(grid, "errored src/other.py::elsewhere\n")
    assert mutate_runner.baseline_gate(grid.dist, {}, {_CELL}) == 0


def test_a_baseline_is_read_sorted_and_a_hand_edit_that_breaks_it_is_named(
    tmp_path: pathlib.Path,
) -> None:
    """W2340: comments and blanks are skipped, and an unknown verdict or a disorder is a problem."""
    grid = _declared_grid(tmp_path)
    assert mutate_runner.read_baseline(grid.dist) == ({}, "")
    _baselined(grid, "# note\n\nerrored a::x\nsurvived b::y\n")
    assert mutate_runner.read_baseline(grid.dist) == ({"a::x": "errored", "b::y": "survived"}, "")
    _baselined(grid, "errored b::y\nerrored a::x\n")
    assert "out of order" in mutate_runner.read_baseline(grid.dist)[1]
    _baselined(grid, "ignored a::x\n")
    assert "not '<verdict> <cell>'" in mutate_runner.read_baseline(grid.dist)[1]


_REPORT = """fence shard 1/2: ATTEMPTED 3 def-site(s) in 1 module(s)

KILLED (1) — the suite RAN and a test FAILED:
    src/m.py::a

SURVIVED (1) — the suite ran and noticed nothing:
    src/m.py::b

ERRORED (0) — the suite did NOT run, so it noticed nothing:

UNREACHABLE (1) — constructed at IMPORT time:
    src/m.py::Enum

REGEX (2) — defects the distribution DECLARED:
    src/m.py::planted -> killed
    src/m.py::blind -> survived
"""


def test_a_shard_report_gives_the_cells_it_ran_and_the_ones_in_debt() -> None:
    """W2340: KILLED, SURVIVED, ERRORED and REGEX cells ran, UNREACHABLE ones did not."""
    ran, debt = mutate_runner.cells_from_log(_REPORT)
    assert ran == {"src/m.py::a", "src/m.py::b", "src/m.py::planted", "src/m.py::blind"}
    assert debt == {"src/m.py::b": "survived", "src/m.py::blind": "survived"}
    assert mutate_runner.cells_from_log("Traceback (most recent call last):\n") == (set(), {})


def test_writing_a_baseline_replaces_only_the_cells_the_reports_ran_and_refuses_a_crash(
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W2340: a report updates its own cells, keeps the others, and an empty report is refused."""
    grid = _declared_grid(tmp_path)
    _baselined(grid, "errored src/m.py::a\nerrored src/z.py::kept\n")
    report = tmp_path / "shard.log"
    report.write_text(_REPORT, encoding="utf-8")
    assert mutate_runner.write_baseline(grid.dist, [report]) == 0
    text = (grid.dist / mutate_runner.BASELINE_FILE).read_text(encoding="utf-8")
    entries = [line for line in text.splitlines() if not line.startswith("#")]
    assert entries == [
        "survived src/m.py::b",
        "survived src/m.py::blind",
        "errored src/z.py::kept",
    ]
    crashed = tmp_path / "crashed.log"
    crashed.write_text("Traceback (most recent call last):\n", encoding="utf-8")
    assert mutate_runner.write_baseline(grid.dist, [crashed]) == 1
    assert "holds no shard report" in capsys.readouterr().err
    assert mutate_runner.cli(["r", "--check-baseline", str(grid.dist)]) == 0
    _baselined(grid, "errored b::y\nerrored a::x\n")
    assert mutate_runner.cli(["r", "--check-baseline", str(grid.dist)]) == 1


def test_a_phase_report_prints_its_cpu_only_when_phases_are_asked_for(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W2458: `MUTATE_PHASES` makes a phase print its CPU delta, and unset it prints nothing."""
    monkeypatch.delenv("MUTATE_PHASES", raising=False)
    mutate_runner.report_phase("copy", mutate_runner.cpu_mark())
    assert not capsys.readouterr().out
    monkeypatch.setenv("MUTATE_PHASES", "1")
    mutate_runner.report_phase("copy", mutate_runner.cpu_mark() - 1.0)
    printed = capsys.readouterr().out
    assert printed.startswith("      phase copy: ")
    assert printed.endswith("s cpu\n")
    assert float(printed.split(": ")[1].split("s")[0]) >= 1.0


def test_quiet_git_adds_the_two_settings_to_an_environment_without_a_config_count() -> None:
    """W2724: maintenance.auto false and gc.auto 0, as git's own GIT_CONFIG_* variables."""
    got = mutate_runner.quiet_git({"PATH": "/bin"})
    assert got == {
        "PATH": "/bin",
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": "maintenance.auto",
        "GIT_CONFIG_VALUE_0": "false",
        "GIT_CONFIG_KEY_1": "gc.auto",
        "GIT_CONFIG_VALUE_1": "0",
    }


def test_quiet_git_appends_to_a_config_count_the_environment_already_carries() -> None:
    """W2724: a caller's own entry stays and the count grows by two; nothing is clobbered."""
    given = {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "user.name",
        "GIT_CONFIG_VALUE_0": "t",
    }
    got = mutate_runner.quiet_git(given)
    assert got["GIT_CONFIG_COUNT"] == "3"
    assert (got["GIT_CONFIG_KEY_0"], got["GIT_CONFIG_VALUE_0"]) == ("user.name", "t")
    assert (got["GIT_CONFIG_KEY_1"], got["GIT_CONFIG_VALUE_1"]) == ("maintenance.auto", "false")
    assert (got["GIT_CONFIG_KEY_2"], got["GIT_CONFIG_VALUE_2"]) == ("gc.auto", "0")


def test_quiet_git_does_not_change_the_environment_it_was_given() -> None:
    """W2724: it returns a new mapping, so a caller's own environment is never edited."""
    given = {"PATH": "/bin"}
    mutate_runner.quiet_git(given)
    assert given == {"PATH": "/bin"}


_QUIET_GIT_SUITE = """\
import subprocess
import tempfile

import mod


def _setting(repo: str, name: str) -> str:
    done = subprocess.run(
        ["git", "-C", repo, "config", "--get", name],
        capture_output=True,
        text=True,
        check=False,
    )
    return done.stdout.strip()


def test_f_under_a_git_that_starts_no_background_maintenance() -> None:
    with tempfile.TemporaryDirectory() as repo:
        subprocess.run(["git", "init", "-q", repo], check=True)
        assert _setting(repo, "maintenance.auto") == "false"
        assert _setting(repo, "gc.auto") == "0"
    assert mod.f() == 1
"""


def test_a_cells_git_runs_under_no_background_maintenance(tmp_path: pathlib.Path) -> None:
    """W2724: the suite sees maintenance.auto false and gc.auto 0, so its control passes.

    Red with the injection removed: the settings read empty, the control fails on the unmutated
    module, and the cell reads errored instead of killed.
    """
    dist = tmp_path / "dist"
    (dist / "src").mkdir(parents=True)
    (dist / "tests").mkdir()
    (dist / "src" / "mod.py").write_text(_SITE_SOURCE, encoding="utf-8")
    (dist / "tests" / "test_quiet.py").write_text(_QUIET_GIT_SUITE, encoding="utf-8")
    (dist / "pyproject.toml").write_text("", encoding="utf-8")
    grid = mutate_runner.Grid(pathlib.Path(sys.executable), dist, dist / "pyproject.toml")
    mutant = mutate_runner.Mutant(pathlib.Path("src/mod.py"), _SITE_SOURCE, _SITE)
    assert mutate_runner.run(grid, mutant) == "killed"
