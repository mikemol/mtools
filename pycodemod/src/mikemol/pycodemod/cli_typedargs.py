# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`typed-args` and its kin: plan each file, check the prospective output with the project's tools.

⚑⚑ A FILE IS WRITTEN ONLY WHEN THE TARGET PROJECT'S OWN JUDGE SAYS IT GOT BETTER (operator
2026-09-01: a codemod runs the checks on what it is about to write). The candidate text goes to a
probe file beside the real one, has its imports sorted and its unused imports dropped and is
formatted with the project's `ruff`, and is measured with the project's `mypy` beside the original
text measured the same way. It is accepted when the findings' MESSAGES, as a multiset, are a
subset of the original's and there are strictly fewer of them: a set comparison, not a count, so a
fixed finding that trades for a new one is refused and the new message is named. Anything else
goes to the worklist, printed with its reason; nothing is written.

⚑ THE JUDGE IS ONE FUNCTION AND THE PLANNER IS A PARAMETER: `typed-args` and `or-empty` differ only
in how a file's text becomes a candidate (a `Plan`); both are measured, written and reported here
by the same code, so a second codemod adds a planner, never a second judge.

⚑ THE PROBE EXISTS FOR SECONDS AND IS REMOVED ON EVERY EXIT. It must sit inside the project so mypy
and ruff resolve its imports and read its configuration (a temp file elsewhere is judged under
other rules than the file it stands for), and a codemod run beside other sessions leaves nothing
behind in a shared tree.

⚑ A TOOL THAT CANNOT RUN IS NOT A CLEAN BILL: mypy and ruff exit 0 or 1 for "judged", and anything
else is exit 2 here, never a pass.

    mikemol-pycodemod typed-args --root PROJECT [--write] FILE...
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.procrun import proc

from mikemol.pycodemod import typedargs

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

type Runner = Callable[[Sequence[str], Path], tuple[int, str, str]]

TIMEOUT_S = 300.0
PROBE_PREFIX = "_typedargs_probe_"
JUDGED = frozenset({0, 1})
CLIP = 200
LABEL = "typed-args"


@dataclass(frozen=True, slots=True)
class TypedArgsFlags:
    """What a judged codemod was asked: the project to judge in, and write or not."""

    root: str
    write: bool


@dataclass(frozen=True, slots=True)
class Plan:
    """A planner's answer for one file: the candidate text, how many sites changed, the worklist.

    `worklist` holds (line, function, why) for what the planner refused to touch.
    """

    text: str
    changes: int
    worklist: tuple[tuple[int, str, str], ...] = ()


type Planner = Callable[[str], Plan]


@dataclass(frozen=True, slots=True)
class Verdict:
    """The judge's reading of one candidate: accepted or not, the counts, and the formatted text."""

    ok: bool
    before: int
    after: int
    new: list[str]
    text: str
    error: str | None = None


def run_tool(argv: Sequence[str], cwd: Path) -> tuple[int, str, str]:
    """Run a tool to completion in `cwd` through procrun's one seam.

    Returns:
        the exit code, stdout and stderr.

    """
    done = proc.capture(argv, cwd=cwd, timeout=TIMEOUT_S)
    return done.returncode, done.stdout, done.stderr


def _say(line: str) -> None:
    sys.stdout.write(f"{line}\n")


def _mypy(root: Path, rel: Path, run: Runner) -> Counter[str] | str:
    # The multiset of mypy messages for one file, or why mypy could not judge it.
    argv = [str(root / ".venv" / "bin" / "mypy"), "--no-error-summary", "--output", "json"]
    code, out, err = run([*argv, str(rel)], root)
    if code not in JUDGED:
        return f"mypy could not run (exit {code}): {err.strip()[:CLIP]}"
    found: Counter[str] = Counter()
    for line in out.splitlines():
        if line.startswith("{"):
            record = cast("dict[str, object]", json.loads(line))
            if record.get("file") == rel.as_posix():
                found[str(record["message"])] += 1
    return found


def _format(root: Path, rel: Path, run: Runner) -> str | None:
    # Sort imports, drop unused ones, then format the probe in place with the project's ruff;
    # None when all of it ran, else why not. A rewrite that leaves `cast` unused or adds an
    # import out of order is judged AFTER the project's own sorter has had its say.
    ruff = str(root / ".venv" / "bin" / "ruff")
    fix, _, fix_err = run([ruff, "check", "--select", "I,F401", "--fix", "--quiet", str(rel)], root)
    if fix not in JUDGED:
        return f"ruff check could not run (exit {fix}): {fix_err.strip()[:CLIP]}"
    code, _, err = run([ruff, "format", str(rel)], root)
    return None if code == 0 else f"ruff format could not run (exit {code}): {err.strip()[:CLIP]}"


