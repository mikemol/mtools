# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The waypoint vector grammar: a CVSS-shaped string, checked here and scored elsewhere (W248).

⚑ OWN PREFIX, NOT CVSS 4.0 (luthen W190/W218, nemik W107, 2026-09-28). CVSS base metrics describe
an attacker's preconditions and have no value for tenant, cluster or host reach; a CVSS calculator
fed a waypoint would print a precise score that measures nothing. `WV:` is what no such tool reads.

⚑ THE WRITER VALIDATES, THE RANKER SCORES. nemik owns bands, ordering guarantees and the default
for an unscored waypoint; this module holds no weights. An unscored waypoint has NO vector, never a
zero, so a census can count them.

⚑ EVERY METRIC IS REQUIRED. A vector missing one would leave the ranker to fill it in, which is
the silent default luthen's letter rules out.
"""

from __future__ import annotations

from mikemol.pathsforward.model import RefusedError

VERSION = "WV:1"

# Fixed order (luthen W218): reach, egress, C/I/A impact, precondition, scope, fix known, witness.
# Egress is its own metric because a tenant-reach item can egress and a host-reach one may not.
METRICS: tuple[tuple[str, frozenset[str]], ...] = (
    ("R", frozenset("LTCH")),
    ("E", frozenset("YN")),
    ("C", frozenset("NLH")),
    ("I", frozenset("NLH")),
    ("A", frozenset("NLH")),
    ("X", frozenset("NP")),
    ("S", frozenset("UC")),
    ("F", frozenset("KU")),
    ("W", frozenset("YN")),
)

SOURCES = frozenset({"default", "signal", "agent"})


def parse(vector: str) -> dict[str, str]:
    """Read a vector into its metric values, refusing anything outside the grammar.

    Returns:
        metric name to value, in the grammar's order.

    Raises:
        RefusedError: naming the first part that is out of place, unknown or missing.

    """
    parts = vector.split("/")
    if parts[0] != VERSION:
        msg = f"vector must start with {VERSION}, got {parts[0]!r}"
        raise RefusedError(msg)
    body = parts[1:]
    if len(body) != len(METRICS):
        names = ",".join(name for name, _ in METRICS)
        msg = f"vector has {len(body)} metrics; {VERSION} needs all of {names}, in that order"
        raise RefusedError(msg)
    values: dict[str, str] = {}
    for part, (name, allowed) in zip(body, METRICS, strict=True):
        key, sep, value = part.partition(":")
        if key != name or not sep:
            msg = f"vector metric {part!r} is out of place; expected {name}:<value>"
            raise RefusedError(msg)
        if value not in allowed:
            msg = f"vector metric {name} has {value!r}; allowed: {'|'.join(sorted(allowed))}"
            raise RefusedError(msg)
        values[name] = value
    return values


def refuse_source(source: str) -> None:
    """Refuse a vector_source outside default, signal and agent.

    Raises:
        RefusedError: on any other value.

    """
    if source not in SOURCES:
        msg = f"vector_source {source!r} is not one of {'|'.join(sorted(SOURCES))}"
        raise RefusedError(msg)
