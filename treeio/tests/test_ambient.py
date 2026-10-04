# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `ambient`: write-once binding, agreeing resolution, and the scoped override."""

from __future__ import annotations

import contextvars
from typing import TYPE_CHECKING

import pytest

from mikemol.treeio.ambient import (
    SANCTIONED_OVERRIDES,
    Ambient,
    AmbientConflictError,
    Override,
)
from mikemol.treeio.errors import AmbientVocabError, MutationContractError

if TYPE_CHECKING:
    from collections.abc import Callable

_LABEL = "prune_leaf_opens (dry-run writes-then-restores)"


def _fresh[T](fn: Callable[[], T]) -> T:
    """Run `fn` as its own invocation, in a genuinely fresh context.

    Returns:
        Whatever `fn` returns.

    """
    return contextvars.copy_context().run(fn)


def _probe() -> Ambient:
    """Make a throwaway ambient with a two-value vocabulary.

    Returns:
        An unbound ambient named probe.

    """
    return Ambient("probe", ("x", "y"), "two readings")


def _intent() -> Ambient:
    """Make an ambient named intent, the only name a registered override exists for.

    Returns:
        An unbound ambient named intent.

    """
    return Ambient("intent", ("apply", "dry-run"), "two readings")


def test_a_new_ambient_is_unbound_and_keeps_its_declaration() -> None:
    """The declaration is kept as given, the vocabulary as a tuple, and nothing is bound."""
    amb = _probe()
    assert amb.kw == "probe"
    assert amb.vocab == ("x", "y")
    assert amb.two_readings == "two readings"
    assert _fresh(amb.get) is None
    assert _fresh(amb.origin) is None


def test_a_first_write_binds_the_value_and_its_origin_in_one_act() -> None:
    """Both halves are set together, and the tokens of the two writes are returned."""

    def bind() -> tuple[str | None, str | None, int]:
        amb = _probe()
        tokens = amb.set("x", "first")
        return amb.get(), amb.origin(), len(tokens)

    assert _fresh(bind) == ("x", "first", len(("value", "origin")))


def test_a_value_outside_the_vocabulary_refuses_and_names_the_vocabulary() -> None:
    """An unrecognised value never passes: the refusal quotes what it wanted."""

    def bad() -> str:
        try:
            _probe().set("z", "a-site")
        except AmbientVocabError as e:
            return str(e)
        return "NO RAISE"

    message = _fresh(bad)
    assert message.startswith("⚑ a-site: probe='z' is not one of 'x' / 'y'.")
    assert "REFUSES rather than passing" in message


def test_a_second_write_raises_and_names_who_bound_it_and_who_tried() -> None:
    """The positive control: write-once refuses the second binding, at the write."""

    def twice() -> str:
        amb = _probe()
        amb.set("x", "first")
        try:
            amb.set("y", "second")
        except AmbientConflictError as e:
            return str(e)
        return "NO RAISE"

    message = _fresh(twice)
    assert (
        "⚑ second: probe is ALREADY BOUND for this invocation ('x') and is WRITE-ONCE." in message
    )
    assert "  bound:    'x'  by first\n" in message
    assert "  attempted:'y'  at second\n" in message
    assert "  two readings\n" in message
    assert "values MATCH" not in message


def test_a_second_write_of_the_same_value_is_still_a_defect() -> None:
    """Two sites each believing they decide is the shape; they agree today, by luck."""

    def twice() -> str:
        amb = _probe()
        amb.set("x", "first")
        try:
            amb.set("x", "second")
        except AmbientConflictError as e:
            return str(e)
        return "NO RAISE"

    message = _fresh(twice)
    assert "The values MATCH, which is not a reprieve" in message
    assert "two readings" not in message


def test_the_conflict_message_names_its_successors_in_order() -> None:
    """A refusal that names no successor invites a local invention, so all three are named."""

    def conflict() -> AmbientConflictError:
        amb = _probe()
        amb.set("x", "first")
        try:
            amb.set("y", "second")
        except AmbientConflictError as e:
            return e
        raise AssertionError

    err = _fresh(conflict)
    text = str(err)
    assert "1. READ IT, do not re-bind it: `mikemol.treeio.context.PROBE.get()`" in text
    assert "2. BIND IT ONCE, AT ENTRY" in text
    assert "3. If this genuinely is a NEW invocation" in text
    assert "`PROBE.override(...)`" in text
    assert "`mikemol.treeio.ambient.SANCTIONED_OVERRIDES`" in text
    assert text.index("1. READ IT") < text.index("2. BIND IT") < text.index("3. If this")
    assert (err.label, err.stated, err.ambient, err.origin) == ("second", "y", "x", "first")
    assert isinstance(err, MutationContractError)
    assert not isinstance(err, Exception)


def test_an_agreeing_resolve_passes_silently_and_a_disagreeing_one_raises() -> None:
    """The negative control and the positive control of resolution against a bound value."""

    def agree() -> str | None:
        amb = _probe()
        amb.set("x", "entry")
        return amb.resolve("a callee", stated="x")

    def disagree() -> str:
        amb = _probe()
        amb.set("x", "entry")
        try:
            amb.resolve("a callee", stated="y")
        except AmbientConflictError as e:
            return str(e)
        return "NO RAISE"

    assert _fresh(agree) == "x"
    assert "  attempted:'y'  at stated at a callee\n" in _fresh(disagree)


