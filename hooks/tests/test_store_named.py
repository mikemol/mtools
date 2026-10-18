# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A session with no MIKEMOL_ENDPOINTS still names a store through the host's file (W1528)."""

from pathlib import Path

from mikemol.hooks import commit_span


def _home(tmp_path: Path, *, with_file: bool) -> dict[str, str]:
    if with_file:
        path = tmp_path / commit_span.HOME_FILE
        path.parent.mkdir(parents=True)
        path.write_text("{}", encoding="utf-8")
    return {"HOME": str(tmp_path)}


def test_the_variable_alone_names_a_store() -> None:
    """The old rule still holds: a set variable is enough, with no HOME at all."""
    assert commit_span.store_named({commit_span.ENDPOINTS_ENV: "/x/endpoints.json"})


def test_the_hosts_file_under_home_names_a_store_when_the_variable_is_unset(tmp_path: Path) -> None:
    """The fix: the file luthen publishes counts, so a session with no variable still sends."""
    env = _home(tmp_path, with_file=True)
    assert commit_span.store_named(env)
    assert commit_span.store_named({**env, commit_span.ENDPOINTS_ENV: ""})


def test_no_variable_and_no_file_name_no_store(tmp_path: Path) -> None:
    """The negative control: an empty environment, and a HOME with no file, send nothing."""
    assert not commit_span.store_named({})
    assert not commit_span.store_named(_home(tmp_path, with_file=False))
