# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a vendored wheel is measured against the must-have fixes by ancestry (W1138).

⚑ THE CONTROLS: a fix that names another dist does not make a pin behind; a pin git cannot resolve
is not measured (None, never current); a git pin keeps its SAME or DIFFERS and carries no
measurement; and the metrics say 1 for a wheel lacking a fix, 0 for one that has them all, and
nothing for one that was not measured.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import musthave, repin_cli, repin_metrics

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pytest

_FIX = "a" * 40
_OTHER = "b" * 40
_PAR = "c" * 40
_WHEEL = "vendor/wheels/mikemol_hooks-0.1.0+g1234567-py3-none-any.whl"
_GIT = "https://github.com/mikemol/mtools.git@"
_GITPIN = f"mikemol-fence @ git+{_GIT}{'d' * 40}#subdirectory=fence"


def _entries() -> list[dict[str, object]]:
    return [
        {"sha": _FIX, "dists": ["hooks"], "reason": "r", "requires": []},
        {"sha": _OTHER, "dists": ["fence"], "reason": "r", "requires": []},
    ]


def _runner(*, lacks: frozenset[str] = frozenset(), unknown: bool = False) -> musthave.Runner:
    def run(argv: Sequence[str], _repo: Path) -> tuple[int, str]:
        if argv[1] == "cat-file":
            return (1, "") if unknown else (0, "")
        if argv[1] == "merge-base":
            return (1, "") if argv[3] in lacks else (0, "")
        if argv[1] == "show":
            return 0, json.dumps(_entries())
        return 0, ""

    return run


def test_a_wheel_lacking_a_fix_that_names_its_dist_is_behind_and_another_dists_fix_is_not() -> None:
    """The hooks fix is missing, so hooks is behind by it; the fence fix is not hooks' concern."""
    lacks = frozenset({_FIX, _OTHER})
    got = musthave.missing_for("1234567", "hooks", _entries(), Path("/m"), _runner(lacks=lacks))
    assert got == (_FIX,)
    assert musthave.missing_for("1234567", "hooks", _entries(), Path("/m"), _runner()) == ()


def test_a_pin_git_cannot_resolve_is_not_measured() -> None:
    """An unknown commit gives None, so no claim is made that it is current or behind."""
    got = musthave.missing_for("1234567", "hooks", _entries(), Path("/m"), _runner(unknown=True))
    assert got is None


def test_the_fixes_are_read_at_the_par_commit_and_no_list_there_means_no_measurement() -> None:
    """`git show PAR:file` supplies the entries; a failing show is a reason, not an empty list."""
    got = musthave.at_commit(_PAR, Path("/m"), _runner())
    assert isinstance(got, list)
    assert [e["sha"] for e in got] == [_FIX, _OTHER]

    def none_there(_argv: Sequence[str], _repo: Path) -> tuple[int, str]:
        return 128, ""

    assert "cannot be read" in str(musthave.at_commit(_PAR, Path("/m"), none_there))

    def broken(_argv: Sequence[str], _repo: Path) -> tuple[int, str]:
        return 0, "[["

    assert "is not JSON" in str(musthave.at_commit(_PAR, Path("/m"), broken))


def _root(tmp_path: Path) -> Path:
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(f'dependencies = ["{_GITPIN}"]\n# {_WHEEL}\n', "utf-8")
    return tmp_path


def test_survey_measures_only_the_vendored_wheel(tmp_path: Path) -> None:
    """The wheel row carries its missing fixes; the git row keeps its status and has none."""
    root = _root(tmp_path)

    def measure(_pin: object) -> tuple[str, ...] | None:
        return (_FIX,)

    rows = repin_cli.survey(root, _PAR, None, measure)
    wheel = next(r for r in rows if r.form == "wheel")
    git = next(r for r in rows if r.form != "wheel")
    assert wheel.missing == (_FIX,)
    assert (git.missing, git.status) == (None, "DIFFERS")
    assert repin_cli.survey(root, _PAR, None)[0].missing is None


def test_the_metrics_say_behind_for_a_lacking_wheel_and_nothing_when_not_measured(
    tmp_path: Path,
) -> None:
    """1 plus a missing_fix series for the lacking wheel; 0 when whole; absent when unmeasured."""
    rows = [
        repin_cli.Row("a", "hooks", "wheel", "1234567", "VENDORED", (_FIX,)),
        repin_cli.Row("b", "hooks", "wheel", "7654321", "VENDORED", ()),
        repin_cli.Row("c", "hooks", "wheel", "1111111", "VENDORED", None),
        repin_cli.Row("d", "fence", "pep508", "d" * 40, "DIFFERS"),
    ]
    text = repin_metrics.render(rows, str(tmp_path), _PAR)
    assert 'mikemol_repin_behind_par{repo="a",dist="hooks"} 1' in text
    assert 'mikemol_repin_behind_par{repo="b",dist="hooks"} 0' in text
    assert 'mikemol_repin_behind_par{repo="c"' not in text
    assert 'mikemol_repin_behind_par{repo="d",dist="fence"} 1' in text
    assert f'mikemol_repin_missing_fix{{repo="a",dist="hooks",fix="{_FIX[:12]}"}} 1' in text
    assert text.count("mikemol_repin_missing_fix{") == 1


def test_main_reads_the_list_at_par_and_publishes_the_measurement(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With a par sha and a metrics file the wheel is measured and its fix is a series."""
    root = _root(tmp_path)
    out = tmp_path / "pins.prom"
    argv = ["--root", str(root), "--sha", _PAR, "--metrics", str(out), "--mtools", str(tmp_path)]
    assert repin_cli.main(argv, _runner(lacks=frozenset({_FIX}))) == 0
    capsys.readouterr()
    text = out.read_text(encoding="utf-8")
    assert 'mikemol_repin_behind_par{repo="consumer",dist="hooks"} 1' in text
    assert "mikemol_repin_missing_fix" in text
