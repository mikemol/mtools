# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `context`: the intent and tenant ambients and the snapshot record."""

from __future__ import annotations

import contextvars
from typing import TYPE_CHECKING

import pytest

from mikemol.treeio import ambient
from mikemol.treeio.ambient import AmbientConflictError
from mikemol.treeio.context import (
    INTENT,
    SNAPSHOT_STATE,
    TENANT,
    IntentConflict,
    SnapshotState,
    bind_intent,
    naming_tenant,
    resolve_intent,
    sanctioned_setters,
)
from mikemol.treeio.errors import AmbientVocabError

if TYPE_CHECKING:
    from collections.abc import Callable


def _fresh[T](fn: Callable[[], T]) -> T:
    """Run `fn` as its own invocation, in a genuinely fresh context.

    Returns:
        Whatever `fn` returns.

    """
    return contextvars.copy_context().run(fn)


def test_the_intent_ambient_is_closed_to_apply_and_dry_run_and_names_its_two_readings() -> None:
    """Intent is write-once over two values, and a conflict says what the two readings are."""
    assert (INTENT.kw, INTENT.vocab) == ("intent", ("apply", "dry-run"))
    assert INTENT.two_readings.startswith("These are two different propositions spelled the same")
    assert "'what the operator asked for'" in INTENT.two_readings
    assert "'what this branch actually does'" in INTENT.two_readings


def test_the_tenant_ambient_is_closed_to_live_and_sandbox_and_says_why() -> None:
    """Tenant is write-once over two values, and a conflict says one report read two stores."""
    assert (TENANT.kw, TENANT.vocab) == ("tenant", ("live", "sandbox"))
    assert "plausible rows nobody can distinguish" in TENANT.two_readings
    assert "one report read two stores" in TENANT.two_readings


def test_bind_intent_binds_once_and_a_second_binding_raises() -> None:
    """Binding records the value and the origin, and a second binding names both sites."""

    def bind() -> tuple[str | None, str | None, str]:
        tokens = bind_intent("apply", "argv at tool (--apply)")
        return INTENT.get(), INTENT.origin(), str(len(tokens))

    def rebind() -> str:
        bind_intent("apply", "argv at tool (--apply)")
        try:
            bind_intent("dry-run", "somewhere else")
        except AmbientConflictError as e:
            return e.origin
        return "NO RAISE"

    assert _fresh(bind) == ("apply", "argv at tool (--apply)", "2")
    assert _fresh(rebind) == "argv at tool (--apply)"


def test_resolve_intent_binds_when_unbound_agrees_silently_and_refuses_a_disagreement() -> None:
    """The three arms: bind, agree, and disagree."""

    def arms() -> tuple[str | None, str | None, str | None, str | None]:
        before = resolve_intent("nobody")
        bound = resolve_intent("first", stated="dry-run")
        agreed = resolve_intent("second", stated="dry-run")
        try:
            resolve_intent("third", stated="apply")
        except AmbientConflictError:
            return before, bound, agreed, INTENT.origin()
        return None, None, None, "NO RAISE"

    assert _fresh(arms) == (None, "dry-run", "dry-run", "stated at first")


def test_naming_tenant_returns_the_label_a_result_must_carry() -> None:
    """Binding the tenant hands back the bracketed label so a printed result names its store."""

    def name() -> tuple[str, str | None]:
        return naming_tenant("live", "a-report"), TENANT.get()

    assert _fresh(name) == ("[tenant=live]", "live")


def test_two_independent_tenant_resolutions_in_one_invocation_raise_naming_the_first() -> None:
    """The wrong-store incident in miniature: two functions, one report, two answers."""

    def coverage() -> str:
        return naming_tenant("sandbox", "_live_indexed")

    def selectivity() -> str:
        return naming_tenant("live", "_selectivity")

    def report() -> str:
        coverage()
        try:
            selectivity()
        except AmbientConflictError as e:
            return str(e)
        return "NO RAISE"

    message = _fresh(report)
    assert "bound:    'sandbox'  by stated at _live_indexed" in message
    assert "attempted:'live'  at stated at _selectivity" in message


def test_a_tenant_outside_the_vocabulary_is_refused() -> None:
    """An unrecognised tenant never binds: the refusal quotes the two it wanted."""

    def bad() -> str:
        try:
            naming_tenant("prod", "a-report")
        except AmbientVocabError as e:
            return str(e)
        return "NO RAISE"

    assert "tenant='prod' is not one of 'live' / 'sandbox'" in _fresh(bad)


def test_the_snapshot_record_starts_unbound_and_its_copied_set_is_its_own() -> None:
    """No record exists before a snapshot, and two records never share one copied set."""
    assert _fresh(SNAPSHOT_STATE.get) is None
    first = SnapshotState(sha=None, label="a")
    second = SnapshotState(sha="deadbeef", label="b")
    first.copied.add("x.agda")
    assert (first.sha, first.label, first.copied) == (None, "a", {"x.agda"})
    assert (second.sha, second.label, second.copied) == ("deadbeef", "b", set())


def test_the_snapshot_copied_set_accumulates_and_a_latch_would_not() -> None:
    """The record keeps one sha and grows its copies, which a module-level latch cannot say."""

    def accumulate() -> tuple[str | None, int]:
        SNAPSHOT_STATE.set(SnapshotState(sha="deadbeef", label="t"))
        state = SNAPSHOT_STATE.get()
        assert state is not None
        state.copied.add("a.agda")
        state.copied.add("b.agda")
        again = SNAPSHOT_STATE.get()
        assert again is not None
        return again.sha, len(again.copied)

    assert _fresh(accumulate) == ("deadbeef", len(("a.agda", "b.agda")))


def test_a_write_in_one_context_does_not_reach_a_sibling_context() -> None:
    """The latch's bug in miniature: sibling invocations must not share arming."""
    probe = contextvars.ContextVar[dict[str, bool] | None]("probe_isolation", default=None)
    _fresh(lambda: probe.set({"armed": True}))
    assert _fresh(probe.get) is None
    _fresh(lambda: SNAPSHOT_STATE.set(SnapshotState(sha="x", label="t")))
    assert _fresh(SNAPSHOT_STATE.get) is None


def test_the_sanctioned_setters_are_enumerable_data_and_each_call_gets_its_own_copy() -> None:
    """A new binding site is a new key, so a gate can refuse it; the census is data."""
    got = sanctioned_setters()
    assert sorted(got) == [
        ("intent", "require_explicit_mutation"),
        ("intent", "resolve_intent"),
        ("snapshot", "snapshot"),
        ("snapshot", "snapshot_once"),
        ("tenant", "naming_tenant"),
    ]
    assert got["intent", "resolve_intent"] == "binds a stated intent when none is ambient"
    got.clear()
    assert len(sanctioned_setters()) == len(("a", "b", "c", "d", "e"))


def test_the_old_conflict_names_are_the_one_error_class() -> None:
    """Paperkit's earlier spellings stay importable and are the same class, not subclasses."""
    assert IntentConflict is AmbientConflictError
    assert ambient.AmbientConflict is AmbientConflictError


def test_an_unregistered_tenant_override_is_refused_through_the_shared_machinery() -> None:
    """The tenant ambient is the same mechanism as intent, so its override roster refuses too."""
    with pytest.raises(ValueError, match="NOT REGISTERED"):
        TENANT.override("live", reason="because", label="not_registered")
