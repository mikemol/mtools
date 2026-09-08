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
    return subprocess.run(  # noqa: S603 — argv is this interpreter and a fixture path
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
