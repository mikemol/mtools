# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the prime-fingerprint algebra: exact decode, lax default, gcd lattice, monotone."""

from __future__ import annotations

import math

import pytest

from mikemol.pycodemod import fingerprint as fp

_FIRST_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
_PAIR = 2
_FOUR = ["core_id", "relpath", "wobble", "flange"]


def _registry_of(*keys: str) -> fp.PrimeRegistry:
    registry = fp.PrimeRegistry()
    for key in keys:
        registry.get_or_assign(key)
    return registry


def test_registry_accepts_any_nonempty_key_and_assigns_ascending_primes() -> None:
    """Any non-empty spelling gets the next prime, skipping composites."""
    registry = fp.PrimeRegistry()
    keys = ["if", "3", "ζ", "core_id", "x" * 64, "a", "b", "c", "d", "e"]
    assert [registry.get_or_assign(k) for k in keys] == _FIRST_PRIMES


def test_registry_is_idempotent_and_reports_the_prime_for_a_key() -> None:
    """A repeated key keeps its prime; an unassigned key has none."""
    registry = _registry_of("a", "b")
    assert registry.get_or_assign("b") == registry.prime_for("b")
    assert registry.prime_for("never") is None


def test_registry_refuses_an_empty_key_and_nothing_else() -> None:
    """The one validation is non-empty."""
    with pytest.raises(ValueError, match="non-empty"):
        fp.PrimeRegistry().get_or_assign("")


def test_registry_resumes_from_a_negative_candidate_at_the_first_prime() -> None:
    """A candidate below 2 is clamped, never read as prime."""
    registry = fp.PrimeRegistry(next_candidate=-5)
    assert registry.get_or_assign("a") == _FIRST_PRIMES[0]


def test_distinct_keys_get_distinct_primes() -> None:
    """Six keys, six primes."""
    registry = fp.PrimeRegistry()
    assert len({registry.get_or_assign(k) for k in "abcdef"}) == len("abcdef")


def test_fingerprint_is_squarefree_a_repeat_adds_no_factor() -> None:
    """The product runs over the distinct set."""
    registry = fp.PrimeRegistry()
    assert fp.fingerprint(["a", "b", "a", "a"], registry) == fp.fingerprint(["a", "b"], registry)


def test_decode_is_exact_understood_times_remainder_is_the_fingerprint() -> None:
    """Multiplying the understood primes back by the remainder recovers the fingerprint."""
    registry = fp.PrimeRegistry()
    fingerprint = fp.fingerprint(_FOUR, registry)
    keys, remainder = fp.decode_with_remainder(
        fingerprint, fp.reverse_index(registry, only={"core_id", "relpath"})
    )
    product = math.prod(registry.get_or_assign(k) for k in keys)
    assert product * remainder == fingerprint


def test_decode_returns_the_understood_keys_and_the_unmodelled_product() -> None:
    """The keys are the modelled ones; the remainder is the rest multiplied."""
    registry = fp.PrimeRegistry()
    fingerprint = fp.fingerprint(_FOUR, registry)
    keys, remainder = fp.decode_with_remainder(
        fingerprint, fp.reverse_index(registry, only={"core_id", "relpath"})
    )
    assert sorted(keys) == ["core_id", "relpath"]
    assert remainder == registry.get_or_assign("wobble") * registry.get_or_assign("flange")


def test_decode_of_one_is_nothing_understood_and_remainder_one() -> None:
    """The empty product decodes to no keys."""
    registry = _registry_of("a")
    assert fp.decode_with_remainder(1, fp.reverse_index(registry)) == ([], 1)


def test_decode_default_is_lax_and_swallows_the_remainder() -> None:
    """The default returns keys rather than raising on an unknown remainder."""
    registry = fp.PrimeRegistry()
    fingerprint = fp.fingerprint(_FOUR, registry)
    rev = fp.reverse_index(registry, only={"core_id", "relpath"})
    assert sorted(fp.decode(fingerprint, rev)) == ["core_id", "relpath"]


def test_decode_strict_raises_on_an_unknown_remainder() -> None:
    """The rigid mode is one keyword away."""
    registry = fp.PrimeRegistry()
    fingerprint = fp.fingerprint(_FOUR, registry)
    rev = fp.reverse_index(registry, only={"core_id"})
    with pytest.raises(ValueError, match="outside the registry"):
        fp.decode(fingerprint, rev, strict=True)


def test_decode_strict_with_a_complete_registry_does_not_raise() -> None:
    """Strict raises only when something is left over."""
    registry = fp.PrimeRegistry()
    fingerprint = fp.fingerprint(_FOUR, registry)
    keys = fp.decode(fingerprint, fp.reverse_index(registry), strict=True)
    assert sorted(keys) == sorted(_FOUR)


def test_gcd_is_the_shared_referent_product() -> None:
    """The gcd of two fingerprints is the product of what they share."""
    registry = fp.PrimeRegistry()
    a = fp.fingerprint(["p", "q", "r"], registry)
    b = fp.fingerprint(["q", "r", "s"], registry)
    assert fp.fp_shared(a, b) == fp.fingerprint(["q", "r"], registry)


def test_containment_is_one_modulo_subset_and_non_subset() -> None:
    """A subset divides; a non-subset and zero do not."""
    registry = fp.PrimeRegistry()
    a = fp.fingerprint(["p", "q", "r"], registry)
    assert fp.fp_contains(a, fp.fingerprint(["p", "q"], registry))
    assert not fp.fp_contains(a, fp.fingerprint(["p", "s"], registry))
    assert not fp.fp_contains(a, 0)


def test_difference_drops_the_shared_part() -> None:
    """What remains is each side's own referents."""
    registry = fp.PrimeRegistry()
    a = fp.fingerprint(["p", "q", "r"], registry)
    b = fp.fingerprint(["q", "r", "s"], registry)
    assert fp.fp_difference(a, b) == fp.fingerprint(["p", "s"], registry)


def test_a_larger_modelled_set_gives_a_remainder_that_divides_and_never_rises() -> None:
    """Growing the modelled set removes factors: divisibility, value and omega all hold."""
    registry = fp.PrimeRegistry()
    fingerprint = fp.fingerprint(["aa", "bb", "cc", "dd"], registry)
    primes = sorted(registry.primes.values())
    _, small = fp.decode_with_remainder(fingerprint, fp.reverse_index(registry, only={"aa"}))
    _, big = fp.decode_with_remainder(
        fingerprint, fp.reverse_index(registry, only={"aa", "bb", "cc"})
    )
    assert small % big == 0
    assert big <= small
    assert fp.omega_against(big, primes) <= fp.omega_against(small, primes)


def test_an_empty_modelled_set_leaves_the_whole_fingerprint() -> None:
    """Nothing understood means everything remains."""
    registry = fp.PrimeRegistry()
    fingerprint = fp.fingerprint(["aa", "bb"], registry)
    _, remainder = fp.decode_with_remainder(fingerprint, fp.reverse_index(registry, only=set()))
    assert remainder == fingerprint


def test_sites_sharing_two_referents_have_gcd_omega_two_and_a_third_is_outside() -> None:
    """The class gcd counts two referents and excludes a site sharing none."""
    registry = fp.PrimeRegistry()
    first = fp.fingerprint(["u", "v", "w"], registry)
    second = fp.fingerprint(["u", "v", "z"], registry)
    third = fp.fingerprint(["q"], registry)
    shared = fp.fp_shared(first, second)
    assert fp.omega_against(shared, sorted(registry.primes.values())) == _PAIR
    assert not fp.fp_contains(third, shared)
