# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--write` lowers a per-module mypy baseline part by part, rewriting only what changed (W2191).

⚑ THE CONTROLS (github:R212, nemik's rule 3): two stacks lowering different modules must write
disjoint files, so a part whose counts did not change is NOT rewritten, a file that no longer has a
finding drops out of its part, a rise in any module refuses and writes nothing, and the single
`mypy-baseline.json` is never written beside the directory.
"""

import io
import json
from pathlib import Path

from mikemol.hooks import baselinedir, pycheck_ratchet_write, pyratchet
from mikemol.hooks.pycheck_ratchet import MYPY_BASELINE, RUFF_BASELINE, Tools

type Row = dict[str, str | None]

_A = '{"a.py": {"misc": 2}}'
_B = '{"b.py": {"misc": 1}}'


def _tools(root: Path, mypy_counts: dict[str, int]) -> Tools:
    mypy_rows: list[Row] = [
        {"file": str(root / name), "severity": "error", "code": "misc"}
        for name, count in mypy_counts.items()
        for _ in range(count)
    ]

    def ruff(_root: Path) -> str:
        return "[]"

    def mypy(_root: Path) -> str:
        return "\n".join(json.dumps(row) for row in mypy_rows)

    def read(path: Path) -> str | None:
        merged = baselinedir.read(root / baselinedir.DIR)
        return {RUFF_BASELINE: "{}", MYPY_BASELINE: merged}.get(path.name)

    return Tools(ruff, mypy, read)


def _lower(root: Path, counts: dict[str, int]) -> tuple[int, dict[str, str]]:
    """Make two parts, run `--write` over today's counts.

    Returns:
        the exit code and the files written, by path under the root.

    """
    folder = root / baselinedir.DIR
    folder.mkdir()
    (folder / "m1.json").write_text(_A, encoding="utf-8")
    (folder / "m2.json").write_text(_B, encoding="utf-8")
    saved: dict[str, str] = {}

    def write(path: Path, text: str) -> None:
        saved[str(path.relative_to(root))] = text

    tools = _tools(root, counts)
    code = pycheck_ratchet_write.lower(root, tools, write, io.StringIO(), io.StringIO())
    return code, saved


def test_only_the_part_whose_count_fell_is_rewritten_and_the_single_file_is_not_written(
    tmp_path: Path,
) -> None:
    """a.py fell from 2 to 1 (m1 changes); b.py is unchanged (m2 is left alone)."""
    code, saved = _lower(tmp_path, {"a.py": 1, "b.py": 1})
    assert code == 0
    assert set(saved) == {RUFF_BASELINE, "mypy-baseline.d/m1.json"}
    assert saved["mypy-baseline.d/m1.json"] == '{\n "a.py": {\n  "misc": 1\n }\n}\n'


def test_a_file_with_no_finding_left_drops_out_of_its_part(tmp_path: Path) -> None:
    """b.py is fixed: m2 is rewritten empty, m1 (unchanged at 2) is not."""
    code, saved = _lower(tmp_path, {"a.py": 2})
    assert code == 0
    assert saved["mypy-baseline.d/m2.json"] == "{}\n"
    assert "mypy-baseline.d/m1.json" not in saved


def test_a_rise_in_any_module_refuses_and_writes_nothing(tmp_path: Path) -> None:
    """a.py rose from 2 to 3: the exit is the rise exit and no file is written."""
    code, saved = _lower(tmp_path, {"a.py": 3, "b.py": 1})
    assert code == pyratchet.EXIT_RISE
    assert saved == {}


def test_lowered_keeps_a_part_to_its_own_keys_and_leaves_an_unreadable_part_alone() -> None:
    """The pure rule: unchanged parts are absent, a torn part and a non-object are skipped."""
    found = [("a.json", _A), ("b.json", _B), ("bad.json", "not json"), ("list.json", "[1]")]
    now = {"a.py": {"misc": 1}, "b.py": {"misc": 1}, "new.py": {"misc": 5}}
    assert baselinedir.lowered(found, now) == {"a.json": {"a.py": {"misc": 1}}}
    assert baselinedir.parts(Path("/absent/dir")) == []
