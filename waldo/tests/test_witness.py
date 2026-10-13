# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the witness evaluator: six kinds, and none passes vacuously.

W1057. ⚑ THE GREEN READING IS THE POSITIVE CONTROL: each kind first accepts the output it should,
so its refusal of the near-miss means the kind can tell them apart. The last two kinds are the point
of the module: a standing state ("Synced=True" before and after) must NOT satisfy `advances`, and a
stale heartbeat must NOT satisfy `fresh_since`, even though both read green.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.waldo.witness import (
    Witness,
    capture_before,
    group_of,
    judge,
    non_empty,
    reading_of,
    run_all,
    tail_of,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

_EXIT_FAILED = 3
_START = 1_000_000.0
_FRESH = 1_000_050
_STALE = 999_000
_SIX = 6
_TWO = 2


def _witness(
    *,
    json_empty: tuple[str, ...] = (),
    must_contain: tuple[str, ...] = (),
    must_match: tuple[str, ...] = (),
    advances: tuple[str, ...] = (),
    fresh_since: tuple[str, ...] = (),
) -> Witness:
    return Witness(
        "w",
        ("cmd",),
        json_empty=json_empty,
        must_contain=must_contain,
        must_match=must_match,
        advances=advances,
        fresh_since=fresh_since,
    )


def test_a_clean_exit_with_nothing_declared_is_met() -> None:
    """The control: no conditions and exit 0 is a pass, and the result carries its name and tail."""
    result = judge(_witness(), 0, "ok\n")
    assert (result.name, result.rc, result.unmet, result.tail) == ("w", 0, (), ("ok",))


def test_a_non_zero_exit_fails_whatever_the_output_says() -> None:
    """The command's own status survives even when every condition is met."""
    assert judge(_witness(must_contain=("ok",)), _EXIT_FAILED, "ok").rc == _EXIT_FAILED


def test_must_contain_names_the_text_that_is_absent() -> None:
    """The unmet line says which text was missing and the rc is 1."""
    result = judge(_witness(must_contain=("rolled out", "ready")), 0, "rolled out")
    assert result.unmet == ("must_contain ready",)
    assert result.rc == 1


def test_must_match_is_a_regular_expression() -> None:
    """A pattern that matches passes; one that does not is named."""
    assert judge(_witness(must_match=(r"replicas: \d+",)), 0, "replicas: 3").rc == 0
    assert judge(_witness(must_match=(r"replicas: \d+",)), 0, "none").unmet == (
        r"must_match replicas: \d+",
    )


def test_json_empty_needs_the_key_present_and_empty() -> None:
    """Exit 0 with a drift list is a failure; a missing key is one too, not a pass."""
    clean = judge(_witness(json_empty=("drift",)), 0, 'out {"drift": []} end')
    assert clean.rc == 0
    listed = judge(_witness(json_empty=("drift",)), 0, '{"drift": ["a"]}')
    assert listed.unmet == ("json_empty drift",)
    absent = judge(_witness(json_empty=("drift",)), 0, '{"other": []}')
    assert absent.unmet == ("json_empty drift",)
    unreadable = judge(_witness(json_empty=("drift",)), 0, "no json here")
    assert unreadable.unmet == ("json_empty drift",)


def test_advances_needs_a_pre_act_reading_that_differs() -> None:
    """A resourceVersion that moved passes; the same one before and after does not."""
    w = _witness(advances=(r"resourceVersion=(\d+)",))
    assert judge(w, 0, "resourceVersion=12", before="resourceVersion=11").rc == 0
    still = judge(w, 0, "resourceVersion=11", before="resourceVersion=11")
    assert still.unmet == (r"advances resourceVersion=(\d+): still 11",)


def test_advances_is_unmet_without_a_pre_act_reading() -> None:
    """With nothing to compare to, the witness cannot pass: a standing green is not success."""
    w = _witness(advances=(r"v=(\d+)",))
    assert judge(w, 0, "v=1").unmet == (r"advances v=(\d+): no pre-act reading",)
    assert judge(w, 0, "nothing", before="v=1").unmet == (
        r"advances v=(\d+): no match in the reading",
    )


def test_increases_needs_a_number_strictly_above_the_pre_act_reading() -> None:
    """A heartbeat that moved up passes; equal and lower do not; a standing value is refused."""
    w = Witness("hb", ("hb",), increases=(r"ts=(\d+)",))
    assert judge(w, 0, "ts=12", before="ts=11").rc == 0
    equal = judge(w, 0, "ts=11", before="ts=11")
    assert equal.unmet == (r"increases ts=(\d+): 11 is not above 11",)
    lower = judge(w, 0, "ts=10", before="ts=11")
    assert lower.unmet == (r"increases ts=(\d+): 10 is not above 11",)


def test_increases_refuses_a_mangled_read_and_a_missing_pre_act_reading() -> None:
    """A non-number on either side is refused, not reasoned about; no pre-act reading is unmet."""
    w = Witness("hb", ("hb",), increases=(r"ts=(\w+)",))
    after_bad = judge(w, 0, "ts=soon", before="ts=11")
    assert after_bad.unmet == (r"increases ts=(\w+): not a number before and after",)
    before_bad = judge(w, 0, "ts=12", before="ts=then")
    assert before_bad.unmet == (r"increases ts=(\w+): not a number before and after",)
    missing = judge(w, 0, "ts=12")
    assert missing.unmet == (r"increases ts=(\w+): no pre-act reading",)


def test_fresh_since_needs_a_time_at_or_after_the_start() -> None:
    """A heartbeat from this run passes; a stale one, an unreadable one and no start do not."""
    w = _witness(fresh_since=(r"ts=(\d+)",))
    assert judge(w, 0, f"ts={_FRESH}", started=_START).rc == 0
    assert judge(w, 0, f"ts={int(_START)}", started=_START).rc == 0
    stale = judge(w, 0, f"ts={_STALE}", started=_START)
    assert stale.unmet == (r"fresh_since ts=(\d+): 999000 is before the start 1e+06",)
    assert judge(w, 0, "ts=soon", started=_START).unmet == (
        r"fresh_since ts=(\d+): no time in the reading",
    )
    assert judge(w, 0, f"ts={_FRESH}").unmet == (r"fresh_since ts=(\d+): no start time",)


def test_the_json_object_is_read_from_first_brace_to_last() -> None:
    """Text around the object is ignored; an array or broken JSON is not an object."""
    assert reading_of('prefix {"a": 1} suffix') == {"a": 1}
    assert reading_of("[1, 2]") is None
    assert reading_of("{broken") is None
    assert non_empty('{"a": [], "b": 1}', ["a", "b", "c"]) == ["b", "c"]


def test_group_of_reads_the_first_group_or_nothing() -> None:
    """A pattern without a group gives None even when it matches."""
    assert group_of(r"x=(\d+)", "x=7") == "7"
    assert group_of(r"x=\d+", "x=7") is None
    assert group_of(r"x=(\d+)", "y=7") is None


def test_the_tail_is_the_last_non_empty_lines() -> None:
    """At most six lines survive, blank lines are dropped, and the order is kept."""
    text = "\n".join(f"line {i}\n" for i in range(10))
    assert tail_of(text) == tuple(f"line {i}" for i in range(4, 10))
    assert len(tail_of(text)) == _SIX


class _Runner:
    """A stand-in for the command runner that answers by argv and records the calls."""

    def __init__(self, answers: dict[str, list[tuple[int, str]]]) -> None:
        self.answers = answers
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, argv: Sequence[str]) -> tuple[int, str]:
        self.calls.append(tuple(argv))
        return self.answers[argv[0]].pop(0)


