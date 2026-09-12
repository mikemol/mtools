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

import re
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

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


def _run(doc: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Invoke the CLI as a caller does, as a subprocess rather than in-process.

    ⚑ A SUBPROCESS IS THE SUBJECT HERE, NOT A CONVENIENCE. These arms are about what a mode does
    with an argv it does not understand, and an in-process call would test the library function
    the flag was supposed to reach — which is the very step the defect skipped.

    Returns:
        the completed process, so an arm can assert on its exit status and both streams.

    """
    return subprocess.run(
        [sys.executable, "-m", "mikemol.mdstruct.cli", "rows", str(doc), *args],
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
    documented = {m.group(1) for m in
                  re.finditer(r"^    mdstruct (\w+) ", banner.stderr, re.MULTILINE)}
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
