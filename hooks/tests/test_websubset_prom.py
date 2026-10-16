# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the Codon idiom textfile (mtools:W1350): the series, the zeros and the file.

⚑ THE CONTROLS ARE WHAT MUST NOT VANISH: a rule with no finding is written as 0 (a series that drops
out reads as stale, not as burned down), each metric family is contiguous under one HELP and TYPE,
and the scan time is absent unless it was given.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import websubset, websubset_cli, websubset_prom, websubset_tree

if TYPE_CHECKING:
    from pathlib import Path

_FAMILIES = 4
_FOUND = websubset_tree.TreeCensus(
    "codon", 5, 2, 0, (websubset_tree.RuleCount("tuple-except", 3, 4),)
)


def _body(scanned: int | None = None) -> str:
    return websubset_prom.render([("mtools", _FOUND)], scanned)


def test_a_rule_with_findings_is_written_with_its_modules_and_sites() -> None:
    """The planted rule carries 3 modules and 4 sites under repo, target and rule labels."""
    body = _body()
    assert 'mikemol_codon_idiom_modules{repo="mtools",target="codon",rule="tuple-except"} 3' in body
    assert 'mikemol_codon_idiom_sites{repo="mtools",target="codon",rule="tuple-except"} 4' in body
    assert 'mikemol_codon_modules{repo="mtools",target="codon"} 5' in body
    assert 'mikemol_codon_clean_modules{repo="mtools",target="codon"} 2' in body


def test_every_rule_of_the_target_is_written_and_an_unseen_one_is_zero() -> None:
    """A rule the census did not see is a 0 series, so its last module leaving is a step."""
    body = _body()
    for rule in websubset.RULES["codon"]:
        assert f'idiom_modules{{repo="mtools",target="codon",rule="{rule}"}}' in body
    assert 'rule="future-import"} 0' in body


def test_each_family_is_contiguous_under_one_header_and_scan_time_is_optional() -> None:
    """One TYPE line per family, the series right after it; the scan time only when given."""
    lines = _body().splitlines()
    types = [line for line in lines if line.startswith("# TYPE")]
    assert len(types) == len(set(types)) == _FAMILIES
    assert "scan_time_seconds" not in _body()
    assert "mikemol_codon_scan_time_seconds 77" in _body(77)


def test_the_cli_writes_the_textfile_atomically_beside_the_report(tmp_path: Path) -> None:
    """`--idioms ROOT --prom FILE` leaves the file with the repo label and no temporary file."""
    src = tmp_path / "repo" / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "m.py").write_text("from __future__ import annotations\n", encoding="utf-8")
    out = tmp_path / "codon.prom"
    root = str(tmp_path / "repo")
    assert websubset_cli.main(["--idioms", root, "--target", "codon", "--prom", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert 'repo="repo",target="codon",rule="future-import"} 1' in text
    assert not list(tmp_path.glob(".*.tmp"))
