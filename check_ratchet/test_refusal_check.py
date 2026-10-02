# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""refusal_check with a fake ratchet: a refusal by name passes, any toleration is named."""

from __future__ import annotations

from typing import TYPE_CHECKING

import refusal_check

if TYPE_CHECKING:
    from pathlib import Path


def _dist(root: Path) -> Path:
    dist = root / "pkg"
    (dist / "src" / "mikemol" / "pkg").mkdir(parents=True)
    (dist / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
    (dist / "build" / "lib").mkdir(parents=True)
    (dist / "build" / "lib" / "stale.py").write_text("x = 1\n", encoding="utf-8")
    return dist


def _ratchet(status: int, seen: list[Path]) -> refusal_check.Ratchet:
    def run(copy: Path) -> tuple[int, str]:
        seen.append(copy)
        planted = (copy / "src" / "mikemol" / "pkg" / "_probe.py").is_file()
        stale = (copy / "build").exists()
        return status, f"planted={planted} stale={stale} + src/mikemol/pkg/_probe.py:7"

    return run


def test_a_refusal_naming_the_plant_passes(tmp_path: Path) -> None:
    """The ratchet exits nonzero and names the planted module: the baseline refuses."""
    seen: list[Path] = []
    assert refusal_check.check(_dist(tmp_path), _ratchet(1, seen)) == []
    [copy] = seen
    assert copy.name == "pkg"


def test_a_tolerated_plant_is_named(tmp_path: Path) -> None:
    """Exit 0 over a planted finding means the baseline refuses nothing; that is the finding."""
    [finding] = refusal_check.check(_dist(tmp_path), _ratchet(0, []))
    assert "TOLERATED a planted finding (rc=0)" in finding


def test_a_refusal_that_does_not_name_the_plant_is_named(tmp_path: Path) -> None:
    """A nonzero exit for some OTHER finding (build residue, say) is not a refusal of the plant.

    The original arm's F-arm measured exactly this: a copy carrying stale build/ refused, by
    name, for files that were not the distribution, so a refusal is only one when it names the
    plant.
    """

    def run(copy: Path) -> tuple[int, str]:
        del copy
        return 1, "+ src/mikemol/pkg/other.py:3"

    [finding] = refusal_check.check(_dist(tmp_path), run)
    assert "TOLERATED a planted finding (rc=1)" in finding


def test_the_plant_lands_in_a_copy_without_build_residue(tmp_path: Path) -> None:
    """The plant is in the copy, build/ is not copied, and the real tree is untouched."""
    dist = _dist(tmp_path)
    outputs: list[str] = []

    def run(copy: Path) -> tuple[int, str]:
        status, output = _ratchet(1, [])(copy)
        outputs.append(output)
        return status, output

    refusal_check.check(dist, run)
    assert outputs == ["planted=True stale=False + src/mikemol/pkg/_probe.py:7"]
    assert not (dist / "src" / "mikemol" / "pkg" / "_probe.py").exists()


def test_a_dist_without_one_package_is_named(tmp_path: Path) -> None:
    """No single package under src/mikemol means nothing to plant in; that is reported, not passed."""
    dist = tmp_path / "bare"
    (dist / "src" / "mikemol").mkdir(parents=True)
    [finding] = refusal_check.check(dist, _ratchet(1, []))
    assert "expected one package under src/mikemol, found 0" in finding


def test_main_reports_exit_codes(tmp_path: Path) -> None:
    """1 with no pyproject.toml, 2 on a usage error (no ratchet is run)."""
    missing = str(tmp_path / "absent.toml")
    codes = [refusal_check.main(["r", "f", missing]), refusal_check.main([])]
    assert codes == [1, 2]
