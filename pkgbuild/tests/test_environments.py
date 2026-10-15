# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that `environments` makes the two GitHub environments, dry by default (W1217).

⚑ `gh` IS A FAKE that records each call and the body file it was given, so no test reaches GitHub.
⚑ THE CONTROLS: the dry run makes no call at all, a failed sign-in stops before any PUT, a failed
PUT is exit 1 and says FAILED, and an absent `gh` is a status and a message, not a crash.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.pkgbuild import environments

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pytest

_USAGE = 2
_USER = "4242"


class _Gh:
    """A fake `gh`: answers `api user` with an id and records every PUT with its body."""

    def __init__(self, *, signed_in: bool = True, put_status: int = 0) -> None:
        self.signed_in = signed_in
        self.put_status = put_status
        self.calls: list[list[str]] = []
        self.bodies: dict[str, dict[str, object]] = {}

    def __call__(self, argv: Sequence[str]) -> tuple[int, str]:
        self.calls.append(list(argv))
        if argv[:2] == ["api", "user"]:
            return (0, _USER) if self.signed_in else (1, "not logged in")
        path = argv[argv.index("PUT") + 1]
        source = Path(argv[argv.index("--input") + 1])
        self.bodies[path] = cast("dict[str, object]", json.loads(source.read_text("utf-8")))
        return self.put_status, "{}"


def test_a_dry_run_lists_both_requests_and_calls_nothing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Without `--write`: two `would PUT` lines, no call to gh."""
    fake = _Gh()
    assert environments.run(["mikemol/mtools"], fake) == 0
    out = capsys.readouterr().out.splitlines()
    assert [line.split()[2] for line in out] == [
        "repos/mikemol/mtools/environments/testpypi",
        "repos/mikemol/mtools/environments/pypi",
    ]
    assert fake.calls == []


def test_write_makes_testpypi_with_no_rules_and_pypi_needing_the_signed_in_user(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The user's id comes from gh; testpypi gets an empty body, pypi that user to approve."""
    fake = _Gh()
    assert environments.run(["mikemol/mtools", "--write"], fake) == 0
    assert fake.bodies["repos/mikemol/mtools/environments/testpypi"] == {}
    assert fake.bodies["repos/mikemol/mtools/environments/pypi"] == {
        "reviewers": [{"type": "User", "id": int(_USER)}]
    }
    assert capsys.readouterr().out.count("ok PUT") == len(fake.bodies)


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    for folder in ("alpha", "beta", "gamma"):
        (root / folder).mkdir(parents=True)
        (root / folder / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    return root


def test_a_directory_with_a_two_org_layout_makes_environments_in_each_distinct_repo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W1222: alpha and beta moved to separate repos, gamma keeps the default: three repos, once."""
    layout = tmp_path / "repos.toml"
    layout.write_text(
        '[dist.alpha]\nowner = "org-one"\nrepo = "alpha"\n'
        '[dist.beta]\nowner = "org-two"\nrepo = "beta"\n',
        encoding="utf-8",
    )
    fake = _Gh()
    assert environments.run([str(_tree(tmp_path)), "--repos", str(layout), "--write"], fake) == 0
    assert sorted(fake.bodies) == sorted(
        f"repos/{slug}/environments/{name}"
        for slug in ("org-one/alpha", "org-two/beta", "mikemol/mtools")
        for name in ("testpypi", "pypi")
    )
    assert capsys.readouterr().out.count("ok PUT") == len(fake.bodies)


def test_a_directory_without_a_layout_is_one_repository(tmp_path: Path) -> None:
    """The default layout puts every dist in mikemol/mtools: one pair of environments."""
    fake = _Gh()
    assert environments.run([str(_tree(tmp_path)), "--write"], fake) == 0
    assert len(fake.bodies) == _USAGE


def test_a_bad_layout_a_dangling_flag_or_an_empty_directory_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The controls: nothing is called when the repositories cannot be named."""
    fake = _Gh()
    bad = tmp_path / "repos.toml"
    bad.write_text("[default]\nowner = 'x'\n", encoding="utf-8")
    root = _tree(tmp_path)
    assert environments.run([str(root), "--repos", str(bad), "--write"], fake) == _USAGE
    assert environments.run([str(root), "--repos"], fake) == _USAGE
    empty = tmp_path / "empty"
    empty.mkdir()
    assert environments.run([str(empty), "--write"], fake) == _USAGE
    assert fake.calls == []
    assert "no dist found" in capsys.readouterr().err


def test_a_failed_sign_in_stops_before_any_put(capsys: pytest.CaptureFixture[str]) -> None:
    """The control: no id, no PUT, exit 1, and the reason on standard error."""
    fake = _Gh(signed_in=False)
    assert environments.run(["mikemol/mtools", "--write"], fake) == 1
    assert fake.bodies == {}
    assert "not logged in" in capsys.readouterr().err


def test_a_failed_put_is_exit_one_and_says_failed(capsys: pytest.CaptureFixture[str]) -> None:
    """GitHub refusing a request is reported per request and fails the run."""
    fake = _Gh(put_status=1)
    assert environments.run(["mikemol/mtools", "--write"], fake) == 1
    assert capsys.readouterr().out.count("FAILED PUT") == len(fake.bodies)


def test_a_wrong_repository_or_no_argument_is_a_usage_error() -> None:
    """`OWNER/REPO` must be exactly that shape."""
    assert environments.run([], _Gh()) == _USAGE
    assert environments.run(["mtools"], _Gh()) == _USAGE
    assert environments.run(["a/b/c"], _Gh()) == _USAGE


def test_an_absent_gh_is_a_status_and_a_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With nothing on PATH the runner returns 127 and says why."""
    monkeypatch.setenv("PATH", str(tmp_path))
    status, why = environments.gh(["api", "user"])
    assert status == environments.NOT_FOUND
    assert "not installed" in why
