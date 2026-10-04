# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""A prime per distinct referent; the product is the fingerprint, the remainder is the finding.

Ported from substrate's `scratch/_pycodemod_fingerprint.py` (W607), the census-free algebra only:
registry, decode and gcd lattice. The referent extractor, the Census arithmetic and the site walk
are later units.

⚑⚑ THE ALGEBRA IS LIFTED FROM GABION'S `type_fingerprints` AND NOT IMPORTED FROM IT. Gabion's
`PrimeRegistry` carries atom ids, bit positions, assignment observers and ambient deadline
machinery, and installing it drags seven runtime dependencies into a stdlib-only tool. What is
kept is `get_or_assign` with non-empty as the only validation, the `while` decode loop, and
`strict=False` as the default.

⚑ THE COPY DIVERGES ON PURPOSE (census-kit rule B4: record, never quotient). Primes are assigned
in FREQUENCY ORDER here (the caller feeds `get_or_assign` its keys by descending corpus count,
ties by key), where gabion assigns in alpha order; there is no exponent sidecar, because
fingerprints are squarefree; the four-name seeded basis is dropped. The two are not claimed
equivalent.

⚑ NON-EMPTY IS THE ONLY VALIDATION: any further rule about what a key may look like would be a
taxonomy. Assigning a prime asserts only that a referent is distinct and countable.

⚑ THE REMAINDER IS EXACT AND MONOTONE: understood primes times the remainder recover the
fingerprint, and growing the modelled set can only remove factors from a remainder, so the new
remainder divides the old one. Seeds are an argument of the caller (`reverse_index(only=...)`),
never a constant here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

_FIRST_PRIME = 2


def _is_prime(value: int) -> bool:
    """Return whether `value` is prime, by trial division to its square root.

    Returns:
        the verdict.

    """
    if value < _FIRST_PRIME:
        return False
    return all(value % d for d in range(_FIRST_PRIME, math.isqrt(value) + 1))


def _next_prime(start: int) -> int:
    """Return the smallest prime at or above `start`.

    Returns:
        that prime.

    """
    candidate = max(start, _FIRST_PRIME)
    while not _is_prime(candidate):
        candidate += 1
    return candidate


@dataclass
class PrimeRegistry:
    """Map key to prime, assigned as keys first arrive; an empty key is the only refusal."""

    primes: dict[str, int] = field(default_factory=dict)
    next_candidate: int = _FIRST_PRIME

    def get_or_assign(self, key: str) -> int:
        """Return the key's prime, assigning the next unused one when the key is new.

        Returns:
            the key's prime.

        Raises:
            ValueError: the key is empty.

        """
        if not key:
            message = "referent key must be non-empty"
            raise ValueError(message)
        existing = self.primes.get(key)
        if existing is not None:
            return existing
        assigned = _next_prime(self.next_candidate)
        self.primes[key] = assigned
        self.next_candidate = assigned + 1
        return assigned

    def prime_for(self, key: str) -> int | None:
        """Return the key's prime, or None when it was never assigned.

        Returns:
            the prime or None.

        """
        return self.primes.get(key)


def fingerprint(keys: Iterable[str], registry: PrimeRegistry) -> int:
    """Return the product over the DISTINCT keys, squarefree by construction.

    Returns:
        the fingerprint.

    """
    product = 1
    for key in sorted(set(keys)):
        product *= registry.get_or_assign(key)
    return product


def reverse_index(
    registry: PrimeRegistry, only: Collection[str] | None = None
) -> list[tuple[int, str]]:
    """Return `(prime, key)` ascending by prime, restricted to `only` when given.

    That restricted index IS the primes understood; decoding against it is the whole decode.

    Returns:
        the decode order.

    """
    items = [(prime, key) for key, prime in registry.primes.items() if only is None or key in only]
    return sorted(items)


def decode_with_remainder(fp: int, rev: Iterable[tuple[int, str]]) -> tuple[list[str], int]:
    """Return `(keys_understood, integer_not)`, exact: understood primes times it give `fp`.

    ⚑ THE `while` RATHER THAN AN `if` KEEPS THE DECODER CORRECT FOR A MULTISET FINGERPRINT.

    Returns:
        the understood keys and the remainder.

    """
    remaining = fp
    keys: list[str] = []
    if remaining <= 1:
        return keys, remaining
    for prime, key in rev:
        while remaining % prime == 0:
            keys.append(key)
            remaining //= prime
        if remaining == 1:
            break
    return keys, remaining


def decode(fp: int, rev: Iterable[tuple[int, str]], *, strict: bool = False) -> list[str]:
    """Return the understood keys; an unknown remainder is swallowed unless `strict`.

    Returns:
        the understood keys.

    Raises:
        ValueError: `strict` and the fingerprint carries primes outside `rev`.

    """
    keys, remainder = decode_with_remainder(fp, rev)
    if strict and remainder not in {0, 1}:
        message = f"fingerprint {fp} carries primes outside the registry"
        raise ValueError(message)
    return keys


def fp_shared(a: int, b: int) -> int:
    """Return the shared structure of two fingerprints: their gcd.

    Returns:
        the gcd.

    """
    return math.gcd(a, b)


def fp_contains(container: int, part: int) -> bool:
    """Return whether `part` is inside `container`: one modulo.

    Returns:
        the verdict.

    """
    return part != 0 and container % part == 0


def fp_difference(a: int, b: int) -> int:
    """Return what is not shared: each side with the shared part divided out, multiplied.

    Returns:
        the structural difference.

    """
    shared = math.gcd(a, b)
    return (a // shared) * (b // shared)


def omega_against(n: int, primes: Iterable[int]) -> int:
    """Return how many of `primes` divide `n`, with multiplicity.

    Returns:
        the count.

    """
    count, remaining = 0, n
    for prime in primes:
        while remaining % prime == 0:
            count += 1
            remaining //= prime
        if remaining == 1:
            break
    return count
