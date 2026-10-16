# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the transpile target of the web subset (mtools:W1322).

⚑ A TARGET'S LIST IS ITS OWN: a rule taken off one target still fires for the other, a module that
does not parse is refused by every target, and an unknown target is a usage error, never a silent
fall back to the default list.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import websubset, websubset_cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_FLOAT = "def f(x: float) -> bool:\n    return x == 1.5\n"
_OK = 0


def _rules(source: str, target: str) -> list[str]:
    return [finding.rule for finding in websubset.check(source, target)]


def test_codon_refuses_everything_py2many_does_and_py2many_reads_no_codon_rule() -> None:
    """The codon row is the shared rules plus its own; py2many gains none of them."""
    shared = websubset.RULES["py2many"]
    assert shared < websubset.RULES["codon"]
    assert "future-import" in websubset.RULES["codon"]
    assert "future-import" not in shared


def test_a_rule_removed_from_one_target_still_fires_for_the_other(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Taking float-equality off codon silences it there and nowhere else."""
    narrowed = websubset.RULES["codon"] - {"float-equality"}
    monkeypatch.setitem(websubset.RULES, "codon", narrowed)
    assert _rules(_FLOAT, "codon") == []
    assert _rules(_FLOAT, "py2many") == ["float-equality"]


def test_a_module_that_does_not_parse_is_refused_by_every_target() -> None:
    """`syntax` belongs to no target's list and is kept by all of them."""
    for target in websubset.RULES:
        assert _rules("def (:\n", target) == ["syntax"]


def test_the_default_target_is_py2many() -> None:
    """A call without a target reads the py2many row, so existing callers are unchanged."""
    assert websubset.check(_FLOAT) == websubset.check(_FLOAT, "py2many")


def test_cli_target_flag_picks_the_list_and_an_unknown_one_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--target codon` runs; `--target nope` exits 2 and names the usage."""
    source = tmp_path / "m.py"
    source.write_text("def f(a: int) -> int:\n    return a\n", encoding="utf-8")
    assert websubset_cli.main(["--check-file", str(source), "--target", "codon"]) == _OK
    assert websubset_cli.main(["--check-file", str(source), "--target", "nope"]) == (
        websubset_cli.EXIT_USAGE
    )
    assert "usage" in capsys.readouterr().err
