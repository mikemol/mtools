# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The verdict record authority: the one place that makes a verdict record.

A verdict is an oracle's answer, a record of a verb and a verdict word. The oracle differs per
verb (does a file exist, does a command exit 0, do several producers agree, does a calculation's
baseline hold, do sibling records read pass), but the record is one type.

Centralising it kills the format-drift class. Every record is written compact and stable, and
every consumer PARSES the record; it never greps the bytes. A grep-against-emit spacing mismatch
once silently dropped fails: a failing record written with the default JSON spacing was never
matched by a gate that grepped for the compact spelling, so a failed check went green. One writer
and parsing consumers make that unrepresentable.

    mikemol-gradekit-verdict emit   <verb> <pass|fail|cannot-run> <out> [--account FILE]
    mikemol-gradekit-verdict exists <verb> <path> <out>
    mikemol-gradekit-verdict agg    <verb> <out> <field> <bad> <record>...
    mikemol-gradekit-verdict agree  <verb> <out> <produced>...
    mikemol-gradekit-verdict calc   <verb> <calc.json> <out>
    mikemol-gradekit-verdict cohere <verb> <project> <out> <calc>... [--coherence SCRIPT]
    mikemol-gradekit-verdict canary <pos.json> <nul.json> <out>

`agg` passes iff no record has the field in the bad set, a comma list. For an adequacy floor the
bad set is `below:<grade>`, derived from the ladder. `agree` passes iff at least two produced
outputs exist, all byte-equal, none marked failed. `canary` passes iff the guaranteed-flip
evaluation flipped and the null identity did not; anything else means the harness itself is
degraded, and it fails loudly with a named message, never a silent green.

The verdict is a tristate: pass, fail, or cannot-run. A cannot-run is a check whose host toolchain
is absent, and it is not a failure: the aggregator's bad set is the failing word alone, so it does
not turn the gate red on a machine without the toolchain, yet it stays distinguishable from a pass.

The record writer is `mikemol.atomicwrite.durable.write_atomic`. An earlier copy of it lived in the
paperkit original so the tool could be staged into a sandbox as a lone file, with a test gating the
two for agreement. This package is installed beside its dependencies, so the copy is gone.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.atomicwrite.durable import write_atomic
from mikemol.grade.grade import below
from mikemol.gradekit.cli import UsageError, report, take_options
from mikemol.gradekit.jsonio import RecordError, as_record, read_json

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.grade.grade import Json, Record

VERDICT_WORDS = ("pass", "fail", "cannot-run")
TAIL_LINES = 40
AGG_WHY_LIMIT = 400
COHERE_WHY_LIMIT = 2000
COHERE_CANNOT_RUN_STATUS = 2
PAIR = 2
DEFAULT_COHERENCE = "paperkit/coherence.py"
FLOOR_PREFIX = "below:"
ALLOWED_OPTIONS = {
    "emit": ("account",),
    "exists": (),
    "agg": (),
    "agree": (),
    "calc": (),
    "cohere": ("coherence",),
    "canary": (),
}
ARITY = {"emit": 3, "exists": 3, "agg": 4, "agree": 2, "calc": 3, "cohere": 3, "canary": 3}
EXACT = frozenset({"emit", "exists", "calc", "canary"})


class VerdictError(Exception):
    """A verdict command cannot be carried out as asked."""


def verdict_word(*, ok: bool) -> str:
    """Name a boolean outcome as a verdict word.

    Returns:
        `pass` when `ok`, else `fail`.

    """
    return "pass" if ok else "fail"