def _failed(candidate: str, why: str) -> Verdict:
    return Verdict(ok=False, before=0, after=0, new=[], text=candidate, error=why)


def _verdict(before: Counter[str], after: Counter[str], text: str) -> Verdict:
    new = sorted((after - before).elements())
    total_before, total_after = sum(before.values()), sum(after.values())
    ok = not new and total_after < total_before
    return Verdict(ok=ok, before=total_before, after=total_after, new=new, text=text)


def judge(root: Path, rel: Path, original: str, candidate: str, run: Runner) -> Verdict:
    """Judge a candidate against its original under the project's own mypy and ruff.

    Returns:
        the Verdict; `error` is set (and nothing is accepted) when a tool could not run.

    """
    probe_rel = rel.with_name(PROBE_PREFIX + rel.name)
    probe = root / probe_rel
    try:
        probe.write_text(original, encoding="utf-8")
        before = _mypy(root, probe_rel, run)
        probe.write_text(candidate, encoding="utf-8")
        failed = _format(root, probe_rel, run)
        text = probe.read_text(encoding="utf-8")
        after = _mypy(root, probe_rel, run)
    finally:
        probe.unlink(missing_ok=True)
    for problem in (before, after, failed):
        if isinstance(problem, str):
            return _failed(candidate, problem)
    return _verdict(cast("Counter[str]", before), cast("Counter[str]", after), text)


def _relative(root: Path, path: Path) -> Path | None:
    try:
        return path.resolve().relative_to(root)
    except ValueError:
        return None


def _settle(label: str, path: Path, changes: int, verdict: Verdict, *, write: bool) -> int:
    # Say what happened to a judged file, write it only if accepted; the exit contribution.
    moved = f"findings {verdict.before}->{verdict.after}"
    if verdict.error is not None:
        _say(f"{label} error {path}: {verdict.error}")
        return 2
    if not verdict.ok:
        news = "; ".join(verdict.new) if verdict.new else "no fewer findings"
        _say(f"{label} rejected {path} {moved} parsers={changes}: {news}")
        return 1
    if write:
        path.write_text(verdict.text, encoding="utf-8")
    _say(f"{label} {'written' if write else 'would-write'} {path} {moved} parsers={changes}")
    return 0


def _check_file(
    root: Path, path: Path, flags: TypedArgsFlags, run: Runner, plan: tuple[str, Planner]
) -> int:
    # Plan one file, judge a changed candidate; the exit contribution (0 ok, 1 worklist, 2 error).
    label, planner = plan
    rel = _relative(root, path)
    if rel is None:
        _say(f"{label} error {path}: not under {root}")
        return 2
    try:
        original = path.read_text(encoding="utf-8")
    except OSError as exc:
        _say(f"{label} error {path}: {exc}")
        return 2
    planned = planner(original)
    for line, function, why in planned.worklist:
        _say(f"{label} refused {path}:{line} {function}: {why}")
    worklist = 1 if planned.worklist else 0
    if not planned.changes:
        return worklist
    verdict = judge(root, rel, original, planned.text, run)
    return max(worklist, _settle(label, path, planned.changes, verdict, write=flags.write))


def typedargs_plan(text: str) -> Plan:
    """Plan `typed-args` for one file's text through typedargs.plan.

    Returns:
        the Plan: the candidate text, the parser count, and each refusal as a worklist row.

    """
    planned = typedargs.plan(text)
    refused = tuple((r.line, r.function, r.why) for r in planned.refusals)
    return Plan(planned.text, planned.parsers, refused)


def print_judged(
    paths: Sequence[str], flags: TypedArgsFlags, plan: tuple[str, Planner], run: Runner = run_tool
) -> int:
    """Run one planner over files: report, judge each changed candidate, write the accepted.

    Returns:
        0 when every file was done or untouched, 1 when any is on the worklist (a refusal or a
        rejected candidate), 2 when a tool could not run or a file could not be read.

    """
    root = Path(flags.root).resolve()
    code = 0
    for name in paths:
        code = max(code, _check_file(root, Path(name), flags, run, plan))
    return code


def print_typedargs(paths: Sequence[str], flags: TypedArgsFlags, run: Runner = run_tool) -> int:
    """Run `typed-args` over files; see `print_judged`.

    Returns:
        the exit code `print_judged` computed.

    """
    return print_judged(paths, flags, (LABEL, typedargs_plan), run)
