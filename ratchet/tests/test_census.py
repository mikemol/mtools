# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the census: the key's grain, and refusing an untrustworthy read."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.ratchet.census import parse_concise, run_ruff

if TYPE_CHECKING:
    from pathlib import Path


def test_the_key_is_file_and_rule_not_line() -> None:
    """The key is file-and-rule, not file-and-line.

    ⚑⚑ A LINE NUMBER CHANGES WHEN ANYTHING ABOVE IT MOVES.

    A line-keyed baseline reports a whole file as new debt after an unrelated edit — every
    key refused, none of it real — and a gate that cries wolf gets disabled.
    """
    keys = parse_concise([
        "src/a.py:1:1: docstring-missing-returns: msg",
        "src/a.py:99:4: docstring-missing-returns: msg",
    ])
    assert keys == frozenset({"src/a.py:docstring-missing-returns"})


def test_the_key_keeps_the_file_rather_than_collapsing_to_the_rule() -> None:
    """The key keeps the file rather than collapsing to the rule.

    ⚑ Collapsing to the rule loses WHERE the debt is, so paying one file down while another
    regresses reads as unchanged — the substitution blindness, one axis over.
    """
    keys = parse_concise([
        "src/a.py:1:1: compare-to-empty-string: msg",
        "src/b.py:1:1: compare-to-empty-string: msg",
    ])
    assert keys == frozenset({"src/a.py:compare-to-empty-string",
                              "src/b.py:compare-to-empty-string"})


def test_a_path_containing_colons_is_parsed() -> None:
    """A path containing colons is parsed.

    ⚑ The path is matched non-greedily, because `./src/x.py` carries colons that a greedy
    match would swallow into the rule field.
    """
    assert parse_concise(["./src/a.py:3:9: literal-membership: msg"]) == frozenset(
        {"./src/a.py:literal-membership"})


def test_a_non_finding_line_is_dropped() -> None:
    """Summary lines and warnings are not findings."""
    assert parse_concise(["Found 3 errors.", "warning: something", ""]) == frozenset()


def test_an_unexpected_exit_refuses_rather_than_reporting_an_empty_census(
        tmp_path: Path) -> None:
    """An unexpected exit refuses rather than reporting an empty census.

    ⚑⚑⚑ A CENSUS FROM A CHECKER THAT DID NOT RUN IS AN EMPTY SET THAT LOOKS CLEAN.

    Exit 0 and 1 are both success — a clean tree and findings. Anything else means the
    checker failed, and reporting that as an empty census would pay the entire baseline
    down in one run. That is the fail-open shape this ecosystem keeps paying for.
    """
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "ruff").write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
    (tmp_path / ".venv" / "bin" / "ruff").chmod(0o755)
    with pytest.raises(RuntimeError, match="not trustworthy"):
        run_ruff(tmp_path, preview=True)


def test_a_synthesized_package_marker_is_not_censused(tmp_path: Path) -> None:
    """An EMPTY `__init__.py` is a build artifact and does not enter the census.

    ⚑⚑ rules_python writes one at every level of a runfiles tree so it is importable. None exist
    in the source tree, and `src/mikemol/__init__.py` is the file PEP 420 forbids here outright.
    Measured: the first honest run of the bazel ratchet gate REFUSED 8 keys, all from these.

    ⚑ THE DISCRIMINATOR IS EMPTINESS, NOT THE NAME. A first cut excluded every `__init__.py` and
    over-excluded — `mdstruct/src/mikemol/mdstruct/__init__.py` exists, carries content and
    legitimately held a key, so dropping it PAID DOWN REAL DEBT by accident. That is the mirror
    defect: a domain too NARROW, which serves a stale green rather than failing loudly.
    """
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "__init__.py").write_text('"""Real."""\n', encoding="utf-8")
    keys = parse_concise(
        ["pkg/__init__.py:1:1: some-rule: msg", "real/__init__.py:1:1: some-rule: msg"],
        tmp_path)
    assert keys == frozenset({"real/__init__.py:some-rule"})


