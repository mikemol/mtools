# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the re-vendor sequence, over a fake git and uv that act on a real directory.

W990. ⚑ THE APPLIED SWAP IS THE POSITIVE CONTROL: the refusals (dirty tree, failed build, a writer
that reads the queue differently, a lock that fails) only mean something beside a run that does
swap, and every refusal is checked to have left the repo exactly as it was.
"""

from __future__ import annotations

import hashlib
import io
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import revendor, revendor_apply
from mikemol.hooks.revendor_apply import Target

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

OLD = "a61069e"
NEW = "3142177"
SHA = "31421775e3e7e140dbd1b97adef99185f6d82cd9"
LIVE_HASH = "v2:1111"
VERSION_LINE = 'version = "0.1.0"\n'
EXIT_FAILED = 3


def _pyproject(short: str) -> str:
    sources = "".join(
        f'mikemol-{d} = {{ path = "vendor/wheels/{revendor.wheel_name(d, short)}" }}\n'
        for d in revendor.DISTS
    )
    return f'name = "luthen"\n{sources}'


def _archive(argv: Sequence[str], archived: str) -> tuple[int, str]:
    out = next(a for a in argv if a.startswith("--output=")).removeprefix("--output=")
    with tarfile.open(out, "w") as tar:
        for dist in revendor.KNOWN:
            data = archived.encode()
            info = tarfile.TarInfo(f"{dist}/pyproject.toml")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return 0, ""


def _build(argv: Sequence[str], cwd: Path) -> tuple[int, str]:
    text = (cwd / "pyproject.toml").read_text(encoding="utf-8")
    version = text.split('version = "')[1].split('"')[0]
    outdir = Path(argv[argv.index("--out-dir") + 1])
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"mikemol_{cwd.name}-{version}-py3-none-any.whl").write_text(text, "utf-8")
    return 0, ""


def _venv(argv: Sequence[str]) -> tuple[int, str]:
    (Path(argv[-1]) / "bin").mkdir(parents=True)
    return 0, ""


def _remove(argv: Sequence[str], cwd: Path) -> tuple[int, str]:
    (cwd / argv[-1]).unlink()
    return 0, ""


class _World:
    """A fake git and uv: each does to the disk what the real one does, and records the call."""

    def __init__(
        self,
        *,
        status: str = "",
        new_hash: str = LIVE_HASH,
        live_hash: str = LIVE_HASH,
        failing: frozenset[str] = frozenset(),
        archived: str = VERSION_LINE,
    ) -> None:
        self.calls: list[list[str]] = []
        self.status = status
        self.new_hash = new_hash
        self.live_hash = live_hash
        self.failing = failing
        self.archived = archived

    def __call__(self, argv: Sequence[str], cwd: Path) -> tuple[int, str]:
        self.calls.append(list(argv))
        bare = argv[2:] if argv[0] == "env" else argv
        key = " ".join(bare[:2])
        if key in self.failing:
            return EXIT_FAILED, "it broke"
        if argv[-1] == "--hash":
            return 0, (self.new_hash if "venv" in argv[0] else self.live_hash) + "\n"
        return self._act(key, argv, cwd)

    def _act(self, key: str, argv: Sequence[str], cwd: Path) -> tuple[int, str]:
        table: dict[str, Callable[[], tuple[int, str]]] = {
            "git status": lambda: (0, self.status),
            "git -C": lambda: _archive(argv, self.archived),
            "git rm": lambda: _remove(argv, cwd),
            "uv build": lambda: _build(argv, cwd),
            "uv venv": lambda: _venv(argv),
        }
        return table[key]() if key in table else (0, "")


def _repo(tmp_path: Path) -> Target:
    repo = tmp_path / "luthen"
    (repo / "vendor" / "wheels").mkdir(parents=True)
    (repo / ".claude").mkdir()
    (repo / ".claude" / "paths-forward.json").write_text("{}\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text(_pyproject(OLD), encoding="utf-8")
    for dist in revendor.DISTS:
        old = repo / "vendor" / "wheels" / revendor.wheel_name(dist, OLD)
        old.write_text("old wheel", encoding="utf-8")
    return Target(repo, tmp_path / "mtools", SHA, Path("/live/mikemol-paths-forward"))


def _untouched(target: Target) -> bool:
    wheels = sorted(p.name for p in (target.repo / "vendor" / "wheels").iterdir())
    olds = sorted(revendor.wheel_name(d, OLD) for d in revendor.DISTS)
    text = (target.repo / "pyproject.toml").read_text(encoding="utf-8")
    return wheels == olds and text == _pyproject(OLD)


def test_apply_builds_checks_and_swaps_both_dists(tmp_path: Path) -> None:
    """The control: new wheels carry the local version, old ones go, pins move, lock then sync."""
    target = _repo(tmp_path)
    world = _World()
    assert revendor_apply.apply(world, target) is None
    wheels = target.repo / "vendor" / "wheels"
    assert sorted(p.name for p in wheels.iterdir()) == sorted(
        revendor.wheel_name(d, NEW) for d in revendor.DISTS
    )
    built = (wheels / revendor.wheel_name("hooks", NEW)).read_text(encoding="utf-8")
    assert f'version = "0.1.0+g{NEW}"' in built
    assert revendor.pinned_shorts((target.repo / "pyproject.toml").read_text("utf-8")) == {NEW}
    steps = [" ".join(c[:2]) for c in world.calls]
    assert steps.index("uv lock") < steps.index("uv sync")
    assert steps.index("uv pip") < steps.index("git rm") < steps.index("uv lock")


def test_the_checksums_are_those_of_the_wheels_in_the_tree(tmp_path: Path) -> None:
    """The record for vendor/wheels/README.md hashes what is on disk, not what was built."""
    target = _repo(tmp_path)
    assert revendor_apply.apply(_World(), target) is None
    sums = revendor_apply.checksums(target)
    path = target.repo / "vendor" / "wheels" / revendor.wheel_name("pathsforward", NEW)
    assert sums["pathsforward"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert set(sums) == set(revendor.DISTS)


def _repo_with_the_fence(tmp_path: Path) -> Target:
    """Make the repo of `_repo`, and add the fence wheel and its source line beside the pair.

    Returns:
        the target, whose dists include the fence.

    """
    base = _repo(tmp_path)
    fence = f'mikemol-fence = {{ path = "vendor/wheels/{revendor.wheel_name("fence", OLD)}" }}\n'
    project = base.repo / "pyproject.toml"
    project.write_text(project.read_text(encoding="utf-8") + fence, encoding="utf-8")
    (base.repo / "vendor" / "wheels" / revendor.wheel_name("fence", OLD)).write_text(
        "old fence wheel", encoding="utf-8"
    )
    return Target(base.repo, base.mtools, SHA, base.writer, (*revendor.DISTS, "fence"))


def test_a_vendored_fence_is_rebuilt_swapped_and_checksummed_with_the_pair(
    tmp_path: Path,
) -> None:
    """mtools:W1031: the fence wheel is built at the commit, the old one goes, the pin moves."""
    target = _repo_with_the_fence(tmp_path)
    assert revendor_apply.apply(_World(), target) is None
    wheels = target.repo / "vendor" / "wheels"
    assert sorted(p.name for p in wheels.iterdir()) == sorted(
        revendor.wheel_name(d, NEW) for d in target.dists
    )
    text = (target.repo / "pyproject.toml").read_text(encoding="utf-8")
    assert revendor.pinned_shorts(text) == {NEW}
    assert set(revendor_apply.checksums(target)) == {"hooks", "pathsforward", "fence"}


def test_a_dirty_tree_is_refused_before_anything_is_built(tmp_path: Path) -> None:
    """Uncommitted changes to the files a re-vendor writes stop it before git archive runs."""
    target = _repo(tmp_path)
    world = _World(status=" M uv.lock\n")
    assert "uncommitted" in (revendor_apply.apply(world, target) or "")
    assert not any("archive" in c for c in world.calls)
    assert _untouched(target)


def test_a_writer_that_reads_the_queue_differently_stops_the_swap(tmp_path: Path) -> None:
    """Both hashes are named and the repo is exactly as it was."""
    target = _repo(tmp_path)
    why = revendor_apply.apply(_World(new_hash="v2:2222"), target) or ""
    assert LIVE_HASH in why
    assert "v2:2222" in why
    assert _untouched(target)


def test_a_live_writer_that_gives_no_hash_stops_the_swap(tmp_path: Path) -> None:
    """An empty live hash can equal nothing: a writer that fails is not a match."""
    target = _repo(tmp_path)
    why = revendor_apply.apply(_World(live_hash="", new_hash=""), target)
    assert why is not None
    assert "reads the queue differently" in why
    assert _untouched(target)


def test_a_failed_build_names_the_dist_and_leaves_the_repo(tmp_path: Path) -> None:
    """A failing build says which exit and writes nothing into the repo."""
    target = _repo(tmp_path)
    why = revendor_apply.apply(_World(failing=frozenset({"uv build"})), target) or ""
    assert "uv build hooks failed (exit 3)" in why
    assert _untouched(target)


def test_an_archived_pyproject_without_the_version_is_refused(tmp_path: Path) -> None:
    """No 0.1.0 line means a refusal naming the dist, not a wheel with the wrong version."""
    target = _repo(tmp_path)
    why = revendor_apply.apply(_World(archived='version = "0.2.0"\n'), target) or ""
    assert "hooks/pyproject.toml has no version 0.1.0" in why
    assert _untouched(target)


def test_a_failed_lock_is_named(tmp_path: Path) -> None:
    """Past the swap the failure is reported by step: the lock, not a generic error."""
    target = _repo(tmp_path)
    why = revendor_apply.apply(_World(failing=frozenset({"uv lock"})), target) or ""
    assert "uv lock failed (exit 3)" in why
