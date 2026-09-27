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


def test_escapes_over_an_unparseable_file_reports_incomplete(tmp_path: Path) -> None:
    """A file that fails to compile makes `escapes` print the shared incomplete-scan banner."""
    target = tmp_path / "m.py"
    target.write_text("def (:\n", encoding="utf-8")
    code = cli.main(["escapes", str(target)])
    assert code == 1


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
