# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the selftest: every arm holds, and the arms are the ones the docstring names."""

from __future__ import annotations

from mikemol.pathsforward import selftest

_ARMS = 7


def test_every_arm_holds() -> None:
    """Every built-in arm holds on this code."""
    assert selftest.run() == (_ARMS, [])


def test_the_hash_arms_are_present() -> None:
    """The two hash arms (summit's) are among the arms, so a pass is not a pass over nothing."""
    labels = [label for label, _ in selftest.arms()]
    assert (
        "a heartbeat change does not move the hash" in labels,
        "a waypoint change moves the hash" in labels,
        len(labels),
    ) == (True, True, _ARMS)
