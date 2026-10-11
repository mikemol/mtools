# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Unit witnesses for the result cache, the adapter table and the outcome axes, without pytester.

W1004. ⚑ THESE WERE ONLY REACHED THROUGH A WHOLE PYTEST SESSION, and a declared defect in each
survived: a cache entry for another impl or key, a missing result or a non-object entry still hit;
two keys were still cached; a duplicate implementation name was accepted; a case denied and
withheld read as withheld. The plugin tests drive the happy path; these drive each refusal.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from mikemol.pytestspec import adapters, cache, outcomes
from mikemol.pytestspec.spec import DO_NOT_PORT, Case, Disposition, Expect, SpecDataError, Verdict

ROOT_CASE: Case = {"case": "c", "fixture": "F", "operands": "O", "extra": 1}


class _Hook:
    """The two hook callers the cache and the adapter table ask, answering from a fixed list."""

    def __init__(self, answers: list[object]) -> None:
        self.answers = answers

    def pytest_spec_cache_key(self, impl: str, case: Case) -> list[object]:
        """Answer the cache-key hook.

        Returns:
            the fixed answers.

        """
        del impl, case
        return list(self.answers)

    def pytest_spec_implementations(self) -> list[object]:
        """Answer the implementations hook.

        Returns:
            the fixed answers.

        """
        return list(self.answers)


@dataclass
class _Config:
    hook: _Hook


def _config(*answers: object) -> pytest.Config:
    """Build a stand-in for `pytest.Config` whose hooks answer with `answers`.

    Returns:
        the stand-in, typed as the real thing.

    """
    return cast("pytest.Config", _Config(_Hook(list(answers))))


def _echo(fixture: object, operands: object) -> object:
    return (fixture, operands)


def _other(fixture: object, operands: object) -> object:
    del fixture, operands
    return None


# --- cache -------------------------------------------------------------------------------------


def test_a_stored_result_is_loaded_back_under_the_same_impl_and_key(tmp_path: Path) -> None:
    """The control: what is stored under (impl, key) is what a load of (impl, key) returns."""
    assert cache.store(tmp_path, "a", "k", {"x": 1})
    assert cache.load(tmp_path, "a", "k") == (True, {"x": 1})


def test_two_impls_with_one_key_keep_separate_entries(tmp_path: Path) -> None:
    """The entry is addressed by the impl too, so the second impl does not overwrite the first."""
    assert cache.store(tmp_path, "a", "k", 1)
    assert cache.store(tmp_path, "b", "k", 2)
    assert cache.load(tmp_path, "a", "k") == (True, 1)
    assert cache.load(tmp_path, "b", "k") == (True, 2)


@pytest.mark.parametrize(
    "text",
    [
        '{"impl": "other", "key": "k", "result": 1}',
        '{"impl": "a", "key": "other", "result": 1}',
        '{"impl": "a", "key": "k"}',
        "[1, 2]",
        "{not json",
    ],
)
def test_an_entry_that_is_not_for_this_impl_and_key_or_holds_no_result_is_a_miss(
    tmp_path: Path, text: str
) -> None:
    """A collision, a hand-copied file, a half entry and garbage are all misses, never hits."""
    cache.entry(tmp_path, "a", "k").write_text(text, encoding="utf-8")
    assert cache.load(tmp_path, "a", "k") == (False, None)


def test_an_absent_entry_is_a_miss(tmp_path: Path) -> None:
    """No file is a miss, not an error."""
    assert cache.load(tmp_path, "a", "k") == (False, None)


def test_a_result_json_cannot_hold_is_not_stored_and_does_not_raise(tmp_path: Path) -> None:
    """The case still runs: storing an object that is no JSON returns False and writes nothing."""
    assert not cache.store(tmp_path, "a", "k", object())
    assert not list(tmp_path.iterdir())


def test_a_stored_entry_leaves_no_partial_file_and_sorts_its_result_keys(tmp_path: Path) -> None:
    """The write goes through a partial file that is renamed away, and keys are written sorted."""
    assert cache.store(tmp_path, "a", "k", {"b": 1, "a": 2})
    assert [p.name for p in tmp_path.iterdir()] == [cache.entry(tmp_path, "a", "k").name]
    text = cache.entry(tmp_path, "a", "k").read_text(encoding="utf-8")
    assert '"result": {"a": 2, "b": 1}' in text