def test_a_synthesized_bootstrap_is_not_censused(tmp_path: Path) -> None:
    """A generated py_binary bootstrap is a build artifact and does not enter the census.

    ⚑⚑⚑ THE SIBLING ARM ABOVE RECORDS *THE DISCRIMINATOR IS EMPTINESS, NOT THE NAME* — AND THE
    PREDICATE IT GUARDS CHECKED THE NAME FIRST. `_is_synthesized` returned False immediately
    unless the path ended in `__init__.py`, so emptiness was only ever consulted for one filename.
    A domain too narrow, which the arm above names as the mirror defect and then reproduces.

    ⚑⚑ MEASURED BY A DEPENDENCY BUMP, 2026-09-10: `rules_python` 1.0.0 -> 2.3.3 generates
    `_ratchet_cli_stage2_bootstrap.py` into the runfiles tree, and `//ratchet:ratchet_gate`
    REFUSED **49 NEW KEYS** — every one of them in a file nobody wrote. It exists only under
    `bazel-out/`; `git status --ignored` over `ratchet/` shows no such file in source.

    ⚑ NOT A FALSE POSITIVE AND NOT A REGRESSION: the census was correct over the wrong
    population. Its scope is *everything ruff reports in cwd*, and a dependency bump changed what
    is in cwd. ⚑ THE RATCHET CAUGHT ITS OWN BLIND SPOT — a bump that silently added 49 keys to a
    baseline would have been far worse than one that refused.

    ⚑ THE ARM ASSERTS BOTH DIRECTIONS. A generated bootstrap is dropped; a hand-written module
    with an underscore name is KEPT, because "starts with an underscore" is a naming convention
    this repository uses for its own private modules and excluding on it would pay down real debt
    by accident — precisely the over-exclusion the sibling arm was written about.
    """
    (tmp_path / "ratchet").mkdir()
    (tmp_path / "ratchet" / "_ratchet_cli_stage2_bootstrap.py").write_text(
        "# generated by rules_python\nimport sys\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "_private.py").write_text('"""A real private module."""\n',
                                                  encoding="utf-8")
    keys = parse_concise(
        ["ratchet/_ratchet_cli_stage2_bootstrap.py:1:1: some-rule: msg",
         "src/_private.py:1:1: some-rule: msg"],
        tmp_path)
    assert keys == frozenset({"src/_private.py:some-rule"})


@pytest.mark.parametrize("rc", [0, 1])
def test_a_successful_exit_is_accepted_not_merely_not_refused(rc: int, tmp_path: Path) -> None:
    """Exit 0 and exit 1 both produce a census rather than a refusal.

    ⚑⚑⚑ THE SIBLING ARM ABOVE IS ONE-ARMED AND WOULD PASS ON A PREDICATE THAT REFUSED
    EVERYTHING. It proves an unexpected status refuses; nothing proved the expected ones are
    ACCEPTED. A checker rewritten to refuse every exit status satisfies it completely, which is
    the broken-shut gate this repository's own discipline names — a refusal arm without its
    positive control measures that something happened, not that the right thing did.

    ⚑⚑ AND BOTH VALUES ARE LOAD-BEARING FOR DIFFERENT REASONS. Exit 0 is a clean tree; exit 1 is
    a tree WITH FINDINGS, which is the normal case for a census and the one whose loss would be
    silent — refusing it would turn every real census into a refusal, and refusing 0 would turn a
    clean distribution into one that cannot be measured at all.

    ⚑ THIS ARM IS ALSO THE CONTROL FOR A REFACTOR. The membership test is being rewritten from a
    tuple to a set literal on a linter's advice; a rewrite that changed WHICH statuses are accepted
    would be invisible to the one-armed sibling and is caught here.
    """
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    ruff = tmp_path / ".venv" / "bin" / "ruff"
    ruff.write_text(f"#!/bin/sh\nexit {rc}\n", encoding="utf-8")
    ruff.chmod(0o755)
    # ⚑ NO RAISE. The assertion is that this RETURNS at all; an empty census from a checker that
    # ran cleanly is a correct empty census, unlike one from a checker that never ran.
    # ⚑⚑ A `frozenset`, AND I ASSERTED A LIST. The first cut compared against `[]` — the return
    # type read from expectation rather than from the function. The behaviour was already correct;
    # only my claim about it was wrong, which is the cheapest possible instance of characterising
    # an instrument without reading it.
    assert run_ruff(tmp_path, preview=True) == frozenset()
