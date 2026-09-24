# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.witness.warrant_integrity`: substrate's 18 selftest arms, ported.

The engine is the caller's argument here, and this stdlib-only distribution never imports it, so
a stand-in plays it: `raw_bib.parse` (which, like the engine, keeps the last of a duplicated key),
raising on text with no entry opening as the engine raises a syntax error. The four member arms
ran against substrate's LIVE bib; each now runs its witness against a fixture bib.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.witness import raw_bib, warrant_integrity, witness_row

if TYPE_CHECKING:
    from pathlib import Path

_GOOD = """@misc{ALPHA,
  section = {s},
  claim   = {a claim long enough to be a real commitment a reader could act on},
  check   = {item:ALPHA}
}

@misc{BETA,
  section = {s},
  claim   = {another claim long enough to be a real commitment for this fixture},
  check   = {item:BETA}
}
"""

_SHADOWED = """@misc{ALPHA,
  section = {s},
  claim   = {a claim long enough to be a real commitment a reader could act on},
  check   = {item:ALPHA}
}

@misc{ALPHA,
  section = {s},
  claim   = {a REDECLARED claim, also long enough to read as a commitment here},
  check   = {item:ALPHA}
}
"""

_THIN = """@misc{ALPHA,
  section = {s},
  claim   = {too short},
  check   = {item:ALPHA}
}
"""

_NO_CHECK = """@misc{ALPHA,
  section = {s},
  claim   = {a claim long enough to be a real commitment a reader could act on}
}
"""

_TWO_ENTRIES = 2
_FOUR_MEMBERS = 4


def _engine(path: Path) -> dict[str, dict[str, str]]:
    """Stand in for the engine's parse: raise on non-bib text, else parse, last duplicate winning.

    Returns:
        `{key: {field: value}}`.

    Raises:
        ValueError: when content lines exist and none opens an entry, as a syntax error would.

    """
    text = path.read_text(encoding="utf-8")
    content = [line for line in text.splitlines() if line.strip() and not line.startswith("%")]
    if content and "@" not in text:
        msg = "syntax error: no entry opening"
        raise ValueError(msg)
    return raw_bib.parse(text)


def _bib(tmp_path: Path, text: str) -> Path:
    """Write a fixture warrants bib.

    Returns:
        its path.

    """
    path = tmp_path / "warrants.bib"
    path.write_text(text, encoding="utf-8")
    return path


def _read(tmp_path: Path, text: str) -> warrant_integrity.Integrity:
    """Read a fixture bib through both routes, failing the test if it does not read.

    Returns:
        the integrity reading.

    """
    got, why = warrant_integrity.read(_bib(tmp_path, text), parse=_engine)
    assert got is not None, why
    return got


def _closes(rows: list[witness_row.Part | witness_row.Verdict]) -> bool:
    """Say whether a witness's rows end in a closed verdict.

    Returns:
        True for a last row that is a closed verdict.

    """
    return bool(rows) and isinstance(rows[-1], witness_row.Verdict) and not rows[-1].is_open


def test_the_warrant_set_is_not_empty(tmp_path: Path) -> None:
    """The presence witness reaches a closed verdict on a populated set."""
    path = _bib(tmp_path, _GOOD)
    assert _closes(list(warrant_integrity.witness_present("k", path=path, parse=_engine)))


def test_no_key_is_silently_shadowed(tmp_path: Path) -> None:
    """The shadowing witness reaches a closed verdict on distinct keys."""
    path = _bib(tmp_path, _GOOD)
    assert _closes(list(warrant_integrity.witness_unshadowed("k", path=path, parse=_engine)))


def test_every_entry_carries_a_claim_and_a_check(tmp_path: Path) -> None:
    """The commitment witness reaches a closed verdict when both fields survive."""
    path = _bib(tmp_path, _GOOD)
    assert _closes(list(warrant_integrity.witness_committed("k", path=path, parse=_engine)))


def test_every_claim_carries_readable_prose(tmp_path: Path) -> None:
    """The legibility witness reaches a closed verdict on adequate prose."""
    path = _bib(tmp_path, _GOOD)
    assert _closes(list(warrant_integrity.witness_legible("k", path=path, parse=_engine)))


def test_a_well_formed_set_reads_clean(tmp_path: Path) -> None:
    """The healthy case reports nothing: the positive control for all four claims.

    ⚑ Without it, a reader that flagged everything would satisfy every other case here.
    """
    got = _read(tmp_path, _GOOD)
    assert len(got.parsed) == _TWO_ENTRIES
    assert not got.shadowed
    assert not got.thin_prose()
    assert not got.missing_field("check")


