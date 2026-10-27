# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Every whole-list setter refuses a dropped line unless the file declares it gone (W2058).

⚑ THE CONTROLS (the class of W1930 and W862): a stored line missing from the new file is refused
and named, the same line declared with `# replaces:` or `# retires:` is admitted and the
declaration is NOT stored as content, a first set and a file that keeps or adds lines are
admitted, a refused set leaves the stored list exactly as it was, and the standing list and the
preamble behave the same as the tick hooks.
"""

import json
from pathlib import Path
from typing import cast

import pytest

from mikemol.pathsforward import cli, wholelist

_SETTERS = [("--standing-set", "standing"), ("--preamble-set", "preamble")]


def _repo(tmp_path: Path) -> Path:
    state = tmp_path / "repo" / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True)
    root = str(state.parent.parent)
    doc: dict[str, object] = {"counter": 0, "waypoints": [], "project_root": root}
    state.write_text(json.dumps(doc), encoding="utf-8")
    return state


def _set(state: Path, mode: str, text: str) -> int:
    source = state.parent.parent / "list.txt"
    source.write_text(text, encoding="utf-8")
    return cli.main(["--state", str(state), mode, str(source)])


def _stored(state: Path, key: str) -> object:
    doc = cast("dict[str, object]", json.loads(state.read_text(encoding="utf-8")))
    return doc.get(key)


def test_the_pure_check_names_lines_the_file_loses_and_honours_declarations() -> None:
    """Compared stripped; `# replaces:` and `# retires:` both declare a line gone."""
    assert wholelist.lost(["a", "b", "c"], "a\n  c  \n") == ["b"]
    assert wholelist.lost(["a", "b"], "a\n# replaces: b\n") == []
    assert wholelist.lost(["a", "b"], "a\n# retires: b\n") == []
    assert wholelist.lost(["a", "b"], "a\n# retires: other\n") == ["b"]
    assert wholelist.lost(["a", ""], "a\n") == []


def test_the_declaration_comments_are_not_content() -> None:
    """`split` keeps every other line, including ordinary comments, and drops the declarations."""
    kept, gone = wholelist.split("# a comment\nrule\n# replaces: old\n")
    assert kept == ["# a comment", "rule"]
    assert gone == {"old"}


@pytest.mark.parametrize(("mode", "key"), _SETTERS)
def test_a_dropped_line_is_refused_named_and_the_list_is_left_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], mode: str, key: str
) -> None:
    """The witness: a file missing a current line exits non-zero and names it."""
    state = _repo(tmp_path)
    assert _set(state, mode, "keep this\nlose this\n") == 0
    capsys.readouterr()
    assert _set(state, mode, "keep this\nnew line\n") == cli.EXIT_REFUSED
    assert "lose this" in capsys.readouterr().err
    assert _stored(state, key) == ["keep this", "lose this"]


def _outcomes(state: Path, advance: str, other: str, *extra: str) -> int:
    return cli.main(["--state", str(state), "--outcomes-set", advance, other, *extra])


def test_a_dropped_outcome_word_is_refused_named_and_the_sets_are_left_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--outcomes-set` has no file for a `# replaces:` line: the words go in `--retires`."""
    state = _repo(tmp_path)
    assert _outcomes(state, "advanced,landed", "idle,blocked") == 0
    capsys.readouterr()
    assert _outcomes(state, "advanced", "idle") == cli.EXIT_REFUSED
    said = capsys.readouterr().err
    assert "'landed'" in said
    assert "'blocked'" in said
    assert "--retires" in said
    assert _stored(state, "ledger_outcomes") == {
        "advance": ["advanced", "landed"],
        "other": ["idle", "blocked"],
    }


def test_a_retired_outcome_word_a_kept_one_and_a_first_declaration_are_admitted(
    tmp_path: Path,
) -> None:
    """Retiring declares the drop; a word moved between the sets is kept, not dropped."""
    state = _repo(tmp_path)
    assert _outcomes(state, "advanced,landed", "idle") == 0
    assert _outcomes(state, "advanced", "idle,landed") == 0
    assert _outcomes(state, "advanced", "idle", "--retires", "landed") == 0
    assert _stored(state, "ledger_outcomes") == {"advance": ["advanced"], "other": ["idle"]}


@pytest.mark.parametrize(("mode", "key"), _SETTERS)
def test_a_declared_replacement_is_admitted_and_the_declaration_is_not_stored(
    tmp_path: Path, mode: str, key: str
) -> None:
    """The first set is admitted; a declared drop is admitted; no declaration lands in the list."""
    state = _repo(tmp_path)
    assert _set(state, mode, "old rule\n") == 0
    assert _set(state, mode, "# replaces: old rule\nnew rule\n") == 0
    assert _stored(state, key) == ["new rule"]
