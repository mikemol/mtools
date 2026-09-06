# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ratchet's witnesses: set membership, the four states, and the required write."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.ratchet.core import Diff, partition, ratchet, read_baseline, write_baseline
from mikemol.ratchet.state import BaselineState

if TYPE_CHECKING:
    from pathlib import Path


def _base(tmp_path: Path, keys: set[str]) -> Path:
    path = tmp_path / "baseline.txt"
    write_baseline(path, keys, write=True)
    return path


def test_a_substitution_at_constant_size_is_refused(tmp_path: Path) -> None:
    """⚑⚑⚑ THE ARM THAT PROVES THIS IS A SET RATCHET AND NOT A COUNT WEARING THE NAME.

    Pay one key down and add another: the cardinality is unchanged, so a count-based ratchet
    reports green while the membership churned entirely. The origin measured this as
    "six-vs-six different sets". Under set membership the added key is refused.
    """
    path = _base(tmp_path, {"a", "b"})
    code, lines = ratchet({"a", "z"}, path, write=False)
    assert code == 1
    assert any("+ z" in line for line in lines)


def test_growth_is_refused(tmp_path: Path) -> None:
    """A key present now and absent from the baseline is refused."""
    assert ratchet({"a", "b", "c"}, _base(tmp_path, {"a", "b"}), write=False)[0] == 1


def test_an_unchanged_census_passes(tmp_path: Path) -> None:
    """The P-arm. Without it every refusal above passes against a gate that refuses all."""
    assert ratchet({"a", "b"}, _base(tmp_path, {"a", "b"}), write=False)[0] == 0


def test_paydown_passes_and_lowers_the_baseline(tmp_path: Path) -> None:
    """⚑ PAYDOWN LOWERS PERMANENTLY, so a repair cannot silently regress."""
    path = _base(tmp_path, {"a", "b"})
    assert ratchet({"a"}, path, write=True)[0] == 0
    assert read_baseline(path)[1] == frozenset({"a"})
    assert ratchet({"a", "b"}, path, write=False)[0] == 1


def test_a_mixed_run_refuses_and_writes_nothing(tmp_path: Path) -> None:
    """⚑ Lowering alongside growth would bank the paydown and lose the refusal in one run."""
    path = _base(tmp_path, {"a", "b"})
    assert ratchet({"a", "c"}, path, write=True)[0] == 1
    assert read_baseline(path)[1] == frozenset({"a", "b"})


def test_an_absent_baseline_is_refused_rather_than_read_as_clean(tmp_path: Path) -> None:
    """⚑⚑ ABSENT READS GREEN WHILE ASSERTING NOTHING, which is why it exits 1 here.

    A gate with no baseline has nothing to check against and is indistinguishable in a
    summary line from a gate that examined a clean tree.
    """
    code, lines = ratchet({"a"}, tmp_path / "nothing.txt", write=False)
    assert code == 1
    assert any("green over nothing" in line for line in lines)


def test_an_empty_baseline_refuses_every_key(tmp_path: Path) -> None:
    """⚑⚑ EMPTY IS THE STRONGEST STATE, NOT A DEGRADED ONE — every key reads as new."""
    path = tmp_path / "empty.txt"
    write_baseline(path, set(), write=True)
    assert read_baseline(path)[0] is BaselineState.EMPTY
    assert ratchet({"a"}, path, write=False)[0] == 1
    assert ratchet(set(), path, write=False)[0] == 0


def test_absent_and_empty_are_different_facts(tmp_path: Path) -> None:
    """ABSENT and EMPTY are different facts.

    ⚑⚑ Both yield an empty key set, and they are OPPOSITES: one asserts nothing, the other
    is zero tolerance. A reader keeping only the set cannot tell them apart.
    """
    absent, absent_keys = read_baseline(tmp_path / "missing.txt")
    path = tmp_path / "empty.txt"
    write_baseline(path, set(), write=True)
    empty, empty_keys = read_baseline(path)
    assert absent_keys == empty_keys == frozenset()
    assert absent is BaselineState.ABSENT
    assert empty is BaselineState.EMPTY
    assert absent.is_defect
    assert not empty.is_defect


def test_an_unreadable_baseline_is_unread_rather_than_empty(tmp_path: Path) -> None:
    """⚑ A decode failure is a fact about the READER, not a verdict about the gate.

    Reporting it as EMPTY would silently widen what the ratchet permits to everything.
    """
    path = tmp_path / "binary.txt"
    path.write_bytes(b"\xff\xfe\x00 not utf-8")
    state, keys = read_baseline(path)
    assert state is BaselineState.UNREAD
    assert keys == frozenset()
    assert ratchet({"a"}, path, write=False)[0] == 1


