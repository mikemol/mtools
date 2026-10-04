# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `zswap_probe`: a planted cgroup tree is sampled in one pass, labelled per field."""

from __future__ import annotations

import errno
import json
from typing import TYPE_CHECKING, cast

from mikemol.memres import zswap_probe

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_SATURATED = ("402632704", "402653184")
_UNSATURATED = ("100000000", "402653184")
_TOLERANCE = 4096 * 64
_RATIO = 4.0
_ZSWAP = 1000
_ZSWAPPED = 4000
_SURVIVORS = 3


def _planted(tmp_path: Path, rel: str) -> tuple[Path, Path, Path]:
    """Plant a cgroup root, a `/proc/self/cgroup` naming `rel`, and the leaf directory.

    Returns:
        `(root, cgroup_file, leaf)`.

    """
    root = tmp_path / "cgroup"
    leaf = root / rel.lstrip("/")
    leaf.mkdir(parents=True)
    cgroup_file = tmp_path / "self-cgroup"
    cgroup_file.write_text(f"0::{rel}\n", encoding="utf-8")
    return root, cgroup_file, leaf


def _fill(directory: Path, **files: str) -> None:
    """Plant cgroup files, `memory_current=` standing for `memory.current`."""
    for name, text in files.items():
        (directory / name.replace("_", ".")).write_text(f"{text}\n", encoding="utf-8")


def test_cg_dir_joins_the_path_after_the_last_double_colon_under_the_root(
    tmp_path: Path,
) -> None:
    """The cgroup directory is the root plus the unified-hierarchy path, leading slash dropped."""
    cgroup_file = tmp_path / "cg"
    cgroup_file.write_text("0::/user.slice/job.service\n", encoding="utf-8")
    root = tmp_path / "root"
    assert zswap_probe.cg_dir(cgroup_file, root) == root / "user.slice" / "job.service"


def test_read_gives_the_value_or_a_named_reason_never_a_zero(tmp_path: Path) -> None:
    """A file reads stripped; an absent one and an unreadable one say why they have no value."""
    _fill(tmp_path, memory_current="  12345  ")
    (tmp_path / "memory.peak").mkdir()
    assert zswap_probe.read(tmp_path, "memory.current") == "12345"
    assert zswap_probe.read(tmp_path, "memory.max") == {"unavailable": "absent"}
    assert zswap_probe.read(tmp_path, "memory.peak") == {
        "unavailable": f"unreadable:{errno.EISDIR}",
    }


def test_stat_keys_picks_integers_and_names_what_is_missing(tmp_path: Path) -> None:
    """Each key is an int when present, `key-absent` when not, and the file's reason if no file."""
    keys = ("zswap", "zswapped", "nope")
    assert zswap_probe.stat_keys(tmp_path, keys) == {key: {"unavailable": "absent"} for key in keys}
    (tmp_path / "memory.stat").write_text(
        f"anon 5\nzswap {_ZSWAP}\nzswapped {_ZSWAPPED}\nlonely\n",
        encoding="utf-8",
    )
    assert zswap_probe.stat_keys(tmp_path, keys) == {
        "zswap": _ZSWAP,
        "zswapped": _ZSWAPPED,
        "nope": {"unavailable": "key-absent"},
    }


def test_zswap_bound_finds_the_nearest_ancestor_that_can_refuse_a_store(tmp_path: Path) -> None:
    """A parent's bound binds a child whose own file reads `max`; levels run leaf to root."""
    root, _, leaf = _planted(tmp_path, "/a/b")
    _fill(leaf, memory_zswap_max="max", memory_zswap_current="7")
    _fill(leaf.parent, memory_zswap_max="500")
    found = zswap_probe.zswap_bound(leaf, root)
    assert found["effective_bound_at"] == str(leaf.parent)
    assert found["levels"] == [
        {"cgroup": str(leaf), "zswap_max": "max", "zswap_current": "7"},
        {
            "cgroup": str(leaf.parent),
            "zswap_max": "500",
            "zswap_current": {"unavailable": "absent"},
        },
        {
            "cgroup": str(root),
            "zswap_max": {"unavailable": "absent"},
            "zswap_current": {"unavailable": "absent"},
        },
    ]


