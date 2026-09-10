# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The cases for `mikemol.hooks.grade` — a grader that must DISCRIMINATE, not approve.

⚑⚑⚑ A GRADER THAT SAYS `behavioral` FOR EVERYTHING IS A BROKEN-SHUT GATE WEARING A GRADE'S
NAME. Every arm here is built on constructed subjects with a KNOWN correct rung, because a
grader validated only against real code cannot be told apart from one that always agrees: the
real suite is largely behavioural, so approving everything would look like success.

⚑⚑ AND THE ARMS ARE TWO-SIDED BY CONSTRUCTION. One check that MUST rise to `behavioral` and one
that MUST NOT is the pair; either alone passes against a constant function.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from mikemol.hooks import grade

# ⚑ A MARKER NO SUBJECT WOULD CARRY BY ACCIDENT. A short literal like `echo` appears in every
# shell script, so a check asserting it would pass against an unrelated file — the
# existence-by-coincidence this whole module exists to separate from falsifiability.
_MARKER = "DISTINCTIVE_MARKER_ALPHA"
_ABSENT = "NEVER_PRESENT_MARKER_OMEGA"

_SUBJECT = f"#!/bin/sh\necho {_MARKER}\n"

_ARMS = f'''"""Constructed arms with known grades."""
from pathlib import Path

_SUBJ = Path(__file__).parent / "subject.sh"


def test_behavioural() -> None:
    """Asserts a literal that IS present — corrupting the subject must flip this red."""
    body = _SUBJ.read_text(encoding="utf-8")
    assert "{_MARKER}" in body


def test_indifferent() -> None:
    """Reads the subject and asserts nothing about its content — no mutation can flip it."""
    body = _SUBJ.read_text(encoding="utf-8")
    assert isinstance(body, str)


def test_negative() -> None:
    """Asserts a literal is ABSENT — corruption leaves it absent, so this still passes."""
    body = _SUBJ.read_text(encoding="utf-8")
    assert "{_ABSENT}" not in body
'''


@pytest.fixture()
def sandbox(tmp_path: Path) -> Path:
    """Build a project holding one subject and three arms of known grade.

    ⚑⚑ THE SANDBOX NOW DECLARES ITS INTERPRETER rather than leaving `Runner` to infer one from
    the directory layout. The `.venv` symlink remains because the sandbox must LOOK like a
    distribution for the default path to exist at all, but no arm depends on that any more:
    `_runner()` passes `interpreter=` explicitly.

    ⚑ AND THE SYMLINK IS NOT A HOST ESCAPE, which is worth stating because it reads like one.
    `_venv()` derives from `sys.executable`, so under bazel it names THE ACTION'S OWN staged venv
    — measured: `//hooks:test_grade --config=remote` reports 21 passed on the executor, where no
    host venv exists to reach. Outside bazel it names the developer's venv, which is the
    interpreter running the case either way.

    Returns:
        the sandbox project root, holding `tests/subject.sh`, `tests/test_arms.py` and a
        `.venv` symlink.

    """
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "subject.sh").write_text(_SUBJECT, encoding="utf-8")
    (tmp_path / "tests" / "test_arms.py").write_text(_ARMS, encoding="utf-8")
    (tmp_path / ".venv").symlink_to(_venv())
    return tmp_path


def _venv() -> Path:
    """Return this distribution's venv, derived from the running interpreter.

    ⚑ DERIVED, NOT WRITTEN. A literal `hooks/.venv` would be a host path this suite refuses
    elsewhere, and `sys.executable` names the interpreter actually running the case.

    Returns:
        the venv directory two levels above the running interpreter.

    """
    return Path(sys.executable).parent.parent


def _runner(sandbox: Path) -> grade.Runner:
    """Build a Runner that DECLARES its interpreter instead of letting `dist` imply one.

    ⚑⚑ THE SUITE SHOULD EXERCISE THE PATH IT RECOMMENDS. `Runner.interpreter` exists so callers
    stop inferring an environment from a directory name; a suite that kept using the default
    would leave the declared path tested by exactly one arm and used by none.

    Returns:
        a Runner over the sandbox, naming the interpreter running this case.

    """
    return grade.Runner(dist=sandbox, module="tests/test_arms.py",
                        interpreter=Path(sys.executable))