def test_write_false_is_a_no_op(tmp_path: Path) -> None:
    """⚑⚑ `write` IS REQUIRED AND EXPLICIT — no environment variable arms a mutation here.

    An ambient switch is the same shape as a hook reporting itself armed while refusing
    nothing, and under a build system a cached write is a skipped write.
    """
    path = tmp_path / "unwritten.txt"
    write_baseline(path, {"a"}, write=False)
    assert not path.exists()


def test_a_write_confirms_what_landed(tmp_path: Path) -> None:
    """A write confirms what landed.

    ⚑ A write succeeding and a write landing are different claims. A baseline that did not
    land reads as ABSENT next run — which reads green while asserting nothing.
    """
    path = tmp_path / "written.txt"
    write_baseline(path, {"b", "a"}, write=True)
    assert path.read_text(encoding="utf-8") == "a\nb\n"


def test_the_partition_separates_growth_from_paydown() -> None:
    """Growth and paydown are independent; a run can do both."""
    diff = partition({"a", "c"}, {"a", "b"})
    assert diff == Diff(added=frozenset({"c"}), paid=frozenset({"b"}))
    assert diff.grew


@pytest.mark.parametrize(
    ("state", "is_defect", "deserves_mark"),
    [(BaselineState.OK, False, False),
     (BaselineState.EMPTY, False, False),
     (BaselineState.ABSENT, True, True),
     (BaselineState.UNREAD, False, True)])
def test_each_state_declares_two_independent_properties(
        state: BaselineState, is_defect: bool, deserves_mark: bool) -> None:  # noqa: FBT001
    """Each state declares two independent properties.

    ⚑⚑ A 2-BIT SPACE A BOOLEAN CANNOT CARRY. UNREAD marks without being a defect; EMPTY is
    neither. Any `!= OK` flattens it to one bit, always reading strictness as debt.
    """
    assert state.is_defect is is_defect
    assert state.deserves_mark is deserves_mark


def test_a_relocated_finding_is_a_move_not_growth(tmp_path: Path) -> None:
    """A rename is content-preserving but KEY-CHANGING, and must not read as new debt.

    ⚑⚑⚑ CONFLATING A MOVE WITH GROWTH BLOCKS THE DRAIN THAT EARNS THE PAYDOWN. The old key
    retires and a new one is minted for a byte-identical finding; a set ratchet sees "a key
    appeared" and refuses — and because it returns on `added` before reaching the paydown
    branch, the churn also stops real paydown recording. MEASURED before this existed, one
    `git mv` of lint.py: `1 new key REFUSED` AND `1 key paid down`, for no content change.
    """
    path = _base(tmp_path, {"a.py:rule1"})
    code, lines = ratchet({"b.py:rule1"}, path, write=False)
    assert code == 0
    assert any("MOVED" in line for line in lines)


def test_a_move_lowers_the_baseline(tmp_path: Path) -> None:
    """A move lowers the baseline.

    ⚑ Else the next run refuses the same relocation again, blocking a reorganisation
    permanently rather than once — which is the defect the distinction exists to remove.
    """
    path = _base(tmp_path, {"a.py:rule1"})
    assert ratchet({"b.py:rule1"}, path, write=True)[0] == 0
    assert read_baseline(path)[1] == frozenset({"b.py:rule1"})


def test_a_different_rule_at_a_new_path_is_growth(tmp_path: Path) -> None:
    """A different rule at a new path is growth, not a move.

    ⚑ THE IDENTITY IS THE RULE, so only a matching rule pairs. A different finding at a
    different path is two facts, not one relocated one — and absorbing it as a move would be
    the ratchet weakened rather than sharpened.
    """
    assert ratchet({"b.py:rule2"}, _base(tmp_path, {"a.py:rule1"}), write=False)[0] == 1


def test_a_move_alongside_growth_still_refuses(tmp_path: Path) -> None:
    """⚑ Recognising the move must not launder the growth beside it."""
    path = _base(tmp_path, {"a.py:rule1"})
    assert ratchet({"b.py:rule1", "c.py:new"}, path, write=True)[0] == 1
    assert read_baseline(path)[1] == frozenset({"a.py:rule1"})


