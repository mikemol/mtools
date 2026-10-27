# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--tick-hooks-set` refuses to drop a stored hook without saying so (W1930).

⚑ THE CONTROLS: a stored line missing from the new file is refused and named, the same line
declared with `# replaces:` or `# retires:` is admitted, a file that adds lines or keeps them all
is admitted, the first set (nothing stored) is admitted, and a refused set leaves the stored list
exactly as it was.
"""

import json
from pathlib import Path
from typing import cast

import pytest

from mikemol.pathsforward import cli, tickhooks


def _repo(tmp_path: Path) -> Path:
    state = tmp_path / "repo" / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True)
    root = str(state.parent.parent)
    doc: dict[str, object] = {"counter": 0, "waypoints": [], "project_root": root}
    state.write_text(json.dumps(doc), encoding="utf-8")
    return state


def _set(state: Path, source: Path, text: str) -> int:
    source.write_text(text, encoding="utf-8")
    return cli.main(["--state", str(state), "--tick-hooks-set", str(source)])


def _stored(state: Path) -> object:
    doc = cast("dict[str, object]", json.loads(state.read_text(encoding="utf-8")))
    return doc.get(tickhooks.KEY)


def test_a_line_present_before_and_absent_after_is_dropped() -> None:
    """The pure check: the lines the new text loses, in stored order."""
    assert tickhooks.dropped(["a", "b", "c"], "a\nc\n") == ["b"]
    assert tickhooks.dropped(["a"], "a\nb\n") == []
    assert tickhooks.dropped([], "a\n") == []


def test_a_declared_replacement_or_retirement_is_not_a_drop() -> None:
    """`# replaces: b` and `# retires: b` name the line gone on purpose."""
    assert tickhooks.dropped(["a", "b"], "a\n# replaces: b\nb2\n") == []
    assert tickhooks.dropped(["a", "b"], "a\n# retires: b\n") == []
    assert tickhooks.dropped(["a", "b"], "a\n# replaces: other\n") == ["b"]


def test_the_command_refuses_a_drop_names_it_and_leaves_the_list_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The witness: a file missing a current line exits non-zero and names it."""
    state, source = _repo(tmp_path), tmp_path / "hooks.txt"
    assert _set(state, source, "echo landings\necho pace\n") == 0
    capsys.readouterr()
    assert _set(state, source, "echo pace\necho widened\n") == cli.EXIT_REFUSED
    assert "echo landings" in capsys.readouterr().err
    assert _stored(state) == ["echo landings", "echo pace"]


def test_the_command_admits_a_declared_replacement_and_a_first_set(tmp_path: Path) -> None:
    """Nothing stored is admitted; so is a drop the file declares."""
    state, source = _repo(tmp_path), tmp_path / "hooks.txt"
    assert _set(state, source, "echo landings\n") == 0
    assert _set(state, source, "# replaces: echo landings\necho landings per repo\n") == 0
    assert _stored(state) == ["echo landings per repo"]
