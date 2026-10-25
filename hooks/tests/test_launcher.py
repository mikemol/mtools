# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Another repo committing through a bazel-bin launcher is told to install the pin (W1743)."""

import io
import sys
from pathlib import Path

import pytest

from mikemol.hooks import commit_kata, launcher

_BAZEL_OUT = "/var/cache/bazel/execroot/_main/bazel-out/k8-fastbuild/bin/hooks/.venv"
_LINK = "/home/u/github/mtools/bazel-bin/hooks/.venv"
_OWN = "/home/u/github/other/.venv"


def _mtools(tmp_path: Path) -> Path:
    (tmp_path / "hooks").mkdir(parents=True)
    (tmp_path / "hooks" / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    return tmp_path


def test_a_bazel_venv_committing_another_repo_is_noticed_with_the_pin_line(tmp_path: Path) -> None:
    """Both spellings of a bazel venv's prefix are noticed, naming the repo and the spec."""
    other = tmp_path / "other"
    other.mkdir()
    for prefix in (_BAZEL_OUT, _LINK):
        said = launcher.notice(prefix, other, {})
        assert said is not None
        assert "committing other" in said
        assert launcher.SPEC in said


def test_a_bazel_venv_that_carries_the_hooks_wheel_is_not_noticed(tmp_path: Path) -> None:
    """The notice reads the dist-info the venv imports: a vendored wheel is no link farm."""
    other = tmp_path / "other"
    other.mkdir()
    farm = tmp_path / "bazel-bin" / "farm" / ".venv"
    wheel = tmp_path / "bazel-bin" / "wheel" / ".venv"
    (farm / "lib" / "python3.13" / "site-packages" / "mikemol").mkdir(parents=True)
    packages = wheel / "lib" / "python3.13" / "site-packages"
    (packages / "mikemol_hooks-0.1.0+57b9f2a.dist-info").mkdir(parents=True)
    assert launcher.notice(str(farm), other, {}) is not None
    assert launcher.notice(str(wheel), other, {}) is None
    assert launcher.wheel_installed(str(wheel))
    assert not launcher.wheel_installed(str(farm))


def test_the_repos_own_venv_and_the_mtools_tree_are_not_noticed(tmp_path: Path) -> None:
    """An installed pin is the sound path, and mtools's own tree is what the launcher follows."""
    other = tmp_path / "other"
    other.mkdir()
    assert launcher.notice(_OWN, other, {}) is None
    assert launcher.notice(_BAZEL_OUT, _mtools(tmp_path / "t"), {}) is None


def test_a_bazel_test_is_not_noticed_whatever_its_prefix(tmp_path: Path) -> None:
    """A test run under bazel sets TEST_SRCDIR; its commits are the gate's, not a user's."""
    other = tmp_path / "other"
    other.mkdir()
    assert launcher.notice(_BAZEL_OUT, other, {launcher.TEST_ENV: "/x"}) is None


def test_announce_writes_the_notice_and_a_clean_launcher_writes_nothing(tmp_path: Path) -> None:
    """The line goes to the stream given, newline-terminated; no notice, no write."""
    other = tmp_path / "other"
    other.mkdir()
    out = io.StringIO()
    launcher.announce(_LINK, other, {}, out)
    assert out.getvalue().startswith("mikemol-commit: NOTICE")
    assert out.getvalue().endswith("\n")
    quiet = io.StringIO()
    launcher.announce(_OWN, other, {}, quiet)
    assert not quiet.getvalue()


def test_resolving_a_repository_notices_the_launcher_on_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The commit's own entry runs the notice for each repository it resolves."""
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setattr(sys, "prefix", _LINK)
    assert commit_kata.resolve_root(str(other), {}) == other.resolve()
    assert "NOTICE, committing other" in capsys.readouterr().err
    monkeypatch.setattr(sys, "prefix", _OWN)
    commit_kata.resolve_root(str(other), {})
    assert not capsys.readouterr().err
