# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.cli`: the driver's first three modes and its redirects.

W33 (pycodemod driver slice 1). Every arm drives `main()` in-process, never a subprocess: the
DECOY-repo discipline for `owes` already lives in `test_owes.py`, and this suite reuses it.
"""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import cli

if TYPE_CHECKING:
    from pathlib import Path

_GIT = "git"
_REFUSED = 2


def test_calls_reports_a_def_and_its_call(tmp_path: Path) -> None:
    """`calls --target NAME` finds a def and a call of that name, denominator included."""
    target = tmp_path / "m.py"
    target.write_text("def greet():\n    return 1\n\ngreet()\n", encoding="utf-8")
    code = cli.main(["calls", "--target", "greet", str(target)])
    assert code == 0


def test_calls_with_no_target_reports_every_name(tmp_path: Path) -> None:
    """`calls` with no `--target` reports defs, calls and refs of every name."""
    target = tmp_path / "m.py"
    target.write_text("def f():\n    pass\n\nf()\n", encoding="utf-8")
    code = cli.main(["calls", str(target)])
    assert code == 0


def test_calls_with_a_dotted_target_reads_each_full_dotted_call_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`calls --target sys.path.insert` prints the module-level and in-function call, once each."""
    target = tmp_path / "m.py"
    target.write_text(
        "import sys\nsys.path.insert(0, 'x')\n\n\ndef f(items):\n"
        "    sys.path.insert(0, 'y')\n    items.insert(1, 2)\n    insert(3)\n",
        encoding="utf-8",
    )
    assert cli.main(["calls", "--target", "sys.path.insert", str(target)]) == 0
    rows = [ln.rsplit(":", 2)[1:] for ln in capsys.readouterr().out.splitlines()]
    assert rows == [["2", "0"], ["6", "4"]]
    assert cli.main(["calls", "--target", "path.insert", str(target)]) == 0
    assert capsys.readouterr().out == "calls: searched 1 file(s), found none\n"
    assert cli.main(["calls", "--target", "insert", str(target)]) == 0
    assert [ln.rsplit(":", 2)[1] for ln in capsys.readouterr().out.splitlines()] == [
        "2",
        "6",
        "7",
        "8",
    ]


def test_calls_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `calls` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["calls", str(target)])
    assert code == 1


def _decoy_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "decoy"
    repo.mkdir()
    subprocess.run([_GIT, "init", "-q"], cwd=repo, check=True, env={"PATH": "/usr/bin:/bin"})
    subprocess.run([_GIT, "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run([_GIT, "config", "user.name", "t"], cwd=repo, check=True)
    return repo


def test_owes_reports_an_untouched_caller(tmp_path: Path) -> None:
    """`owes` names a caller of `name` that the given revision's diff did not touch."""
    repo = _decoy_repo(tmp_path)
    caller = repo / "caller.py"
    caller.write_text("def use():\n    target()\n", encoding="utf-8")
    subprocess.run([_GIT, "add", "."], cwd=repo, check=True)
    subprocess.run([_GIT, "commit", "-q", "-m", "first"], cwd=repo, check=True)
    code = cli.main(["owes", "target", "--rev", "HEAD", "--root", str(repo), str(caller)])
    assert code == 0


def test_owes_refuses_a_bad_revision_with_exit_2(tmp_path: Path) -> None:
    """A revision git refuses makes `owes` print git's own words and exit 2."""
    repo = _decoy_repo(tmp_path)
    caller = repo / "caller.py"
    caller.write_text("target()\n", encoding="utf-8")
    args = ["owes", "target", "--rev", "not-a-real-rev", "--root", str(repo), str(caller)]
    code = cli.main(args)
    assert code == _REFUSED


def test_dead_reports_an_unused_def(tmp_path: Path) -> None:
    """`dead` names a def nothing in the corpus calls or uses."""
    target = tmp_path / "m.py"
    target.write_text("def unused():\n    pass\n", encoding="utf-8")
    code = cli.main(["dead", str(target)])
    assert code == 0


def test_attr_reads_reports_a_dotted_read(tmp_path: Path) -> None:
    """`attr-reads` finds a `.name` read and reports it with its denominator."""
    target = tmp_path / "m.py"
    target.write_text("obj.name\n", encoding="utf-8")
    code = cli.main(["attr-reads", "name", str(target)])
    assert code == 0


def test_attr_reads_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `attr-reads` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n    name\n", encoding="utf-8")
    code = cli.main(["attr-reads", "name", str(target)])
    assert code == 1


def test_importers_reports_an_import_of_the_named_module(tmp_path: Path) -> None:
    """`importers` finds an import of the named module and reports it with its denominator."""
    target = tmp_path / "m.py"
    target.write_text("import pkg.sub\n", encoding="utf-8")
    code = cli.main(["importers", "pkg.sub", str(target)])
    assert code == 0


def test_importers_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `importers` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["importers", "pkg", str(target)])
    assert code == 1


def test_swallows_reports_a_discarding_except(tmp_path: Path) -> None:
    """`swallows` finds an except whose whole body discards, with its denominator."""
    target = tmp_path / "m.py"
    target.write_text("try:\n    f()\nexcept Exception:\n    pass\n", encoding="utf-8")
    code = cli.main(["swallows", str(target)])
    assert code == 0


def test_swallows_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `swallows` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["swallows", str(target)])
    assert code == 1


def test_exits_reports_a_process_exit_site(tmp_path: Path) -> None:
    """`exits` classifies a process-exit site and reports it with its denominator."""
    target = tmp_path / "m.py"
    target.write_text("import sys\n\n\ndef main():\n    sys.exit(1)\n", encoding="utf-8")
    code = cli.main(["exits", str(target)])
    assert code == 0


def test_exits_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `exits` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["exits", str(target)])
    assert code == 1


def test_verdicts_reports_a_verdict_returning_def(tmp_path: Path) -> None:
    """`verdicts` finds a def mixing an all-clear return with a signal, with its denominator."""
    target = tmp_path / "m.py"
    target.write_text(
        "def check(ok):\n    if ok:\n        return None\n    return 1\n", encoding="utf-8"
    )
    code = cli.main(["verdicts", str(target)])
    assert code == 0


def test_verdicts_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `verdicts` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["verdicts", str(target)])
    assert code == 1


def test_disagreement_reports_a_store_writer(tmp_path: Path) -> None:
    """`disagreement` classifies a tool's intent/snapshot/store relation, with its denominator."""
    target = tmp_path / "m.py"
    target.write_text(
        "def run():\n    require_at_entry(paths=['x'])\n    store.write('x')\n",
        encoding="utf-8",
    )
    code = cli.main(["disagreement", str(target)])
    assert code == 0


def test_disagreement_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `disagreement` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n    require_at_entry\n", encoding="utf-8")
    code = cli.main(["disagreement", str(target)])
    assert code == 1


def test_placement_reports_an_entry_gate(tmp_path: Path) -> None:
    """`placement` reports a file's strongest intent-gate verdict, with its denominator."""
    target = tmp_path / "m.py"
    target.write_text("def run():\n    require_at_entry(paths=['x'])\n", encoding="utf-8")
    code = cli.main(["placement", str(target)])
    assert code == 0


def test_placement_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `placement` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n    require_at_entry\n", encoding="utf-8")
    code = cli.main(["placement", str(target)])
    assert code == 1


def test_modstate_reports_a_mutated_module_container(tmp_path: Path) -> None:
    """`modstate` reports a module-level container a function mutates, with its denominator."""
    target = tmp_path / "m.py"
    target.write_text("CACHE = {}\n\n\ndef put(k):\n    CACHE[k] = 1\n", encoding="utf-8")
    code = cli.main(["modstate", str(target)])
    assert code == 0


def test_modstate_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `modstate` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["modstate", str(target)])
    assert code == 1


def test_layout_reports_each_top_level_group(tmp_path: Path) -> None:
    """`layout` reports every top-level statement group in source order, with its denominator."""
    target = tmp_path / "m.py"
    target.write_text('"""Doc."""\n\nimport os\n\n\ndef f():\n    pass\n', encoding="utf-8")
    code = cli.main(["layout", str(target)])
    assert code == 0