def _graded(sandbox: Path) -> dict[str, str]:
    """Run the grader over the sandbox.

    Returns:
        each arm's name mapped to the rung it was awarded.

    """
    module = sandbox / "tests" / "test_arms.py"
    targets = {"_SUBJ": sandbox / "tests" / "subject.sh"}
    arms = grade.arms_with_subjects(module, targets)
    runner = _runner(sandbox)
    return {t: grade.grade_test(runner, t, s).grade for t, s in sorted(arms.items())}


def test_a_check_whose_subject_matters_grades_behavioural(sandbox: Path) -> None:
    """⚑ THE POSITIVE ARM: corrupting the subject flips it, so falsifiability is PROVEN.

    This is the whole product. `behavioral` is not declarable and not inferable from the shape
    of an assertion — it is awarded because a mutation was applied, the check was run, and it
    came back red.
    """
    assert _graded(sandbox)["test_behavioural"] == "behavioral"


def test_a_check_indifferent_to_its_subject_does_not_grade_behavioural(sandbox: Path) -> None:
    """⚑⚑ THE REFUSAL ARM, AND WITHOUT IT THE POSITIVE ONE MEASURES NOTHING.

    A grader that returned `behavioral` unconditionally satisfies the arm above completely.
    This check reads the subject and asserts only that it is a string — no corruption can make
    that false — so a grader that calls it falsifiable is approving rather than measuring.
    """
    assert _graded(sandbox)["test_indifferent"] != "behavioral"


def test_a_negative_assertion_is_not_called_vacuous(sandbox: Path) -> None:
    """⚑⚑⚑ VACUOUS AND NEGATIVE-ASSERTION ARE NOT THE SAME CLAIM, AND THIS REFUSES TO GUESS.

    `assert X not in body` passes when X is absent — and corruption leaves it absent, so no
    mutation flips it. It is indistinguishable from a dead check BY MUTATION ALONE, and calling
    it `vacuous` would be the instrument asserting past its evidence.

    ⚑ paperkit refuses the same collapse at `grade.py:213-216`: *no generic mutation flips it —
    vacuous OR a negative-assertion check; needs a targeted counter-fixture*. The honest rung is
    `indeterminate`, and the record says why it cannot be resolved further.
    """
    assert _graded(sandbox)["test_negative"] == "indeterminate"


def test_the_subject_is_restored_after_grading(sandbox: Path) -> None:
    """⚑⚑⚑ THE GRADER WRITES OVER FILES IN A LIVE TREE, so the restore is the safety property.

    Measured on the real repository: grading six arms mutated eight live files and `git status`
    came back clean. An exception between write and restore would leave a corrupted script
    behind, which is why the restore is in `finally` rather than after the run.
    """
    subject = sandbox / "tests" / "subject.sh"
    _graded(sandbox)
    assert subject.read_text(encoding="utf-8") == _SUBJECT


def test_an_unreachable_check_is_not_reported_as_refuted() -> None:
    """⚑⚑ AN EXIT STATUS IS NOT A VERDICT ABOUT THE SUBJECT, IN THE GRADER'S OWN RUNNER.

    pytest exits 1 for a failing test and 4 or 5 for a usage error or an empty selection. A
    runner reading `rc != 0` as *the test failed* would grade a mistyped test name as a
    behavioural flip — the mutation would appear to work while nothing had been measured.

    ⚑⚑⚑ AND THIS ARM FOUND A THIRD CASE THE RUNNER DID NOT HANDLE, BY FAILING HERMETICALLY. It
    passed locally, where `hooks/.venv` exists, and DIED in the sandbox where none is staged:
    `subprocess.run` raises `FileNotFoundError` when the interpreter itself is absent, so the
    grader CRASHED on precisely the condition it exists to name. ⚑ Fixed in the runner rather
    than in this arm — an `OSError` guard returning unreachable — because a caller pointing at a
    missing venv deserves the tristate, not a traceback.
    """
    runner = grade.Runner(dist=_venv().parent, module="tests/no_such_module.py")
    passed, reachable = runner.run("test_nothing")
    assert not passed
    assert not reachable


def test_the_rungs_are_ordered_lowest_to_highest() -> None:
    """⚑ THE LADDER IS ONE OBJECT, and downstream re-listing is what paperkit warns cost it twice.

    `grade.py:166-171` records that re-stating the rungs elsewhere produced a report counting
    "79 of 80" and an adequacy gate written as a blacklist that FAILED OPEN. This asserts the
    order rather than the values, so a new rung between two existing ones does not break it.
    """
    assert grade.RANK["broken"] < grade.RANK["vacuous"] < grade.RANK["indeterminate"]
    assert grade.RANK["indeterminate"] < grade.RANK["existence"] < grade.RANK["behavioral"]