def account_tail(path: Path) -> list[str]:
    """Read the last non-blank lines of a check's own standard error.

    A check cell exits 0 and reports its verdict as a record, so the build system never sees a
    failed action and never prints the error it captured. Folding the tail into the record is how
    the failure travels with the artifact.

    Returns:
        At most the last forty non-blank lines, or none if the file cannot be read.

    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [line for line in text.splitlines() if line.strip()][-TAIL_LINES:]


def write_record(
    out: Path,
    verb: str,
    verdict: str,
    why: str = "",
    account: Path | None = None,
) -> None:
    """Write one compact verdict record to `out`, atomically.

    The record may carry its reason, and omitting it is a lossy verdict: a log line is read by
    whoever is watching, a record is read by whatever comes next. `why` is absent from the record
    when empty, so every record without one is byte-identical to what it always was. A failing
    check's own error tail rides the record under `account` on a non-pass; a pass carries none,
    since a green check's error output is noise.
    """
    record: Record = {"verb": verb, "verdict": verdict}
    if why:
        record["why"] = why
    if account is not None and verdict != "pass":
        tail = account_tail(account)
        if tail:
            lines: list[Json] = [*tail]
            record["account"] = lines
    write_atomic(out, json.dumps(record, separators=(",", ":")) + "\n")


def bad_set(bad: str) -> set[str]:
    """Resolve the bad-value argument of the aggregator.

    `below:<floor>` derives the failing set from the ladder instead of naming it. A literal list
    of failing grades makes an adequacy gate fail OPEN: every rung added to the ladder afterwards
    is absent from the list and passes by default. Asking the ladder judges a new rung the moment
    it exists, and a floor that is not a rung is refused rather than quietly grading everything
    green.

    Returns:
        The lower-cased values that count as failing.

    Raises:
        VerdictError: The floor is not a rung of the ladder.

    """
    if bad.startswith(FLOOR_PREFIX):
        floor = bad[len(FLOOR_PREFIX) :]
        try:
            return set(below(floor))
        except KeyError as exc:
            msg = f"{floor!r} is not a rung of the grade ladder"
            raise VerdictError(msg) from exc
    return {item.lower() for item in bad.split(",")}


def field_value(record_path: Path, name: str) -> str:
    """Read one field of a record file as lower-cased text.

    Returns:
        The field's text; an absent field reads as `none`.

    """
    record = as_record(read_json(record_path), str(record_path))
    return str(record.get(name)).lower()


def run_emit(args: Sequence[str], options: dict[str, list[str]]) -> None:
    """Record a verdict the caller computed; any word but the three verdicts fails closed."""
    verb, word, out = args
    account = Path(options["account"][-1]) if "account" in options else None
    write_record(Path(out), verb, word if word in VERDICT_WORDS else "fail", account=account)


def run_exists(args: Sequence[str], _options: dict[str, list[str]]) -> None:
    """Record pass iff the named path is present."""
    verb, path, out = args
    write_record(Path(out), verb, verdict_word(ok=Path(path).exists()))


def run_agg(args: Sequence[str], _options: dict[str, list[str]]) -> None:
    """Record pass iff no named record has the field in the bad set.

    The offenders are named in the record, not only the conjunction. They were already computed to
    decide it, and a record that says only that the aggregate failed sends the reader to hunt for
    which input broke.
    """
    verb, out, name, bad, *records = args
    values = [(path, field_value(Path(path), name)) for path in records]
    bad_values = bad_set(bad)
    offenders = [(path, value) for path, value in values if value in bad_values]
    why = "; ".join(f"{Path(path).name}={value}" for path, value in offenders)[:AGG_WHY_LIMIT]
    write_record(Path(out), verb, verdict_word(ok=not offenders), why=why)


def run_agree(args: Sequence[str], _options: dict[str, list[str]]) -> None:
    """Record pass iff at least two produced outputs exist, are byte-equal, and none failed.

    The whole output is compared, not one line of it: a producer's output is a document, and
    collapsing to lines would demand every producer be a single line.
    """
    verb, out, *produced = args
    texts = [Path(path).read_text(encoding="utf-8") for path in produced]
    distinct = set(texts)
    agreed = len(texts) >= PAIR and len(distinct) == 1 and "__FAIL__" not in next(iter(distinct))
    write_record(Path(out), verb, verdict_word(ok=agreed))


def run_calc(args: Sequence[str], _options: dict[str, list[str]]) -> None:
    """Record pass iff the calculation record's baseline holds."""
    verb, calc, out = args
    record = as_record(read_json(Path(calc)), calc)
    write_record(Path(out), verb, verdict_word(ok=bool(record.get("baseline"))))


