# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `sens`: cell records fold into a sensitivity set that fails loud when unsafe."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, cast

from mikemol.mutantcell import sens

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_LEAKED = 1


def _record(tmp_path: Path, name: str, **fields: object) -> str:
    """Write one cell record as JSON.

    Returns:
        The record's path.

    """
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(fields), encoding="utf-8")
    return str(path)


def _printed(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    """Read the one JSON line `sens` printed.

    Returns:
        The object on stdout.

    """
    return cast("dict[str, object]", json.loads(capsys.readouterr().out))


def test_the_sensitivity_set_is_the_flipped_sites_sorted_and_attempted_lists_every_site(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Only flipped sites enter `sens`; every swept site, flipped or not, is `attempted`."""
    base = _record(tmp_path, "base", claim="c1", site="0", flipped=False)
    hit_b = _record(tmp_path, "b", site="m.py::b", flipped=True)
    miss = _record(tmp_path, "m", site="m.py::m", flipped=False)
    hit_a = _record(tmp_path, "a", site="m.py::a", flipped=True)
    assert sens.main(["--baseline", base, hit_b, miss, hit_a]) == 0
    assert _printed(capsys) == {
        "claim": "c1",
        "baseline": True,
        "sens": ["m.py::a", "m.py::b"],
        "attempted": ["m.py::a", "m.py::b", "m.py::m"],
    }


def test_a_flipped_baseline_reads_baseline_false_so_the_sens_is_not_trusted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The unmutated check failing is reported as `baseline: false`, not hidden."""
    base = _record(tmp_path, "base", claim="c1", site="0", flipped=True)
    hit = _record(tmp_path, "h", site="m.py::f", flipped=True)
    assert sens.main(["--baseline", base, hit]) == 0
    got = _printed(capsys)
    assert got["baseline"] is False
    assert got["sens"] == ["m.py::f"]


def test_a_baseline_with_no_cells_yields_empty_lists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No records at all: an empty set swept, said plainly."""
    base = _record(tmp_path, "base", claim="c9", flipped=False)
    assert sens.main(["--baseline", base]) == 0
    assert _printed(capsys) == {"claim": "c9", "baseline": True, "sens": [], "attempted": []}


def test_a_flip_cell_that_reached_the_sensitivity_set_fails_loud(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A `::flip:` cell is non-monotone: it leaked the partition, so exit 1 naming it."""
    base = _record(tmp_path, "base", claim="c1", flipped=False)
    good = _record(tmp_path, "g", site="m.py::f", flipped=True)
    leak = _record(tmp_path, "l", site="m.py::flip:f#1", flipped=True)
    assert sens.main(["--baseline", base, good, leak]) == _LEAKED
    captured = capsys.readouterr()
    assert not captured.out
    assert "NON-monotone cell(s) reached pk_sens" in captured.err
    assert "m.py::flip:f#1" in captured.err
    assert "'m.py::f'" not in captured.err


def test_a_dflip_cell_is_refused_the_same_way(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A `::dflip:` data-value perturb is non-monotone too."""
    base = _record(tmp_path, "base", claim="c1", flipped=False)
    leak = _record(tmp_path, "l", site="m.py::dflip:T#2", flipped=False)
    assert sens.main(["--baseline", base, leak]) == _LEAKED
    assert "m.py::dflip:T#2" in capsys.readouterr().err


def test_main_reads_sys_argv_when_given_no_argument(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The `-m` path: `main()` takes its operands from `sys.argv[1:]`."""
    base = _record(tmp_path, "base", claim="c1", flipped=False)
    monkeypatch.setattr(sys, "argv", ["sens", "--baseline", base])
    assert sens.main() == 0
    assert _printed(capsys)["claim"] == "c1"
