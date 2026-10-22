# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-vlog --follow` is the file form's pass repeated, and refuses any other form (W1817).

⚑ THE LOOP IS A SEAM, NOT A WAIT: `vlogfollow.follow` is replaced by a recorder that runs the pass
the unit would run, appends to the file between two passes, and returns, so no test sleeps or
loops. What the real loop does is `test_vlogfollow`'s.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, cast

from mikemol.hooks import vlogcli, vlogfollow

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    import pytest

_USAGE = 2
_PASSES = 2
Doc = dict[str, object]


def _spooled(spool_dir: Path) -> list[str]:
    found: list[str] = []
    for path in sorted(spool_dir.glob("vlog-*.spool")):
        lines = path.read_text(encoding="utf-8").splitlines()
        found.extend(str(cast("Doc", json.loads(line))["_msg"]) for line in lines)
    return found


def _run(tmp_path: Path, *extra: str, stdin: str = "") -> tuple[int, list[Sequence[str]]]:
    spawned: list[Sequence[str]] = []
    base = ["--spool-dir", str(tmp_path / "spool"), "--config", str(tmp_path / "none.toml")]
    code = vlogcli.main([*base, *extra], io.StringIO(stdin), spawned.append)
    return code, spawned


def test_follow_without_a_file_or_with_a_command_is_a_usage_error(tmp_path: Path) -> None:
    """Only a file can be followed from an offset: stdin and a wrapped command cannot."""
    assert _run(tmp_path, "--follow", stdin="x\n")[0] == _USAGE
    log = tmp_path / "app.log"
    log.write_text("one\n", encoding="utf-8")
    code, _ = _run(tmp_path, "--follow", "--from-file", str(log), "--", "true")
    assert code == _USAGE
    assert not (tmp_path / "spool").exists()


def test_each_pass_the_loop_makes_ships_only_what_is_new(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two passes over a file that grows between them: every line once, in order, exit 0."""
    log = tmp_path / "app.log"
    log.write_text("one\ntwo\n", encoding="utf-8")
    seen: list[bool] = []

    def fake_follow(
        step: Callable[[], bool],
        path: Path,
        pause: Callable[[], None],
        stop: Callable[[], bool] = vlogfollow.never,
    ) -> int:
        assert path == log
        assert callable(pause)
        assert not stop()
        seen.append(step())
        with log.open("a", encoding="utf-8") as handle:
            handle.write("three\n")
        seen.append(step())
        return _PASSES

    monkeypatch.setattr(vlogfollow, "follow", fake_follow)
    code, spawned = _run(tmp_path, "--follow", "--from-file", str(log), "--state", str(log) + ".s")
    assert code == 0
    assert _spooled(tmp_path / "spool") == ["one", "two", "three"]
    assert seen == [False, False]
    assert len(spawned) == _PASSES
