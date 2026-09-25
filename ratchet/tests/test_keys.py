# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the key schema: which field is the path, declared rather than guessed.

⚑⚑ EVERY WITNESS DRIVES A PUBLIC SEAM — `partition`, `ratchet`, or the CLI — and never imports
the schema module by name. The defect these pin is a verdict the gate reaches, so the arm is the
verdict; a witness importing a module that does not exist yet fails at collection, which says
nothing about behaviour. Written this way, each fails by ASSERTION against a schema-less ratchet:
an absent keyword is turned into `pytest.fail`, an absent flag into argparse's exit code.

⚑ NO FIXTURE HERE RUNS GIT, so the remap suite's `no_ambient_git` guard has nothing to guard.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.ratchet import cli, core

if TYPE_CHECKING:
    from pathlib import Path

RUFF = "ruff"
SUMTYPE = "substrate:sumtype"
DISCHARGE = "substrate:discharge"
BAN = "substrate:ban"
CLAIMS = "substrate:claims"
PUBLIC = "substrate:public"
MALFORMED_NAME = "MalformedKeyError"
BASELINE_NAME = "ratchet-preview.txt"
REFUSED = 1
PASSED = 0

# ruff's `path:rule`, including a path that itself carries a colon.
RUFF_OLD = "pkg/a.py:docstring-missing-returns"
RUFF_NEW = "pkg/b.py:docstring-missing-returns"
RUFF_COLON_PATH = "./odd:dir/c.py:magic-value-comparison"
RUFF_POPULATION = frozenset({RUFF_OLD, RUFF_COLON_PATH, "pkg/z.py:other-rule"})

# sumtype/discharge emit `name::relpath` — the path is SECOND.
SUM_OLD = "Crumb::agda/Substrate/Foo.agda"
SUM_RENAMED = "Crumb::agda/Substrate/Bar.agda"
SUM_OTHER_NAME_SAME_FILE = "Loaf::agda/Substrate/Foo.agda"

# ban/claims are triples; the identity is BOTH non-path fields.
BAN_OLD = "agda/Substrate/Foo.agda::Substrate.Bar::using"
BAN_SAME_MIDDLE = "agda/Substrate/Baz.agda::Substrate.Bar::using"
BAN_OTHER_MIDDLE = "agda/Substrate/Baz.agda::Substrate.Qux::using"
CLAIMS_OLD = "agda/Substrate/Foo.agda::shim::self"
CLAIMS_OTHER_MIDDLE = "agda/Substrate/Baz.agda::lemma::self"

# A pair where a triple is declared, and a ruff key where `::` is declared.
BAN_PAIR = "agda/Substrate/Foo.agda::Substrate.Bar"
RUFF_UNDER_PUBLIC = "a.py:some-rule"


def _partition(current: frozenset[str], baseline: frozenset[str], schema: str) -> core.Diff:
    """Partition under a declared schema, failing (not erroring) where the seam is absent.

    Returns:
        the partition of `current` against `baseline` under `schema`.

    """
    try:
        return core.partition(current, baseline, schema=schema)
    except TypeError as exc:
        pytest.fail(f"partition takes no declared key schema: {exc}")


def _ratchet(current: frozenset[str], path: Path, schema: str) -> tuple[int, list[str]]:
    """Run a dry ratchet under a declared schema, failing where the seam is absent.

    Returns:
        the ratchet's exit code and report lines.

    """
    try:
        return core.ratchet(current, path, write=False, schema=schema)
    except TypeError as exc:
        pytest.fail(f"ratchet takes no declared key schema: {exc}")


def _main(argv: list[str]) -> int:
    """Run the CLI, reading an argparse exit as the code it carries.

    Returns:
        the exit code, whether returned or raised.

    """
    try:
        return cli.main(argv)
    except SystemExit as exc:
        return int(str(exc.code))


def _dist(tmp_path: Path, findings: frozenset[str]) -> Path:
    """Build a fake distribution whose ruff reports `findings` as `path:rule` keys.

    Returns:
        The distribution root.

    """
    binroot = tmp_path / ".venv" / "bin"
    binroot.mkdir(parents=True)
    body = "".join(
        f'echo "{key.rpartition(":")[0]}:1:1: {key.rpartition(":")[2]}: msg"\n'
        for key in sorted(findings)
    )
    ruff = binroot / "ruff"
    ruff.write_text(f"#!/bin/sh\n{body}exit 1\n", encoding="utf-8")
    ruff.chmod(0o755)
    return tmp_path


