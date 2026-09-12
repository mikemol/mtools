# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A flag a mode does not implement must REFUSE, never be silently ignored.

⚑⚑⚑ AN IGNORED FLAG IS WORSE THAN AN ABSENT ONE, AND A PEER MEASURED IT ON THIS TOOL. `rows`
accepted `--table N` and returned every row of every table, byte-identically for a valid index, a
different valid index, and an impossible one. Their control is what makes it a finding rather than
a suspicion: `--table 99` on a five-table document returned all 33 rows.

⚑⚑ THE COST LANDED IN A COMMIT MESSAGE OF MINE. I wrote *"measured with `mdstruct rows --table
6`"* as the evidence sentence for a defect report, and that operation never occurred — I had read
the full output and attributed the isolation to a filter that did nothing. The conclusion was
right and the reproduction step does not reproduce, which is one revision from a finding nobody
can re-derive.

⚑ THE ASYMMETRY IS THE TRAP. `classify` parses `--table` and refuses an unparseable value;
`rows` never looks for it. So the flag works in the mode a reader tries second, and the two modes
share a document, a vocabulary and a help text. `_rows` already refuses an unparseable `--col` and
refuses `--col` without `--starts` — it had the discipline for the flags it knew about, and no way
to notice one it did not.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

from mikemol.mdstruct import cli as _cli_module

pytestmark = pytest.mark.needs_pandoc

_FIXTURE = """# Doc

| alpha | beta |
|---|---|
| a1 | b1 |

| gamma | delta |
|---|---|
| g1 | d1 |
| g2 | d2 |
"""

# Table 1 holds two rows; table 0 holds one. Distinct sizes, so a scoped read is distinguishable
# from an unscoped one by COUNT as well as by content.
_TABLE_ONE_ROWS = 2

# No such table: the fixture has two. ⚑ The control — a flag that does nothing returns the same
# answer here as for a valid index, which is what makes the defect invisible without it.
_IMPOSSIBLE = "99"

_REFUSED = 2

# ⚑ THE MODULE'S SOURCE, LOCATED VIA THE IMPORTED PACKAGE rather than from this file's own path.
# A `Path(__file__).parent.parent / "src" / ...` spelling is the runfiles-layout trap this suite
# has already paid for twice: under bazel the tests and the sources sit in different trees, and a
# relative walk names nothing there while reading as correct here.
# ⚑ THE MODULE OBJECT, NOT `find_spec`, because a spec's `origin` is `str | None` on a spec that is
# itself `ModuleSpec | None` — two unions to narrow for a path that is not in question once the
# import succeeded. `__file__` on an imported module is the same fact with one narrowing.
_CLI_SOURCE = Path(str(_cli_module.__file__))


def _run(doc: Path, *args: str, mode: str = "rows",
         extra: list[str] | None = None,
         terminator: bool = False) -> subprocess.CompletedProcess[str]:
    """Invoke the CLI as a caller does, as a subprocess rather than in-process.

    ⚑ A SUBPROCESS IS THE SUBJECT HERE, NOT A CONVENIENCE. These arms are about what a mode does
    with an argv it does not understand, and an in-process call would test the library function
    the flag was supposed to reach — which is the very step the defect skipped.

    ⚑⚑ `mode` DEFAULTS TO `rows` SO THE FOUR EXISTING CALLERS ARE UNCHANGED. Rewriting them to
    pass a mode they already imply would be a diff across arms this change does not touch, and
    each one edited is one more chance to alter a measurement while meaning to relocate it.

    Args:
        doc: the fixture document, passed as the mode's path operand.
        *args: trailing arguments after the path, for the `rows`-shaped callers.
        mode: which mode to dispatch.
        extra: arguments placed AFTER the path, for modes taking modifiers.
        terminator: place `--` before the first of `*args`, so a dash-leading operand is passed
            as an operand rather than read as an option. ⚑ The subject of its own arm, so it is
            a parameter rather than something a caller spells inline and gets subtly wrong.

    Returns:
        the completed process, so an arm can assert on its exit status and both streams.

    """
    head = [sys.executable, "-m", "mikemol.mdstruct.cli", mode]
    # ⚑ `grep` TAKES ITS PATTERN BEFORE THE PATH and every other mode takes the path first, which
    # is the tool's own argument order — so the helper follows it rather than imposing one shape.
    lead = [*(["--"] if terminator else []), *args, str(doc)] if mode == "grep" \
        else [str(doc), *args]
    return subprocess.run([*head, *lead, *(extra or [])],
                          check=False, capture_output=True, text=True)


def test_rows_scoped_to_one_table_returns_only_that_tables_rows(doc: Path) -> None:
    """⚑ THE CAPABILITY, ASSERTED BEFORE THE REFUSAL BELOW MEANS ANYTHING.

    A mode that refused every `--table` would satisfy an arm asserting only that impossible
    indices are rejected. This pins that a valid index does the thing the flag claims.
    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    result = _run(doc, "--table", "1")
    assert result.returncode == 0, f"a valid table index was refused: {result.stderr!r}"
    body = [ln for ln in result.stdout.splitlines() if ln.startswith("  table ")]
    assert len(body) == _TABLE_ONE_ROWS, (
        f"--table 1 returned {len(body)} row(s), expected {_TABLE_ONE_ROWS}: {body}"
    )
    # ⚑ NAMED, NOT COUNTED. Two populations of two can differ entirely, and the failure this arm
    # exists for returns THREE rows spanning both tables — a count alone would catch that, but a
    # future off-by-one selecting table 0 twice would not.
    assert all("table 1" in ln for ln in body), f"a row from another table appeared: {body}"


def test_an_impossible_table_index_refuses_rather_than_returning_everything(doc: Path) -> None:
    """⚑⚑⚑ THE MEASURED DEFECT: `--table 99` returned all 33 rows of a five-table document.

    Accepted silently, and byte-identical to a valid index — so a reader who mistypes an index, or
    who assumes a flag exists in this mode because it exists in a sibling mode, receives a
    complete answer to a question they did not ask and no signal that anything was wrong.

    ⚑ A REFUSAL, NOT AN EMPTY RESULT. Returning nothing would be indistinguishable from a table
    that genuinely has no rows, which is this tree's standing absence-versus-unavailable defect
    wearing a new hat.
    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    result = _run(doc, "--table", _IMPOSSIBLE)
    assert result.returncode == _REFUSED, (
        f"an impossible table index returned rc={result.returncode} with "
        f"{len(result.stdout.splitlines())} line(s) of output — it must refuse"
    )
    assert _IMPOSSIBLE in result.stderr, (
        f"the refusal must name the index it rejected; stderr was {result.stderr!r}"
    )


def test_an_unparseable_table_index_refuses(doc: Path) -> None:
    """⚑ THE SAME DISCIPLINE `--col` ALREADY HAS, and the reason is recorded beside it.

    Silently reading table 0 for `--table two` would answer a question nobody asked and report it
    as a clean result. `classify` refuses this; `rows` must agree, or one document read two ways
    gives two answers to one malformed query.
    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    result = _run(doc, "--table", "two")
    assert result.returncode == _REFUSED, (
        f"an unparseable table index returned rc={result.returncode}; it must refuse"
    )


def test_the_usage_text_names_every_registered_mode() -> None:
    """⚑⚑⚑ THE TOOL UNDER-REPORTED ITSELF, AND A PEER CONCLUDED A MODE DID NOT EXIST.

    Two spellings of one fact, and they drifted. The unknown-mode refusal DERIVES its list from
    the dispatch registry; the usage banner is hand-written prose. Measured 2026-09-12: the
    registry held ELEVEN modes and the banner named TEN. The missing one was `verify` —
    registered, dispatchable, and named by the routing table's own instruction (*"`verify` before
    any bounded write"*).

    ⚑⚑⚑ AND I FIRST WROTE THAT AS *12 AND 11*, WHICH IS WRONG IN BOTH TERMS AND SHIPPED IN THE
    COMMIT THAT FIXED THE DEFECT. I read the refusal's comma-separated list and COUNTED IT BY EYE
    rather than running a counter — in the very repair whose subject is a hand-maintained figure
    drifting from a derived one. `linux-sources-94` re-measured and reported 11; the registry
    literal has 11 entries. The defect, the fix and this arm are unaffected, and every figure in
    them was wrong.
    ⚑⚑ THE LESSON IS NOT *COUNT MORE CAREFULLY*. It is that a count stated in prose is the same
    object as the banner this arm exists to police, one layer up — so the arm below asserts a
    RELATION between two live surfaces and never a cardinality, and cannot inherit this mistake.

    ⚑⚑ AND THE COST IS NOT COSMETIC, because the usage text is what a reader consults BEFORE
    deciding a capability is absent. `linux-sources-94` was migrating onto this tool; a mode
    absent from `--help` reads as a mode the tool does not have, and the honest conclusion from
    that reading is to keep using the other implementation.

    ⚑ BOTH SURFACES ARE DRIVEN AS PROGRAMS, which is the correction to a first cut that imported
    the module and read the registry attribute directly. That version needed a private-name escape
    AND measured an attribute rather than the artifact — and the artifact is the point: these two
    strings are what a caller actually SEES, and reading the registry in-process proves nothing
    about whether the banner a user is shown agrees with the refusal a user is shown.

    ⚑⚑ THE REFUSAL IS THE DENOMINATOR, so the arm asserts it parsed a non-empty list before
    comparing. A split that silently yielded nothing would make this pass over zero modes — the
    vacuous-arm shape, arriving in the arm written to catch a different vacuity.

    ⚑⚑⚑ AND NO CARDINALITY APPEARS ANYWHERE, INCLUDING IN THE EVIDENCE STRING. A first version
    reported *"N of M mode(s) absent"*, which is a count in prose derived from a correct
    computation — stale the instant a mode is added, and the very thing the commit correcting this
    arm's own figures was about. `linux-sources-94` found the identical defect in their uncommitted
    equivalent (*"both surfaces name the same 13 slice(s)"*) from this rule. The assertion states a
    RELATION and the message names the DIFFERING ELEMENTS; a reader who wants a total counts the
    list.

    ⚑⚑ THE COMPARISON RUNS BOTH WAYS, because one-directional containment passes a banner that
    advertises a mode the dispatcher does not have — the opposite drift, and worse for a reader,
    since they would run it and get a refusal from the tool that documented it. F-armed in both
    directions: deleting the `verify` line reds one side, and a `phantom` line documenting an
    unregistered mode reds the other. The first arm could only have caught the first.

    ⚑⚑ THE POPULATION IS TWO SURFACES, AND THAT IS A MEASUREMENT RATHER THAN AN ASSUMPTION.
    `linux-sources-94` asked this of their own equivalent and found their tree publishes THREE
    slice lists — `--help`, the refusal, and a `--slices` flag matched by neither of their
    patterns — all agreeing today, so a two-surface comparison would have reported concord over an
    incomplete population. Swept here 2026-09-12: the only other enumerations of this mode set are
    `mdstruct/build/lib/` (a stale setuptools artifact, not a live surface) and findings prose
    recording past measurements. `cli.py` is the sole publisher. ⚑ A THIRD SURFACE ADDED LATER
    WOULD NOT BE CAUGHT BY THIS ARM — the defence there is not a better pattern but a surface the
    arm does not yet read, which is the no-cardinality rule in the POPULATION dimension rather
    than the value dimension.
    """
    banner = subprocess.run(
        [sys.executable, "-m", "mikemol.mdstruct.cli"],
        capture_output=True, text=True, check=False,
    )
    refusal = subprocess.run(
        [sys.executable, "-m", "mikemol.mdstruct.cli", "nosuchmode", "x.md"],
        capture_output=True, text=True, check=False,
    )
    declared = refusal.stderr.split("known modes are", 1)[-1].strip().rstrip(".")
    dispatchable = {m.strip() for m in declared.split(",") if m.strip()}
    assert dispatchable, (
        f"the refusal named no modes — this arm cannot measure drift without its denominator; "
        f"stderr was {refusal.stderr!r}"
    )
    # ⚑ NARROWED AT THE BOUNDARY, NOT SUPPRESSED. `re.findall` is typed `list[Any]`, so every set
    # operation below would leak an `Any` through this repository's `disallow_any_expr` — and an
    # annotation on the binding alone does NOT close it, because the comprehension still reads
    # `Any` elements. `finditer` yields `Match[str]`, whose `.group` is `str` by construction, so
    # the narrowing happens where the type is actually known rather than being asserted downstream.
    # ⚑⚑ `[\w-]` RATHER THAN `\w`, AND THE ARM CAUGHT ITS OWN GAP. When the first HYPHENATED modes
    # landed (`replace-section`, `append-section`) this pattern matched neither, and the arm
    # reported them as documented-nowhere — a TRUE statement about the pattern and a false one
    # about the banner, which had both lines. A reader's pattern is a third spelling of the mode
    # set, one layer below the two this arm compares, and it drifted the moment the naming
    # convention widened.
    documented = {m.group(1) for m in
                  re.finditer(r"^    mdstruct ([\w-]+) ", banner.stderr, re.MULTILINE)}
    assert documented, (
        f"the usage banner named no modes — with an empty set this arm's containment check is "
        f"vacuously true in one direction; stderr was {banner.stderr!r}"
    )
    assert dispatchable == documented, (
        f"the two surfaces disagree. dispatchable but undocumented: "
        f"{sorted(dispatchable - documented)} — a reader concludes these do not exist. "
        f"documented but not dispatchable: {sorted(documented - dispatchable)} — a reader runs "
        f"these and is refused by the tool that advertised them."
    )


def test_an_operand_after_the_terminator_reaches_the_mode(doc: Path) -> None:
    """⚑⚑⚑ THE DEFECT THAT BLOCKS A WRITE CLI, MEASURED AT THE READ PATH WHERE IT IS HARMLESS.

    `main` filtered every dash-leading token out of its operands, and `--` with them. So a needle
    beginning with a dash VANISHED and the operands shifted left. Measured on the shipped tool
    before the repair: `grep -- '-caveat' FILE.md` reported a usage error, because both the
    terminator and the needle were discarded as option-shaped.

    ⚑⚑ FOR A READER THAT IS A BAD RESULT; FOR A WRITE IT IS THE SILENT-WRONG-TARGET CLASS. A
    `replace-section HEADING FILE.md` whose heading vanishes leaves a VALID two-operand shape, so
    the FILE slides into the heading slot and the write lands on a section nobody named — beneath
    the ambiguity refusal and `exact=`, before `find_section` is ever called. `grep` survives only
    because its arity check catches the collapse; a two-positional writer has no such luck.

    ⚑ A HEADING BEGINNING WITH PUNCTUATION IS NOT EXOTIC. This repository's worklist is full of
    `⟐`-prefixed headings; a changelog's are routinely `-`-prefixed. The existing modes never
    surfaced this because a PATTERN that looks like a flag is unusual, and a HEADING that does
    is not.
    """
    doc.write_text("# Top\n\n-caveat appears here\n", encoding="utf-8")
    result = _run(doc, "-caveat", mode="grep", terminator=True)
    assert result.returncode == 0, (
        f"a dash-leading needle after `--` did not reach the searcher; rc={result.returncode}, "
        f"stderr={result.stderr!r}"
    )
    assert "-caveat" in result.stdout, (
        f"the match was not reported, so the needle reached the searcher as something else; "
        f"stdout was {result.stdout!r}"
    )


def test_a_flag_the_mode_does_not_own_is_refused(doc: Path) -> None:
    """⚑⚑⚑ A FILTER CANNOT REFUSE — the other half of the same root cause.

    Every dash token was discarded unread, so `spans FILE.md --nonsense-flag` ran CLEAN and
    reported success. **A flag that does nothing is indistinguishable from a flag that worked.**
    `substrate-9c` measured the identical shape in their own writer the same day and named the
    root exactly: *the filter is the only thing reading dash tokens, and a filter cannot refuse.*

    ⚑⚑ AND THE REFUSAL IS PER-MODE, WHICH A GLOBAL UNION COULD NOT BE. `--width` is a real flag
    that `lint` owns and `spans` does not read; a union of every flag the tool accepts would admit
    it here and answer a question nobody asked. The arm below uses `--width` on `spans` precisely
    because it is the case that separates ownership from mere spelling.
    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    result = _run(doc, mode="spans", extra=["--width", "80"])
    assert result.returncode == _REFUSED, (
        f"`spans --width` returned rc={result.returncode} — a mode that does not read a flag must "
        f"refuse it, not ignore it"
    )
    assert "--width" in result.stderr, (
        f"the refusal must name the flag it rejected; stderr was {result.stderr!r}"
    )


def test_the_owning_mode_still_accepts_its_own_flag(doc: Path) -> None:
    """⚑ THE POSITIVE CONTROL, without which the arm above passes on a broken-shut gate.

    A refusal that fires on everything is not a refusal, it is a broken-shut gate — the one-armed
    failure this repository's two-armed hook discipline exists to prevent, arriving in argument
    parsing. `lint` owns `--width`, so it must still honour it in BOTH spellings the tool's own
    `_flag` contract accepts: a check on the raw token would refuse `--width=80`, which is a worse
    defect than the one being repaired.
    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    spaced = _run(doc, mode="lint", extra=["--width", "200"])
    equals = _run(doc, mode="lint", extra=["--width=200"])
    assert spaced.returncode != _REFUSED, (
        f"`lint --width 200` was refused by the mode that owns the flag; stderr={spaced.stderr!r}"
    )
    assert equals.returncode != _REFUSED, (
        f"`lint --width=200` was refused — the `=` spelling binds in `_flag`, so refusing it here "
        f"rejects a form the tool accepts; stderr={equals.stderr!r}"
    )


# ⚑⚑ THE CONTRACT GATE'S READER, AT MODULE LEVEL RATHER THAN INSIDE THE ARM. A first cut put the
# whole walk in the test body and ruff refused it at complexity 23 — correctly: a check nobody can
# read is a check nobody can audit, and this one exists to be audited. Split by QUESTION, so each
# helper answers one and the arm states the relation.


def _string_constants(tree: ast.Module) -> dict[str, str]:
    """Return every module-level `NAME = "literal"` binding.

    ⚑ A REGISTRY KEY SPELLED AS A NAME RESOLVES THROUGH HERE. `_MODES` keys `grep` via the constant
    `_PATTERN_MODE`, and the probe that became this gate recorded the VARIABLE NAME as a mode —
    reporting a spurious disagreement plus a phantom mode that does not exist. The probe's own
    defect wearing the shape of the thing it was built to find.

    Returns:
        `{name: value}` for module-level string assignments.

    """
    out: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        value = node.value.value
        if not isinstance(value, str):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                out[target.id] = value
    return out


def _string_literals(node: ast.AST) -> set[str]:
    """Return every string literal anywhere under `node`.

    Returns:
        The set of string constants, narrowed at the boundary — `Constant.value` is a union over
        every literal type, so indexing it without this check leaks `Any` into every caller.

    """
    return {
        e.value for e in ast.walk(node)
        if isinstance(e, ast.Constant) and isinstance(e.value, str)
    }


def _dict_literal(tree: ast.Module, name: str, consts: dict[str, str]) -> dict[str, ast.expr]:
    """Return the annotated module-level dict `name`, keyed by resolved string.

    Args:
        tree: the parsed module.
        name: the variable to find.
        consts: module-level string constants, for a key spelled as a NAME.

    Returns:
        `{key: value_node}`, empty when the name is absent — which the arm treats as a REFUSAL
        rather than as agreement, because a parse that silently yields nothing would make every
        comparison below vacuously true.

    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign) or not isinstance(node.target, ast.Name):
            continue
        if node.target.id != name or not isinstance(node.value, ast.Dict):
            continue
        out: dict[str, ast.expr] = {}
        for k, v in zip(node.value.keys, node.value.values, strict=True):
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                out[k.value] = v
            elif isinstance(k, ast.Name):
                out[consts.get(k.id, k.id)] = v
        return out
    return {}


def _flags_reachable(funcs: dict[str, ast.FunctionDef], name: str,
                     seen: set[str] | None = None) -> set[str]:
    """Return every dash-leading literal reachable from `name`, following local calls.

    ⚑ FOLLOWING CALLS IS WHAT MAKES THIS MEASURE THE MODE rather than its adapter. Each registry
    entry names a thin `_x_mode` wrapper that delegates to the real reader, so a walk stopping at
    the wrapper would find no flags anywhere and report every mode as declaring flags it does not
    read — a gate that fires on everything, which is the broken-shut failure.

    Returns:
        The dash-leading string literals in `name` and in everything it calls.

    """
    seen = seen if seen is not None else set()
    if name in seen or name not in funcs:
        return set()
    seen.add(name)
    out = {lit for lit in _string_literals(funcs[name]) if lit.startswith("-") and lit != "-"}
    for node in ast.walk(funcs[name]):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            out |= _flags_reachable(funcs, node.func.id, seen)
    return out


def test_every_mode_declares_exactly_the_flags_its_code_reads() -> None:
    """⚑⚑⚑ THE MODE-CONTRACT GATE, on an operator ruling, armed over a tree that ALREADY PASSES IT.

    `_MODE_OPTS` says which modifiers a mode owns; the mode's own code reads flags by name. Two
    spellings of one fact — the drift class this module already measured once in the usage banner,
    where the registry and the hand-written help disagreed and a peer concluded a mode did not
    exist. Nothing had been checking the same relation for FLAGS.

    ⚑⚑ IT ASSERTS NOTHING NEW ABOUT QUALITY, WHICH IS WHY IT CAN BE ARMED NOW. Measured before it
    was written: twelve modes, zero disagreements, and the source needed no change. Arming a gate
    over a tree that does not yet pass it blocks the commits that would clean it — this
    repository's recorded sequencing hazard — so a gate firing on nothing today is the one that may
    land today.

    ⚑ READ FROM THE AST, NOT BY IMPORTING THE REGISTRY. The pre-commit gate runs BARE PYTEST with
    no bazel and no sandbox, so the check must not depend on import machinery beyond the module
    itself, and reading the literal is what lets a failure name the MODE rather than an object.

    ⚑ SUBSTRATE'S `climode` IS THE DECLARATION FORMAT THIS ANSWERS TO, adopted as a concept rather
    than imported — on their own advice that a declaration with no gate to read it is
    built-then-orphaned. This is that gate; with it, importing their format becomes a real question.
    """
    tree = ast.parse(_CLI_SOURCE.read_text(encoding="utf-8"))
    consts = _string_constants(tree)
    declared_nodes = _dict_literal(tree, "_MODE_OPTS", consts)
    registry = _dict_literal(tree, "_MODES", consts)
    funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

    assert registry, (
        "no mode registry parsed — every comparison below would be vacuously true over an empty "
        "population, which is the shape this gate exists to catch one level down"
    )
    universal: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_GLOBAL_OPTS" for t in node.targets
        ):
            universal = _string_literals(node.value)
    assert universal, (
        "the universal option set parsed empty — a future global option would then read as "
        "per-mode drift in every mode at once, which is a false report, not a missed one"
    )

    declared = {mode: _string_literals(node) for mode, node in declared_nodes.items()}
    drift: dict[str, tuple[list[str], list[str]]] = {}
    for mode, entry in registry.items():
        if not isinstance(entry, ast.Name):
            continue
        owns = declared.get(mode, set()) - universal
        reads = _flags_reachable(funcs, entry.id) - universal
        if owns != reads:
            drift[mode] = (sorted(owns - reads), sorted(reads - owns))

    assert not drift, (
        f"declaration and implementation disagree. per mode, (declared-but-unread, "
        f"read-but-undeclared): {drift} — a declared flag the code never reads is a promise the "
        f"refusal still honours, so a caller passes it and NOTHING HAPPENS; a read flag that is "
        f"undeclared is REFUSED by the very check that should admit it."
    )
