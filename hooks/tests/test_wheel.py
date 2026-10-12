# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-wheel`, over a fake git and uv that act on a real directory.

W992. ⚑ THE BUILT PAIR IS THE POSITIVE CONTROL: the usage refusals, the missing dist and the failed
build only mean something beside a run that does print one JSON line per wheel in the order named.
The determinism itself was measured against the real uv (two builds of one commit, byte-identical
wheels, from a git checkout and from an unpacked archive); here the inputs that make it so are
pinned: the fixed epoch on the tree and in the environment, and the version edit in the copy only.
"""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import revendor, wheel

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pytest

SHA = "31421775e3e7e140dbd1b97adef99185f6d82cd9"
SHORT = "3142177"
DISTS = ["atomicwrite", "importdag"]
BASE = 'version = "0.1.0"\n'
EXIT_BUILD = 3


class _Tools:
    """A fake git and uv: archive writes a tar, build writes a wheel and records what it saw."""

    def __init__(self, *, fail_build: bool = False) -> None:
        self.calls: list[list[str]] = []
        self.mtimes: list[float] = []
        self.fail_build = fail_build

    def __call__(self, argv: Sequence[str], cwd: Path) -> tuple[int, str]:
        self.calls.append(list(argv))
        if argv[0] == "env":
            return self._build(argv, cwd)
        out = next(a for a in argv if a.startswith("--output=")).removeprefix("--output=")
        with tarfile.open(out, "w") as tar:
            for dist in argv[argv.index(SHA) + 1 :]:
                info = tarfile.TarInfo(f"{dist}/pyproject.toml")
                info.size = len(BASE)
                tar.addfile(info, io.BytesIO(BASE.encode()))
        return 0, ""

    def _build(self, argv: Sequence[str], cwd: Path) -> tuple[int, str]:
        if self.fail_build:
            return EXIT_BUILD, "uv exploded"
        self.mtimes.append((cwd / "pyproject.toml").stat().st_mtime)
        text = (cwd / "pyproject.toml").read_text(encoding="utf-8")
        version = text.split('version = "')[1].split('"')[0]
        outdir = Path(argv[argv.index("--out-dir") + 1])
        if not outdir.exists():
            # uv build leaves a `.gitignore` of `*` in an output directory it creates (W1042)
            outdir.mkdir(parents=True)
            (outdir / ".gitignore").write_text("*\n", encoding="utf-8")
        (outdir / f"mikemol_{cwd.name}-{version}-py3-none-any.whl").write_text(text, "utf-8")
        return 0, ""


def _tree(root: Path) -> Path:
    for dist in DISTS:
        (root / dist).mkdir(parents=True)
        (root / dist / "pyproject.toml").write_text(BASE, encoding="utf-8")
    return root


def _args(out: Path, *source: str, sha: str = SHA) -> list[str]:
    return [*DISTS, "--sha", sha, "--out", str(out), *source]


def _line(out: Path, dist: str) -> str:
    name = revendor.wheel_name(dist, SHORT)
    digest = hashlib.sha256((out / name).read_bytes()).hexdigest()
    record: dict[str, str] = {"dist": dist, "wheel": name, "sha256": digest}
    return json.dumps(record)


def test_a_checkout_builds_every_dist_and_prints_a_json_line_each(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: one record per dist in the order named, the sha256 of the file written."""
    out = tmp_path / "out"
    assert wheel.main(_args(out, "--mtools", str(tmp_path)), _Tools()) == 0
    assert capsys.readouterr().out.splitlines() == [_line(out, d) for d in DISTS]
    built = (out / revendor.wheel_name("atomicwrite", SHORT)).read_text(encoding="utf-8")
    assert f'version = "0.1.0+g{SHORT}"' in built


def test_the_build_runs_at_the_fixed_epoch_on_a_tree_stamped_with_it(tmp_path: Path) -> None:
    """The inputs that make the bytes depend on neither the clock nor the archive."""
    tools = _Tools()
    assert wheel.main(_args(tmp_path / "out", "--mtools", str(tmp_path)), tools) == 0
    builds = [c for c in tools.calls if c[0] == "env"]
    assert all(f"SOURCE_DATE_EPOCH={wheel.EPOCH}" in c for c in builds)
    assert tools.mtimes == [float(wheel.EPOCH)] * len(DISTS)


