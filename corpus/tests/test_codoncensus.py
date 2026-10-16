# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the Codon census: it classifies a rejection, takes both readings, and samples."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.corpus import codoncensus

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

_FUTURE = "from __future__ import annotations\n\nVALUE = 1\n"
_ANSI_FUTURE = (
    "\x1b[1mm.py:1 (1-35): \x1b[1;31merror:\x1b[0m\x1b[1m no module named '__future__'\x1b[0m"
)
_OK = 0
_FAILED = 1


def _fake(source_seen: list[str]) -> codoncensus.Runner:
    """Build a Codon stand-in that rejects any source holding the future import.

    Returns:
        a runner recording each source it was asked to compile.

    """

    def run(argv: Sequence[str], cwd: Path) -> tuple[int, str]:
        text = (cwd / argv[-1]).read_text(encoding="utf-8")
        source_seen.append(text)
        if "from __future__" in text:
            return _FAILED, _ANSI_FUTURE
        return _OK, ""

    return run


def test_a_message_is_classified_by_its_shape() -> None:
    """Each known rejection gets its kind, and an unknown one is `other`, never dropped."""
    kinds = {
        "no module named '__future__'": "future-import",
        "no module named 'mikemol.hooks'": "missing-module",
        "cannot import name 'UTC' from 'datetime'": "missing-name",
        "'Any' object has no attribute '__iter__'": "any-use",
        "unexpected token": "syntax",
        "something wholly new": "other",
    }
    assert {m: codoncensus.classify(m) for m in kinds} == kinds


def test_the_first_error_is_read_out_of_coloured_output() -> None:
    """The colour codes are removed and the message after `error:` is returned."""
    assert codoncensus.first_error(_ANSI_FUTURE) == "no module named '__future__'"
    assert codoncensus.first_error("no error line here") == "no error line here"


def test_the_future_import_is_removed_only_as_a_whole_line() -> None:
    """The control: a mention elsewhere in the text is left alone."""
    kept = 'text = "from __future__ import annotations"\n'
    assert codoncensus.strip_future(_FUTURE) == "\nVALUE = 1\n"
    assert codoncensus.strip_future(kept) == kept


def test_both_readings_are_taken_and_the_second_has_no_future_import() -> None:
    """As it is, the module is rejected for the import; without it Codon accepts this one."""
    seen: list[str] = []
    verdict = codoncensus.judge("codon", "m.py", _FUTURE, _fake(seen))
    assert verdict is not None
    assert verdict.kind == "future-import"
    stripped = codoncensus.strip_future(_FUTURE)
    assert codoncensus.judge("codon", "m.py", stripped, _fake(seen)) is None


def test_the_census_reads_the_file_twice_and_never_edits_it(tmp_path: Path) -> None:
    """The file keeps its import; the second compile sees a copy without it."""
    module = tmp_path / "m.py"
    module.write_text(_FUTURE, encoding="utf-8")
    seen: list[str] = []
    rows = codoncensus.census_of("codon", [module], _fake(seen))
    assert module.read_text(encoding="utf-8") == _FUTURE
    assert [("from __future__" in s) for s in seen] == [True, False]
    assert rows[0].as_is is not None
    assert rows[0].stripped is None


def test_pick_keeps_src_modules_and_thins_evenly(tmp_path: Path) -> None:
    """Tests, stubs, venvs and `__init__` are skipped; a sample takes every k-th sorted file."""
    src = tmp_path / "d" / "src" / "p"
    src.mkdir(parents=True)
    for n in range(10):
        (src / f"m{n}.py").write_text("x = 1\n", encoding="utf-8")
    (src / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "d" / "tests").mkdir()
    (tmp_path / "d" / "tests" / "t.py").write_text("x = 1\n", encoding="utf-8")
    everything = codoncensus.pick([tmp_path / "d"], None)
    assert [p.name for p in everything] == [f"m{n}.py" for n in range(10)]
    thinned = codoncensus.pick([tmp_path / "d"], 5)
    assert [p.name for p in thinned] == ["m0.py", "m2.py", "m4.py", "m6.py", "m8.py"]


def test_the_tally_counts_accepted_and_each_kind() -> None:
    """The totals line: how many modules fall in each class for each reading."""
    rejected = codoncensus.Verdict("future-import", "m")
    rows = [
        codoncensus.Row("a", rejected, None),
        codoncensus.Row("b", rejected, codoncensus.Verdict("missing-name", "n")),
        codoncensus.Row("c", None, None),
    ]
    assert codoncensus.tally(rows, "as-is") == {"future-import": 2, "accepted": 1}
    assert codoncensus.tally(rows, "stripped") == {"accepted": 2, "missing-name": 1}


def test_main_refuses_a_missing_operand(capsys: pytest.CaptureFixture[str]) -> None:
    """Usage: with no root it is exit 2 and the usage line on stderr."""
    assert codoncensus.main(["codon"]) == codoncensus.EXIT_USAGE
    assert "usage:" in capsys.readouterr().err
