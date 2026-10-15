# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the exit-constant census: it reads constants and judges them by the table."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.corpus import exitcensus

if TYPE_CHECKING:
    import pytest

_TABLE_DOC = {
    "REFUSE": {"value": 3, "names": ["REFUSED"]},
    "USAGE": {"value": 2, "names": ["USAGE"]},
}
_REAL_TABLE = Path(__file__).parents[1] / "exit-table.json"


def _table() -> exitcensus.Table:
    return exitcensus.table_of(_TABLE_DOC)


def _real() -> dict[str, dict[str, object]]:
    """Read the tracked table.

    Returns:
        verdict to its entry.

    """
    text = _REAL_TABLE.read_text(encoding="utf-8")
    return cast("dict[str, dict[str, object]]", json.loads(text))


def test_constants_reads_plain_and_annotated_integer_assignments_only() -> None:
    """EXIT_ integers at module level are read; other names, strings and expressions are not."""
    source = "EXIT_A = 1\nEXIT_B: int = 2\nOTHER = 3\nEXIT_C = 'x'\nEXIT_D = 1 + 1\n"
    found = exitcensus.constants(source, "m.py")
    assert [(c.name, c.value, c.line) for c in found] == [("EXIT_A", 1, 1), ("EXIT_B", 2, 2)]


def test_a_class_level_or_unparseable_source_yields_nothing() -> None:
    """Only module-level assignments count, and a file that does not parse is skipped."""
    assert exitcensus.constants("class K:\n    EXIT_A = 1\n", "m.py") == []
    assert exitcensus.constants("def (:\n", "m.py") == []


def test_a_name_at_its_verdicts_value_is_ok_and_at_another_is_a_violation() -> None:
    """REFUSED at 3 is OK; REFUSED at 2 is a VIOLATION naming the right value."""
    ok = exitcensus.judge(exitcensus.Constant("m.py", 1, "EXIT_REFUSED", 3), _table())
    bad = exitcensus.judge(exitcensus.Constant("m.py", 1, "EXIT_REFUSED", 2), _table())
    assert (ok.status, bad.status, bad.detail) == ("OK", "VIOLATION", "REFUSE is 3")


def test_a_name_the_table_does_not_list_is_unknown_not_a_violation() -> None:
    """The control: a gap in the table is reported apart from a defect in the tool."""
    row = exitcensus.judge(exitcensus.Constant("m.py", 1, "EXIT_MYSTERY", 9), _table())
    assert row.status == "UNKNOWN"


def test_census_walks_src_trees_and_skips_venvs_and_tests(tmp_path: Path) -> None:
    """A constant under `src` is read; one under `tests` or `.venv` is not."""
    (tmp_path / "d" / "src").mkdir(parents=True)
    (tmp_path / "d" / "tests").mkdir()
    (tmp_path / "d" / ".venv" / "src").mkdir(parents=True)
    (tmp_path / "d" / "src" / "a.py").write_text("EXIT_REFUSED = 2\n", encoding="utf-8")
    (tmp_path / "d" / "tests" / "t.py").write_text("EXIT_REFUSED = 2\n", encoding="utf-8")
    (tmp_path / "d" / ".venv" / "src" / "v.py").write_text("EXIT_REFUSED = 2\n", encoding="utf-8")
    rows = exitcensus.census([tmp_path], _table())
    assert [r.status for r in rows] == ["VIOLATION"]