def test_an_empty_parse_is_detectable(tmp_path: Path) -> None:
    """A bib that parses to nothing is REPORTED empty rather than reading clean.

    ⚑⚑⚑ Zero entries satisfies every "for all" claim, so a destroyed warrant set reads as a
    perfect one. The fixture is a VALID but entry-less bib (a comment only), not garbage.
    """
    assert _read(tmp_path, "% a comment, and not one entry\n").empty


def test_a_malformed_bib_says_why_rather_than_reading_empty(tmp_path: Path) -> None:
    """A file the engine rejects returns a REASON, not an empty set.

    ⚑⚑ "declares no claims" and "is not parseable" call for different repairs; mapping a syntax
    error onto empty would report a mangled file as an honest absence.
    """
    got, why = warrant_integrity.read(_bib(tmp_path, "not a bib at all\n"), parse=_engine)
    assert got is None
    assert why


def test_a_populated_set_is_not_reported_empty(tmp_path: Path) -> None:
    """The emptiness predicate discriminates: the control for the empty case."""
    assert not _read(tmp_path, _GOOD).empty


def test_a_shadowed_key_is_named(tmp_path: Path) -> None:
    """A key written twice is reported by name, and the two routes disagree on the count.

    ⚑⚑ The engine's parse already lost the duplicate; the file says how many were written.
    """
    got = _read(tmp_path, _SHADOWED)
    assert got.shadowed == ("ALPHA",)
    assert len(got.written) != len(got.parsed)


def test_a_distinct_set_reports_no_shadowing(tmp_path: Path) -> None:
    """Distinct keys are not reported: the control for the shadowing case."""
    assert _read(tmp_path, _GOOD).shadowed == ()


def test_a_missing_check_is_named(tmp_path: Path) -> None:
    """An entry whose check did not survive the parse is reported: the real silent shadowing."""
    assert _read(tmp_path, _NO_CHECK).missing_field("check") == ("ALPHA",)


def test_a_thin_claim_is_named_with_its_length(tmp_path: Path) -> None:
    """A claim too short to commit is reported with its length: the length is actionable."""
    ((key, length),) = _read(tmp_path, _THIN).thin_prose()
    assert key == "ALPHA"
    assert length < warrant_integrity.MIN_PROSE


def test_a_full_claim_is_not_reported_thin(tmp_path: Path) -> None:
    """Adequate prose passes: the control for the thin case."""
    assert _read(tmp_path, _GOOD).thin_prose() == ()


def test_an_absent_bib_says_why(tmp_path: Path) -> None:
    """A missing file returns a reason rather than raising: a raise takes the whole roster down."""
    got, why = warrant_integrity.read(tmp_path / "no-such.bib", parse=_engine)
    assert got is None
    assert why


def test_a_witness_on_an_unreadable_bib_opens_naming_why(tmp_path: Path) -> None:
    """A witness over a bib that cannot be read yields ONE open verdict carrying the reason.

    ⚑ Found by the mutation grid: no ported arm ran a witness against an unreadable bib, so the
    verdict for it (substrate's `_unreadable`) could be deleted with every case still green. An
    unreadable warrant set must read as OPEN, never as a witness that fell silent.
    """
    rows = list(
        warrant_integrity.witness_present("k", path=tmp_path / "no-such.bib", parse=_engine)
    )
    assert len(rows) == 1
    (verdict,) = rows
    assert isinstance(verdict, witness_row.Verdict)
    assert verdict.is_open
    assert "ABSENT" in verdict.why


def test_every_member_rests_on_the_non_empty_claim() -> None:
    """The three universally-quantified members declare a premise.

    ⚑⚑ Each is satisfied by an empty set, so deleting the non-empty claim makes all three pass
    vacuously, which a premise edge exists to make visible.
    """
    root = "the_warrant_set_is_not_empty"
    family = warrant_integrity.FAMILY
    assert [m.name for m in family.members if m.name != root and not m.premises] == []


def test_the_familys_premises_all_resolve() -> None:
    """No declared premise names a member the family does not hold."""
    assert warrant_integrity.FAMILY.dangling_premises() == ()


def test_the_family_holds_one_member_per_claim() -> None:
    """The roster is the four claims, each one case, none unsplit."""
    family = warrant_integrity.FAMILY
    assert len(family.members) == _FOUR_MEMBERS
    assert family.count == len(family.members)
    assert family.unsplit() == ()


def test_the_render_names_every_population(tmp_path: Path) -> None:
    """The report covers all four claims, not just the ones with findings."""
    text = warrant_integrity.render(_read(tmp_path, _GOOD))
    assert [w for w in ("non-empty", "shadowed", "missing", "thin prose") if w not in text] == []