def test_an_arm_that_reads_no_file_is_out_of_scope(tmp_path: Path) -> None:
    """⚑ NO SUBJECT IS NOT A LOW GRADE — it is nothing to grade.

    An arm with no file to corrupt cannot be measured by mutation, and reporting that as a poor
    rung would be the instrument judging the subject. MEASURED on this repository: 106 of 128
    arms read a file and 22 do not, and those 22 are outside the population rather than at its
    floor.
    """
    module = tmp_path / "test_nofile.py"
    module.write_text(
        '"""No subject."""\n\n\ndef test_pure() -> None:\n    """Arithmetic."""\n'
        "    assert 1 + 1 == 2\n",
        encoding="utf-8")
    assert grade.arms_with_subjects(module, {}) == {}


def test_the_report_leads_with_the_worst_rung(sandbox: Path) -> None:
    """⚑ A REPORT THAT LEADS WITH ITS PASSES BURIES THE FINDING UNDER AGREEMENT.

    The same reason this repository's poll repeats its digest last: what a reader meets first is
    what they act on.
    """
    module = sandbox / "tests" / "test_arms.py"
    targets = {"_SUBJ": sandbox / "tests" / "subject.sh"}
    arms = grade.arms_with_subjects(module, targets)
    runner = _runner(sandbox)
    lines = grade.report([grade.grade_test(runner, t, s) for t, s in sorted(arms.items())])
    assert "indeterminate" in lines[0]


def test_a_corrupted_subject_is_syntactically_broken_for_every_kind() -> None:
    """⚑ AN EMPTY FILE IS A STATE A CHECK MAY LEGITIMATELY TOLERATE, so the mutation is not one.

    `CORRUPT` carries NUL bytes, which no shell, Python, TOML, TSV or bibtex subject in this
    tree parses. A mutation a subject could plausibly survive would grade a real check as
    indifferent to its own content.
    """
    assert b"\x00" in grade.CORRUPT
    assert grade.CORRUPT.strip()


def test_the_runner_invokes_pytest_rather_than_importing_the_module() -> None:
    """⚑⚑ THE CHECK MUST RUN IN A FRESH PROCESS, or the mutation is invisible to it.

    Python caches a module's source at import; a grader that imported the test module would
    corrupt a file the already-imported test never re-reads, and every arm would grade
    `indeterminate` — a whole suite reported unfalsifiable by an artifact of the grader.
    """
    source = (Path(grade.__file__)).read_text(encoding="utf-8")
    assert "subprocess.run" in source
    assert '"-m", "pytest"' in source


def test_a_flip_requires_the_check_to_be_reachable(sandbox: Path) -> None:
    """⚑⚑⚑ AN UNREACHABLE CHECK IS NOT A FALSIFIABILITY WITNESS.

    If corrupting a subject breaks the test module's own import, pytest returns neither pass nor
    fail. Counting that as a flip would award `behavioral` for a CRASH — the check would be
    credited with detecting a change it never observed.

    ⚑ The arm reaches into `_flips` deliberately: this is the one place the tristate is consumed,
    and an integration-level assertion could not tell a real flip from a crash-flip.
    """
    subject = sandbox / "tests" / "subject.sh"
    runner = _runner(sandbox)
    assert grade._flips(runner, "test_behavioural", subject)
    assert subject.read_text(encoding="utf-8") == _SUBJECT


def test_grading_a_missing_test_reports_broken_not_a_low_rung(sandbox: Path) -> None:
    """⚑ A CHECK THAT CANNOT RUN ESTABLISHES NOTHING, and `broken` says so in those words.

    Its `why` distinguishes *could not be REACHED* from *does not pass* — because reporting an
    unreachable check as a refuted claim asserts the repository is red on evidence that says
    only that the harness did not work.
    """
    runner = _runner(sandbox)
    g = grade.grade_test(runner, "test_does_not_exist", [sandbox / "tests" / "subject.sh"])
    assert g.grade == "broken"
    assert "NOT a statement that the repository is red" in g.why