def test_the_default_schema_partitions_ruff_keys_as_before() -> None:
    """Declaring `ruff` yields exactly the undeclared partition over a ruff population."""
    current = RUFF_POPULATION - {RUFF_OLD} | {RUFF_NEW}
    declared = _partition(current, RUFF_POPULATION, RUFF)
    assert declared == core.partition(current, RUFF_POPULATION)
    assert declared.moved == frozenset({(RUFF_OLD, RUFF_NEW)})
    assert not declared.added


def test_the_cli_round_trips_ruff_keys_under_the_default_schema(tmp_path: Path) -> None:
    """`--key-schema ruff` mints and re-reads a ruff census, colon-bearing path included."""
    dist = _dist(tmp_path, RUFF_POPULATION)
    assert _main([str(dist), "--key-schema", RUFF, "--init-absent"]) == PASSED
    assert _main([str(dist), "--key-schema", RUFF]) == PASSED
    assert core.read_baseline(dist / BASELINE_NAME)[1] == RUFF_POPULATION


def test_a_reversed_key_relocating_is_a_move() -> None:
    """Under sumtype the path is field 1, so a renamed file pairs as a move."""
    diff = _partition(frozenset({SUM_RENAMED}), frozenset({SUM_OLD}), SUMTYPE)
    assert diff.moved == frozenset({(SUM_OLD, SUM_RENAMED)})
    assert not diff.added


def test_a_reversed_key_with_a_new_name_is_growth_not_a_move() -> None:
    """Under discharge a different leading name in the same file is new debt, not churn."""
    diff = _partition(frozenset({SUM_OTHER_NAME_SAME_FILE}), frozenset({SUM_OLD}), DISCHARGE)
    assert diff.added == frozenset({SUM_OTHER_NAME_SAME_FILE})
    assert not diff.moved


def test_a_triple_sharing_its_middle_field_relocates_as_a_move() -> None:
    """Positive control: a ban triple whose identity is intact pairs across a move."""
    diff = _partition(frozenset({BAN_SAME_MIDDLE}), frozenset({BAN_OLD}), BAN)
    assert diff.moved == frozenset({(BAN_OLD, BAN_SAME_MIDDLE)})
    assert not diff.added


def test_ban_triples_differing_in_the_middle_do_not_collide() -> None:
    """Two ban triples sharing only the last field are growth, not a move."""
    diff = _partition(frozenset({BAN_OTHER_MIDDLE}), frozenset({BAN_OLD}), BAN)
    assert diff.added == frozenset({BAN_OTHER_MIDDLE})
    assert not diff.moved


def test_claims_triples_differing_in_the_middle_do_not_collide() -> None:
    """Two claims triples sharing only the last field are growth, not a move."""
    diff = _partition(frozenset({CLAIMS_OTHER_MIDDLE}), frozenset({CLAIMS_OLD}), CLAIMS)
    assert diff.added == frozenset({CLAIMS_OTHER_MIDDLE})
    assert not diff.moved


def test_a_malformed_key_is_refused_by_the_ratchet(tmp_path: Path) -> None:
    """A pair under a triple schema exits nonzero and names the error; a triple passes."""
    path = tmp_path / "base.txt"
    path.write_text(f"{BAN_OLD}\n", encoding="utf-8")
    good_code, _good_lines = _ratchet(frozenset({BAN_OLD}), path, BAN)
    bad_code, bad_lines = _ratchet(frozenset({BAN_OLD, BAN_PAIR}), path, BAN)
    assert good_code == PASSED
    assert bad_code == REFUSED
    assert any(MALFORMED_NAME in line and BAN_PAIR in line for line in bad_lines)


def test_a_malformed_census_is_refused_by_the_cli(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A ruff key under a `::` schema is refused by name, and nothing is minted."""
    dist = _dist(tmp_path, frozenset({RUFF_UNDER_PUBLIC}))
    assert _main([str(dist), "--key-schema", PUBLIC, "--init-absent"]) == REFUSED
    assert MALFORMED_NAME in capsys.readouterr().err
    assert not (dist / BASELINE_NAME).exists()