def test_zswap_bound_with_no_bound_anywhere_is_unbounded_to_the_root(tmp_path: Path) -> None:
    """Every level reading `max` leaves the pool unbounded."""
    root, _, leaf = _planted(tmp_path, "/a")
    _fill(leaf, memory_zswap_max="max")
    assert zswap_probe.zswap_bound(leaf, root)["effective_bound_at"] == "unbounded-to-root"


def test_zswap_bound_stops_at_the_filesystem_root_for_a_leaf_outside_the_given_root(
    tmp_path: Path,
) -> None:
    """A leaf not under `root` ends at `/` instead of walking forever."""
    leaf = tmp_path / "elsewhere"
    leaf.mkdir()
    found = zswap_probe.zswap_bound(leaf, tmp_path / "unrelated-root")
    levels = cast("list[dict[str, object]]", found["levels"])
    assert levels[0]["cgroup"] == str(leaf)
    assert levels[-1]["cgroup"] == "/"


def test_pinned_separates_a_saturated_pair_from_an_unsaturated_one() -> None:
    """A charge within the tolerance of its ceiling is pinned; far under it is not."""
    assert zswap_probe.pinned(*_SATURATED)
    assert not zswap_probe.pinned(*_UNSATURATED)
    assert not zswap_probe.pinned("0", "0")


def test_pinned_honours_its_tolerance_and_sign_knobs() -> None:
    """The gap is `max - current`; a wider tolerance admits more, a flipped sign inverts it."""
    assert zswap_probe.pinned(*_UNSATURATED, tol_abs=10**9)
    assert not zswap_probe.pinned(*_SATURATED, tol_abs=0, tol_rel=10**9)
    assert not zswap_probe.pinned(*_UNSATURATED)
    assert zswap_probe.pinned(*_UNSATURATED, flip=True)
    assert zswap_probe.pinned("500", "400", flip=True)
    assert zswap_probe.pinned("0", str(_TOLERANCE))
    assert not zswap_probe.pinned("0", str(_TOLERANCE + 1 + 100 * _TOLERANCE))


def test_sample_reads_one_unbounded_pinned_cgroup_and_labels_every_field(tmp_path: Path) -> None:
    """The reading carries counters, ratio, pinned bit, conditions, hierarchy and validity."""
    root, cgroup_file, leaf = _planted(tmp_path, "/a/job.service")
    _fill(
        leaf,
        memory_current=_SATURATED[0],
        memory_peak="999",
        memory_max=_SATURATED[1],
        memory_swap_max="max",
        memory_zswap_max="max",
    )
    (leaf / "memory.stat").write_text(
        f"zswap {_ZSWAP}\nzswapped {_ZSWAPPED}\n",
        encoding="utf-8",
    )
    got = zswap_probe.sample(cgroup_file, root)
    assert got["cgroup"] == str(leaf)
    assert got["is_root"] is False
    assert {key: got[key] for key in ("current", "peak", "zswap_max", "memory_max")} == {
        "current": _SATURATED[0],
        "peak": "999",
        "zswap_max": "max",
        "memory_max": _SATURATED[1],
    }
    assert (got["zswap"], got["zswapped"]) == (_ZSWAP, _ZSWAPPED)
    assert got["compression_ratio"] == _RATIO
    assert got["ratio_means"] == "compressibility"
    assert got["pinned_at_ceiling"] is True
    assert got["_conditions"] == {
        "swap_max": "max",
        "own_cgroup": True,
        "cgroup_is_leaf": True,
    }
    assert cast("dict[str, object]", got["hierarchy"])["effective_bound_at"] == "unbounded-to-root"
    assert got["_validity"] == {
        "current": "instantaneous",
        "zswap": "instantaneous",
        "zswapped": "instantaneous",
        "zswap_max": "config",
        "peak": "cumulative-since-cgroup-creation",
        "memory_max": "config",
        "pinned_at_ceiling": "derived",
        "ratio_means": "derived",
    }