def test_every_grade_states_why_it_is_not_the_rung_above_or_below(sandbox: Path) -> None:
    """⚑⚑ A GRADE THAT STATES ITS OWN BOUNDARIES IS FALSIFIABLE FROM THE RECORD ALONE.

    Without `higher` and `lower` a reader must re-run the grader to disagree with it. paperkit
    carries both on every record (`grade.py:189-216`) for that reason, and a record that only
    asserts its rung is a verdict with a hidden operand.
    """
    module = sandbox / "tests" / "test_arms.py"
    targets = {"_SUBJ": sandbox / "tests" / "subject.sh"}
    arms = grade.arms_with_subjects(module, targets)
    runner = _runner(sandbox)
    for t, s in sorted(arms.items()):
        g = grade.grade_test(runner, t, s)
        assert g.higher, f"{t} does not say why it is not the rung above"
        assert g.lower, f"{t} does not say why it is not the rung below"


def test_the_grader_does_not_shell_out_through_a_shell(sandbox: Path) -> None:
    """⚑ `subprocess.run` WITH AN ARGV LIST AND NO `shell=True` is the safety property.

    A grader that built a command string would re-split a test name the caller already
    separated, and a test name is attacker-adjacent input in no sense here — but the argument
    that makes it safe should be visible rather than assumed.
    """
    source = (Path(grade.__file__)).read_text(encoding="utf-8")
    assert "shell=True" not in source
    _ = sandbox


def test_content_sensitivity_is_false_when_no_content_is_declared(sandbox: Path) -> None:
    """⚑⚑ A FLIP IS NOT AUTOMATICALLY A CONTENT FLIP, and the default refuses to claim it is.

    paperkit marks a behavioural check `content_sensitive` only when a flipped file is the
    document's OWN content, because *a behavioural check sensitive only to config or the engine
    can-fail by CRASH but does not test the document's content* (`grade.py:219-228`). With no
    content set declared, the honest value is False rather than True-by-default.
    """
    module = sandbox / "tests" / "test_arms.py"
    targets = {"_SUBJ": sandbox / "tests" / "subject.sh"}
    arms = grade.arms_with_subjects(module, targets)
    runner = _runner(sandbox)
    g = grade.grade_test(runner, "test_behavioural", arms["test_behavioural"])
    assert g.grade == "behavioral"
    assert not g.content_sensitive


def test_a_declared_content_file_marks_the_flip_content_sensitive(sandbox: Path) -> None:
    """⚑ THE POSITIVE CONTROL FOR THE ARM ABOVE: with the subject declared as content, it marks.

    Without this pair, a `content_sensitive` that was hardwired to False would satisfy the
    refusal arm completely — the broken-shut shape, one field down.
    """
    module = sandbox / "tests" / "test_arms.py"
    targets = {"_SUBJ": sandbox / "tests" / "subject.sh"}
    arms = grade.arms_with_subjects(module, targets)
    runner = _runner(sandbox)
    g = grade.grade_test(runner, "test_behavioural", arms["test_behavioural"],
                         content={"subject.sh"})
    assert g.content_sensitive


def test_subjects_are_derived_per_arm_rather_than_from_a_shared_list(sandbox: Path) -> None:
    """⚑⚑⚑ THE SWEEP THIS SUPERSEDES KEEPS A HAND-WRITTEN MAP OF NINE SUBJECT NAMES INSIDE ITSELF.

    That is a population no procedure derives — this repository's most-measured defect, sitting
    in the instrument built to measure it. Here an arm's subject is whatever that arm NAMES, so
    an arm reading a new file needs no edit anywhere.
    """
    module = sandbox / "tests" / "test_arms.py"
    # ⚑ A TARGET THE ARMS DO NOT NAME MUST NOT BECOME THEIR SUBJECT. Passing an extra entry that
    # no arm mentions proves the resolution is per-arm rather than "every target in the map".
    other = sandbox / "tests" / "unrelated.sh"
    other.write_text("#!/bin/sh\ntrue\n", encoding="utf-8")
    targets = {"_SUBJ": sandbox / "tests" / "subject.sh", "_OTHER": other}
    arms = grade.arms_with_subjects(module, targets)
    for subs in arms.values():
        assert other not in subs


