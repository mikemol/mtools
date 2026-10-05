# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The command line: plan prints JSON, mint syncs the queue, and every refusal is exit 2."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, cast

import pytest
from mikemol.pathsforward.model import strlist, text
from mikemol.pathsforward.store import load

from mikemol.debtplan.cli import EXIT_CANNOT, EXIT_OK, main
from mikemol.debtplan.queue import Queue

if TYPE_CHECKING:
    from pathlib import Path

THREE = 3


def _no_worktrees(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the walk's git question answer none, so no repository is needed."""

    def fake(_root: Path) -> list[Path]:
        return []

    monkeypatch.setattr("mikemol.pathwalk.walk.other_worktrees", fake)


def _repo(root: Path, ledger: str, files: dict[str, str]) -> Path:
    """Plant `files` (path to source) and a ledger under `root`.

    Returns:
        The ledger's path.

    """
    for name, source in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    path = root / "ledger.json"
    path.write_text(ledger, encoding="utf-8")
    return path


def _chain(root: Path) -> Path:
    """Plant leaf, mid and top (each importing the one before) and their ledger.

    Returns:
        The ledger's path.

    """
    files = {
        "leaf.py": "x = 1\n",
        "mid.py": "from leaf import x\n",
        "top.py": "from mid import x\n",
    }
    return _repo(root, '{"leaf.py": 2, "mid.py": 1, "top.py": 3}', files)


def _args(root: Path, ledger: Path, *extra: str) -> list[str]:
    """Build the operands every command takes.

    Returns:
        `--root`, `--ledger` and whatever else.

    """
    return ["--root", str(root), "--ledger", str(ledger), *extra]


def test_plan_prints_the_rows_in_pay_down_order_as_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The leaf is first and ready; each later row waits on what it imports."""
    ledger = _chain(tmp_path)
    assert main(["plan", *_args(tmp_path, ledger, "--no-universe")]) == EXIT_OK
    shown = cast("object", json.loads(capsys.readouterr().out))
    assert shown == {
        "rows": [
            {
                "file": "leaf.py",
                "count": 2,
                "ready": True,
                "waits_on": [],
                "waited_by": ["mid.py", "top.py"],
            },
            {
                "file": "mid.py",
                "count": 1,
                "ready": False,
                "waits_on": ["leaf.py"],
                "waited_by": ["top.py"],
            },
            {
                "file": "top.py",
                "count": THREE,
                "ready": False,
                "waits_on": ["leaf.py", "mid.py"],
                "waited_by": [],
            },
        ],
        "ambiguous": {},
    }


def test_a_plan_with_no_universe_prints_no_walk_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Nothing was walked, so nothing is reported skipped."""
    main(["plan", *_args(tmp_path, _chain(tmp_path), "--no-universe")])
    assert not capsys.readouterr().err


def test_the_universe_is_walked_by_default_and_what_it_skipped_is_printed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The walk reads the tree's files and says how many, and what it left out."""
    _no_worktrees(monkeypatch)
    ledger = _chain(tmp_path)
    assert main(["plan", *_args(tmp_path, ledger)]) == EXIT_OK
    assert capsys.readouterr().err == (
        "mikemol-debtplan: universe 3 file(s); skipped 0 worktree(s), 0 virtualenv(s), "
        "0 symlink(s), 0 excluded director(ies)\n"
    )


def test_the_closure_runs_through_a_clean_module_unless_told_not_to(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A reaches the debt file only through a clean module: the universe finds the wait."""
    _no_worktrees(monkeypatch)
    files = {"a.py": "import clean\n", "clean.py": "import debt\n", "debt.py": "x = 1\n"}
    ledger = _repo(tmp_path, '{"a.py": 1, "debt.py": 1}', files)

    def ready_of(*extra: str) -> dict[str, object]:
        main(["plan", *_args(tmp_path, ledger, *extra)])
        shown = cast("dict[str, list[dict[str, object]]]", json.loads(capsys.readouterr().out))
        return {str(row["file"]): row["ready"] for row in shown["rows"]}

    assert ready_of() == {"debt.py": True, "a.py": False}
    assert ready_of("--no-universe") == {"a.py": True, "debt.py": True}


def test_a_named_directory_is_excluded_and_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--exclude` may repeat, and each pruned directory is counted in the walk line."""
    _no_worktrees(monkeypatch)
    files = {"a.py": "x = 1\n", "build/g.py": "y = 1\n", "dist/h.py": "z = 1\n"}
    ledger = _repo(tmp_path, '{"a.py": 1}', files)
    main(["plan", *_args(tmp_path, ledger, "--exclude", "build", "--exclude", "dist")])
    assert "universe 1 file(s); skipped 0 worktree(s), 0 virtualenv(s), 0 symlink(s), 2 excl" in (
        capsys.readouterr().err
    )


def test_the_arguments_default_to_the_process_command_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no argv given, the command line of the process is read."""
    ledger = _chain(tmp_path)
    argv = ["mikemol-debtplan", "plan", *_args(tmp_path, ledger, "--no-universe")]
    monkeypatch.setattr(sys, "argv", argv)
    assert main() == EXIT_OK
    assert '"file": "leaf.py"' in capsys.readouterr().out


def test_a_malformed_ledger_is_refused_with_exit_2_and_names_the_ledger(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The refusal goes to standard error, naming the ledger, and nothing is printed to stdout."""
    ledger = _repo(tmp_path, "[]", {})
    assert main(["plan", *_args(tmp_path, ledger, "--no-universe")]) == EXIT_CANNOT
    shown = capsys.readouterr()
    assert not shown.out
    assert shown.err.startswith(f"mikemol-debtplan: {ledger}: expected a JSON object")


def test_a_missing_ledger_is_refused_with_exit_2(tmp_path: Path) -> None:
    """An unreadable ledger is a refusal and not an empty plan."""
    argv = ["plan", *_args(tmp_path, tmp_path / "absent.json", "--no-universe")]
    assert main(argv) == EXIT_CANNOT


def test_a_root_git_cannot_describe_is_refused_with_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With the universe on and no worktree answer, the refusal is reported and not guessed past."""
    ledger = _chain(tmp_path)
    assert main(["plan", *_args(tmp_path, ledger)]) == EXIT_CANNOT
    assert "refused" in capsys.readouterr().err


def test_mint_syncs_the_queue_and_says_what_changed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A first mint adds a card per file and reports the counts."""
    ledger = _chain(tmp_path)
    (tmp_path / ".claude").mkdir()
    queue = Queue(tmp_path / ".claude" / "paths-forward.json")
    assert queue.run("--init")[0] == 0
    args = ["mint", *_args(tmp_path, ledger, "--no-universe", "--prefix", "t: ")]
    assert main(args) == EXIT_OK
    assert capsys.readouterr().out == "mikemol-debtplan: added 3, rewrote 3, retired 0\n"
    assert set(queue.cards("t: ")) == {"leaf.py", "mid.py", "top.py"}


def test_the_default_prefix_names_the_repository_and_the_default_state_is_its_queue(
    tmp_path: Path,
) -> None:
    """Without --prefix the title says `<repo> debt: `, and the queue is ROOT/.claude's."""
    ledger = _chain(tmp_path)
    (tmp_path / ".claude").mkdir()
    queue = Queue(tmp_path / ".claude" / "paths-forward.json")
    queue.run("--init")
    assert main(["mint", *_args(tmp_path, ledger, "--no-universe")]) == EXIT_OK
    assert set(queue.cards(f"{tmp_path.name} debt: ")) == {"leaf.py", "mid.py", "top.py"}


def test_a_named_state_file_is_the_queue_that_is_synced(tmp_path: Path) -> None:
    """`--state` points the writer elsewhere than the default."""
    ledger = _chain(tmp_path)
    queue = Queue(tmp_path / "elsewhere.json")
    queue.run("--init")
    args = ["mint", *_args(tmp_path, ledger, "--no-universe", "--prefix", "t: ")]
    assert main([*args, "--state", str(queue.state)]) == EXIT_OK
    assert len(queue.cards("t: ")) == THREE


def test_mint_options_set_the_step_the_tags_and_the_vector(tmp_path: Path) -> None:
    """`--how`, `--touches` and `--vector` are what the cards carry."""
    ledger = _chain(tmp_path)
    queue = Queue(tmp_path / "pf.json")
    queue.run("--init")
    vector = "WV:1/R:T/E:Y/C:L/I:L/A:L/X:P/S:U/F:U/W:N"
    options = ["--how", "so it passes", "--touches", "typing", "mypy", "--vector", vector]
    args = ["mint", *_args(tmp_path, ledger, "--no-universe", "--prefix", "t: ", *options)]
    assert main([*args, "--state", str(queue.state)]) == EXIT_OK
    record = next(r for r in load(queue.state).waypoints if text(r, "title").startswith("t: leaf"))
    assert "so it passes" in text(record, "next_bounded_step")
    assert strlist(record, "touches") == ["typing", "mypy"]
    assert text(record, "vector") == vector


def test_a_refused_mint_is_exit_2_and_says_why(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no queue file the writer refuses to lock it, and the sync stops."""
    ledger = _chain(tmp_path)
    args = ["mint", *_args(tmp_path, ledger, "--no-universe", "--prefix", "t: ")]
    assert main(args) == EXIT_CANNOT
    assert "cannot take the tick lock" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [["frobnicate"], [], ["plan"], ["mint", "--root", "r"]])
def test_an_unknown_command_or_missing_operand_is_a_usage_error(argv: list[str]) -> None:
    """Argparse refuses it with its own exit code 2."""
    with pytest.raises(SystemExit) as raised:
        main(argv)
    assert raised.value.code == EXIT_CANNOT
