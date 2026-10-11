# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-repin --revendor`: the plan, the dry run, the apply, and the refusals.

W991. ⚑ THE APPLIED RUN IS THE POSITIVE CONTROL: the dry run that builds nothing, a repo that
vendors nothing and a refused apply only mean something beside a run that does call the apply with
the right repo, commit, mtools and writer. The sequence itself is tested in test_revendor_apply.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import repin_cli, revendor, revendor_apply, revendor_cli

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

SHA = "31421775e3e7e140dbd1b97adef99185f6d82cd9"
OLD = "a61069e"
DIGEST = "ab" * 32
FAILED = revendor_cli.EXIT_FAILED


def _repo(root: Path, *, vendors: bool = True) -> Path:
    repo = root / "luthen"
    repo.mkdir()
    sources = "".join(
        f'mikemol-{d} = {{ path = "vendor/wheels/{revendor.wheel_name(d, OLD)}" }}\n'
        for d in revendor.DISTS
    )
    (repo / "pyproject.toml").write_text(sources if vendors else "x = 1\n", encoding="utf-8")
    (root / "mtools").mkdir()
    return repo


def _runner(_argv: Sequence[str], _cwd: Path) -> tuple[int, str]:
    return 0, ""


def _args(repo: Path, mtools: Path, *extra: str) -> list[str]:
    return ["--revendor", "--sha", SHA, "--root", str(repo), "--mtools", str(mtools), *extra]


class _Apply:
    """A stand-in for the apply sequence that records what it was asked to move."""

    def __init__(self, failure: str | None = None) -> None:
        self.targets: list[revendor_apply.Target] = []
        self.failure = failure

    def __call__(self, _run: object, target: revendor_apply.Target) -> str | None:
        self.targets.append(target)
        return self.failure


def _sums(_target: revendor_apply.Target) -> dict[str, str]:
    return dict.fromkeys(revendor.DISTS, DIGEST)


def _install(monkeypatch: pytest.MonkeyPatch, apply: _Apply) -> None:
    monkeypatch.setattr(revendor_apply, "apply", apply)
    monkeypatch.setattr(revendor_apply, "checksums", _sums)


def test_write_applies_at_the_repo_with_its_own_writer_and_prints_the_sums(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: the apply gets this repo, this commit, this mtools and the repo's own writer."""
    repo = _repo(tmp_path)
    apply = _Apply()
    _install(monkeypatch, apply)
    assert repin_cli.main(_args(repo, tmp_path / "mtools", "--write"), _runner) == 0
    target = apply.targets[0]
    assert (target.repo, target.sha, target.mtools) == (repo, SHA, tmp_path / "mtools")
    assert target.writer == repo / ".venv" / "bin" / "mikemol-paths-forward"
    said = capsys.readouterr().out
    assert f"SHA256 hooks {DIGEST}" in said
    assert f"SHA256 pathsforward {DIGEST}" in said
    assert "APPLIED luthen at 3142177" in said


def test_a_dry_run_prints_the_plan_and_builds_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without --write the plan names the new sha and the old pin and the apply is never called."""
    repo = _repo(tmp_path)
    apply = _Apply()
    _install(monkeypatch, apply)
    assert repin_cli.main(_args(repo, tmp_path / "mtools"), _runner) == 0
    said = capsys.readouterr().out
    assert apply.targets == []
    assert "PLAN" in said
    assert "3142177" in said
    assert OLD in said


def test_a_refused_apply_is_exit_one_and_says_why(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The refusal reason is printed and no checksum line follows it."""
    repo = _repo(tmp_path)
    _install(monkeypatch, _Apply("the new writer reads the queue differently"))
    assert repin_cli.main(_args(repo, tmp_path / "mtools", "--write"), _runner) == FAILED
    said = capsys.readouterr().out
    assert "REFUSED the new writer reads the queue differently" in said
    assert "SHA256" not in said


def test_a_repo_that_vendors_nothing_is_refused_before_any_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Handing wheels to a repo that references none would leave them unused."""
    repo = _repo(tmp_path, vendors=False)
    apply = _Apply()
    _install(monkeypatch, apply)
    args = _args(repo, tmp_path / "mtools", "--write")
    assert repin_cli.main(args, _runner) == repin_cli.EXIT_USAGE
    assert "vendors no hooks or pathsforward wheel" in capsys.readouterr().err
    assert apply.targets == []


def test_usage_refusals_exit_two_and_apply_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing or short sha and a missing mtools checkout are refused."""
    repo = _repo(tmp_path)
    apply = _Apply()
    _install(monkeypatch, apply)
    mtools = str(tmp_path / "mtools")
    refused = [
        ["--revendor", "--root", str(repo), "--mtools", mtools, "--write"],
        ["--revendor", "--sha", "3142177", "--root", str(repo), "--mtools", mtools],
        ["--revendor", "--sha", SHA, "--root", str(repo), "--mtools", str(tmp_path / "nope")],
    ]
    codes = [repin_cli.main(args, _runner) for args in refused]
    assert codes == [repin_cli.EXIT_USAGE] * len(refused)
    assert apply.targets == []
