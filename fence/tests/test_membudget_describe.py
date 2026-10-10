# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-membudget describe`: the defaults and the verb roster as parseable rows.

W964. ⚑ THE ROWS ARE COMPARED TO THE CODE'S OWN CONSTANTS AND DISPATCH TABLE, not to copies of
them: a describe that printed a retyped roster would pass a test that retyped it too.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.fence import membudget_cli

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pytest


def _rows(capsys: pytest.CaptureFixture[str]) -> list[str]:
    assert membudget_cli.main(["describe"]) == 0
    return capsys.readouterr().out.splitlines()


def test_describe_prints_the_defaults_and_every_verb(capsys: pytest.CaptureFixture[str]) -> None:
    """The control: the two numbers are the code's, and each dispatch verb has a row."""
    rows = _rows(capsys)
    assert f"default_mb {membudget_cli.DEFAULT_MB}" in rows
    assert f"max_mb {membudget_cli.CEILING_MB}" in rows
    assert [r for r in rows if r.startswith("verb ")] == [f"verb {v}" for v in membudget_cli.VERBS]


def test_describe_lists_itself(capsys: pytest.CaptureFixture[str]) -> None:
    """A caller can see that the client answers describe."""
    assert "verb describe" in _rows(capsys)


def _extra(_args: Sequence[str], _ctx: membudget_cli.Context) -> int:
    return 0


def test_a_verb_added_to_the_table_appears_without_editing_describe(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The roster is derived from the dispatch table, not copied."""
    monkeypatch.setitem(membudget_cli.VERBS, "zzz-new", _extra)
    assert "verb zzz-new" in _rows(capsys)


def test_every_row_is_a_name_and_one_value(capsys: pytest.CaptureFixture[str]) -> None:
    """Parseable by splitting on whitespace: two fields, the number rows numeric."""
    for row in _rows(capsys):
        name, value = row.split(" ")
        assert name in {"default_mb", "max_mb", "verb"}
        assert value.isdigit() == (name != "verb")
