# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `policy`: the host's values come from a data file, and a gap is named (W878)."""

from __future__ import annotations

from pathlib import Path

import pytest

from mikemol.katas import policy

_FULL = """\
root = "/h"
logs = "/h/logs"
commit_tool = "/m/hooks/bin/mikemol-commit"
pathsforward = "/m/pf"
host_state = "/h/.claude/paths-forward.json"
holder = "github-b3"
nemik = "/n/bin"
templates = "/h/templates"
bazel_version = "8.7.0"
"""


def _file(tmp_path: Path, text: str) -> Path:
    """Write a policy file.

    Returns:
        its path.

    """
    path = tmp_path / "katas.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_file_loads_every_value(tmp_path: Path) -> None:
    """Paths become Paths, the holder and version stay strings."""
    got = policy.load(_file(tmp_path, _FULL))
    assert got.root == Path("/h")
    assert got.commit_tool == Path("/m/hooks/bin/mikemol-commit")
    assert got.holder == "github-b3"
    assert got.bazel_version == "8.7.0"


def test_the_optional_values_default_to_nothing_machine_specific(tmp_path: Path) -> None:
    """No skip list, no standing warnings, no cron job file, the standing waypoint W2."""
    got = policy.load(_file(tmp_path, _FULL))
    assert not got.skip_flush
    assert not got.standing_warnings
    assert got.job_file is None
    assert got.standing_waypoint == "W2"


def test_the_optional_values_are_read_when_given(tmp_path: Path) -> None:
    """A skip list, standing warnings, a job file and a standing waypoint override the defaults."""
    extra = (
        'skip_flush = ["substrate", "paperkit"]\n'
        'standing_warnings = ["no working card"]\n'
        'job_file = "/h/cron.job"\n'
        'standing_waypoint = "W7"\n'
    )
    got = policy.load(_file(tmp_path, _FULL + extra))
    assert got.skip_flush == frozenset({"substrate", "paperkit"})
    assert got.standing_warnings == ("no working card",)
    assert got.job_file == Path("/h/cron.job")
    assert got.standing_waypoint == "W7"


def test_every_missing_required_key_is_named_at_once(tmp_path: Path) -> None:
    """A file with two gaps names both, so the operator fixes it in one pass."""
    text = "\n".join(
        line for line in _FULL.splitlines() if not line.startswith(("holder", "nemik"))
    )
    with pytest.raises(policy.PolicyError, match=r"holder.*nemik|nemik.*holder"):
        policy.load(_file(tmp_path, text))


def test_an_empty_string_is_not_a_value(tmp_path: Path) -> None:
    """A blank holder is the same gap as an absent one, and the key is named."""
    text = _FULL.replace('holder = "github-b3"', 'holder = ""')
    with pytest.raises(policy.PolicyError, match="holder"):
        policy.load(_file(tmp_path, text))


def test_a_skip_list_that_is_not_strings_is_refused(tmp_path: Path) -> None:
    """The list type is checked, naming the key."""
    with pytest.raises(policy.PolicyError, match="skip_flush"):
        policy.load(_file(tmp_path, _FULL + "skip_flush = [1, 2]\n"))


def test_a_missing_file_is_a_policy_error_naming_the_path(tmp_path: Path) -> None:
    """No file is not a traceback."""
    with pytest.raises(policy.PolicyError, match=r"absent\.toml"):
        policy.load(tmp_path / "absent.toml")


def test_a_file_that_is_not_toml_is_a_policy_error(tmp_path: Path) -> None:
    """A syntax error is reported against the file."""
    with pytest.raises(policy.PolicyError, match=r"katas\.toml"):
        policy.load(_file(tmp_path, "root = = ="))


def test_the_default_path_honours_xdg_config_home(tmp_path: Path) -> None:
    """`$XDG_CONFIG_HOME` wins; otherwise the home directory's `.config`."""
    xdg = policy.default_path({"XDG_CONFIG_HOME": "/x"}, tmp_path)
    assert xdg == Path("/x/mikemol/katas.toml")
    assert policy.default_path({}, tmp_path) == tmp_path / ".config" / "mikemol" / "katas.toml"
