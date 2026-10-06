# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `read_guard`: an oversized, unbounded whole-file Read is denied, nothing else."""

from __future__ import annotations

import io
import json
import sys
from typing import TYPE_CHECKING

from mikemol.hooks import entry, hook_argv, read_guard

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

BIG = read_guard.MAX_BYTES + 1
LOG = "/data/tasks/gate.output"
PAGES = "1-3"
LIMIT = 40


def _big(path: Path) -> int | None:
    """Size every path as just over the cap.

    Returns:
        MAX_BYTES + 1, whatever the path.

    """
    del path
    return BIG


def _at_the_cap(path: Path) -> int | None:
    """Size every path as exactly the cap.

    Returns:
        MAX_BYTES, whatever the path.

    """
    del path
    return read_guard.MAX_BYTES


def _unsizable(path: Path) -> int | None:
    """Size no path: stands in for a missing or unreadable file.

    Returns:
        None, whatever the path.

    """
    del path
    return None


def _deny_line(reason: str) -> str:
    """Return the exact deny JSON `run` prints.

    Returns:
        the decision JSON, with no trailing newline.

    """
    decision: dict[str, dict[str, str]] = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    return json.dumps(decision)


def test_a_regular_file_is_sized_and_anything_else_is_not(tmp_path: Path) -> None:
    """A file reads its byte count; a missing path and a directory are None, never zero."""
    data = tmp_path / "data"
    data.write_bytes(b"x" * 123)
    assert read_guard.file_size(data) == len(b"x" * 123)
    assert read_guard.file_size(tmp_path / "no-such-file") is None
    assert read_guard.file_size(tmp_path) is None


def test_only_a_limit_or_a_pages_range_bounds_a_read() -> None:
    """An integer limit and a pages range bound the read; a bool, a string and nothing do not."""
    assert read_guard.bounds_the_read({"limit": LIMIT})
    assert read_guard.bounds_the_read({"limit": 0})
    assert read_guard.bounds_the_read({"pages": PAGES})
    assert not read_guard.bounds_the_read({"limit": True})
    assert not read_guard.bounds_the_read({"limit": "40"})
    assert not read_guard.bounds_the_read({"pages": ""})
    assert not read_guard.bounds_the_read({"file_path": LOG})


def test_an_unbounded_read_of_an_oversized_file_is_refused_with_the_cheaper_reads() -> None:
    """The reason names the file, its size and the two cheaper reads (offset and limit, grep)."""
    reason = read_guard.refusal({"file_path": LOG}, _big)
    assert reason is not None
    assert "gate.output" in reason
    assert f"{BIG:,} bytes" in reason
    assert "offset" in reason
    assert "limit" in reason
    assert "grep" in reason


def test_a_file_at_the_cap_and_a_bounded_read_are_admitted() -> None:
    """The cap is inclusive of its own size, and a limit or pages makes any size admissible."""
    assert read_guard.refusal({"file_path": LOG}, _at_the_cap) is None
    assert read_guard.refusal({"file_path": LOG, "limit": LIMIT}, _big) is None
    assert read_guard.refusal({"file_path": LOG, "pages": PAGES}, _big) is None


def test_a_rendered_type_a_missing_file_and_no_path_are_admitted() -> None:
    """Rendered types, an unsizable file and a missing path are the tool's to handle."""
    for name in ("/x/shot.png", "/x/SHOT.JPG", "/x/paper.pdf", "/x/book.ipynb"):
        assert read_guard.refusal({"file_path": name}, _big) is None
    assert read_guard.refusal({"file_path": LOG}, _unsizable) is None
    assert read_guard.refusal({}, _big) is None
    assert read_guard.refusal({"file_path": ""}, _big) is None


def test_a_refused_read_prints_the_deny_decision() -> None:
    """The denial goes to stdout as the harness's PreToolUse deny JSON, exit code zero."""
    out = io.StringIO()
    payload: dict[str, object] = {"tool_name": "Read", "tool_input": {"file_path": LOG}}
    assert read_guard.run(payload, _big, out) == 0
    reason = read_guard.refusal({"file_path": LOG}, _big)
    assert reason is not None
    assert out.getvalue() == _deny_line(reason)


def test_an_admitted_read_prints_nothing() -> None:
    """A read that is fine says nothing at all."""
    out = io.StringIO()
    payload: dict[str, object] = {"tool_input": {"file_path": LOG, "limit": LIMIT}}
    assert read_guard.run(payload, _big, out) == 0
    assert not out.getvalue()


def _stdin(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    """Make stdin carry a PreToolUse(Read) payload for `path`."""
    payload: dict[str, object] = {"tool_name": "Read", "tool_input": {"file_path": str(path)}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))


def test_main_denies_a_real_oversized_file_when_armed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Through main, with the real size reader, an armed guard denies a file over the cap."""
    big = tmp_path / "big.log"
    big.write_bytes(b"x" * BIG)
    monkeypatch.setenv(read_guard.OWN_SWITCH, "1")
    _stdin(monkeypatch, big)
    assert read_guard.main() == 0
    assert '"permissionDecision": "deny"' in capsys.readouterr().out


def test_main_is_silent_when_unarmed_or_stood_down(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Unarmed says nothing, and the hook's own switch at 0 beats the shared switch at 1."""
    big = tmp_path / "big.log"
    big.write_bytes(b"x" * BIG)
    monkeypatch.delenv(read_guard.OWN_SWITCH, raising=False)
    monkeypatch.delenv("STRUCT_HOOK_BLOCK", raising=False)
    _stdin(monkeypatch, big)
    assert read_guard.main() == 0
    assert not capsys.readouterr().out
    monkeypatch.setenv("STRUCT_HOOK_BLOCK", "1")
    monkeypatch.setenv(read_guard.OWN_SWITCH, "0")
    _stdin(monkeypatch, big)
    assert read_guard.main() == 0
    assert not capsys.readouterr().out


def test_main_says_nothing_for_an_unreadable_payload_even_when_armed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A malformed payload is not a read to judge, so an armed guard stays silent."""
    monkeypatch.setenv(read_guard.OWN_SWITCH, "1")
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert read_guard.main() == 0
    assert not capsys.readouterr().out


def test_the_console_entry_refuses_an_argument_before_reading_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The argv contract: a hook takes no arguments, and the refusal names the program."""
    monkeypatch.setattr(sys, "argv", ["mikemol-hook-read-guard", "--help"])
    assert entry.read_guard_main() == hook_argv.EXIT_REFUSED
    assert "mikemol-hook-read-guard" in capsys.readouterr().err