def test_sample_says_eviction_churn_when_an_ancestor_binds_the_pool(tmp_path: Path) -> None:
    """The same ratio means eviction churn once any ancestor bounds zswap."""
    root, cgroup_file, leaf = _planted(tmp_path, "/a/job.service")
    _fill(leaf.parent, memory_zswap_max="500")
    (leaf / "memory.stat").write_text(
        f"zswap {_ZSWAP}\nzswapped {_ZSWAPPED}\n",
        encoding="utf-8",
    )
    got = zswap_probe.sample(cgroup_file, root)
    assert got["ratio_means"] == "eviction-churn-under-bound"
    assert got["pinned_at_ceiling"] is None


def test_sample_of_an_unmeasurable_scope_leaf_with_children_omits_the_ratio(
    tmp_path: Path,
) -> None:
    """No stat means no ratio; a `.scope` with a populated child is neither own nor a leaf."""
    root, cgroup_file, leaf = _planted(tmp_path, "/a/cell.scope")
    child = leaf / "child"
    child.mkdir()
    (child / "cgroup.procs").write_text("1\n", encoding="utf-8")
    got = zswap_probe.sample(cgroup_file, root)
    assert "compression_ratio" not in got
    assert "ratio_means" not in got
    assert got["zswap"] == {"unavailable": "absent"}
    assert got["_conditions"] == {
        "swap_max": {"unavailable": "absent"},
        "own_cgroup": False,
        "cgroup_is_leaf": False,
    }


def test_sample_of_the_root_cgroup_says_it_is_the_root(tmp_path: Path) -> None:
    """A cgroup file naming `/` samples the root itself."""
    root = tmp_path / "cgroup"
    root.mkdir()
    cgroup_file = tmp_path / "self-cgroup"
    cgroup_file.write_text("0::/\n", encoding="utf-8")
    got = zswap_probe.sample(cgroup_file, root)
    assert got["is_root"] is True
    assert got["cgroup"] == str(root)


def test_main_prints_one_sample_as_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With no flag the sample of the planted cgroup is printed as indented JSON."""
    root, cgroup_file, leaf = _planted(tmp_path, "/a/job.service")
    _fill(leaf, memory_current="42")
    assert zswap_probe.main([], cgroup_file, root) == 0
    printed = cast("dict[str, object]", json.loads(capsys.readouterr().out))
    assert printed["cgroup"] == str(leaf)
    assert printed["current"] == "42"


def test_main_selftest_passes_with_the_intact_predicate_and_three_caught_mutants(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--selftest` is exit 0, PASS on stdout and silence on stderr."""
    assert zswap_probe.main(["--selftest"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "ZSWAP_PROBE SELFTEST: PASS (1 P-arm, 3 valid mutants caught)\n"
    assert not captured.err


def test_main_selftest_fails_naming_each_mutant_a_deaf_predicate_lets_survive(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A predicate that ignores its knobs separates P but lets all three mutants survive."""

    def deaf(
        cur: str,
        mx: str,
        *,
        tol_rel: int = 0,
        tol_abs: int = 0,
        flip: bool = False,
    ) -> bool:
        del tol_rel, tol_abs, flip
        return int(mx) - int(cur) <= _TOLERANCE

    monkeypatch.setattr(zswap_probe, "pinned", deaf)
    assert zswap_probe.main(["--selftest"]) == 1
    captured = capsys.readouterr()
    assert captured.out == f"ZSWAP_PROBE SELFTEST: FAIL ({_SURVIVORS})\n"
    assert captured.err.splitlines() == [
        "  XX F: mutant 'sign-swapped gap' SURVIVED - the predicate is not reading the gap",
        "  XX F: mutant 'tolerance widened to 1GB' SURVIVED - the predicate is not reading the gap",
        "  XX F: mutant 'tolerance driven to 0' SURVIVED - the predicate is not reading the gap",
    ]