def test_resolve_binds_when_unbound_and_only_reads_when_nothing_is_stated() -> None:
    """An unbound resolve with a statement binds it, and a bare resolve reads whatever is bound."""

    def bind() -> tuple[str | None, str | None, str | None]:
        amb = _probe()
        before = amb.resolve("nobody")
        stated = amb.resolve("only site", stated="y")
        return before, stated, amb.origin()

    def read_back() -> str | None:
        amb = _probe()
        amb.set("x", "entry")
        return amb.resolve("a reader")

    assert _fresh(bind) == (None, "y", "stated at only site")
    assert _fresh(read_back) == "x"


def test_run_bound_runs_in_a_copied_context_and_leaves_the_outer_binding_alone() -> None:
    """The body sees the divergent value and origin; the caller afterwards sees its own."""

    def scoped() -> tuple[str | None, str | None, str | None, str | None, int]:
        amb = _probe()
        amb.set("x", "outer")
        inside = amb.run_bound("y", "inner", lambda: (amb.get(), amb.origin()))
        return inside[0], inside[1], amb.get(), amb.origin(), amb.run_bound("x", "i", lambda: 7)

    assert _fresh(scoped) == ("y", "inner", "x", "outer", 7)


def test_an_override_refuses_a_value_outside_the_vocabulary() -> None:
    """An override is at least as strict as the contract it diverges from."""
    with pytest.raises(ValueError, match="not one of 'apply' / 'dry-run'") as caught:
        _intent().override("maybe", reason="because", label=_LABEL)
    assert str(caught.value).startswith("intent.override('maybe'): not one of 'apply' / 'dry-run'.")


def test_an_override_refuses_a_missing_or_blank_reason() -> None:
    """A reasonless override is a no-verify: it leaves no trace of why."""
    for reason in ("", "   "):
        with pytest.raises(ValueError, match="requires a REASON") as caught:
            _intent().override("apply", reason=reason, label=_LABEL)
        assert "`--no-verify`" in str(caught.value)


def test_an_unregistered_override_refuses_and_names_the_roster() -> None:
    """The refusal names the three successors and the roster to register in."""
    with pytest.raises(ValueError, match="NOT REGISTERED") as caught:
        _intent().override("apply", reason="because", label="not_registered")
    message = str(caught.value)
    assert message.startswith("intent.override(...) at label 'not_registered' is NOT REGISTERED.")
    assert "1. DO NOT DIVERGE — let the ambient intent stand." in message
    assert "2. State it at the ENTRY point instead" in message
    assert (
        "mikemol.treeio.ambient.SANCTIONED_OVERRIDES` under ('intent', 'not_registered')" in message
    )
    assert "a local branch that 'knows better'" in message


def test_the_roster_has_its_one_registered_case_with_a_reason() -> None:
    """A roster with one member is the honest shape, and its reason says why it exists."""
    assert list(SANCTIONED_OVERRIDES) == [("intent", _LABEL)]
    assert "EVEN IN DRY RUN" in SANCTIONED_OVERRIDES["intent", _LABEL]


def test_a_registered_override_runs_scoped_and_announces_what_it_displaced() -> None:
    """The body sees the override, the outer binding survives, and the divergence says why."""
    heard: list[str] = []

    def scoped() -> tuple[str | None, str | None, str | None, str | None]:
        amb = _intent()
        amb.set("dry-run", "entry")
        over = amb.override(
            "apply", reason="  writes then restores  ", label=_LABEL, announce_to=heard.append
        )
        inside = over.run(lambda: (amb.get(), amb.origin()))
        return inside[0], inside[1], amb.get(), amb.origin()

    inner_value, inner_origin, outer_value, outer_origin = _fresh(scoped)
    assert (inner_value, outer_value, outer_origin) == ("apply", "dry-run", "entry")
    assert inner_origin == f"override at {_LABEL}: writes then restores"
    assert heard == [
        (
            f"   ⚑ {_LABEL}: intent OVERRIDE 'dry-run' → 'apply' in a copied context "
            "(outer binding by entry is unchanged)\n     reason: writes then restores"
        )
    ]


def test_an_override_that_displaces_nothing_is_silent() -> None:
    """Unbound, or already equal to the divergent value, there is nothing to announce."""
    heard: list[str] = []

    def runs() -> tuple[str | None, str | None]:
        unbound = _intent()
        over = unbound.override("apply", reason="r", label=_LABEL, announce_to=heard.append)
        first = over.run(unbound.get)
        same = _intent()
        same.set("apply", "entry")
        second = same.override("apply", reason="r", label=_LABEL, announce_to=heard.append).run(
            same.get
        )
        return first, second

    assert _fresh(runs) == ("apply", "apply")
    assert heard == []


def test_an_override_announces_to_stderr_by_default(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With no sink given the divergence is said on stderr, never silently."""

    def scoped() -> None:
        amb = _intent()
        amb.set("dry-run", "entry")
        amb.override("apply", reason="r", label=_LABEL).run(amb.get)

    _fresh(scoped)
    err = capsys.readouterr().err
    assert err.startswith(f"   ⚑ {_LABEL}: intent OVERRIDE 'dry-run' → 'apply'")
    assert err.endswith("reason: r\n")


def test_an_override_is_not_a_context_manager_and_names_the_callable_successor() -> None:
    """A with block would write then reset, the hole write-once closes, so it is refused."""
    over = _intent().override("apply", reason="r", label=_LABEL)
    assert isinstance(over, Override)
    with pytest.raises(TypeError, match="not a context manager, deliberately") as caught, over:
        pass
    message = str(caught.value)
    assert "INTENT.override('apply', reason=…, label=…)" in message
    assert ".run(lambda: <the work>)" in message
    assert Override.__exit__ is Override.__enter__
