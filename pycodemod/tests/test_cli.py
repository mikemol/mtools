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
    assert "relname" not in capsys.readouterr().out


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