def test_one_retirement_cannot_absolve_two_arrivals(tmp_path: Path) -> None:
    """Refuse an absolution of two arrivals by one retirement.

    ⚑⚑ The false absolution, F-armed. Identity alone paired `a.py` with BOTH `b.py` and
    `z.py` and reported no growth — measured in this repository's own first cut, and warned
    about by the peer that hit it on its first live run. A move is ONE-TO-ONE.
    """
    path = _base(tmp_path, {"a.py:rule1"})
    assert ratchet({"b.py:rule1", "z.py:rule1"}, path, write=True)[0] == 1
    assert read_baseline(path)[1] == frozenset({"a.py:rule1"})


def test_a_shared_rule_at_an_unrelated_path_is_not_a_move(tmp_path: Path) -> None:
    """Refuse a pairing that names no relocation.

    ⚑ One-to-one is necessary and NOT sufficient: `a.py` and `q/z.py` are unambiguously
    pairable by count while naming no relocation any tree performed. The pairing therefore
    also demands a plausible path move — a split into a directory, or a rename within one.
    """
    path = _base(tmp_path, {"a.py:rule1"})
    assert ratchet({"q/z.py:rule1"}, path, write=True)[0] == 1


def test_two_findings_relocating_together_are_two_moves(tmp_path: Path) -> None:
    """Recognise a two-for-two directory reorganisation.

    ⚑ The case the count asymmetry alone REFUSED. A directory reorganisation retires two
    keys and adds two; distinct identities pair independently, so this is churn, not growth.
    """
    path = _base(tmp_path, {"pkg/a.py:rule1", "pkg/b.py:rule2"})
    assert ratchet({"pkg/x.py:rule1", "pkg/y.py:rule2"}, path, write=True)[0] == 0


def test_fan_out_refusal_is_unconditional_not_a_mode(tmp_path: Path) -> None:
    """⚑⚑⚑ The divergence from the peer implementation, pinned as an assertion.

    Both trees derived path-plausibility independently and AGREE on every classification.
    They disagree on ONE thing: the peer's fan-out defence is a `strict=` parameter,
    opt-in at its CLI and defaulting OFF — measured by running its own `classify` on this
    exact shape, which returned two churn entries under the default and two SUSPECT
    entries only when strict was passed. Its production caller threads the flag through
    from an argv check.

    ⚑ A DEFENCE THAT DEFAULTS OFF IS THE FALSE ABSOLUTION WITH A FLAG BESIDE IT. The whole
    hazard is that the laundering is silent; a mode nobody passes cannot announce itself,
    and the operator who most needs the refusal is the one who does not know to ask. Here
    it is unconditional, so this test exists to refuse a future `strict=` parameter as much
    as to check the behaviour.
    """
    path = _base(tmp_path, {"a.py:rule1"})
    assert ratchet({"b.py:rule1", "z.py:rule1"}, path, write=True)[0] == 1
    assert "moved" not in " ".join(ratchet({"b.py:rule1", "z.py:rule1"}, path, write=False)[1])


def test_an_ambiguous_refusal_is_marked_suspect() -> None:
    """⚑⚑ The third outcome: refused, AND the evidence could not distinguish it from a move.

    A fan-out means at most one of the arrivals is the relocation and nothing in the census
    says which. Both are refused — the verdict is unchanged — but an operator reading the
    transcript needs "I refused this and could not have told you it was real" apart from
    "this is new debt".
    """
    assert partition({"b.py:rule1", "z.py:rule1"}, {"a.py:rule1"}).suspect == frozenset(
        {"b.py:rule1", "z.py:rule1"})


def test_an_unambiguous_refusal_is_not_suspect() -> None:
    """⚑⚑⚑ The arm that gives the mark its meaning. A state everything carries says nothing.

    `q/z.py` shares a rule with the retired `a.py` and is refused — but it was never
    path-plausible, so the census CAN tell it is new debt. Marking it too would make
    `suspect` a synonym for `added`, which is the failure mode of every added state that
    was not F-armed.
    """
    assert partition({"q/z.py:rule1"}, {"a.py:rule1"}).suspect == frozenset()


def test_suspect_never_softens_the_verdict(tmp_path: Path) -> None:
    """⚑⚑⚑ `suspect` says WHY a key was refused, never WHETHER.

    The peer implementation carries this state behind a `strict=` flag defaulting OFF, so its
    fan-out classifies as churn unless asked — measured by running its own classifier. Here
    the refusal is unconditional and the state is pure vocabulary, so it cannot become a route
    by which something passes. This test is the guard on that.
    """
    path = _base(tmp_path, {"a.py:rule1"})
    code, lines = ratchet({"b.py:rule1", "z.py:rule1"}, path, write=True)
    assert code == 1
    assert any("AMBIGUOUS" in line for line in lines)
    assert read_baseline(path)[1] == frozenset({"a.py:rule1"})
