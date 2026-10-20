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
import os
import pathlib
import subprocess
import sys
import threading

import mutate_runner
import pytest

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
    assert [k for k in seen[0] if k.startswith("GIT_")] == [], "a GIT_* variable reached the suite"


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
        _env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        text = (cwd / "src" / "mod.py").read_text(encoding="utf-8")
        seen.append(text)
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