def test_main_exits_one_on_a_violation_and_zero_without(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The exit status is the verdict: 1 with a violation, 0 once the constant is right."""
    (tmp_path / "src").mkdir()
    table = tmp_path / "t.json"
    table.write_text(json.dumps(_TABLE_DOC), encoding="utf-8")
    source = tmp_path / "src" / "a.py"
    source.write_text("EXIT_REFUSED = 2\n", encoding="utf-8")
    assert exitcensus.main([str(table), str(tmp_path)]) == 1
    assert "VIOLATION" in capsys.readouterr().out
    source.write_text("EXIT_REFUSED = 3\n", encoding="utf-8")
    assert exitcensus.main([str(table), str(tmp_path)]) == 0


def test_main_refuses_a_missing_table(capsys: pytest.CaptureFixture[str]) -> None:
    """Usage: no table file is exit 2 with the usage line on stderr."""
    assert exitcensus.main(["/usr/nonexistent/x.json", "."]) == exitcensus.EXIT_USAGE
    assert "usage:" in capsys.readouterr().err


def test_the_key_leaves_out_the_root_so_a_baseline_holds_in_another_checkout() -> None:
    """The key starts at the dist directory above `src`, not where the tree was checked out."""
    here = exitcensus.Constant("/a/b/mtools/fence/src/m/x.py", 4, "EXIT_REFUSED", 2)
    there = exitcensus.Constant("/c/mtools/fence/src/m/x.py", 4, "EXIT_REFUSED", 2)
    assert exitcensus.key_of(here) == exitcensus.key_of(there)
    assert exitcensus.key_of(here) == "fence/src/m/x.py EXIT_REFUSED 2"


def test_diff_reports_a_new_violation_and_a_fixed_one_still_listed() -> None:
    """A violation the baseline lacks is NEW; a baseline key that no longer violates is FIXED."""
    bad = exitcensus.judge(exitcensus.Constant("d/src/a.py", 1, "EXIT_REFUSED", 2), _table())
    good = exitcensus.judge(exitcensus.Constant("d/src/b.py", 1, "EXIT_REFUSED", 3), _table())
    listed = ["d/src/b.py EXIT_REFUSED 2", ""]
    new, fixed = exitcensus.diff([bad, good], listed)
    assert (new, fixed) == (["d/src/a.py EXIT_REFUSED 2"], ["d/src/b.py EXIT_REFUSED 2"])


def test_a_baseline_run_fails_on_new_and_on_fixed_and_passes_on_equal(tmp_path: Path) -> None:
    """Write the baseline, check it passes; fix the code, it fails until the baseline shrinks."""
    (tmp_path / "d" / "src").mkdir(parents=True)
    table = tmp_path / "t.json"
    table.write_text(json.dumps(_TABLE_DOC), encoding="utf-8")
    source = tmp_path / "d" / "src" / "a.py"
    source.write_text("EXIT_REFUSED = 2\n", encoding="utf-8")
    base = tmp_path / "base.txt"
    root = str(tmp_path / "d")
    assert exitcensus.main(["--write-baseline", str(base), str(table), root]) == 0
    assert exitcensus.main(["--baseline", str(base), str(table), root]) == 0
    source.write_text("EXIT_REFUSED = 3\n", encoding="utf-8")
    assert exitcensus.main(["--baseline", str(base), str(table), root]) == 1
    source.write_text("EXIT_REFUSED = 4\n", encoding="utf-8")
    base.write_text("", encoding="utf-8")
    assert exitcensus.main(["--baseline", str(base), str(table), root]) == 1


def test_a_scoped_verdict_is_allowed_only_in_its_listed_modules() -> None:
    """BLOCK at 2 is the harness's, so it holds in a listed hook module and violates elsewhere."""
    doc = {
        "USAGE": {"value": 2, "names": ["USAGE"]},
        "BLOCK": {"value": 2, "names": ["BLOCK"], "modules": ["h/src/hook.py"]},
    }
    table = exitcensus.table_of(doc)
    inside = exitcensus.judge(exitcensus.Constant("/r/h/src/hook.py", 1, "EXIT_BLOCK", 2), table)
    outside = exitcensus.judge(exitcensus.Constant("/r/h/src/cli.py", 1, "EXIT_BLOCK", 2), table)
    assert (inside.status, outside.status) == ("OK", "VIOLATION")
    assert "only for h/src/hook.py" in outside.detail


def test_the_tracked_table_gives_each_value_one_verdict_and_each_name_one_value() -> None:
    """The real table: no value belongs to two verdicts and no name is listed under two."""
    doc = _real()
    values = [cast("int", e["value"]) for e in doc.values() if "modules" not in e]
    names = [name for entry in doc.values() for name in cast("list[str]", entry["names"])]
    assert len(values) == len(set(values))
    assert len(names) == len(set(names))
