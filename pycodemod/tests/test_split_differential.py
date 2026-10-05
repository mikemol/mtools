# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The cases-versus-`split.plan` adapter: every origin case replays, each difference declared.

`differential/split.cases.json` carries the origin's inputs and check text. The adapter in
`differential/split_replay.py` runs them through the port and records how each came out. A case
may differ from the origin only in the two ways the port declares (the origin's empty part 00 and
its `# noqa: F401`, which became a generated `__all__`); anything else fails here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from differential import split_replay as replay
from mikemol.pycodemod import split

if TYPE_CHECKING:
    from pathlib import Path

_CASES = replay.load()
_COUNT = 28
_TWO_DEFS = "def a():\n    return 1\n\ndef b():\n    return 2\n"


def _origin(parts: list[list[int]], files: dict[str, str]) -> dict[str, object]:
    tops = [{"i": 9, "is_import": True}, {"i": 0, "is_import": False}, {"i": 1, "is_import": False}]
    return {"tops": tops, "parts": parts, "files": files}


def _planned(tmp_path: Path) -> split.Plan:
    path = tmp_path / "two.py"
    path.write_text(_TWO_DEFS, encoding="utf-8")
    return split.plan(str(path), split.Options(max_defs=1))


def test_the_cases_file_loads_every_origin_case() -> None:
    """The adapter reads all 28 cases, each with a check text and at least one call."""
    assert len(_CASES) == _COUNT
    assert all(c.check and c.calls for c in _CASES)
    assert _CASES[0].number == "307"


@pytest.mark.parametrize("case", _CASES, ids=[c.number for c in _CASES])
def test_a_split_case_replays_without_an_undeclared_difference(
    case: replay.Case, tmp_path: Path
) -> None:
    """Each case passes its origin check, and differs from the origin's plan only as declared."""
    got = replay.judge(case, tmp_path)
    assert got.failures == ()
    assert [d for d in got.differences if not d.declared] == []
    assert got.status in {"pass", "declared"}


def test_the_replay_declares_the_part_00_and_the_noqa_on_the_cases_that_carry_a_plan(
    tmp_path: Path,
) -> None:
    """Exactly the cases whose operands record the origin's plan carry the two declared kinds."""
    kinds = {
        c.number: {d.kind for d in replay.judge(c, tmp_path / c.number).differences}
        for c in _CASES
        if any("p" in call.args for call in c.calls)
    }
    assert kinds
    assert all(k == {"empty-part-00", "noqa-to-all"} for k in kinds.values())
    assert set(replay.DECLARED) == {"empty-part-00", "noqa-to-all"}


def test_an_unlisted_difference_is_undeclared_and_fails_the_status(tmp_path: Path) -> None:
    """A partition the origin did not make is not declared, so the outcome reads `differs`."""
    p = _planned(tmp_path)
    found = replay.compare(_origin([[0, 1]], {"two.py": ""}), p)
    assert [d.kind for d in found] == ["partition"]
    assert not found[0].declared
    assert replay.Outcome("x", (), found).status == "differs"


def test_an_imports_only_part_and_a_suppression_comment_are_declared(tmp_path: Path) -> None:
    """The origin's import-only part 00 and its noqa re-exports are the declared kinds."""
    p = _planned(tmp_path)
    origin = _origin([[9], [0], [1]], {"two.py": "import two_00  # noqa: F401\n"})
    found = replay.compare(origin, p)
    assert {d.kind for d in found} == {"empty-part-00", "noqa-to-all"}
    assert all(d.declared for d in found)
    assert replay.Outcome("x", (), found).status == "declared"


def test_a_failed_check_makes_the_outcome_differ_even_without_a_difference() -> None:
    """A failure of the origin's own check is `differs`; no failure and no difference is `pass`."""
    assert replay.Outcome("x", ("boom",), ()).status == "differs"
    assert replay.Outcome("x", (), ()).status == "pass"


def test_a_case_with_no_registered_check_is_refused(tmp_path: Path) -> None:
    """A case whose number has no check raises instead of passing vacuously."""
    stray = replay.Case("999-stray", "text", (), {})
    with pytest.raises(replay.CaseShapeError):
        replay.judge(stray, tmp_path)


def test_a_call_with_no_port_counterpart_is_refused(tmp_path: Path) -> None:
    """An origin function the adapter does not map raises instead of being skipped."""
    stray = replay.Case("307-stray", "text", (replay.Call("mystery", {}),), {})
    with pytest.raises(replay.CaseShapeError):
        replay.judge(stray, tmp_path)


def test_a_malformed_cases_file_is_refused(tmp_path: Path) -> None:
    """A cases file that is not a list of case objects raises."""
    bad = tmp_path / "bad.cases.json"
    bad.write_text('{"case": 1}', encoding="utf-8")
    with pytest.raises(replay.CaseShapeError):
        replay.load(bad)