def test_run_all_runs_each_witness_in_order_and_judges_it() -> None:
    """One result per witness, in the order declared, each judged on its own output."""
    ws = [Witness("a", ("a",), must_contain=("A",)), Witness("b", ("b",), must_contain=("B",))]
    runner = _Runner({"a": [(0, "A")], "b": [(0, "nope")]})
    results = run_all(ws, runner)
    assert [(r.name, r.rc) for r in results] == [("a", 0), ("b", 1)]
    assert [call[0] for call in runner.calls] == ["a", "b"]


def test_a_witness_with_no_argv_fails_with_exit_two() -> None:
    """A declared witness that names no command is a failure, not a skipped check."""
    results = run_all([Witness("empty", ())], _Runner({}))
    assert (results[0].rc, results[0].unmet) == (_TWO, ("no argv",))


def test_capture_before_also_reads_a_witness_that_declares_increases() -> None:
    """The pre-act reading is taken for `increases` witnesses as it is for `advances`."""
    rising = Witness("rising", ("r",), increases=(r"n=(\d+)",))
    runner = _Runner({"r": [(0, "n=1")]})
    assert capture_before([rising], runner) == {"rising": "n=1"}


def test_capture_before_reads_only_witnesses_that_advance_and_feeds_run_all() -> None:
    """The pre-act reading is taken once for `advances` witnesses and used when judging after."""
    moving = Witness("moving", ("m",), advances=(r"v=(\d+)",))
    standing = Witness("standing", ("s",), must_contain=("ok",))
    runner = _Runner({"m": [(0, "v=1"), (0, "v=2")], "s": [(0, "ok")]})
    before = capture_before([moving, standing], runner)
    assert before == {"moving": "v=1"}
    results = run_all([moving, standing], runner, before=before)
    assert [r.rc for r in results] == [0, 0]
    assert [call[0] for call in runner.calls] == ["m", "m", "s"]
