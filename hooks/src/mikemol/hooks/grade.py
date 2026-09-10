# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Grade a test by MUTATING ITS SUBJECT and watching whether it flips red.

⚑⚑⚑ AN EXISTENCE CHECK IS NOT A BEHAVIOURAL ONE, AND THIS REPOSITORY HAD ONLY THE FIRST.
`test_no_string_assertion_in_this_module_is_vacuous` reads a test's SOURCE and confirms each
asserted literal appears in the file that test reads. That establishes the literal is present.
It establishes nothing about whether the test would FAIL if the subject changed — and a check
that cannot fail is the thing the whole suite exists to refuse.

⚑⚑ THE LADDER IS PAPERKIT'S, READ FROM ITS SOURCE RATHER THAN ITS DOCS (`paperkit/grade.py:17`):

    vacuous(0) < indeterminate(1) < existence(1) < behavioral(2) < imported(3)

with the parenthetical at `grade.py:21` giving the whole distinction —
*existence (presence proven) < behavioral (falsifiability proven)*.

⚑ SO A GREEN VACUITY SWEEP IS `existence`, TWO RUNGS BELOW `behavioral` (ranked 0 and 2 at
`paperkit/grade.py:24`). Passing it means rung 0 was avoided, not that rung 2 was reached. That
gap is what this module measures, and the remedy is paperkit's own sentence at
`grader.py:477`: *to rise: test the artifact's CONTENT, not just its presence*.

⚑⚑⚑ BEHAVIOURAL IS NOT DECLARABLE. It is awarded by a measured mutate-run-restore sweep and by
nothing else: corrupt one site of the subject, run the test, restore. If the test flips red, the
mutation is a WITNESS that the test could have failed. `paperkit/grader.py:312` states the
property this module copies — *each reported site is a confirmed single-mutation flip, never
assumed*.

