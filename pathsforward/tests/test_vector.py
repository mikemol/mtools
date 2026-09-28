# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for W248's vector grammar: one control that parses, and a refusal per defect."""

from __future__ import annotations

import pytest

from mikemol.pathsforward import vector
from mikemol.pathsforward.ops import RefusedError

# luthen's example from the W218 letter: host reach, no egress, a scope change, fix known.
_GOOD = "WV:1/R:H/E:N/C:H/I:H/A:N/X:N/S:C/F:K/W:N"


def test_a_complete_vector_parses_in_order() -> None:
    """The W218 example parses to every metric, in the grammar's fixed order."""
    got = vector.parse(_GOOD)
    assert "".join(f"{k}{v}" for k, v in got.items()) == "RHENCHIHANXNSCFKWN"


def test_a_cvss_prefix_is_refused() -> None:
    """A CVSS 4.0 prefix is refused: a waypoint vector must never read as a CVSS score."""
    with pytest.raises(RefusedError, match="must start with WV:1"):
        vector.parse(_GOOD.replace("WV:1", "CVSS:4.0"))


def test_a_missing_metric_is_refused() -> None:
    """A vector without one metric is refused, so the ranker never fills in a silent default."""
    with pytest.raises(RefusedError, match="needs all of"):
        vector.parse(_GOOD.replace("/E:N", ""))


def test_swapped_metrics_are_refused() -> None:
    """Two metrics out of the fixed order are refused, naming the one found out of place."""
    with pytest.raises(RefusedError, match="'E:N' is out of place; expected R"):
        vector.parse(_GOOD.replace("R:H/E:N", "E:N/R:H"))


def test_egress_is_no_longer_a_reach_value() -> None:
    """R:E, reach as egress in the first proposal, is refused since W218 split egress out."""
    with pytest.raises(RefusedError, match="R has 'E'"):
        vector.parse(_GOOD.replace("R:H", "R:E"))


def test_a_metric_without_a_colon_is_refused() -> None:
    """A bare metric name is refused as out of place, not read as an empty value."""
    with pytest.raises(RefusedError, match="out of place"):
        vector.parse(_GOOD.replace("/W:N", "/W"))


@pytest.mark.parametrize("source", ["default", "signal", "agent"])
def test_each_declared_source_is_accepted(source: str) -> None:
    """Each declared vector_source is accepted."""
    vector.refuse_source(source)


def test_an_undeclared_source_is_refused() -> None:
    """A vector_source outside the declared three is refused."""
    with pytest.raises(RefusedError, match="vector_source 'human'"):
        vector.refuse_source("human")
