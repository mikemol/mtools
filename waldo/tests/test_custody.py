# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for custody: a secret prints as its fingerprint, is kept 0600 in 0700, needs an actor.

W1058. ⚑ THE VALUE IS THE THING LOOKED FOR: every print path is checked against the literal secret
text, and the stored file round-trips it, so "never printed" is a claim about a value that does
exist and does come back through `reveal()`. No link is created here (no-symlinks ruling); the
refusal of a link is witnessed by naming one to the guard.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from mikemol.waldo import custody
from mikemol.waldo.custody import CustodyError, Secret

_VALUE = "eyJhbGciOiJSUzI1NiJ9.payload.sig"
_FIRST_TWELVE = custody.fingerprint(_VALUE)
_EXPIRY = 1_700_000_000.0
_EXPIRY_TEXT = "2023-11-14T22:13:20Z"
_TWELVE = 12
_TWICE = 2
_OWNER_ONLY = 0o600
_DIR_OWNER_ONLY = 0o700
_GROUP_READABLE = 0o750


def test_the_fingerprint_is_twelve_hex_of_the_sha256() -> None:
    """Twelve lowercase hex digits, stable for a value, different for another."""
    assert len(_FIRST_TWELVE) == _TWELVE
    assert all(c in "0123456789abcdef" for c in _FIRST_TWELVE)
    assert custody.fingerprint(_VALUE) == _FIRST_TWELVE
    assert custody.fingerprint(_VALUE + "x") != _FIRST_TWELVE


def test_a_secret_prints_as_its_fingerprint_on_every_path() -> None:
    """repr, str, an f-string and a format spec never contain the value."""
    secret = Secret(_VALUE)
    printed = [repr(secret), str(secret), f"{secret}", f"{secret!s}", format(secret, ">40")]
    for text in printed:
        assert _VALUE not in text
        assert _FIRST_TWELVE in text


def test_reveal_is_the_one_way_out() -> None:
    """The value comes back through reveal and nothing else changes it."""
    assert Secret(_VALUE).reveal() == _VALUE
    assert Secret(_VALUE).fingerprint() == _FIRST_TWELVE


def test_scrub_replaces_the_value_wherever_it_appears() -> None:
    """An error message that echoes command output cannot carry the secret out."""
    secret = Secret(_VALUE)
    text = f"kubectl said {_VALUE} and then {_VALUE} again"
    scrubbed = custody.scrub(text, secret)
    assert _VALUE not in scrubbed
    assert scrubbed.count(repr(secret)) == _TWICE


def test_scrub_leaves_text_alone_when_the_secret_is_empty() -> None:
    """An empty secret has nothing to find, so the text is returned untouched."""
    assert custody.scrub("abc", Secret("")) == "abc"


def test_the_file_is_owner_only_in_an_owner_only_directory(tmp_path: Path) -> None:
    """0600 on the file, 0700 on a directory the writer created, and the value reads back."""
    path = tmp_path / "state" / "token"
    custody.write_secret(path, Secret(_VALUE))
    assert stat.S_IMODE(path.stat().st_mode) == _OWNER_ONLY
    assert stat.S_IMODE(path.parent.stat().st_mode) == _DIR_OWNER_ONLY
    stored = custody.read_secret(path)
    assert stored is not None
    assert stored.reveal() == _VALUE


def test_a_rewrite_replaces_the_secret_and_leaves_no_temporary_file(tmp_path: Path) -> None:
    """The rename swaps the value whole; nothing but the one file remains in the directory."""
    path = tmp_path / "state" / "token"
    custody.write_secret(path, Secret("old-value"))
    custody.write_secret(path, Secret(_VALUE))
    assert [p.name for p in path.parent.iterdir()] == ["token"]
    stored = custody.read_secret(path)
    assert stored is not None
    assert stored.reveal() == _VALUE


def test_a_directory_open_to_the_group_is_refused_not_tightened(tmp_path: Path) -> None:
    """An existing directory with group access is the caller's to fix; nothing is written."""
    directory = tmp_path / "state"
    directory.mkdir()
    directory.chmod(_GROUP_READABLE)
    with pytest.raises(CustodyError, match="open to group or others"):
        custody.write_secret(directory / "token", Secret(_VALUE))
    assert not (directory / "token").exists()
    assert stat.S_IMODE(directory.stat().st_mode) == _GROUP_READABLE


def test_a_link_is_refused_for_the_file_and_for_its_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard refuses a path it is told is a link; no link is created to test it."""
    linked = tmp_path / "linked"

    def only_linked(self: Path) -> bool:
        return self.name == "linked"

    monkeypatch.setattr(Path, "is_symlink", only_linked)
    with pytest.raises(CustodyError, match="is a link"):
        custody.write_secret(linked, Secret(_VALUE))
    with pytest.raises(CustodyError, match="is a link"):
        custody.read_secret(linked)
    with pytest.raises(CustodyError, match="is a link"):
        custody.write_secret(linked / "token", Secret(_VALUE))


def test_reading_nothing_or_blank_text_is_none(tmp_path: Path) -> None:
    """No file and a blank file both read as no secret."""
    path = tmp_path / "token"
    assert custody.read_secret(path) is None
    path.write_text("  \n", encoding="utf-8")
    assert custody.read_secret(path) is None


def test_no_identity_is_refused_unless_one_is_named_or_the_caller_opts_in() -> None:
    """The control is the two ways in: a named identity and an explicit as_current_user."""
    assert custody.require_identity("machine-id", as_current_user=False) == "machine-id"
    assert custody.require_identity(None, as_current_user=True) == "current user"
    with pytest.raises(CustodyError, match="no identity chosen"):
        custody.require_identity(None, as_current_user=False)
    with pytest.raises(CustodyError, match="no identity chosen"):
        custody.require_identity("", as_current_user=False)


def test_describe_shows_the_fingerprint_and_the_expiry_never_the_value() -> None:
    """What the queue may see: fingerprint, and the expiry in UTC when known."""
    secret = Secret(_VALUE)
    assert custody.describe(secret) == f"fingerprint {_FIRST_TWELVE}"
    shown = custody.describe(secret, _EXPIRY)
    assert shown == f"fingerprint {_FIRST_TWELVE}, expires {_EXPIRY_TEXT}"
    assert _VALUE not in shown
