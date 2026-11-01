# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The Codon idiom census as OTLP gauge rows: dotted names, repo as namespace, zeros kept (W1366).

⚑ THE CONTROLS ARE WHAT MUST NOT CHANGE FROM THE TEXTFILE: every rule of the target is written, 0
included; the repository is the batch key, not a label; each row is a JSON object that
`mikemol-otlp metrics` reads (a string name, a numeric value, an object of fields, an integer time);
and no freshness class is declared, since none is decided.
"""

import json

from mikemol.hooks import websubset, websubset_otlp, websubset_tree
from mikemol.hooks.payload import as_record

Rec = dict[str, object]

_NOW = 1_700_000_000_000_000_000
_MODULES = 5
_CLEAN = 2
_SEEN_MODULES = 3
_SEEN_SITES = 4
_FOUND = websubset_tree.TreeCensus(
    "codon", _MODULES, _CLEAN, 0, (websubset_tree.RuleCount("tuple-except", 3, 4),)
)
_SEEN = {"target": "codon", "rule": "tuple-except"}
_UNSEEN = {"target": "codon", "rule": "future-import"}


def _load(line: str) -> Rec:
    parsed: object = json.loads(line)
    return as_record(parsed)


def _rows(repo: str = "mtools") -> list[Rec]:
    return [_load(line) for line in websubset_otlp.batches([(repo, _FOUND)], _NOW)[repo]]


def _values(rows: list[Rec], name: str, fields: dict[str, str] | None = None) -> list[object]:
    return [
        row["value"]
        for row in rows
        if row["name"] == f"mikemol.codon.{name}" and (fields is None or row["fields"] == fields)
    ]


def test_the_planted_rule_carries_its_modules_and_sites_under_target_and_rule() -> None:
    """The seen rule has 3 modules and 4 sites; the totals are 5 modules and 2 clean."""
    rows = _rows()
    assert _values(rows, "idiom_modules", _SEEN) == [_SEEN_MODULES]
    assert _values(rows, "idiom_sites", _SEEN) == [_SEEN_SITES]
    assert _values(rows, "modules") == [_MODULES]
    assert _values(rows, "clean_modules") == [_CLEAN]


def test_every_rule_of_the_target_is_written_and_an_unseen_one_is_zero() -> None:
    """A rule the census did not see is a 0 gauge, so its last module leaving is a step."""
    rows = _rows()
    assert len(_values(rows, "idiom_modules")) == len(websubset.RULES["codon"])
    assert _values(rows, "idiom_modules", _UNSEEN) == [0]


def test_the_repository_is_the_batch_key_and_never_a_label() -> None:
    """Two repositories give two batches; no row carries a repo field."""
    both = websubset_otlp.batches([("a", _FOUND), ("b", _FOUND)], _NOW)
    assert list(both) == ["a", "b"]
    assert all("repo" not in as_record(_load(line)["fields"]) for line in both["a"])


def test_each_row_is_a_sample_otlp_reads_and_declares_no_freshness_class() -> None:
    """Name, numeric value, field object, integer time; description and unit set, class absent."""
    for row in _rows():
        assert isinstance(row["name"], str)
        assert isinstance(row["value"], int)
        assert isinstance(row["fields"], dict)
        assert row["time_ns"] == _NOW
        assert row["description"]
        assert row["unit"]
        assert "freshness_class" not in row