def cohere_word(returncode: int) -> str:
    """Map the coherence tool's exit status to a verdict word.

    Zero, one and two are three states. One is a real refutation, and two is a reading the tool
    could not honestly make, such as a calculation set covering part of the graph. Collapsing both
    to fail would score a cannot-run as a refutation.

    Returns:
        `pass` for 0, `cannot-run` for 2, else `fail`.

    """
    if returncode == 0:
        return "pass"
    return "cannot-run" if returncode == COHERE_CANNOT_RUN_STATUS else "fail"


def run_cohere(args: Sequence[str], options: dict[str, list[str]]) -> None:
    """Record the verdict of the coherence tool over the named calculations.

    Its standard error is let through to the caller's, and it also lands in the record's reason,
    capped to its last lines, which carry the diagnosis. The record is a verdict, not a transcript.
    """
    verb, project, out, *calcs = args
    script = options["coherence"][-1] if "coherence" in options else DEFAULT_COHERENCE
    proc = subprocess.run(
        [sys.executable, script, "--from-calcs", project, *calcs],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    why = proc.stderr.strip()[-COHERE_WHY_LIMIT:] if proc.returncode != 0 else ""
    write_record(Path(out), verb, cohere_word(proc.returncode), why)


def run_canary(args: Sequence[str], _options: dict[str, list[str]]) -> None:
    """Record whether the harness is sound: the flip cell flipped and the null identity did not.

    Both directions are asserted, because a gate is sound both ways. A failure is named: the
    degraded state says that it degraded, and why a sandbox that is not hermetic causes it, since
    such a sandbox lets checks resolve to the real unmutated tree.
    """
    pos_path, nul_path, out = args
    pos = as_record(read_json(Path(pos_path)), pos_path)
    nul = as_record(read_json(Path(nul_path)), nul_path)
    ok = pos.get("flipped") is True and nul.get("flipped") is False
    if not ok:
        sys.stderr.write(
            "verdict canary: HARNESS DEGRADED - "
            f"guaranteed-flip mutation flipped={pos.get('flipped')}, "
            f"null identity flipped={nul.get('flipped')}. A non-hermetic sandbox lets checks "
            "resolve to the real unmutated tree; run under the hermetic mutant configuration.\n",
        )
    write_record(Path(out), "canary", verdict_word(ok=ok))


COMMANDS = {
    "emit": run_emit,
    "exists": run_exists,
    "agg": run_agg,
    "agree": run_agree,
    "calc": run_calc,
    "cohere": run_cohere,
    "canary": run_canary,
}


def dispatch(words: Sequence[str]) -> None:
    """Carry out the command named first in `words`.

    Raises:
        UsageError: No command, an unknown command, or the wrong number of arguments for it.

    """
    if not words or words[0] not in COMMANDS:
        msg = f"usage: mikemol-gradekit-verdict <{'|'.join(COMMANDS)}> ..."
        raise UsageError(msg)
    name = words[0]
    args, options = take_options(words[1:], ALLOWED_OPTIONS[name])
    fixed = ARITY[name]
    if len(args) < fixed or (name in EXACT and len(args) != fixed):
        msg = f"{name}: expected {'exactly ' if name in EXACT else 'at least '}{fixed} arguments"
        raise UsageError(msg)
    COMMANDS[name](args, options)


def main(argv: Sequence[str] | None = None) -> int:
    """Write the verdict record the command line asks for.

    Returns:
        0 once the record is written, whatever its verdict; 2 for a usage error, an unreadable or
        malformed input, or a floor that is not a rung.

    """
    try:
        dispatch(sys.argv[1:] if argv is None else argv)
    except (UsageError, RecordError, VerdictError, OSError) as err:
        return report("mikemol-gradekit-verdict", err)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