def test_an_unpacked_tree_is_built_without_git_and_never_edited(tmp_path: Path) -> None:
    """--src copies the dists, so the caller's tree keeps its version and no git runs."""
    tree = _tree(tmp_path / "tree")
    tools = _Tools()
    assert wheel.main(_args(tmp_path / "out", "--src", str(tree)), tools) == 0
    assert (tree / "importdag" / "pyproject.toml").read_text(encoding="utf-8") == BASE
    assert not any(c[0] == "git" for c in tools.calls)


def test_a_dist_missing_from_the_tree_is_a_failure_naming_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 1 and the dist named, with nothing built."""
    tree = _tree(tmp_path / "tree")
    (tree / "importdag" / "pyproject.toml").unlink()
    assert wheel.main(_args(tmp_path / "out", "--src", str(tree)), _Tools()) == 1
    assert "importdag/pyproject.toml is not in" in capsys.readouterr().err


def test_a_failed_build_is_exit_one_with_the_dist_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The failure line names the step, the dist and the exit, and prints no record."""
    code = wheel.main(_args(tmp_path / "out", "--mtools", str(tmp_path)), _Tools(fail_build=True))
    captured = capsys.readouterr()
    assert code == 1
    assert "uv build atomicwrite failed (exit 3)" in captured.err
    assert not captured.out


def test_usage_refusals_exit_two_and_build_nothing(tmp_path: Path) -> None:
    """No dists, no out, a short sha, and neither or both sources are all refused."""
    out = str(tmp_path / "out")
    tools = _Tools()
    refused = [
        ["--sha", SHA, "--out", out, "--mtools", "m"],
        [*DISTS, "--sha", SHA, "--mtools", "m"],
        [*DISTS, "--sha", SHORT, "--out", out, "--mtools", "m"],
        [*DISTS, "--sha", SHA, "--out", out],
        [*DISTS, "--sha", SHA, "--out", out, "--mtools", "m", "--src", "s"],
        [*DISTS, "--sha", SHA, "--out", out, "--bogus"],
    ]
    assert [wheel.main(args, tools) for args in refused] == [wheel.EXIT_USAGE] * len(refused)
    assert tools.calls == []
    assert not Path(out).exists()


def test_describe_leaves_an_empty_record_for_a_wheel_that_is_not_there(tmp_path: Path) -> None:
    """A missing wheel is an empty record, which main turns into a failure."""
    (tmp_path / revendor.wheel_name("atomicwrite", SHORT)).write_text("x", encoding="utf-8")
    records = wheel.describe(tmp_path, DISTS, SHORT)
    assert records[0]["dist"] == "atomicwrite"
    assert records[1] == {}


def test_a_relative_out_and_mtools_reach_the_build_as_absolute_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every step runs in a temp directory, so a relative `--out` must be made absolute first.

    luthen-observability:W843: `--out vendor/wheels` left the wheel under the temp tree and the
    tool reported it missing.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m").mkdir()
    tools = _Tools()
    assert wheel.main([*DISTS, "--sha", SHA, "--out", "out", "--mtools", "m"], tools) == 0
    builds = [c for c in tools.calls if c[0] == "env"]
    staged = {Path(c[c.index("--out-dir") + 1]) for c in builds}
    assert all(path.is_absolute() for path in staged)
    assert (tmp_path / "out" / revendor.wheel_name("atomicwrite", SHORT)).is_file()
    archive = next(c for c in tools.calls if c[0] == "git")
    assert archive[2] == str(tmp_path / "m")


def test_the_caller_gets_the_wheels_and_never_uvs_gitignore(tmp_path: Path) -> None:
    """W1042: the build runs in a temp directory, so no `.gitignore` of `*` reaches the output."""
    out = tmp_path / "vendor" / "wheels"
    assert wheel.main(_args(out, "--mtools", str(tmp_path)), _Tools()) == 0
    names = sorted(path.name for path in out.iterdir())
    assert names == sorted(revendor.wheel_name(dist, SHORT) for dist in DISTS)
    assert not (out / ".gitignore").exists()


def test_an_existing_output_directory_keeps_its_own_files(tmp_path: Path) -> None:
    """Publishing adds wheels beside what is there and removes nothing."""
    out = tmp_path / "out"
    out.mkdir()
    (out / "keep.txt").write_text("mine", encoding="utf-8")
    assert wheel.main(_args(out, "--mtools", str(tmp_path)), _Tools()) == 0
    assert (out / "keep.txt").read_text(encoding="utf-8") == "mine"
