# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A reading that must advance and be fresh: what passes, and each way it fails (W1871).

⚑ NOTHING THAT CANNOT BE JUDGED IS A PASS: the controls are the reading that moved and is fresh,
and each failure is named by its reason: unchanged, absent pointer, stale or unparseable stamp,
no reading before the apply, a reading that cannot run after it, and a reading that checks nothing.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from mikemol.waldo import planreading
from mikemol.waldo.planjson import Json

_BEGAN = "2026-10-23T12:00:00Z"
_TOOL = Path("/usr/bin/reader")
_NO_RUNNER = "no prlimit"


@dataclass
class _Done:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class _Tools:
    def __init__(self, *, found: bool = True, code: int = 0, raises: bool = False) -> None:
        self._found, self._code, self._raises = found, code, raises
        self.calls: list[tuple[Path, tuple[str, ...], Path | None, int]] = []

    def find(self, name: str) -> Path | None:
        return _TOOL if (self._found and name == "reader") else None

    def run(
        self, tool: Path, *args: str, cwd: Path | None = None, stdin_text: str | None = None
    ) -> _Done:
        self.calls.append((tool, (*args, str(stdin_text)), cwd, 0))
        return _Done(self._code)

    def run_bounded(
        self, tool: Path, *args: str, cwd: Path | None = None, cpu_seconds: int
    ) -> _Done:
        if self._raises:
            raise OSError(_NO_RUNNER)
        self.calls.append((tool, args, cwd, cpu_seconds))
        return _Done(self._code, "out\n")


def _read(stdout: str) -> Json:
    return {"status": planreading.READ, "stdout": stdout}


def _json(digest: str, as_of: str = _BEGAN) -> Json:
    inner: dict[str, object] = {"digest": digest, "as_of": as_of}
    outer: dict[str, object] = {"vmalert": inner}
    return _read(json.dumps(outer))


_SPEC: Json = {"advances": "vmalert.digest", "fresh_since": "vmalert.as_of"}


def test_a_dotted_pointer_picks_a_value_and_the_empty_one_the_trimmed_stdout() -> None:
    """Strings as they are, other values as sorted JSON, and an absent path is None."""
    items: list[object] = [1]
    inner: dict[str, object] = {"b": "x", "n": 3, "l": items}
    outer: dict[str, object] = {"a": inner}
    text = json.dumps(outer)
    assert planreading.value(text, "a.b") == "x"
    assert planreading.value(text, "a.n") == "3"
    assert planreading.value(text, "a.l") == "[1]"
    assert planreading.value(text, "a.zz") is None
    assert planreading.value(text, "a.b.c") is None
    assert planreading.value("not json", "a") is None
    assert planreading.value("  6102045 \n", "") == "6102045"


def test_a_reading_that_moved_and_is_fresh_holds() -> None:
    """The control: the digest differs and the stamp is at or after the apply's start."""
    after = _json("bbb", "2026-10-23T12:00:05Z")
    assert planreading.judge(_SPEC, _json("aaa"), after, _BEGAN) is None
    same_second = _json("bbb", _BEGAN)
    assert planreading.judge(_SPEC, _json("aaa"), same_second, _BEGAN) is None


def test_a_reading_that_did_not_move_is_named_with_its_value() -> None:
    """Inequality only: an unchanged value is the failure, whatever it is."""
    why = planreading.judge(_SPEC, _json("aaa"), _json("aaa"), _BEGAN)
    assert why is not None
    assert "did not advance" in why
    assert "'aaa'" in why