⚑ AND `broken` SPLITS UNREACHABLE FROM REFUTED, because an exit status is not a verdict about
the subject. A test that could not RUN establishes nothing; reporting that as "the repo is red"
is the same conflation this repository has measured seven times in its own checkers.
"""

from __future__ import annotations

import ast
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

# ⚑ THE RUNGS, AND THE ORDER IS THE POINT. Written once here so a reader downstream cannot
# re-list them: paperkit records at `grade.py:166-171` that re-listing rungs downstream caused
# two real failures, one of them an adequacy gate written as a blacklist that FAILED OPEN.
RANK = {"broken": -1, "vacuous": 0, "indeterminate": 1, "existence": 2, "behavioral": 3}

# The bytes written over a subject to corrupt it. Not empty: an empty file is a plausible state
# a check might legitimately tolerate, while this is syntactically broken for every subject kind
# the suite reads (shell, python, toml, tsv, bibtex).
CORRUPT = b"\x00CORRUPTED-BY-GRADER\x00\n"


@dataclass(frozen=True)
class Grade:
    """One test's rung, with the evidence that put it there.

    ⚑ `higher` AND `lower` ARE NOT DECORATION. paperkit records both on every grade
    (`grade.py:189-216`), so a record states its own boundaries and a reader can falsify it from
    the record alone rather than having to re-run the grader to disagree.
    """

    test: str
    grade: str
    why: str
    higher: str
    lower: str
    flipped: tuple[str, ...] = ()
    subjects: tuple[str, ...] = ()
    content_sensitive: bool = False

    @property
    def rank(self) -> int:
        """Where this grade sits in the ladder."""
        return RANK[self.grade]


@dataclass
class Runner:
    """Runs one test and reports whether it passed, distinguishing *could not run*.

    ⚑⚑ THE TRISTATE IS LOAD-BEARING. `passed` and `reachable` are separate because a test that
    errored during collection and a test that failed its assertion are different facts, and
    collapsing them makes a broken harness read as a refuted claim.
    """

    dist: Path
    module: str

    # ⚑⚑⚑ THE INTERPRETER IS DECLARED, NOT INFERRED — AND IT USED TO BE INFERRED FROM A DIRECTORY
    # NAME. `dist / ".venv/bin/python3"` made *which interpreter graded a suite* a consequence of
    # where its directory sat, so two callers passing the same `dist` from different trees got
    # different environments with no way to notice. A mutation flip is only ATTRIBUTABLE if the
    # environment is fixed: otherwise a red arm means *the mutation worked* OR *the interpreter
    # differs*, and the instrument built to separate those cannot separate its own.
    # ⚑⚑ THE DEFAULT IS THE OLD CONVENTION, EXACTLY, so no existing caller regrades — what changes
    # is that the fallback is now STATED rather than being the only possibility. `//:venv.bzl`
    # builds a real `<dist>/.venv` per distribution, and naming it is now a caller's decision.
    # ⚑ `Path` AND NOT `Path | None`, WITH THE DEFAULT RESOLVED IN `__post_init__` VIA A FIELD
    # SENTINEL. A nullable field would leave `str(self.interpreter)` able to produce the literal
    # string "None" — a well-formed argv element naming no file, which is this session's most
    # measured shape and would surface as *every arm unreachable* rather than as an error.
    # The empty `Path()` is the sentinel because a caller cannot mean it: it names the cwd, not an
    # interpreter, and `Path("")` compares equal to `Path(".")` only after resolution.
    interpreter: Path = field(default_factory=Path)

    def __post_init__(self) -> None:
        """Resolve the interpreter default once, so `run` reads a settled value."""
        if self.interpreter == Path():
            self.interpreter = self.dist / ".venv/bin/python3"

    def run(self, test: str) -> tuple[bool, bool]:
        """Run one test by name. Returns `(passed, reachable)`.

        Returns:
            `(True, True)` when the test passed; `(False, True)` when it ran and failed;
            `(False, False)` when pytest could not run it at all.

        """
        # ⚑⚑⚑ A MISSING INTERPRETER IS UNREACHABLE, NOT A TRACEBACK. `subprocess.run` raises
        # `FileNotFoundError` when the executable does not exist, and an unhandled raise here
        # would propagate out of a GRADER — the one place whose whole product is distinguishing
        # *could not run* from *ran and failed*. MEASURED in the hermetic sandbox, where no
        # `.venv` is staged: the arm asserting this runner reports unreachable instead DIED on
        # the missing python3, so the grader crashed on exactly the condition it exists to name.
        # ⚑ `OSError` COVERS THE FAMILY, not just the missing file: a non-executable interpreter
        # raises `PermissionError`, and both are the same fact — the runner could not start.
        try:
            proc = subprocess.run(
                [str(self.interpreter), "-m", "pytest", self.module,
                 "-k", test, "-q", "--no-header", "-p", "no:cacheprovider"],
                capture_output=True, text=True, check=False, cwd=str(self.dist),
            )
        except OSError:
            return False, False
        # ⚑ EXIT 0 IS PASS, 1 IS A FAILING TEST, ANYTHING ELSE IS THE RUNNER NOT RUNNING.
        # pytest's own convention: 2 is interrupted, 3 internal error, 4 usage, 5 no tests
        # collected. Reading `rc != 0` as "the test failed" would grade a typo'd test name as a
        # behavioural flip — the mutation would appear to work while nothing was measured.
        if proc.returncode == 0:
            return True, True
        if proc.returncode == 1:
            return False, True
        return False, False


def subjects_of(fn: ast.FunctionDef, targets: dict[str, Path]) -> list[Path]:
    """Return the files this test reads, resolved from the names it mentions.

    ⚑ PER-ARM AND DERIVED, NOT A SHARED LIST. The sweep this module supersedes keeps a
    hand-written map of nine subject names inside itself — a population no procedure derives,
    which is this repository's most-measured defect. Here the subject is whatever the arm
    actually names, so an arm reading a new file needs no edit anywhere.

    Returns:
        every target file this arm names, in walk order, skipping names that resolve to a
        directory or a path that does not exist.

    """
    return [
        targets[n.id]
        for n in ast.walk(fn)
        if isinstance(n, ast.Name) and n.id in targets and targets[n.id].is_file()
    ]


def arms_with_subjects(module: Path, targets: dict[str, Path]) -> dict[str, list[Path]]:
    """Map each test arm to the subject files it reads.

    ⚑ AN ARM THAT READS NO FILE IS OUT OF SCOPE, NOT FAILING. It has no site to corrupt, so a
    mutation grader can say nothing about it — and reporting that as a low grade would be the
    instrument judging the subject. MEASURED on this repository: 106 of 128 arms read a file,
    22 do not; 106 + 22 = 128 from two independent counts.

    Returns:
        every `test_`-prefixed function that reads at least one resolvable subject, mapped to
        those subjects.

    """
    tree = ast.parse(module.read_text(encoding="utf-8"))
    out: dict[str, list[Path]] = {}
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or not fn.name.startswith("test_"):
            continue
        reads = any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "read_text"
            for n in ast.walk(fn)
        )
        if not reads:
            continue
        subs = subjects_of(fn, targets)
        if subs:
            out[fn.name] = subs
    return out


def _flips(runner: Runner, test: str, subject: Path) -> bool:
    """Corrupt one subject, run the test, restore. True iff the test flips red.

    ⚑⚑⚑ THE RESTORE IS IN `finally` AND THAT IS NOT OPTIONAL. This writes over a file in a live
    working tree; an exception between write and restore would leave the repository corrupted.
    paperkit's `_apply` (`grader.py:270-302`) takes the same precaution for the same reason.

    Returns:
        whether corrupting this subject turned the test red — False both when the test still
        passes and when it could not run at all, since a crash is not a falsifiability witness.

    """
    saved = subject.read_bytes()
    try:
        subject.write_bytes(CORRUPT)
        passed, reachable = runner.run(test)
        # ⚑ UNREACHABLE IS NOT A FLIP. If corrupting the subject broke the test module's own
        # import, pytest cannot run and returns neither pass nor fail — counting that as a
        # falsifiability witness would award `behavioral` for a crash.
        return reachable and not passed
    finally:
        subject.write_bytes(saved)


def grade_test(runner: Runner, test: str, subjects: Sequence[Path],
               content: Iterable[str] = ()) -> Grade:
    """Grade one test by mutating each of its subjects in turn.

    Returns:
        the `Grade`, with every subject whose corruption flipped the test recorded as evidence.

    """
    passed, reachable = runner.run(test)
    if not passed:
        return Grade(
            test=test, grade="broken",
            why=("the test could not be REACHED in a pristine tree — nothing was established "
                 "about it, and this is NOT a statement that the repository is red")
                if not reachable else
                "the test does not pass in a pristine tree — the repository is not green",
            higher="—", lower="—",
            subjects=tuple(str(s) for s in subjects),
        )

    flipped = tuple(str(s) for s in subjects if _flips(runner, test, s))
    if flipped:
        names = set(content)
        return Grade(
            test=test, grade="behavioral", flipped=flipped,
            subjects=tuple(str(s) for s in subjects),
            why=f"falsifiable — corrupting {len(flipped)} subject(s) flips it red",
            higher="behavioral is the top rung this grader awards; a proof grade is not defined",
            lower=f"not indeterminate: a mutation DOES flip it ({len(flipped)} subject(s))",
            # ⚑ CONTENT-SENSITIVE, paperkit `grade.py:219-228`: a check sensitive only to config
            # or the engine *can-fail by CRASH but does not test the document's content*. The
            # flip must come from the SUBJECT, or "could have failed" is not "could have failed
            # for the right reason".
            content_sensitive=any(Path(f).name in names for f in flipped) if names else False,
        )
    return Grade(
        test=test, grade="indeterminate",
        subjects=tuple(str(s) for s in subjects),
        why=("no mutation of its subjects flips it — VACUOUS, or a NEGATIVE assertion that a "
             "corrupted subject satisfies just as well"),
        higher="to rise: a targeted counter-fixture — a mutation that SHOULD flip it",
        lower=("not provably vacuous: a negative assertion is a real claim, and this grader "
               "cannot tell the two apart without a counter-fixture"),
    )


def _by_rung(g: Grade) -> tuple[int, str]:
    """Sort key: worst rung first, then by name.

    ⚑ A NAMED FUNCTION RATHER THAN A `key=lambda`, and this is measured rather than stylistic.
    Under `disallow_any_expr` a lambda's parameter has no annotation, so mypy types the whole
    sort as `Any` and reports three errors at one line — the same defect `mdstruct/lint.py`
    solved with its `_at` key. An unannotated callable poisons every expression through it.

    Returns:
        the grade's rank paired with its test name, so equal rungs order by name.

    """
    return (g.rank, g.test)


def report(grades: Iterable[Grade]) -> list[str]:
    """Render the grades as lines, worst rung first.

    ⚑ SORTED BY RANK SO THE FLOOR IS READ FIRST. A report that leads with its passes buries the
    finding under agreement — the same reason this repository's poll repeats its digest last.

    Returns:
        one line per grade, plus a tally by rung.

    """
    ordered = sorted(grades, key=_by_rung)
    lines = [f"  {g.grade:14} {g.test}" + (f"  [{len(g.flipped)} flip(s)]" if g.flipped else "")
             for g in ordered]
    tally: dict[str, int] = {}
    for g in ordered:
        tally[g.grade] = tally.get(g.grade, 0) + 1
    lines.append("  " + "  ".join(f"{k}={v}" for k, v in sorted(tally.items())))
    return lines


__all__ = ["CORRUPT", "RANK", "Grade", "Runner", "arms_with_subjects", "grade_test", "report",
           "subjects_of"]