def test_the_one_key_named_is_the_cases_key() -> None:
    """One hookimpl's key, the same key named twice, and a key beside a None are all that key."""
    assert cache.key_for(_config("k"), "a", ROOT_CASE) == "k"
    assert cache.key_for(_config("k", "k"), "a", ROOT_CASE) == "k"
    assert cache.key_for(_config(None, "k"), "a", ROOT_CASE) == "k"


def test_no_key_or_two_different_keys_means_the_case_is_not_cached() -> None:
    """Nothing named, only non-strings named, and two different keys named are all uncacheable."""
    assert cache.key_for(_config(), "a", ROOT_CASE) is None
    assert cache.key_for(_config(None, 5), "a", ROOT_CASE) is None
    assert cache.key_for(_config("k1", "k2"), "a", ROOT_CASE) is None


# --- adapters ----------------------------------------------------------------------------------


def test_every_offered_implementation_is_collected_by_name() -> None:
    """The control: two tables offering different names give both."""
    got = adapters.registered(_config({"a": _echo}, {"b": _other}))
    assert got == {"a": _echo, "b": _other}


def test_a_name_offered_by_two_plugins_is_refused() -> None:
    """Which one ran would be an accident, so the table refuses it."""
    with pytest.raises(SpecDataError, match="two plugins offer"):
        adapters.registered(_config({"a": _echo}, {"a": _other}))


def test_non_callables_non_string_names_and_non_tables_are_skipped() -> None:
    """Only a string name bound to a callable, in a dict, is an implementation."""
    table: dict[object, object] = {"a": 3, 1: _echo, "b": _other}
    assert adapters.registered(_config(None, "text", table)) == {"b": _other}


def test_a_fill_runs_the_adapter_on_the_fixture_and_operands_and_keeps_the_case() -> None:
    """The result is the adapter's output on (fixture, operands); every other field is kept."""
    filled = adapters.fill(ROOT_CASE, "a", {"a": _echo})
    assert filled == {**ROOT_CASE, "result": ("F", "O")}


def test_an_unknown_implementation_names_the_offered_ones_sorted() -> None:
    """The refusal lists what is offered, in name order."""
    with pytest.raises(SpecDataError, match=r"offered: alpha, zeta"):
        adapters.fill(ROOT_CASE, "nope", {"zeta": _echo, "alpha": _other})


def test_a_case_with_no_fixture_cannot_be_filled() -> None:
    """There is nothing to run the implementation on."""
    with pytest.raises(SpecDataError, match="no `fixture`"):
        adapters.fill({"case": "c"}, "a", {"a": _echo})


# --- outcome axes ------------------------------------------------------------------------------


def test_a_case_both_denied_and_withheld_is_denied() -> None:
    """The deny is the finding, so it wins over the withheld half."""
    both = Verdict(deny=("R1: no",), withheld=("W1: unknown",))
    assert outcomes.verdict_kind(both) == outcomes.DENIED
    assert outcomes.verdict_kind(Verdict(withheld=("W1: unknown",))) == outcomes.WITHHELD
    assert outcomes.verdict_kind(Verdict()) == outcomes.ADMITTED


def test_an_unevaluated_case_against_an_expect_reads_met() -> None:
    """The verdict axis already sends it to unmeasured; the expect axis says only that it stood."""
    declared = Expect(deny=frozenset({"R1"}))
    assert outcomes.expect_kind(None, declared) == outcomes.MET
    assert outcomes.expect_kind(None, None) == outcomes.NO_EXPECT


def test_a_disposition_names_its_kind_and_none_is_undisposed() -> None:
    """The disposition axis reads the declared kind, or `none`."""
    assert outcomes.disposition_kind(None) == outcomes.UNDISPOSED
    assert outcomes.disposition_kind(Disposition(DO_NOT_PORT, "why")) == DO_NOT_PORT
