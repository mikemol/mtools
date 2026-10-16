# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses: the checks a waldo runs before and after its act, over an injected runner (W1057).

Lifted from luthen-observability's `checks/apply_set.py` and extended with the kinds cassian's
recipes needed (`.claude/design/W1053-waldo.md`). A witness is a command and what its output must
show:

    exit code     a non-zero exit is a failure whatever the output says
    json_empty    keys the JSON object inside the output must HAVE and hold empty (a reading that
                  lists drift while exiting 0 is a failure; an unreadable reading is one too)
    must_contain  text the output must contain
    must_match    regular expressions the output must match
    advances      regular expressions whose first group must DIFFER from the same group in the
                  pre-act reading (a resourceVersion or refresh time that moved)
    increases     like advances, but the group is a number that must be STRICTLY GREATER than in
                  the pre-act reading; a non-number on either side is refused (W1063, from
                  cassian's heartbeat witness)
    fresh_since   regular expressions whose first group is a unix time at or after the run's start
                  (a heartbeat written by THIS run, not a Job's exit code)

⚑ SUCCESS MUST NOT BE BYTE-IDENTICAL TO FAILURE. A status that stays green while nothing happened
(a cached `Synced=True`, a Job that exits 0 with a silent curl) satisfies every kind above except
the last two; `advances` and `fresh_since` compare against the world BEFORE the act or the run's
start, so a witness that only reads a standing state cannot pass them. With no pre-act reading, or
no start time, they are UNMET, never vacuously met.

⚑ THE RUNNER IS A SEAM. `Run` takes an argv and gives (exit code, combined output); the pure judge
needs no process, and the tail of the output (last non-empty lines) is kept for the verdict.
"""

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import cast

Run = Callable[[Sequence[str]], tuple[int, str]]

TAIL_LINES = 6
NO_ARGV = 2


@dataclass(frozen=True)
class Witness:
    """One declared check: a command and what its output must show."""

    name: str
    argv: tuple[str, ...]
    json_empty: tuple[str, ...] = ()
    must_contain: tuple[str, ...] = ()
    must_match: tuple[str, ...] = ()
    advances: tuple[str, ...] = ()
    increases: tuple[str, ...] = ()
    fresh_since: tuple[str, ...] = ()
    exit_only: bool = False


@dataclass(frozen=True)
class Result:
    """What one witness found: its exit status, what was unmet, and the tail of its output."""

    name: str
    rc: int
    unmet: tuple[str, ...]
    tail: tuple[str, ...]
    # ⚑ CANNOT EVALUATE IS NOT FAILED (W1272, luthen-observability:W1076): a witness whose command
    # could not reach its target (no kubeconfig, a refused connection) measured nothing, so it is
    # neither met nor unmet. `rc` keeps the command's own non-zero exit; this flag says why.
    unevaluated: bool = False


def tail_of(text: str) -> tuple[str, ...]:
    """Keep the last few non-empty lines of `text`.

    Returns:
        at most TAIL_LINES lines, oldest first.

    """
    return tuple(line for line in text.splitlines() if line.strip())[-TAIL_LINES:]


def reading_of(out: str) -> dict[str, object] | None:
    """Read the JSON object inside `out`, first brace to last.

    Returns:
        the object, or None when there is none or it does not parse as an object.

    """
    start, end = out.find("{"), out.rfind("}")
    if not 0 <= start < end:
        return None
    try:
        parsed = cast("object", json.loads(out[start : end + 1]))
    except ValueError:
        return None
    return cast("dict[str, object]", parsed) if isinstance(parsed, dict) else None


def non_empty(out: str, keys: Sequence[str]) -> list[str]:
    """Name the `keys` the JSON object inside `out` lacks or holds non-empty.

    Returns:
        the failing keys; an unreadable reading fails every key.

    """
    found = reading_of(out) or {}
    return [key for key in keys if key not in found or found[key]]


def group_of(pattern: str, out: str) -> str | None:
    """Give the first group of `pattern`'s first match in `out`.

    Returns:
        the group text, or None when nothing matched or the pattern has no group.

    """
    found = re.search(pattern, out)
    return found.group(1) if found is not None and found.groups() else None


def _not_advanced(patterns: Sequence[str], out: str, before: str | None) -> list[str]:
    """Name the patterns whose group did not change from the pre-act reading.

    Returns:
        the unmet descriptions; with no pre-act reading every pattern is unmet.

    """
    unmet: list[str] = []
    for pattern in patterns:
        now = group_of(pattern, out)
        if before is None:
            unmet.append(f"advances {pattern}: no pre-act reading")
        elif now is None:
            unmet.append(f"advances {pattern}: no match in the reading")
        elif now == group_of(pattern, before):
            unmet.append(f"advances {pattern}: still {now}")
    return unmet


def _not_increased(patterns: Sequence[str], out: str, before: str | None) -> list[str]:
    """Name the patterns whose number is not strictly greater than in the pre-act reading.

    A value that is not a number, before or after, is refused rather than reasoned about: a mangled
    read is not evidence either way.

    Returns:
        the unmet descriptions; with no pre-act reading every pattern is unmet.

    """
    unmet: list[str] = []
    for pattern in patterns:
        now = _stamp(group_of(pattern, out))
        if before is None:
            unmet.append(f"increases {pattern}: no pre-act reading")
            continue
        was = _stamp(group_of(pattern, before))
        if now is None or was is None:
            unmet.append(f"increases {pattern}: not a number before and after")
        elif now <= was:
            unmet.append(f"increases {pattern}: {now:g} is not above {was:g}")
    return unmet


def _stamp(text: str | None) -> float | None:
    """Read a unix time.

    Returns:
        the number, or None when `text` is absent or not a number.

    """
    try:
        return float(text) if text is not None else None
    except ValueError:
        return None


def _not_fresh(patterns: Sequence[str], out: str, started: float | None) -> list[str]:
    """Name the patterns whose unix time is older than the run's start.

    Returns:
        the unmet descriptions; with no start time every pattern is unmet.

    """
    unmet: list[str] = []
    for pattern in patterns:
        stamp = _stamp(group_of(pattern, out))
        if started is None:
            unmet.append(f"fresh_since {pattern}: no start time")
        elif stamp is None:
            unmet.append(f"fresh_since {pattern}: no time in the reading")
        elif stamp < started:
            unmet.append(f"fresh_since {pattern}: {stamp:g} is before the start {started:g}")
    return unmet


def judge(
    witness: Witness,
    code: int,
    out: str,
    before: str | None = None,
    started: float | None = None,
) -> Result:
    """Judge one witness's exit status and output.

    Returns:
        the Result; its rc is the command's own exit status, or 1 when it exited 0 with something
        unmet.

    """
    unmet = [f"json_empty {key}" for key in non_empty(out, witness.json_empty)]
    unmet += [f"must_contain {text}" for text in witness.must_contain if text not in out]
    unmet += [f"must_match {rx}" for rx in witness.must_match if re.search(rx, out) is None]
    unmet += _not_advanced(witness.advances, out, before)
    unmet += _not_increased(witness.increases, out, before)
    unmet += _not_fresh(witness.fresh_since, out, started)
    return Result(witness.name, code or int(bool(unmet)), tuple(unmet), tail_of(out))


def capture_before(witnesses: Sequence[Witness], run: Run) -> dict[str, str]:
    """Take the pre-act reading of each witness that needs one.

    Returns:
        the output by witness name, for the witnesses that declare `advances`.

    """
    return {w.name: run(w.argv)[1] for w in witnesses if (w.advances or w.increases) and w.argv}


def run_all(
    witnesses: Sequence[Witness],
    run: Run,
    before: Mapping[str, str] | None = None,
    started: float | None = None,
    unevaluated: Callable[[int, str], bool] | None = None,
) -> list[Result]:
    """Run each witness and judge it.

    ⚑ `unevaluated` IS THE CALLER'S OWN CLASSIFIER, NOT A RESERVED EXIT CODE: it takes the command's
    (exit code, output) and says whether the command could not reach what it was to measure. A
    reserved code would collide with a witness command that really exits with it, and would read a
    genuine failure as unevaluated; a classifier the caller writes from the fault signatures it
    knows cannot. It is asked only of a non-zero exit, so a command that exited 0 is always judged.

    Returns:
        one Result per witness, in order; a witness with no argv fails with exit 2; one the
        classifier flags carries `unevaluated` and is not judged against its conditions.

    """
    readings = before or {}
    results: list[Result] = []
    for witness in witnesses:
        if not witness.argv:
            results.append(Result(witness.name, NO_ARGV, ("no argv",), ()))
            continue
        code, out = run(witness.argv)
        if code != 0 and unevaluated is not None and unevaluated(code, out):
            blind = Result(witness.name, code, ("cannot evaluate",), tail_of(out), unevaluated=True)
            results.append(blind)
            continue
        prior = readings.get(witness.name)
        results.append(judge(witness, code, out, before=prior, started=started))
    return results