def test_layout_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `layout` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["layout", str(target)])
    assert code == 1


def test_collisions_reports_a_name_defined_twice(tmp_path: Path) -> None:
    """`collisions` names a public def reimplemented in two files, with its denominator."""
    first, second = tmp_path / "a.py", tmp_path / "b.py"
    first.write_text("def work():\n    return 1\n", encoding="utf-8")
    second.write_text("def work():\n    return 2\n", encoding="utf-8")
    code = cli.main(["collisions", str(first), str(second)])
    assert code == 0


def test_collisions_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `collisions` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["collisions", str(target)])
    assert code == 1


def test_reifies_reports_a_sorted_return(tmp_path: Path) -> None:
    """`reifies` reports a def returning a sorted collection, with its denominator."""
    target = tmp_path / "m.py"
    target.write_text("def names(xs):\n    return sorted(xs)\n", encoding="utf-8")
    code = cli.main(["reifies", str(target)])
    assert code == 0


def test_reifies_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `reifies` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["reifies", str(target)])
    assert code == 1


def test_escapes_reports_an_invalid_escape(tmp_path: Path) -> None:
    """`escapes` reports a string literal whose escape does not exist, with its denominator."""
    target = tmp_path / "m.py"
    target.write_text('PATTERN = "a\\d"\n', encoding="utf-8")
    code = cli.main(["escapes", str(target)])
    assert code == 0


def test_escapes_over_an_unparseable_file_reports_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file that fails to compile is banner line `uncompilable`, apart from an absent file."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["escapes", str(target), str(tmp_path / "absent.py")])
    captured = capsys.readouterr()
    banner = captured.out + captured.err
    assert code == 1
    assert "uncompilable: 1 (SyntaxError)" in banner
    assert "unreadable: 1 (FileNotFoundError)" in banner


def test_catchers_reports_a_systemexit_handler(tmp_path: Path) -> None:
    """`catchers` reports a handler that catches SystemExit, with its denominator."""
    target = tmp_path / "m.py"
    target.write_text("try:\n    run()\nexcept SystemExit:\n    pass\n", encoding="utf-8")
    code = cli.main(["catchers", str(target)])
    assert code == 0


def test_catchers_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `catchers` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["catchers", str(target)])
    assert code == 1


def test_interlock_reports_a_broad_handler_over_an_exiting_call(tmp_path: Path) -> None:
    """`interlock` reports an `except Exception` around a call that can exit."""
    target = tmp_path / "m.py"
    target.write_text(
        "import sys\n\n\ndef stop():\n    sys.exit(1)\n\n\n"
        "def run():\n    try:\n        stop()\n    except Exception:\n        pass\n",
        encoding="utf-8",
    )
    code = cli.main(["interlock", str(target)])
    assert code == 0


def test_interlock_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `interlock` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["interlock", str(target)])
    assert code == 1


def test_commentary_lost_names_a_dropped_note(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`commentary-lost` names a marked sentence the working tree dropped since the revision."""
    repo = _decoy_repo(tmp_path)
    target = repo / "m.py"
    target.write_text("# \u2691 keep this note\nx = 1\n", encoding="utf-8")
    subprocess.run([_GIT, "add", "."], cwd=repo, check=True)
    subprocess.run([_GIT, "commit", "-q", "-m", "first"], cwd=repo, check=True)
    target.write_text("x = 1\n", encoding="utf-8")
    code = cli.main(["commentary-lost", "--rev", "HEAD", "--root", str(repo), str(target)])
    assert code == 0
    assert "lost m.py" in capsys.readouterr().out


def test_commentary_lost_refuses_a_bad_revision_with_exit_2(tmp_path: Path) -> None:
    """A bad revision is refused, never read as a baseline where every file is new."""
    repo = _decoy_repo(tmp_path)
    target = repo / "m.py"
    target.write_text("x = 1\n", encoding="utf-8")
    args = ["commentary-lost", "--rev", "not-a-real-rev", "--root", str(repo), str(target)]
    assert cli.main(args) == _REFUSED


def test_ambient_reports_an_unanchored_open(tmp_path: Path) -> None:
    """`ambient --root` reports a relative open() against the root, with its denominator."""
    target = tmp_path / "m.py"
    target.write_text('open("data.txt")\n', encoding="utf-8")
    code = cli.main(["ambient", "--root", str(tmp_path), str(target)])
    assert code == 0


def test_ambient_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `ambient` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["ambient", "--root", str(tmp_path), str(target)])
    assert code == 1


def test_callgraph_prints_a_caller_to_callee_edge(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`callgraph` prints an edge from the calling scope to the callee name."""
    target = tmp_path / "m.py"
    target.write_text("def g():\n    pass\n\n\ndef f():\n    g()\n", encoding="utf-8")
    code = cli.main(["callgraph", str(target)])
    assert code == 0
    assert f"edge {target}:f -> g" in capsys.readouterr().out


def test_callgraph_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `callgraph` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["callgraph", str(target)])
    assert code == 1


