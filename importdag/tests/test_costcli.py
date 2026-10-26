# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The landing-cost command joins the graph's cone with luthen's series, and names what it lacks.

⚑ THE CONTROLS: a test with no measurement is listed and adds nothing, a manifest path the graph
does not name makes the count a floor and is said, a store that answers nothing prices nothing
instead of inventing, and an unreadable graph is exit 2.
"""

import io
import json
from itertools import starmap
from pathlib import Path

from mikemol.importdag import costcli

_USAGE = 2
_GRAPH: dict[str, object] = {
    "modules": {"src/x.py": {"imports": []}},
    "tests": {
        "tests/test_x.py": {"imports": ["src/x.py"], "reads": []},
        "tests/test_y.py": {"imports": ["src/x.py"], "reads": []},
    },
}
_STORE: dict[str, dict[str, str]] = {
    costcli.MEDIAN.format(repo="r"): {"//d:test_x": "2.5"},
    costcli.P90.format(repo="r"): {"//d:test_x": "4.0"},
    costcli.SAMPLES.format(repo="r"): {"//d:test_x": "7"},
}


def _row(target: str, value: str) -> str:
    metric: dict[str, str] = {"repo": "r", "target": target}
    row: dict[str, object] = {"metric": metric, "value": [1, value]}
    return json.dumps(row) + "\n"


def _query(promql: str) -> str:
    return "".join(starmap(_row, _STORE.get(promql, {}).items()))


def _silent(_promql: str) -> str:
    return ""


def test_the_report_prices_the_measured_and_names_the_unmeasured() -> None:
    """test_x is measured (2.5 s, 4.0 s, 7 samples); test_y is not and is listed."""
    lines = costcli.report(_GRAPH, ["src/x.py"], "r", _query)
    assert lines[0] == "tests rerun: 2"
    assert "median 2.5 s, p90 4.0 s over 1 measured" in lines[1]
    assert "fewest samples 7" in lines[1]
    assert lines[2] == "unmeasured (1): tests/test_y.py"


def test_a_store_that_answers_nothing_prices_nothing_and_lists_every_test() -> None:
    """No series means every test is unmeasured and the sums are 0, not an invented average."""
    lines = costcli.report(_GRAPH, ["src/x.py", "src/nowhere.py"], "r", _silent)
    assert lines[0] == "tests rerun: 2"
    assert lines[1] == "not in the graph (the count is a floor): src/nowhere.py"
    assert "median 0.0 s, p90 0.0 s over 0 measured" in lines[2]
    assert "fewest samples none" in lines[2]
    assert "unmeasured (2)" in lines[3]


def test_the_command_reads_the_dists_graph_and_strips_the_dist_prefix(tmp_path: Path) -> None:
    """`--dist d` reads <root>/d/graph.json and a manifest path `d/src/x.py` names `src/x.py`."""
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "graph.json").write_text(json.dumps(_GRAPH), encoding="utf-8")
    out = io.StringIO()
    argv = ["--dist", "d", "--repo", "r", "--root", str(tmp_path), "d/src/x.py", "other/z.py"]
    assert costcli.main(argv, out, _query) == 0
    assert out.getvalue().startswith("tests rerun: 2\n")


def test_an_unreadable_graph_is_a_usage_failure_that_prints_nothing(tmp_path: Path) -> None:
    """No graph.json is exit 2 and nothing on stdout."""
    out = io.StringIO()
    argv = ["--dist", "d", "--repo", "r", "--root", str(tmp_path), "d/src/x.py"]
    assert costcli.main(argv, out, _silent) == _USAGE
    assert not out.getvalue()
