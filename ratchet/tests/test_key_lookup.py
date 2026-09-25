# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `keys.spec_for` and `keys.kind_of`: the two reads a retiring peer module adds.

⚑ THESE ARE LIBRARY READS, NOT GATE VERDICTS. `test_keys` drives only the gate's public seams
because its defects are verdicts; these two feed a peer's own partitions and reach no verdict here,
so they are witnessed directly.

⚑⚑ THE UNDECLARED GATE IS THE LOAD-BEARING ARM: it must read None, never a default schema, because
six of ten of the peer's baselines had no declaration.
"""

from __future__ import annotations

import pytest

from mikemol.ratchet import keys


def test_a_gate_filename_resolves_to_its_declared_schema() -> None:
    """`check_ban_ratchet.py` names the ban schema, which `schema_named` then serves."""
    name = keys.spec_for("scripts/check_ban_ratchet.py")
    assert name == "substrate:ban"
    assert keys.schema_named(name)("a.py::rule::kind").identity == ("rule", "kind")


def test_an_undeclared_gate_is_none_never_a_default() -> None:
    """A gate no schema declares reads None: THE LOAD-BEARING ARM."""
    assert keys.spec_for("check_something_new_ratchet.py") is None


def test_a_hyphenated_schema_matches_its_underscored_filename() -> None:
    """`carrier-locality` is found in `check_carrier_locality.py`."""
    assert keys.spec_for("check_carrier_locality.py") == "substrate:carrier-locality"


def test_a_filename_naming_two_schemas_is_refused() -> None:
    """A filename carrying two gate names is refused, not resolved by table order."""
    with pytest.raises(keys.UnknownSchemaError, match="several gate schemas"):
        keys.spec_for("check_ban_claims_ratchet.py")


def test_a_triple_has_a_kind_and_a_pair_does_not() -> None:
    """A path-first triple's trailing field is its kind; a pair's lone field is not a kind."""
    triple = keys.schema_named("substrate:ban")("a.py::no-print::debug")
    pair = keys.schema_named("substrate:public")("a.py::name")
    assert keys.kind_of(triple) == "debug"
    assert keys.kind_of(pair) is None


def test_a_reversed_pair_and_a_ruff_key_have_no_kind() -> None:
    """The reversed `discharge` pair, which the retiring module would mis-read, has no kind."""
    discharge = keys.schema_named("substrate:discharge")("name::a.py")
    assert discharge.path == "a.py"
    assert keys.kind_of(discharge) is None
    assert keys.kind_of(keys.schema_named(keys.RUFF)("a.py:E501")) is None
