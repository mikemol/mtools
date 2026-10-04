# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `probe`: the marker lands, the count is read from bazel, nothing is stranded."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from mikemol.buildtel import probe

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

_PROCESSES = "INFO: 120 processes: 100 action cache hit, 5 internal, 15 linux-sandbox."
_EXECUTED = 15
_EXIT_NO_FILE = 2
_HOOK_FAILED = 3
_MARKER = "# TEST-MARKER\n"
_ORIGINAL = "VALUE = 1\n"


def _target(tmp_path: Path, text: str = _ORIGINAL) -> Path:
    """Plant the file to be null-edited.

    Returns:
        its path.

    """
    target = tmp_path / "module.py"
    target.write_text(text, encoding="utf-8")
    return target


class _Hook:
    """A stand-in for the bazel runner: records what the file held at each call."""

    def __init__(self, target: Path, answers: Sequence[tuple[int, str]]) -> None:
        """Remember the file to watch and the answers to give, in order."""
        self.target = target
        self.answers = list(answers)
        self.labels: list[str] = []
        self.contents: list[str] = []

    def __call__(self, label: str) -> tuple[int, str]:
        """Record the call and answer with the next scripted result.

        Returns:
            the next `(status, processes line)`.

        """
        self.labels.append(label)
        self.contents.append(self.target.read_text(encoding="utf-8"))
        return self.answers[len(self.labels) - 1]


def _run(
    target: Path,
    run_hook: Callable[[str], tuple[int, str]],
    *flags: str,
) -> int:
    """Run `probe.main` over `target` with a fixed marker.

    Returns:
        main's exit status.

    """
    return probe.main([str(target), *flags], run_hook=run_hook, make_marker=lambda: _MARKER)


def test_executed_counts_everything_that_is_not_a_cache_hit_or_internal() -> None:
    """Of 100 cache hits, 5 internal and 15 sandboxed, the executed count is 15."""
    assert probe.executed(_PROCESSES) == _EXECUTED


def test_executed_sums_every_executing_strategy() -> None:
    """Two executing strategies add."""
    assert probe.executed("INFO: 9 processes: 3 remote, 4 linux-sandbox.") == 3 + 4


def test_executed_is_none_for_a_line_that_is_not_the_processes_line() -> None:
    """Anything else bazel prints, or nothing, has no count."""
    assert probe.executed("INFO: Build completed successfully") is None
    assert probe.executed("") is None


def test_new_marker_is_a_one_line_comment_with_random_hex() -> None:
    """The default marker is a comment line ending in a newline, tagged with 8 hex digits."""
    marker = probe.new_marker()
    assert re.fullmatch(r"# PROBE-MARKER [0-9a-f]{8} \(mikemol\.buildtel\.probe .*\)\n", marker)


def test_hook_streams_stderr_through_and_returns_status_and_the_last_processes_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every stderr line is echoed live; the answer is the LAST processes line, stripped."""
    asked: list[Sequence[str]] = []

    def stream(argv: Sequence[str], on_line: Callable[[str], None]) -> int:
        asked.append(list(argv))
        for line in ("noise\n", "INFO: 1 processes: 1 local.\n", f"{_PROCESSES}\n", "tail\n"):
            on_line(line)
        return _HOOK_FAILED

    status, line = probe.hook("marker build", stream)
    captured = capsys.readouterr()
    assert (status, line) == (_HOOK_FAILED, _PROCESSES)
    assert asked == [["bazel", "test", "//:hook", "--config=mutant"]]
    assert captured.err == f"noise\nINFO: 1 processes: 1 local.\n{_PROCESSES}\ntail\n"
    assert captured.out.startswith("probe: marker build")


def test_hook_with_no_processes_line_answers_empty() -> None:
    """A bazel that printed no processes line gives `""`, not a stale or invented one."""
    assert probe.hook("x", lambda _argv, _on_line: 0) == (0, "")


def test_main_appends_a_verified_marker_for_the_hook_and_restores_the_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """During the build the file ends in the marker once; afterwards it is byte-identical."""
    target = _target(tmp_path)
    hook = _Hook(target, [(0, _PROCESSES), (0, "")])
    assert _run(target, hook) == 0
    assert hook.contents[0] == _ORIGINAL + _MARKER
    assert target.read_text(encoding="utf-8") == _ORIGINAL
    out = capsys.readouterr().out
    assert f"probe: marker verified in {target}\n" in out
    assert f"probe: marker reverted from {target}\n" in out
    assert f"probe: {target} → EXECUTED {_EXECUTED} actions\n" in out
    assert f"probe:   {_PROCESSES}\n" in out


def test_main_resyncs_the_build_state_after_the_revert_unless_told_not_to(tmp_path: Path) -> None:
    """The second hook run, on the restored file, is the resync; `--no-resync` skips it."""
    target = _target(tmp_path)
    hook = _Hook(target, [(0, _PROCESSES), (0, "")])
    _run(target, hook)
    assert (hook.labels, hook.contents[1]) == (["marker build", "build-state resync"], _ORIGINAL)
    chained = _Hook(target, [(0, _PROCESSES)])
    assert _run(target, chained, "--no-resync") == 0
    assert chained.labels == ["marker build"]


def test_main_reports_an_unreadable_count_as_a_question_mark(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no processes line from bazel the count is `?`, never a guess."""
    target = _target(tmp_path)
    assert _run(target, _Hook(target, [(0, "")]), "--no-resync") == 0
    assert "→ EXECUTED ? actions" in capsys.readouterr().out


def test_main_reverts_the_marker_even_when_the_build_crashes(tmp_path: Path) -> None:
    """An exception out of the hook still leaves the file as it was."""
    target = _target(tmp_path)

    def crash(_label: str) -> tuple[int, str]:
        msg = "bazel exploded"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="bazel exploded"):
        _run(target, crash)
    assert target.read_text(encoding="utf-8") == _ORIGINAL


def test_main_flags_a_red_probe_build_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A hook that fails under the marker says the count is not clean, and the exit is 1."""
    target = _target(tmp_path)
    hook = _Hook(target, [(_HOOK_FAILED, _PROCESSES), (0, "")])
    assert _run(target, hook) == 1
    assert f"hook FAILED under the marker (rc={_HOOK_FAILED})" in capsys.readouterr().err
    assert target.read_text(encoding="utf-8") == _ORIGINAL


def test_main_fails_when_the_resync_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A red resync is exit 1 naming its status: the build state is not back in sync."""
    target = _target(tmp_path)
    hook = _Hook(target, [(0, _PROCESSES), (_HOOK_FAILED, "")])
    assert _run(target, hook) == 1
    assert f"resync hook FAILED (rc={_HOOK_FAILED})" in capsys.readouterr().err


def test_main_aborts_and_restores_when_the_marker_did_not_land_exactly_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file that already holds the marker text cannot prove the edit landed: abort, no build."""
    target = _target(tmp_path, _ORIGINAL + _MARKER)
    hook = _Hook(target, [])
    assert _run(target, hook) == 1
    assert hook.labels == []
    assert target.read_text(encoding="utf-8") == _ORIGINAL + _MARKER
    assert "marker failed to land" in capsys.readouterr().err


def test_main_refuses_a_file_that_does_not_exist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing target is exit 2 naming it, before anything is run."""
    missing = tmp_path / "absent.py"
    hook = _Hook(missing, [])
    assert _run(missing, hook) == _EXIT_NO_FILE
    assert hook.labels == []
    assert capsys.readouterr().err == f"probe: no such file {missing}\n"
