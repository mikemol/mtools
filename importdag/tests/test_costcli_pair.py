# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Two cards priced together count a shared test once; the second after the first pays less (W1998).

⚑ THE CONTROLS: the pair's total is the union (111 s, not the 121 s two separate prices sum to),
the second card after the first is only the tests the first did not already rerun, and a single
card's report has no pair lines at all.
"""

import io
import json
from itertools import starmap
from pathlib import Path

from mikemol.importdag import costcli

_GRAPH: dict[str, object] = {
    "modules": {"src/x.py": {"imports": []}, "src/z.py": {"imports": []}},
    "tests": {
        "tests/test_x.py": {"imports": ["src/x.py"], "reads": []},
        "tests/test_xz.py": {"imports": ["src/x.py", "src/z.py"], "reads": []},
        "tests/test_z.py": {"imports": ["src/z.py"], "reads": []},
    },
}
_MEDIANS = {"//d:test_x": "1", "//d:test_xz": "10", "//d:test_z": "100"}
_STORE: dict[str, dict[str, str]] = {
    costcli.MEDIAN.format(repo="r"): _MEDIANS,
    costcli.P90.format(repo="r"): dict.fromkeys(_MEDIANS, "2"),
    costcli.SAMPLES.format(repo="r"): dict.fromkeys(_MEDIANS, "5"),
}
_FIRST = 2


def _row(target: str, value: str) -> str:
    metric: dict[str, str] = {"repo": "r", "target": target}
    row: dict[str, object] = {"metric": metric, "value": [1, value]}
    return json.dumps(row) + "\n"


def _query(promql: str) -> str:
    return "".join(starmap(_row, _STORE.get(promql, {}).items()))


def test_two_cards_together_count_a_test_both_reach_once() -> None:
    """Card x reruns test_x and test_xz, card z reruns test_xz and test_z: 3 tests, 111 s."""
    lines = costcli.report(_GRAPH, ["src/x.py"], "r", _query, then=["src/z.py"])
    assert lines[0] == f"tests rerun: {_FIRST}"
    assert "together: 3 tests; the 1 both reach count once" in lines
    assert any(line.startswith("together: cpu: median 111.0 s") for line in lines)


def test_the_second_card_after_the_first_pays_only_for_what_the_first_did_not_rerun() -> None:
    """After x lands, z still reruns test_z alone: 1 test, 100 s."""
    lines = costcli.report(_GRAPH, ["src/x.py"], "r", _query, then=["src/z.py"])
    assert "second card after the first lands: 1 tests" in lines
    assert any(line.startswith("after: cpu: median 100.0 s") for line in lines)


def test_a_single_card_report_has_no_pair_lines() -> None:
    """Without a second manifest the output is the single-card report, unchanged."""
    lines = costcli.report(_GRAPH, ["src/x.py"], "r", _query)
    assert not any("together" in line or "after" in line for line in lines)


def test_the_command_takes_the_second_manifest_after_then(tmp_path: Path) -> None:
    """`FILE... --then FILE...` strips the dist prefix from both and prints the pair lines."""
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "graph.json").write_text(json.dumps(_GRAPH), encoding="utf-8")
    out = io.StringIO()
    argv = ["--dist", "d", "--repo", "r", "--root", str(tmp_path), "d/src/x.py"]
    assert costcli.main([*argv, "--then", "d/src/z.py"], out, _query) == 0
    assert "together: 3 tests" in out.getvalue()
