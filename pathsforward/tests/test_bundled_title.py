# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A title that bundles several steps is refused at mint time, nemik's predicate (mtools:W869)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward import cli, ops

if TYPE_CHECKING:
    from pathlib import Path

_LIMIT = ops.BUNDLED_LENGTH


def _pad(prefix: str, length: int) -> str:
    """Pad `prefix` with plain words to exactly `length` characters.

    Returns:
        the padded title.

    """
    return (prefix + " word" * length)[:length]


def _state(root: Path) -> Path:
    """Write an empty queue under `root`.

    Returns:
        the state path.

    """
    root.mkdir(parents=True, exist_ok=True)
    doc: dict[str, object] = {
        "counter": 1,
        "project_root": str(root),
        "waypoints": [],
        "residue": [],
    }
    path = root / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_a_long_title_with_a_semicolon_is_refused() -> None:
    """Over the limit and a clause mark: several steps in one waypoint."""
    title = _pad("first step", _LIMIT) + "; then a second"
    with pytest.raises(ops.RefusedError, match="several steps"):
        ops.refuse_bundled(title)


@pytest.mark.parametrize("mark", [";", "—", " -- "])
def test_each_clause_mark_trips_the_refusal(mark: str) -> None:
    """The semicolon, the em dash and the spaced double dash each count as a second clause."""
    title = _pad("first step", _LIMIT) + mark + "second"
    with pytest.raises(ops.RefusedError, match="bundled"):
        ops.refuse_bundled(title)


def test_a_long_single_clause_title_is_allowed() -> None:
    """Length alone is not bundling: nemik's rule needs a clause mark too."""
    ops.refuse_bundled(_pad("one long name", _LIMIT + 40))


def test_a_title_at_the_limit_with_a_mark_is_allowed() -> None:
    """The limit is exclusive: exactly 150 characters with a semicolon still passes."""
    title = _pad("first; second", _LIMIT)
    assert len(title) == _LIMIT
    ops.refuse_bundled(title)


def test_a_short_title_with_marks_is_allowed() -> None:
    """A short title may carry any mark; only the combination bundles."""
    ops.refuse_bundled("rename a; then retire b — done")


def test_add_refuses_a_bundled_title_and_changes_nothing(tmp_path: Path) -> None:
    """`--add` of a bundled title exits as refused and leaves the state file untouched."""
    path = _state(tmp_path)
    before = path.read_bytes()
    title = _pad("first step", _LIMIT) + "; then a second"
    code = cli.main(["--state", str(path), "--add", title])
    assert code == cli.EXIT_REFUSED
    assert path.read_bytes() == before


def test_update_refuses_to_retitle_into_a_bundle(tmp_path: Path) -> None:
    """`--update --title` applies the same refusal, so a title cannot be bundled afterwards."""
    path = _state(tmp_path)
    cli.main(["--state", str(path), "--add", "a short title"])
    before = path.read_bytes()
    title = _pad("first step", _LIMIT) + "; then a second"
    code = cli.main(["--state", str(path), "--update", "W2", "--title", title])
    assert code == cli.EXIT_REFUSED
    assert path.read_bytes() == before