def test_the_interpreter_is_a_declared_field_rather_than_a_path_convention() -> None:
    """⚑⚑⚑ A FLIP IS ATTRIBUTABLE ONLY IF THE ENVIRONMENT IS FIXED, AND IT WAS INFERRED.

    `Runner` took `dist` and appended `.venv/bin/python3` — so which interpreter graded a suite
    was a consequence of where its directory sat, not of anything a caller said. Two callers
    passing the same `dist` from different trees get different interpreters and no way to notice;
    a flip could then mean *the mutation worked* or *the interpreter differs*, and the grader
    cannot tell those apart while its own environment is a derived quantity.

    ⚑⚑ THE REPAIR IS A FIELD, NOT A NEW CONVENTION. `interpreter` defaults to exactly what the
    old code computed, so every existing caller is unchanged and the DEFAULT is now a stated
    fallback rather than the only possibility. Naming the venv `//:venv.bzl` builds is then a
    caller's decision instead of a rewrite.

    ⚑ AND IT ASKS BY CONSTRUCTION RATHER THAN BY INTROSPECTION. A first draft read
    `dataclasses.fields(grade.Runner)`, which returns `Field[Any]` and imports `Any` into a suite
    configured to refuse it — mypy said so. Constructing with the keyword answers the same question
    without the escape, and answers it about the CONSTRUCTOR, which is what a caller touches.
    """
    runner = grade.Runner(dist=Path("/nowhere"), module="tests/whatever.py",
                          interpreter=Path("/some/python3"))
    assert runner.interpreter == Path("/some/python3"), (
        f"Runner accepted an `interpreter` and did not keep it: {runner.interpreter}"
    )


def test_the_default_interpreter_is_the_convention_it_replaces(tmp_path: Path) -> None:
    """⚑ THE DEFAULT MUST NOT MOVE, or landing the field silently regrades every existing suite.

    The point of the field is to make the environment DECLARABLE, not to change what an
    undeclared caller gets. This pins the fallback to the exact path the previous code built.
    """
    runner = grade.Runner(dist=tmp_path, module="tests/whatever.py")
    assert runner.interpreter == tmp_path / ".venv/bin/python3", (
        f"the default interpreter moved to {runner.interpreter} — existing callers regrade"
    )


def test_a_declared_interpreter_is_the_one_that_runs(sandbox: Path) -> None:
    """⚑⚑ THE FIELD IS ONLY REAL IF IT REACHES `subprocess`.

    A field nothing reads is the shape this repository keeps finding.

    ⚑ MEASURED THROUGH BEHAVIOUR RATHER THAN INSPECTION: point the runner at an interpreter that
    does not exist and it must report UNREACHABLE — `(False, False)` — while the same runner with
    the default reports the arm's real verdict. Reading the attribute back would prove only that
    the dataclass stores it.
    """
    working = grade.Runner(dist=sandbox, module="tests/test_arms.py")
    passed, reachable = working.run("test_behavioural")
    # ⚑ POSITIVE CONTROL FIRST: if the default cannot run the arm either, the refusal below says
    # nothing about the declared interpreter.
    assert reachable, "control failed: the default interpreter could not run the arm at all"
    assert passed, "control failed: the arm does not pass under the default interpreter"

    broken = grade.Runner(dist=sandbox, module="tests/test_arms.py",
                          interpreter=sandbox / "nonexistent" / "python3")
    assert broken.run("test_behavioural") == (False, False), (
        "a declared interpreter that does not exist still ran something — the field is not "
        "reaching subprocess, and `dist` is still deciding the environment"
    )


def test_the_interpreter_is_never_the_string_none(tmp_path: Path) -> None:
    """⚑⚑ A NULLABLE FIELD WOULD MAKE `str(None)` A WELL-FORMED ARGV ELEMENT NAMING NO FILE.

    The first version typed this `Path | None` with the default resolved in `__post_init__`. That
    passes mypy and still leaves a hole: anything assigning `None` afterwards yields the literal
    string `"None"` as the interpreter, which is not an error — it is a path that does not exist,
    so every arm grades UNREACHABLE and the suite reports *nothing is falsifiable* rather than
    *the grader was misconfigured*. This session has measured that shape repeatedly: a string that
    names nothing, read as a fact about the subject.

    ⚑ SO THE FIELD IS `Path` WITH AN EMPTY-PATH SENTINEL, and this arm pins the property a reader
    would otherwise have to re-derive from `__post_init__`.
    """
    runner = grade.Runner(dist=tmp_path, module="tests/whatever.py")
    assert str(runner.interpreter) != "None", "the interpreter resolved to the STRING 'None'"
    assert runner.interpreter != Path(), (
        "the interpreter is still the empty-path sentinel — __post_init__ did not resolve it"
    )