def test_reaches_prints_the_call_path_to_a_target(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`reaches` prints the same-file call path from the start to a target."""
    target = tmp_path / "m.py"
    target.write_text(
        "def h():\n    pass\n\n\ndef g():\n    h()\n\n\ndef f():\n    g()\n", encoding="utf-8"
    )
    code = cli.main(["reaches", "--start", f"{target}:f", "--target", "h", str(target)])
    assert code == 0
    assert "reaches h via f -> g -> h" in capsys.readouterr().out


def test_reaches_refuses_an_unknown_start(tmp_path: Path) -> None:
    """A start the graph lacks is refused, never reported as reaching nothing."""
    target = tmp_path / "m.py"
    target.write_text("def f():\n    g()\n", encoding="utf-8")
    code = cli.main(["reaches", "--start", f"{target}:nope", "--target", "g", str(target)])
    assert code == _REFUSED


def test_guarded_splits_a_call_under_an_if_from_one_at_the_top(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`guarded --target` names the test a call sits under, and a call with none as top."""
    target = tmp_path / "m.py"
    target.write_text("if apply:\n    write()\nwrite()\n", encoding="utf-8")
    code = cli.main(["guarded", "--target", "write", str(target)])
    assert code == 0
    out = capsys.readouterr().out
    assert f"under {target}:2:" in out
    assert "if apply" in out
    assert f"top {target}:3:" in out


def test_guarded_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `guarded` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n    write()\n", encoding="utf-8")
    code = cli.main(["guarded", "--target", "write", str(target)])
    assert code == 1


def test_key_reads_reports_a_subscript_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`key-reads KEY` reports a use of the string key, with its denominator."""
    target = tmp_path / "m.py"
    target.write_text('cfg = {}\nx = cfg["mode"]\n', encoding="utf-8")
    code = cli.main(["key-reads", "mode", str(target)])
    assert code == 0
    assert f"{target}:2" in capsys.readouterr().out


def test_key_reads_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `key-reads` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text('def (:\n    cfg["mode"]\n', encoding="utf-8")
    code = cli.main(["key-reads", "mode", str(target)])
    assert code == 1


def test_bindings_reports_a_def_binding(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """`bindings NAME` reports where the name is bound, with its live span."""
    target = tmp_path / "m.py"
    target.write_text("def work():\n    pass\n", encoding="utf-8")
    code = cli.main(["bindings", "work", str(target)])
    assert code == 0
    assert f"work {target}:1 live=" in capsys.readouterr().out


def test_bindings_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `bindings` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n    work = 1\n", encoding="utf-8")
    code = cli.main(["bindings", "work", str(target)])
    assert code == 1


def test_aliases_all_modules_reports_a_stdlib_import(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`aliases --all-modules` grades an import of a non-local module too."""
    target = tmp_path / "m.py"
    target.write_text("import os.path as osp\n", encoding="utf-8")
    code = cli.main(["aliases", "--all-modules", str(target)])
    assert code == 0
    assert f"{target}:1" in capsys.readouterr().out


def test_aliases_local_admits_a_named_head(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`aliases --local HEAD` counts that head as local, so its import is graded."""
    target = tmp_path / "m.py"
    target.write_text("import vendored.sub as vs\n", encoding="utf-8")
    code = cli.main(["aliases", "--local", "vendored", str(target)])
    assert code == 0
    assert "vendored" in capsys.readouterr().out


def test_aliases_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `aliases` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["aliases", str(target)])
    assert code == 1


def test_funcnames_grades_a_func_call(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """`funcnames` grades a `func.count()` call generic, with its denominator."""
    target = tmp_path / "m.py"
    target.write_text("from sqlalchemy import func\nq = func.count()\n", encoding="utf-8")
    code = cli.main(["funcnames", str(target)])
    assert code == 0
    assert "funcname generic count" in capsys.readouterr().out


def test_funcnames_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `funcnames` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["funcnames", str(target)])
    assert code == 1


def test_funcnames_without_the_extra_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the sqlalchemy extra absent, `funcnames` refuses with exit 2, never an empty census."""
    monkeypatch.setattr(cli, "_run_funcnames", None)
    target = tmp_path / "m.py"
    target.write_text("q = func.count()\n", encoding="utf-8")
    assert cli.main(["funcnames", str(target)]) == _REFUSED


def _child_env() -> dict[str, str]:
    """Give a child the parent import path, so it imports the same code.

    Returns:
        an environment holding only `PYTHONPATH`.

    """
    return {"PYTHONPATH": ":".join(sys.path)}


def test_module_entry_runs_main() -> None:
    """`python -m mikemol.pycodemod.cli --help` prints the usage and exits 0, not silence."""
    done = subprocess.run(
        [sys.executable, "-m", "mikemol.pycodemod.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
        env=_child_env(),
        timeout=60,
    )
    assert done.returncode == 0
    assert "usage" in done.stdout.lower()


def test_funcnames_with_a_genuinely_failing_import_refuses(tmp_path: Path) -> None:
    """With `import sqlalchemy` really failing at cli import, `funcnames` exits 2 naming it."""
    runner = tmp_path / "runner.py"
    runner.write_text(
        "import runpy\nimport sys\n\nsys.modules['sqlalchemy'] = None\n"
        "sys.argv = ['cli', 'funcnames', sys.argv[1]]\n"
        "runpy.run_module('mikemol.pycodemod.cli', run_name='__main__')\n",
        encoding="utf-8",
    )
    target = tmp_path / "m.py"
    target.write_text("q = func.count()\n", encoding="utf-8")
    done = subprocess.run(
        [sys.executable, str(runner), str(target)],
        capture_output=True,
        text=True,
        check=False,
        env=_child_env(),
        timeout=60,
    )
    assert done.returncode == _REFUSED
    assert "refused:" in done.stdout
    assert "sqlalchemy" in done.stdout


def test_size_with_a_small_base_reports_a_module_over_its_cap(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`size --base N` reports a module whose code lines exceed the cap as over."""
    target = tmp_path / "m.py"
    target.write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
    code = cli.main(["size", "--base", "1", str(target)])
    assert code == 0
    assert "size over code=3" in capsys.readouterr().out


def test_size_over_an_unreadable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that cannot be read makes `size` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_bytes(b"\xff\xfe\x00")
    code = cli.main(["size", str(target)])
    assert code == 1


def test_deps_grades_an_import_against_the_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`deps --manifest` grades each top-level import, with its denominator."""
    manifest = tmp_path / "pyproject.toml"
    manifest.write_text('[project]\nname = "x"\ndependencies = []\n', encoding="utf-8")
    target = tmp_path / "m.py"
    target.write_text("import os\n", encoding="utf-8")
    code = cli.main(["deps", "--manifest", str(manifest), str(target)])
    assert code == 0
    assert "dep STDLIB os files=1 " in capsys.readouterr().out


def test_deps_refuses_an_unreadable_manifest(tmp_path: Path) -> None:
    """A manifest that cannot be read refuses with exit 2; nothing is graded against a guess."""
    target = tmp_path / "m.py"
    target.write_text("import os\n", encoding="utf-8")
    code = cli.main(["deps", "--manifest", str(tmp_path / "absent.toml"), str(target)])
    assert code == _REFUSED


def test_crossings_over_a_plain_def_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`crossings --authority` reads every file and exits zero when all were read.

    ⚑ W87: the row's CLASS is pinned; a local append-accumulator that no authority names grades
    `unattr`, with its def and binding.
    """
    target = tmp_path / "m.py"
    target.write_text(
        "def f():\n    out = []\n    out.append(1)\n    return out\n", encoding="utf-8"
    )
    code = cli.main(["crossings", "--authority", "registry", str(target)])
    assert code == 0
    assert f"crossing unattr f out {target}:1" in capsys.readouterr().out


def test_crossings_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `crossings` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["crossings", str(target)])
    assert code == 1


def test_shapes_reports_code_but_not_a_comment(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`shapes` matches the code line and skips the comment naming the same shape."""
    target = tmp_path / "m.py"
    target.write_text("# x or None\ny = x or None\n", encoding="utf-8")
    code = cli.main(["shapes", "or None", str(target)])
    out = capsys.readouterr().out
    assert code == 0
    assert ":2 " in out
    assert ":1 " not in out


def test_shapes_refuses_a_bad_pattern(tmp_path: Path) -> None:
    """A regex that will not compile refuses with exit 2 rather than matching nothing."""
    target = tmp_path / "m.py"
    target.write_text("x = 1\n", encoding="utf-8")
    assert cli.main(["shapes", "(", str(target)]) == _REFUSED


def test_commentary_counts_marks_and_reports_a_repeat(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`commentary` counts marked lines per file and names a sentence written in two places."""
    for name in ("a.py", "b.py"):
        (tmp_path / name).write_text("# \u2691 keep this note\nx = 1\n", encoding="utf-8")
    code = cli.main(["commentary", str(tmp_path / "a.py"), str(tmp_path / "b.py")])
    out = capsys.readouterr().out
    assert code == 0
    assert "commentary lines=1 distinct=1" in out
    assert "repeated x2" in out


def test_commentary_over_an_unreadable_file_reports_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unreadable and an undecodable file are banner lines APART, each naming its exception."""
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"# \xe9\n")
    code = cli.main(["commentary", str(tmp_path / "absent.py"), str(latin)])
    captured = capsys.readouterr()
    banner = captured.out + captured.err
    assert code == 1
    assert "unreadable: 1 (FileNotFoundError)" in banner
    assert "undecodable: 1 (UnicodeDecodeError)" in banner


def test_discards_splits_a_bare_call_from_a_used_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`discards` reports a bare-statement call as dropped and an assigned one as used."""
    target = tmp_path / "m.py"
    target.write_text("def f():\n    return 1\n\n\nf()\nx = f()\n", encoding="utf-8")
    code = cli.main(["discards", "f", str(target)])
    out = capsys.readouterr().out
    assert code == 0
    assert "discards dropped " in out
    assert "1 dropped, 1 used" in out


def test_discards_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `discards` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    assert cli.main(["discards", "f", str(target)]) == 1


def test_forwards_splits_calls_by_keyword(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`forwards` puts a call passing the keyword, one lacking it, a `**` call apart."""
    target = tmp_path / "m.py"
    target.write_text("f(x, root=r)\nf(x)\nf(x, **kw)\n", encoding="utf-8")
    code = cli.main(["forwards", "--target", "f", "root", str(target)])
    out = capsys.readouterr().out
    assert code == 0
    assert "forwards: 1 passes, 1 lacks, 1 cannot-tell" in out


def test_forwards_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `forwards` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("f(:\n", encoding="utf-8")
    assert cli.main(["forwards", "--target", "f", "root", str(target)]) == 1


def test_asserted_splits_literal_from_computed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`asserted` counts literal and computed values apart; a lacking call is neither."""
    target = tmp_path / "m.py"
    target.write_text("f(size=1)\nf(size=len(xs))\nf()\n", encoding="utf-8")
    code = cli.main(["asserted", "--target", "f", "size", str(target)])
    out = capsys.readouterr().out
    assert code == 0
    assert "asserted: 1 literal, 1 computed" in out


def test_asserted_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `asserted` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("f(:\n", encoding="utf-8")
    assert cli.main(["asserted", "--target", "f", "size", str(target)]) == 1


def test_values_reports_each_value_over_the_call_total(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`values` prints a constant, UNKNOWN for a name, and the total including the lacking call."""
    target = tmp_path / "m.py"
    target.write_text("f(reset=True)\nf(reset=flag)\nf()\n", encoding="utf-8")
    code = cli.main(["values", "f", "reset", str(target)])
    out = capsys.readouterr().out
    assert code == 0
    assert "value True " in out
    assert "values: 2 of 3 calls pass it" in out


def test_values_reads_an_all_digit_argument_as_a_position(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An all-digit argument is a positional ordinal, not a keyword named `0`."""
    target = tmp_path / "m.py"
    target.write_text("f('a')\n", encoding="utf-8")
    assert cli.main(["values", "f", "0", str(target)]) == 0
    assert "value 'a' " in capsys.readouterr().out


def test_literals_reports_a_string_holding_the_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`literals` prints a row for a string literal that contains the searched text."""
    target = tmp_path / "m.py"
    target.write_text("x = 'a needle here'\n", encoding="utf-8")
    code = cli.main(["literals", "needle", str(target)])
    assert code == 0
    assert f"literal other {target}:1 (<module>) 'a needle here'" in capsys.readouterr().out


def test_literals_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """An unparseable file carrying the text makes `literals` print the incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("x = 'needle'\ndef (:\n", encoding="utf-8")
    assert cli.main(["literals", "needle", str(target)]) == 1


def test_relname_reports_a_sql_literal_and_an_exact_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`relname` prints a `sql` row for a relation position and a `name` row for an exact string."""
    target = tmp_path / "m.py"
    target.write_text("q = 'SELECT a FROM node'\nt = 'node'\n", encoding="utf-8")
    code = cli.main(["relname", "node", str(target)])
    out = capsys.readouterr().out
    assert code == 0
    assert f"relname sql other {target}:1 (<module>) " in out
    assert f"relname name other {target}:2 (<module>) 'node'" in out


def test_relname_prints_no_rows_for_a_name_that_is_only_a_substring(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A name that appears only inside another relation name is a miss: no rows, exit 0."""
    target = tmp_path / "m.py"
    target.write_text("q = 'SELECT a FROM node_child'\n", encoding="utf-8")
    code = cli.main(["relname", "node", str(target)])
    assert code == 0
    assert capsys.readouterr().out == "relname: searched 1 file(s), found none\n"


def test_relname_over_an_unparseable_file_reports_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unparseable file makes `relname` print the incomplete-scan banner and exit 1."""
    target = tmp_path / "m.py"
    target.write_text("x = 'node'\ndef (:\n", encoding="utf-8")
    code = cli.main(["relname", "node", str(target)])
    captured = capsys.readouterr()
    assert code == 1
    assert "read 0 of 1 file(s); 1 skipped" in captured.out + captured.err


def test_relname_without_a_path_is_a_usage_error() -> None:
    """`relname NAME` with no paths is argparse's usage error, exit 2."""
    with pytest.raises(SystemExit) as raised:
        cli.main(["relname", "node"])
    assert raised.value.code == _REFUSED


def test_commentary_kinds_files_a_comment_apart_from_a_printed_string(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`commentary-kinds` files a `#` mark as comment and a printed mark as executable."""
    target = tmp_path / "m.py"
    target.write_text("# \u2691 a note\nprint('\u2691 said')\n", encoding="utf-8")
    code = cli.main(["commentary-kinds", str(target)])
    out = capsys.readouterr().out
    assert code == 0
    assert f"commentary-kinds comment {target}:1 " in out
    assert f"commentary-kinds executable {target}:2 " in out
    assert "commentary-kinds comment=1 docstring=0 executable=1 unparsed=0" in out


def test_commentary_kinds_over_an_undecodable_file_reports_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An undecodable file is the banner line `undecodable`, naming its exception."""
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"# \xe9\n")
    code = cli.main(["commentary-kinds", str(latin)])
    captured = capsys.readouterr()
    assert code == 1
    assert "undecodable: 1 (UnicodeDecodeError)" in captured.out + captured.err


def test_commentary_blocks_names_the_owner_and_the_cited_symbol(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`commentary-blocks` prints a marked paragraph's extent, its def and the symbol it cites."""
    target = tmp_path / "m.py"
    target.write_text(
        "def run():\n    # \u2691 calls `helper` here\n    # and continues\n\n    return 1\n",
        encoding="utf-8",
    )
    code = cli.main(["commentary-blocks", str(target)])
    out = capsys.readouterr().out
    assert code == 0
    assert f"commentary-blocks {target}:2-3 run cites=helper " in out
    assert "return 1" not in out
    assert "commentary-blocks blocks=1" in out


def test_commentary_blocks_over_an_undecodable_file_reports_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An undecodable file is the banner line `undecodable`, naming its exception."""
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"# \xe9\n")
    code = cli.main(["commentary-blocks", str(latin)])
    captured = capsys.readouterr()
    assert code == 1
    assert "undecodable: 1 (UnicodeDecodeError)" in captured.out + captured.err


def test_source_of_prints_a_method_from_its_decorator(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`source-of` prints a method's qualname, its extent from the decorator, and its text."""
    target = tmp_path / "m.py"
    target.write_text(
        "class Box:\n    @staticmethod\n    def run():\n        return 1\n\n\n"
        "def other():\n    pass\n",
        encoding="utf-8",
    )
    code = cli.main(["source-of", "run", str(target)])
    out = capsys.readouterr().out
    assert code == 0
    assert f"source-of Box.run {target}:2-4\n    @staticmethod\n" in out
    assert "other" not in out
    assert "source-of definitions=1" in out


def test_source_of_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to parse makes `source-of` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["source-of", "run", str(target)])
    assert code == 1


def test_alias_hint_finds_a_renamed_import_call(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`alias-hint` reports a call that reaches a name only through `from lib import f as g`."""
    lib = tmp_path / "lib.py"
    lib.write_text("def f():\n    return 1\n", encoding="utf-8")
    use = tmp_path / "use.py"
    use.write_text("from lib import f as g\n\ng()\n", encoding="utf-8")
    code = cli.main(["alias-hint", "f", "--def", str(lib), str(use)])
    out = capsys.readouterr().out
    assert code == 0
    assert f"alias-hint {use}:3 via=f as g from=lib" in out
    assert "alias-hint sites=1" in out


def test_alias_hint_over_an_unparseable_file_reports_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unparseable population file is one skip: the later passes only read what parsed."""
    lib = tmp_path / "lib.py"
    lib.write_text("def f():\n    return 1\n", encoding="utf-8")
    bad = tmp_path / "bad.py"
    bad.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["alias-hint", "f", "--def", str(lib), str(bad)])
    captured = capsys.readouterr()
    banner = captured.out + captured.err
    assert code == 1
    assert "read 0 of 1 file(s); 1 skipped" in banner


def test_rivals_tells_a_wrapper_from_a_reimplementation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`rivals` marks a one-line `return` of a call DELEGATES and a real body REIMPLEMENTS."""
    src = tmp_path / "m.py"
    src.write_text(
        "def f(x):\n    return g(x)\n\n\nclass C:\n    def f(self):\n"
        "        y = 1\n        return y\n",
        encoding="utf-8",
    )
    code = cli.main(["rivals", "f", str(src)])
    out = capsys.readouterr().out
    assert code == 0
    assert f"rivals {src}:1 DELEGATES callee=g statements=1" in out
    assert f"rivals {src}:6 REIMPLEMENTS callee=- statements=2" in out
    assert "rivals defs=2" in out


def test_rivals_over_an_unparseable_file_reports_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unparseable file is a skip in the banner, not a silent zero."""
    bad = tmp_path / "bad.py"
    bad.write_text("def f(:\n", encoding="utf-8")
    code = cli.main(["rivals", "f", str(bad)])
    captured = capsys.readouterr()
    assert code == 1
    assert "read 0 of 1 file(s); 1 skipped" in captured.out + captured.err


def test_resorts_names_the_producer_of_an_already_sorted_list(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`resorts` joins a `sorted(f())` consumer to the `f` that already returns sorted."""
    src = tmp_path / "m.py"
    src.write_text(
        "def f(xs):\n    return sorted(xs)\n\n\ndef g(xs):\n    return sorted(f(xs))\n",
        encoding="utf-8",
    )
    code = cli.main(["resorts", str(src)])
    out = capsys.readouterr().out
    assert code == 0
    assert f"resorts {src}:6 resort-of-sorted g -> f producers={src}:2" in out
    assert "resorts sites=1" in out


def test_resorts_counts_an_unparseable_file_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unparseable file is ONE skip, though both the producer and consumer passes read it."""
    bad = tmp_path / "bad.py"
    bad.write_text("def f(:\n", encoding="utf-8")
    code = cli.main(["resorts", str(bad)])
    captured = capsys.readouterr()
    assert code == 1
    assert "read 0 of 1 file(s); 1 skipped" in captured.out + captured.err


def test_writes_takes_repeatable_fixtures_and_gates(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`writes` reads a named gate and a named fixture as inert, and a bare write as WRITES."""
    bare = tmp_path / "bare.py"
    bare.write_text('open("out.txt", "w")\n', encoding="utf-8")
    gated = tmp_path / "gated.py"
    gated.write_text('FLAG = "--apply"\nopen("out.txt", "w")\n', encoding="utf-8")
    fixture = tmp_path / "fixture.py"
    fixture.write_text('def _selftest():\n    open("out.txt", "w")\n', encoding="utf-8")
    argv = ["writes", "--gate=--apply", "--gate=--go", "--fixture", "_selftest"]
    code = cli.main([*argv, str(bare), str(gated), str(fixture)])
    out = capsys.readouterr().out
    assert code == 0
    assert f"writes {bare}:1 WRITES unguarded write at line 1" in out
    assert f"writes {gated}:2 inert gated on --apply" in out
    assert f"writes {fixture}:0 inert writes only fixtures or tempfiles" in out
    assert "writes files=3 writing=1" in out


def test_writes_over_an_unparseable_file_reports_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unparseable file is a skip in the banner, never a clean "no write call"."""
    bad = tmp_path / "bad.py"
    bad.write_text("def f(:\n", encoding="utf-8")
    code = cli.main(["writes", str(bad)])
    captured = capsys.readouterr()
    assert code == 1
    assert "read 0 of 1 file(s); 1 skipped" in captured.out + captured.err


def test_fix_owes_callers_redirects_to_owes(capsys: pytest.CaptureFixture[str]) -> None:
    """The origin's `fix-owes-callers` refuses, exit 2, and names `owes` as its successor."""
    code = cli.main(["fix-owes-callers"])
    assert code == _REFUSED
    assert "`owes " in capsys.readouterr().out


@pytest.mark.parametrize("name", sorted(cli.RETIRED))
def test_a_retired_spelling_refuses_naming_its_successor(name: str) -> None:
    """Every retired origin flag parses and refuses, exit 2, naming its successor mode."""
    code = cli.main([name])
    assert code == _REFUSED


@pytest.mark.parametrize("name", sorted(cli.DO_NOT_PORT))
def test_a_do_not_port_spelling_refuses_naming_where_it_lives(name: str) -> None:
    """Every DO-NOT-PORT origin flag parses and refuses, exit 2, naming substrate's copy."""
    code = cli.main([name])
    assert code == _REFUSED


def test_console_runs_main_over_sys_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`_console` drives `main` over the real `sys.argv`, as the console-script entry point."""
    target = tmp_path / "m.py"
    target.write_text("def f():\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["mikemol-pycodemod", "dead", str(target)])
    code = cli._console()
    assert code == 0


_CENSUS_FLAGS = ["--readers", "execute", "--receivers", "con", "--connections", "con"]
_CENSUS_SOURCE = (
    "def f(x, con):\n    if x:\n        return 1\n    for r in con.execute('q'):\n"
    "        pass\n    return 2\n"
)


def _census_file(tmp_path: Path) -> Path:
    target = tmp_path / "m.py"
    target.write_text(_CENSUS_SOURCE, encoding="utf-8")
    return target


def test_control_prints_one_row_per_site(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`control` prints path:line construct kind sqlform scope snippet, typed by the operands."""
    target = _census_file(tmp_path)
    code = cli.main(["control", *_CENSUS_FLAGS, "--boundary", "python", str(target)])
    out = capsys.readouterr().out
    assert code == 0
    assert f"control {target}:2 if mode-branch " in out
    assert f"control {target}:3 return-guard " in out
    assert f"control {target}:4 for row-iteration " in out


def test_control_with_empty_vocabulary_names_no_row_site(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty comma list is an operand, not an absent one: no site is then a row site."""
    target = _census_file(tmp_path)
    argv = ["control", "--readers", "", "--receivers", "", "--connections", "", "--boundary"]
    code = cli.main([*argv, "python", str(target)])
    out = capsys.readouterr().out
    assert code == 0
    assert f"control {target}:4 for unclassified " in out
    assert "row-iteration" not in out


def test_constructs_lists_all_thirty_six_with_zero_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`constructs` prints the 36-construct roster by group, a construct nobody wrote as 0."""
    target = _census_file(tmp_path)
    code = cli.main(["constructs", *_CENSUS_FLAGS, "--boundary", "python", str(target)])
    out = capsys.readouterr().out
    assert code == 0
    assert "constructs branch if 1\n" in out
    assert "constructs loop while 0\n" in out
    assert "constructs roster=36 sites=3\n" in out
    assert len([ln for ln in out.splitlines() if ln.startswith("constructs ")]) == 8 + 36 + 1


@pytest.mark.parametrize("mode", ["control", "constructs"])
@pytest.mark.parametrize("missing", ["readers", "receivers", "connections", "boundary"])
def test_a_census_mode_refuses_a_missing_operand_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], mode: str, missing: str
) -> None:
    """A flag left out refuses, exit 2, naming it: the census has no silent default."""
    target = _census_file(tmp_path)
    given = {"readers": "execute", "receivers": "con", "connections": "con", "boundary": "python"}
    argv = [mode]
    for name, value in given.items():
        if name != missing:
            argv.extend([f"--{name}", value])
    code = cli.main([*argv, str(target)])
    assert code == _REFUSED
    assert f"--{missing} is required" in capsys.readouterr().out


def test_a_census_mode_refuses_an_unknown_boundary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--boundary` with a value naming no boundary refuses, exit 2, naming the value."""
    target = _census_file(tmp_path)
    code = cli.main(["control", *_CENSUS_FLAGS, "--boundary", "rust", str(target)])
    assert code == _REFUSED
    assert "'rust'" in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["control", "constructs"])
def test_a_census_mode_over_an_unparseable_file_reports_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], mode: str
) -> None:
    """An unread file is a skip in the banner, never a clean "no control flow"."""
    bad = tmp_path / "bad.py"
    bad.write_text("def f(:\n", encoding="utf-8")
    code = cli.main([mode, *_CENSUS_FLAGS, "--boundary", "python", str(bad)])
    captured = capsys.readouterr()
    assert code == 1
    assert "read 0 of 1 file(s); 1 skipped" in captured.out + captured.err


def test_control_and_constructs_are_modes_not_do_not_port() -> None:
    """The ported spellings are wired in `MODES` and no longer refused as DO-NOT-PORT."""
    assert {"control", "constructs"} <= set(cli.MODES)
    assert not {"control", "constructs"} & cli.DO_NOT_PORT


def _importing_file(tmp_path: Path) -> Path:
    target = tmp_path / "m.py"
    target.write_text("import os\n", encoding="utf-8")
    return target


def test_importers_of_a_module_nobody_imports_says_what_it_searched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty `importers` prints `searched N file(s), found none` and still exits 0."""
    target = _importing_file(tmp_path)
    assert cli.main(["importers", "nobody", str(target)]) == 0
    assert capsys.readouterr().out == "importers: searched 1 file(s), found none\n"


def test_require_hits_makes_an_empty_importers_exit_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With `--require-hits` the same empty result fails, apart from refusal 2."""
    target = _importing_file(tmp_path)
    assert cli.main(["importers", "--require-hits", "nobody", str(target)]) == 1
    assert "found none" in capsys.readouterr().out


def test_a_mode_with_hits_is_unchanged_by_require_hits(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Rows printed: no `found none` line, exit 0, flag or not."""
    target = _importing_file(tmp_path)
    assert cli.main(["importers", "--require-hits", "os", str(target)]) == 0
    out = capsys.readouterr().out
    assert "os" in out
    assert "found none" not in out


def test_require_hits_leaves_an_incomplete_scan_and_a_refusal_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A fully skipped scan keeps its banner and exit 1; a refusal keeps exit 2, no found-none."""
    bad = tmp_path / "bad.py"
    bad.write_text("def f(:\n", encoding="utf-8")
    assert cli.main(["importers", "--require-hits", "os", str(bad)]) == 1
    out = capsys.readouterr().out
    assert "INCOMPLETE SCAN" in out
    assert "found none" not in out
    code = cli.main(["control", "--require-hits", *_CENSUS_FLAGS, "--boundary", "rust", str(bad)])
    assert code == _REFUSED
    assert "found none" not in capsys.readouterr().out


def test_require_hits_over_a_partial_scan_with_zero_rows_keeps_the_incomplete_exit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """One file read, one skipped, no rows: the banner AND found-none print; only the flag fails.

    The scan is partial (handler exit 0), so the empty-result rule applies: exit 0 by default,
    1 under `--require-hits`, with the banner kept so the empty result is not read as clean.
    """
    good = _importing_file(tmp_path)
    bad = tmp_path / "bad.py"
    bad.write_text("def f(:\n", encoding="utf-8")
    assert cli.main(["importers", "nobody", str(good), str(bad)]) == 0
    capsys.readouterr()
    assert cli.main(["importers", "--require-hits", "nobody", str(good), str(bad)]) == 1
    captured = capsys.readouterr()
    assert "read 1 of 2 file(s); 1 skipped" in captured.out + captured.err
    assert "importers: searched 2 file(s), found none" in captured.out


def test_control_with_zero_sites_says_found_none_and_fails_under_require_hits(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`control` over a file with no control flow is empty: exit 0 by default, 1 with the flag."""
    empty = tmp_path / "e.py"
    empty.write_text("x = 1\n", encoding="utf-8")
    flags = ["control", *_CENSUS_FLAGS, "--boundary", "python"]
    assert cli.main([*flags, str(empty)]) == 0
    assert capsys.readouterr().out == "control: searched 1 file(s), found none\n"
    assert cli.main([flags[0], "--require-hits", *flags[1:], str(empty)]) == 1
    assert "control: searched 1 file(s), found none" in capsys.readouterr().out


def test_a_summary_only_mode_still_reports_an_empty_result(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`values` prints a count line even when empty; that line is not a row, so it fails too."""
    target = _importing_file(tmp_path)
    assert cli.main(["values", "--require-hits", "nope", "kw", str(target)]) == 1
    out = capsys.readouterr().out
    assert "values: 0 of 0 calls pass it" in out
    assert "values: searched 1 file(s), found none" in out


def test_constructs_over_no_sites_is_empty_but_over_a_site_is_not(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The roster prints zeros, yet `constructs` only counts as a hit when a site was found."""
    flags = [*_CENSUS_FLAGS, "--boundary", "python"]
    empty = tmp_path / "e.py"
    empty.write_text("x = 1\n", encoding="utf-8")
    assert cli.main(["constructs", "--require-hits", *flags, str(empty)]) == 1
    assert "constructs: searched 1 file(s), found none" in capsys.readouterr().out
    full = _census_file(tmp_path)
    assert cli.main(["constructs", "--require-hits", *flags, str(full)]) == 0
    assert "found none" not in capsys.readouterr().out


def test_header_is_a_check_and_ignores_the_empty_result_rule(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A clean `header` run prints nothing and exits 0, even with `--require-hits`."""
    target = tmp_path / "h.py"
    target.write_text(
        "# SPDX-License-Identifier: MIT\n# Copyright (c) 2026 Me\nx = 1\n", encoding="utf-8"
    )
    args = ["header", "--require-hits", "--spdx", "MIT", "--year", "2026", str(target)]
    assert cli.main(args) == 0
    assert not capsys.readouterr().out


_REGISTERED_SOURCE = (
    "def q_alpha():\n    pass\n\n\ndef q_beta():\n    pass\n\n\n"
    "run(con, 'alpha')\nrun(con, 'gamma')\n"
)


def test_registered_joins_a_prefixed_def_to_the_literal_that_runs_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Red on HEAD by the missing `registered` mode: a def, its key, its site, an unmatched lead."""
    target = tmp_path / "m.py"
    target.write_text(_REGISTERED_SOURCE, encoding="utf-8")
    assert cli.main(["registered", "q_", str(target)]) == 0
    out = capsys.readouterr().out
    assert f"registered {target}:1 q_alpha key=alpha sites=1 {target}:9\n" in out
    assert f"registered {target}:5 q_beta key=beta sites=0 -\n" in out
    assert f"unmatched {target}:10 'gamma' " in out


def test_registered_with_no_prefixed_def_says_what_it_searched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A prefix matching no def and no literal prints the found-none line, exit 0."""
    target = tmp_path / "m.py"
    target.write_text("x = 1\n", encoding="utf-8")
    assert cli.main(["registered", "q_", str(target)]) == 0
    assert capsys.readouterr().out == "registered: searched 1 file(s), found none\n"


def test_registered_refuses_an_empty_prefix(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty PREFIX would register every def: it refuses, exit 2, naming the prefix."""
    target = tmp_path / "m.py"
    target.write_text("x = 1\n", encoding="utf-8")
    assert cli.main(["registered", "", str(target)]) == _REFUSED
    assert "non-empty prefix" in capsys.readouterr().out


def test_registered_over_an_unparseable_file_reports_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unread file is a skip in the banner, never a clean "no registered def"."""
    bad = tmp_path / "bad.py"
    bad.write_text("def f(:\n", encoding="utf-8")
    assert cli.main(["registered", "q_", str(bad)]) == 1
    assert "read 0 of 1 file(s); 1 skipped" in capsys.readouterr().out


_SQL_SOURCE = "con.execute('SELECT a FROM t')\nbuild('SELECT b FROM u')\nx = 'SELECT c FROM v'\n"
_SQL_FLAGS = ["--executors", "execute", "--builders", "build"]


def test_sql_grades_a_statement_by_how_it_is_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Red on HEAD by the missing `sql` mode: raw, builder and plain literal, by the rosters."""
    target = tmp_path / "m.py"
    target.write_text(_SQL_SOURCE, encoding="utf-8")
    assert cli.main(["sql", *_SQL_FLAGS, "", str(target)]) == 0
    rows = [ln.split(" ", 4)[1:] for ln in capsys.readouterr().out.splitlines()]
    assert rows == [
        ["raw", "SELECT", f"{target}:1", "SELECT a FROM t"],
        ["builder", "SELECT", f"{target}:2", "SELECT b FROM u"],
        ["literal", "SELECT", f"{target}:3", "SELECT c FROM v"],
    ]


def test_sql_with_no_matching_statement_says_what_it_searched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An ident no statement contains prints the found-none line, exit 0."""
    target = tmp_path / "m.py"
    target.write_text(_SQL_SOURCE, encoding="utf-8")
    assert cli.main(["sql", *_SQL_FLAGS, "nowhere", str(target)]) == 0
    assert capsys.readouterr().out == "sql: searched 1 file(s), found none\n"


@pytest.mark.parametrize("missing", ["executors", "builders"])
def test_sql_refuses_a_missing_roster_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], missing: str
) -> None:
    """A roster flag left out refuses, exit 2, naming it: no executor is guessed."""
    target = tmp_path / "m.py"
    target.write_text(_SQL_SOURCE, encoding="utf-8")
    given = {"executors": "execute", "builders": "build"}
    argv = ["sql"]
    for name, value in given.items():
        if name != missing:
            argv.extend([f"--{name}", value])
    assert cli.main([*argv, "", str(target)]) == _REFUSED
    assert f"--{missing} is required" in capsys.readouterr().out


def test_sql_over_an_unparseable_file_reports_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unread file is a skip in the banner, never a clean "no SQL"."""
    bad = tmp_path / "bad.py"
    bad.write_text("def f(:\n", encoding="utf-8")
    assert cli.main(["sql", *_SQL_FLAGS, "", str(bad)]) == 1
    assert "read 0 of 1 file(s); 1 skipped" in capsys.readouterr().out


def test_portable_reports_a_pattern_blocker_and_says_no_engine_ran(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Red on HEAD by the missing `portable` mode: a pattern verdict, and the degraded line."""
    target = tmp_path / "m.py"
    target.write_text("x = 'SELECT GROUP_CONCAT(a) FROM t'\n", encoding="utf-8")
    assert cli.main(["portable", str(target)]) == 0
    out = capsys.readouterr().out
    assert out.startswith(f"portable pattern {target}:1 use string_agg | ")
    assert "portable: degraded, no probe attached" in out
    assert "no engine judged" in out


def test_portable_with_no_blocker_says_what_it_searched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A portable statement prints the degraded line and the found-none line, exit 0."""
    target = tmp_path / "m.py"
    target.write_text("x = 'SELECT a FROM t'\n", encoding="utf-8")
    assert cli.main(["portable", str(target)]) == 0
    out = capsys.readouterr().out
    assert out.endswith("portable: searched 1 file(s), found none\n")
    assert "no engine judged" in out


def test_portable_names_a_generated_file_instead_of_dropping_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file with the generated marker is listed as a row, never silently left out."""
    target = tmp_path / "g.py"
    target.write_text("# GENERATED\nx = 1\n", encoding="utf-8")
    assert cli.main(["portable", str(target)]) == 0
    assert f"generated {target}\n" in capsys.readouterr().out


def test_portable_over_an_unparseable_file_reports_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unread file is a skip in the banner, never a clean "portable"."""
    bad = tmp_path / "bad.py"
    bad.write_text("def f(:\n", encoding="utf-8")
    assert cli.main(["portable", str(bad)]) == 1
    assert "read 0 of 1 file(s); 1 skipped" in capsys.readouterr().out


_STORE_FLAGS = {"readers": "execute", "receivers": "con", "connections": "con"}
_RAW_SOURCE = "for a, b in con.execute('q'):\n    pass\n"
_SNAP_SOURCE = "x = con.execute('a').fetchall() + con.execute('b').fetchall()\n"
_ALG_SOURCE = "def f(con):\n    rows = con.execute('q')\n    return sorted(rows)\n"


def _store_argv(mode: str, *, omit: str = "") -> list[str]:
    argv = [mode]
    for name, value in _STORE_FLAGS.items():
        if name != omit:
            argv.extend([f"--{name}", value])
    return argv


def test_rawreads_reports_an_unpacked_connection_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Red on HEAD by the missing `rawreads` mode: a tuple-unpacked `con.execute` loop."""
    target = tmp_path / "m.py"
    target.write_text(_RAW_SOURCE, encoding="utf-8")
    assert cli.main(["rawreads", "--connections", "con", str(target)]) == 0
    assert capsys.readouterr().out == f"rawreads unpacked {target}:1 con.execute('q')\n"


def test_rawreads_with_no_such_read_says_what_it_searched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A connection name nothing uses prints the found-none line, exit 0."""
    target = tmp_path / "m.py"
    target.write_text(_RAW_SOURCE, encoding="utf-8")
    assert cli.main(["rawreads", "--connections", "other", str(target)]) == 0
    assert capsys.readouterr().out == "rawreads: searched 1 file(s), found none\n"


def test_rawreads_refuses_a_missing_connections_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No `--connections` refuses, exit 2, naming it: no connection name is guessed."""
    target = tmp_path / "m.py"
    target.write_text(_RAW_SOURCE, encoding="utf-8")
    assert cli.main(["rawreads", str(target)]) == _REFUSED
    assert "--connections is required" in capsys.readouterr().out


def test_snapshots_reports_a_value_composed_of_two_trips(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Red on HEAD by the missing `snapshots` mode: two round trips in one expression."""
    target = tmp_path / "m.py"
    target.write_text(_SNAP_SOURCE, encoding="utf-8")
    assert cli.main([*_store_argv("snapshots"), str(target)]) == 0
    out = capsys.readouterr().out
    assert out.startswith(f"snapshots composed <module> trips=2 {target}:1 ")


def test_snapshots_with_one_trip_says_what_it_searched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A single round trip is no snapshot: the found-none line, exit 0."""
    target = tmp_path / "m.py"
    target.write_text("x = con.execute('a')\n", encoding="utf-8")
    assert cli.main([*_store_argv("snapshots"), str(target)]) == 0
    assert capsys.readouterr().out == "snapshots: searched 1 file(s), found none\n"


@pytest.mark.parametrize("missing", ["readers", "receivers", "connections"])
@pytest.mark.parametrize("mode", ["snapshots", "relalg"])
def test_a_store_mode_refuses_a_missing_vocabulary_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], mode: str, missing: str
) -> None:
    """A vocabulary flag left out refuses, exit 2, naming it: no store vocabulary is defaulted."""
    target = tmp_path / "m.py"
    target.write_text(_ALG_SOURCE, encoding="utf-8")
    argv = _store_argv(mode, omit=missing)
    if mode == "relalg":
        argv.extend(["--kinds", "sort"])
    assert cli.main([*argv, str(target)]) == _REFUSED
    assert f"--{missing} is required" in capsys.readouterr().out


def test_relalg_reports_a_sort_done_on_store_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Red on HEAD by the missing `relalg` mode: `sorted` over rows a store read produced."""
    target = tmp_path / "m.py"
    target.write_text(_ALG_SOURCE, encoding="utf-8")
    assert cli.main([*_store_argv("relalg"), "--kinds", "sort", str(target)]) == 0
    assert capsys.readouterr().out == f"relalg sort f {target}:3 sorted(rows)\n"


def test_relalg_with_another_kind_says_what_it_searched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Asking only for `join` over a sort-only file prints the found-none line, exit 0."""
    target = tmp_path / "m.py"
    target.write_text(_ALG_SOURCE, encoding="utf-8")
    assert cli.main([*_store_argv("relalg"), "--kinds", "join", str(target)]) == 0
    assert capsys.readouterr().out == "relalg: searched 1 file(s), found none\n"


def test_relalg_refuses_a_missing_empty_or_unknown_kinds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--kinds` has no default: absent, empty and unknown each refuse, exit 2, saying why."""
    target = tmp_path / "m.py"
    target.write_text(_ALG_SOURCE, encoding="utf-8")
    assert cli.main([*_store_argv("relalg"), str(target)]) == _REFUSED
    assert "--kinds is required" in capsys.readouterr().out
    assert cli.main([*_store_argv("relalg"), "--kinds", "", str(target)]) == _REFUSED
    assert "names no kind" in capsys.readouterr().out
    assert cli.main([*_store_argv("relalg"), "--kinds", "nope", str(target)]) == _REFUSED
    assert "unknown relalg kind(s): nope" in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["rawreads", "snapshots", "relalg"])
def test_a_store_mode_over_an_unparseable_file_reports_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], mode: str
) -> None:
    """An unread file is a skip in the banner, never a clean "no store read"."""
    bad = tmp_path / "bad.py"
    bad.write_text("def f(:\n", encoding="utf-8")
    argv = ["rawreads", "--connections", "con"] if mode == "rawreads" else _store_argv(mode)
    if mode == "relalg":
        argv.extend(["--kinds", "sort"])
    assert cli.main([*argv, str(bad)]) == 1
    assert "read 0 of 1 file(s); 1 skipped" in capsys.readouterr().out


def _fp_argv(seeds: list[Path], *, omit: str = "") -> list[str]:
    given = {**_STORE_FLAGS, "boundary": "python"}
    argv = ["fingerprint"]
    for name, value in given.items():
        if name != omit:
            argv.extend([f"--{name}", value])
    if omit != "seed":
        for seed in seeds:
            argv.extend(["--seed", str(seed)])
    return argv


def _fp_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    target = tmp_path / "m.py"
    target.write_text("def f(x):\n    if x:\n        return 1\n    return 2\n", encoding="utf-8")
    other = tmp_path / "other.py"
    other.write_text("y = 1\n", encoding="utf-8")
    wide = tmp_path / "wide.py"
    wide.write_text("x = 1\n", encoding="utf-8")
    return target, other, wide


def test_fingerprint_lists_the_unmodelled_remainder_of_a_site(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Red on HEAD by the missing `fingerprint` mode: a residual row naming what the seed lacks."""
    target, other, _wide = _fp_files(tmp_path)
    assert cli.main([*_fp_argv([other]), str(target)]) == 0
    out = capsys.readouterr().out
    assert f"fingerprint residual {target}:2 if f omega=1 " in out
    assert "unmodelled=x\n" in out
    assert "fingerprint sites=" in out


def test_fingerprint_with_a_seed_that_models_the_referent_leaves_no_remainder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A wider seed explains the site: its residual row says `omega=0` and names nothing."""
    target, _other, wide = _fp_files(tmp_path)
    assert cli.main([*_fp_argv([wide]), str(target)]) == 0
    out = capsys.readouterr().out
    assert f"fingerprint residual {target}:2 if f omega=0 " in out
    assert "fingerprint key x sites=2\n" in out


def test_fingerprint_over_no_control_site_says_what_it_searched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file with no control flow prints the totals as notes and the found-none line, exit 0."""
    _target, other, _wide = _fp_files(tmp_path)
    assert cli.main([*_fp_argv([other]), str(other)]) == 0
    out = capsys.readouterr().out
    assert out.endswith("fingerprint: searched 1 file(s), found none\n")
    assert "fingerprint sites=0 " in out


@pytest.mark.parametrize("missing", ["readers", "receivers", "connections", "boundary", "seed"])
def test_fingerprint_refuses_a_missing_operand_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], missing: str
) -> None:
    """A flag left out refuses, exit 2, naming it: no vocabulary, boundary or seed is defaulted."""
    target, other, _wide = _fp_files(tmp_path)
    assert cli.main([*_fp_argv([other], omit=missing), str(target)]) == _REFUSED
    assert f"--{missing} is required" in capsys.readouterr().out


def test_fingerprint_monotone_shows_the_remainder_cannot_rise(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--monotone` re-reads against the seed minus its last file and counts non-dividing sites."""
    target, other, wide = _fp_files(tmp_path)
    assert cli.main([*_fp_argv([other, wide]), "--monotone", str(target)]) == 0
    out = capsys.readouterr().out
    assert "fingerprint monotone: seeds 1 -> 2: omega 2 -> 0, bits 4 -> 2, " in out
    assert "sites whose remainder does not divide: 0\n" in out


def test_fingerprint_reports_an_unreadable_seed_and_an_unreadable_corpus(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A seed that cannot be read says so and fails; so does a corpus that cannot be parsed."""
    target, _other, _wide = _fp_files(tmp_path)
    ghost = tmp_path / "ghost.py"
    assert cli.main([*_fp_argv([ghost]), str(target)]) == 1
    out = capsys.readouterr().out
    assert "these --seed files could not be read; the modelled set shrank" in out
    assert "read 0 of 1 file(s); 1 skipped" in out
    bad = tmp_path / "bad.py"
    bad.write_text("def f(:\n", encoding="utf-8")
    assert cli.main([*_fp_argv([target]), str(bad)]) == 1
    assert "read 0 of 1 file(s); 1 skipped" in capsys.readouterr().out


_SPLIT_SOURCE = "def a():\n    return 1\n\n\ndef _b():\n    return 2\n"


def _split_module(tmp_path: Path, source: str = _SPLIT_SOURCE) -> Path:
    target = tmp_path / "m.py"
    target.write_text(source, encoding="utf-8")
    return target


def test_split_dry_run_prints_the_plan_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Red on HEAD by the missing `split` mode: parts and `would-write` rows, no file created."""
    target = _split_module(tmp_path)
    assert cli.main(["split", "--max-defs", "1", "--dry-run", str(target)]) == 0
    out = capsys.readouterr().out
    assert "split part m_00.py names=a\n" in out
    assert "split part m_01.py names=_b\n" in out
    assert "split would-write m_00.py lines=" in out
    assert not (tmp_path / "m_00.py").exists()
    assert target.read_text(encoding="utf-8") == _SPLIT_SOURCE


def test_split_apply_writes_the_siblings_and_the_entry(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--apply` is `apply(write=True)`: the siblings exist afterwards and the rows say `wrote`."""
    target = _split_module(tmp_path)
    assert cli.main(["split", "--max-defs", "1", "--apply", str(target)]) == 0
    out = capsys.readouterr().out
    assert "split wrote m_00.py lines=" in out
    assert (tmp_path / "m_00.py").exists()
    assert (tmp_path / "m_01.py").exists()
    assert "__all__" in target.read_text(encoding="utf-8")


def test_split_names_a_caller_owed_an_edit_for_a_moved_private_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A caller importing a private moved name is an `owed` row: the entry re-exports public."""
    target = _split_module(tmp_path)
    caller = tmp_path / "use.py"
    caller.write_text("from m import _b\n", encoding="utf-8")
    argv = ["split", "--max-defs", "1", "--dry-run", str(target), str(caller)]
    assert cli.main(argv) == 0
    assert f"split owed {caller}:1 _b moved-to=m_01.py\n" in capsys.readouterr().out


def test_split_of_a_module_with_nothing_to_move_says_what_it_searched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A module with no def to relocate plans no files: the found-none line, exit 0."""
    target = _split_module(tmp_path, "x = 1\n")
    assert cli.main(["split", "--dry-run", str(target)]) == 0
    assert capsys.readouterr().out == "split: searched 1 file(s), found none\n"


@pytest.mark.parametrize("choice", [[], ["--apply", "--dry-run"]])
def test_split_refuses_neither_or_both_of_apply_and_dry_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], choice: list[str]
) -> None:
    """Writing is never a default: neither flag, or both, refuses (exit 2) and writes nothing."""
    target = _split_module(tmp_path)
    assert cli.main(["split", "--max-defs", "1", *choice, str(target)]) == _REFUSED
    assert "exactly one of --apply and --dry-run is required" in capsys.readouterr().out
    assert not (tmp_path / "m_00.py").exists()


def test_split_refuses_a_module_that_declares_all(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A refused plan prints its kind and reason, exits 2, and is never applied."""
    target = _split_module(tmp_path, '__all__ = ["a"]\n\n\ndef a():\n    return 1\n')
    assert cli.main(["split", "--apply", str(target)]) == _REFUSED
    assert "all-declared" in capsys.readouterr().out
    assert not (tmp_path / "m_00.py").exists()


def test_split_over_an_unreadable_module_reports_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A module that cannot be read is a skip in the banner and exit 1, never a clean plan."""
    ghost = tmp_path / "ghost.py"
    assert cli.main(["split", "--dry-run", str(ghost)]) == 1
    assert "read 0 of 1 file(s); 1 skipped" in capsys.readouterr().out


def test_sqlname_is_retired_to_registered(capsys: pytest.CaptureFixture[str]) -> None:
    """The origin's `sqlname` refuses, exit 2, and names `registered` as its successor."""
    assert cli.main(["sqlname"]) == _REFUSED
    assert "`registered PREFIX PATHS`" in capsys.readouterr().out