def test_a_stale_or_unreadable_timestamp_is_a_failure() -> None:
    """Older than the apply's start, absent, or not a date: none of them is fresh."""
    old = planreading.judge(_SPEC, _json("a"), _json("b", "2026-10-23T11:59:59Z"), _BEGAN)
    assert old is not None
    assert "stale" in old
    absent = planreading.judge({"fresh_since": "nope"}, _json("a"), _json("b"), _BEGAN)
    assert absent is not None
    assert "absent or not a timestamp" in absent
    junk = planreading.judge(_SPEC, _json("a"), _json("b", "yesterday"), _BEGAN)
    assert junk is not None
    assert "absent or not a timestamp" in junk
    assert planreading.judge(_SPEC, _json("a"), _json("b"), "never") is not None


def test_an_absent_advances_pointer_is_a_failure_not_an_equal_pair() -> None:
    """Two readings that both lack the pointer must not read as unchanged or as moved."""
    why = planreading.judge({"advances": "gone"}, _json("a"), _json("b"), _BEGAN)
    assert why is not None
    assert "absent" in why


def test_a_reading_with_nothing_before_or_nothing_after_cannot_hold() -> None:
    """No before-reading, a before that cannot run, and an after that cannot run each fail."""
    assert "before the apply" in str(planreading.judge(_SPEC, None, _json("b"), _BEGAN))
    broken: Json = {"status": planreading.CANNOT_RUN, "why": "x"}
    assert "before the apply" in str(planreading.judge(_SPEC, broken, _json("b"), _BEGAN))
    gone: Json = {"status": planreading.CANNOT_RUN, "why": "tool gone"}
    assert "tool gone" in str(planreading.judge(_SPEC, _json("a"), gone, _BEGAN))


def test_a_reading_that_declares_neither_check_proves_nothing() -> None:
    """A spec with no advances and no fresh_since is refused, never a pass."""
    why = planreading.judge({"tool": "reader"}, _json("a"), _json("b"), _BEGAN)
    assert why is not None
    assert "proves nothing" in why


def test_taking_a_reading_is_bounded_and_every_way_it_cannot_run_says_so(tmp_path: Path) -> None:
    """Found and exits 0 gives stdout; a missing tool, a non-zero exit and no runner do not."""
    tools = _Tools()
    spec: Json = {"tool": "reader", "args": ["-x"], "cpu_seconds": 7}
    assert planreading.take(tools, tmp_path, spec) == {"status": "read", "stdout": "out\n"}
    assert tools.calls == [(_TOOL, ("-x",), tmp_path, 7)]
    bad_cpu: Json = {"tool": "reader", "cpu_seconds": True}
    planreading.take(tools, tmp_path, bad_cpu)
    assert tools.calls[-1][3] == planreading.DEFAULT_CPU_SECONDS
    assert "not found" in str(planreading.take(_Tools(found=False), tmp_path, spec)["why"])
    assert "exited 3" in str(planreading.take(_Tools(code=3), tmp_path, spec)["why"])
    assert "no CPU-bounded" in str(planreading.take(_Tools(raises=True), tmp_path, spec)["why"])


def test_the_verdict_folds_a_reading_into_the_result_and_never_softens_a_failure() -> None:
    """A holding reading adds a mark; a failing one fails a pass; a failed exit stays failed."""
    tools = _Tools()
    passed: Json = {"status": "pass"}
    spec: Json = {"tool": "reader", "advances": ""}
    held = planreading.verdict(tools, Path(), None, planreading.Prior(), passed)
    assert held == passed
    prior = planreading.Prior(_read("different\n"), _BEGAN)
    ok = planreading.verdict(tools, Path(), spec, prior, passed)
    assert (ok["status"], ok["reading"]) == ("pass", "advanced")
    same = planreading.Prior(_read("out\n"), _BEGAN)
    bad = planreading.verdict(tools, Path(), spec, same, passed)
    assert (bad["status"], bad["reading"]) == ("fail", "failed")
    already: Json = {"status": "fail"}
    assert planreading.verdict(tools, Path(), spec, same, already)["status"] == "fail"
    unrun = planreading.verdict(_Tools(code=1), Path(), spec, same, passed)
    assert unrun["status"] == planreading.CANNOT_RUN
