# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the tick hooks: stored whole, run in order, never able to break the tick (W1348).

⚑ THE CONTROLS ARE THE THREE WAYS A HOOK COULD HURT THE TICK: a bad line surfacing mid-tick (it is
refused when stored), a failing command stopping the commands after it (it does not), and a hook
changing the exit status or the lock (it cannot). The process is a recorder except in the tests
that run `echo`, `false` and a missing command for real.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.pathsforward import cli, tickhooks
from mikemol.pathsforward.model import RefusedError

if TYPE_CHECKING:
    from collections.abc import Sequence

Doc = dict[str, object]
OVER = 25
HERE = Path()


def _runner(codes: dict[str, int], output: str = "") -> tuple[tickhooks.Runner, list[str]]:
    seen: list[str] = []

    def run(argv: Sequence[str], cwd: Path) -> tuple[int, str]:
        del cwd
        seen.append(argv[0])
        return codes.get(argv[0], 0), output

    return run, seen


def _repo(tmp_path: Path) -> Path:
    state = tmp_path / "myrepo" / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True)
    doc: Doc = {"counter": 0, "waypoints": [], "project_root": str(tmp_path / "myrepo")}
    state.write_text(json.dumps(doc), encoding="utf-8")
    return state


def _doc(state: Path) -> Doc:
    return cast("Doc", json.loads(state.read_text(encoding="utf-8")))


def test_blank_and_comment_lines_are_skipped_and_the_rest_kept_in_order() -> None:
    """Only commands survive, stripped, in the order written."""
    text = "# the hooks\n\n  git pull  \nnemik-inbound nemik\n   # not this\n"
    assert tickhooks.lines_of(text) == ["git pull", "nemik-inbound nemik"]
    assert tickhooks.lines_of("") == []


def test_an_unbalanced_quote_is_refused_when_stored_not_mid_tick() -> None:
    """The control: the line is named in the refusal."""
    with pytest.raises(RefusedError, match="tick hook"):
        tickhooks.lines_of('echo ok\necho "open\n')


def test_stored_reads_only_a_list_of_strings() -> None:
    """Absent, a string, or a list with a number reads as what it validly holds."""
    assert tickhooks.stored({}) == []
    assert tickhooks.stored({tickhooks.KEY: "git pull"}) == []
    assert tickhooks.stored({tickhooks.KEY: ["git pull", 3, "x"]}) == ["git pull", "x"]


def test_a_failing_hook_is_reported_and_the_next_still_runs() -> None:
    """The control: `b` exits 3, `c` runs anyway, and each result line names its status."""
    run, seen = _runner({"b": 3})
    said = tickhooks.run_all(["a x", "b", "c"], HERE, run)
    assert seen == ["a", "b", "c"]
    assert said == ["HOOK a x exit 0", "HOOK b exit 3", "HOOK c exit 0"]


def test_long_output_is_capped_with_a_count_of_the_rest() -> None:
    """Twenty-five lines show twenty indented and say how many were left out."""
    run, _ = _runner({}, "".join(f"line {n}\n" for n in range(OVER)))
    said = tickhooks.run_all(["noisy"], HERE, run)
    assert said[0] == "HOOK noisy exit 0"
    assert len(said) == 1 + tickhooks.SHOWN + 1
    assert said[1] == "  line 0"
    assert said[-1] == f"  ... {OVER - tickhooks.SHOWN} more line(s)"


def test_the_real_runner_captures_output_and_reports_a_missing_command(tmp_path: Path) -> None:
    """Echo answers with its words; a command that is not there is 127 with the reason."""
    assert tickhooks.run_process(["echo", "hi"], tmp_path) == (0, "hi\n")
    code, why = tickhooks.run_process(["no-such-tick-hook-command"], tmp_path)
    assert code == tickhooks.NOT_FOUND
    assert "no-such-tick-hook-command" in why


def test_set_stores_whole_and_an_empty_file_clears(tmp_path: Path) -> None:
    """`--tick-hooks-set` replaces the list; an empty file is the decision to have none."""
    state = _repo(tmp_path)
    source = tmp_path / "hooks.txt"
    source.write_text("echo one\n# c\necho two\n", encoding="utf-8")
    assert cli.main(["--state", str(state), "--tick-hooks-set", str(source)]) == 0
    assert _doc(state)[tickhooks.KEY] == ["echo one", "echo two"]
    source.write_text("", encoding="utf-8")
    assert cli.main(["--state", str(state), "--tick-hooks-set", str(source)]) == 0
    assert _doc(state)[tickhooks.KEY] == []


def test_tick_open_runs_the_stored_hooks_and_a_failing_one_changes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Real echo and false: both reported, the exit status and the held lock are the tick's own."""
    state = _repo(tmp_path)
    source = tmp_path / "hooks.txt"
    source.write_text("echo hello\nfalse\necho after\n", encoding="utf-8")
    assert cli.main(["--state", str(state), "--tick-hooks-set", str(source)]) == 0
    capsys.readouterr()
    assert cli.main(["--state", str(state), "--tick-open", "tester"]) == 0
    said = capsys.readouterr().out.splitlines()
    assert "HOOK echo hello exit 0" in said
    assert "  hello" in said
    assert "HOOK false exit 1" in said
    assert "HOOK echo after exit 0" in said
    assert said[-1].startswith("tick open as tester")
    assert _doc(state)["lock"]
