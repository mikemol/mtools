# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.ledger.finding_kindspec`: substrate's suite, ported case for case.

⚑⚑⚑ THE MENU IS CASED BECAUSE ITS OMISSION IS MEASURED, NOT HYPOTHETICAL: every kind is NAMED,
`standing` is named WITH its condition, and the ORDER is asserted, not just the membership —
listing `standing` first would pass a presence check while restoring the failure.
"""

from __future__ import annotations

from mikemol.ledger import finding_kindspec


def test_an_unknown_kind_is_refused_with_every_kind_named() -> None:
    """An unknown kind is refused, and the menu names all five kinds."""
    spec, refusal = finding_kindspec.parse("nonsense-kind")
    assert spec is None
    for kind in ("selftest:<command>", "refuses:<command>", "mode:TOOL:FLAG", "unwitnessed"):
        assert kind in refusal
    assert "standing" in refusal


def test_the_falsifiable_kinds_come_before_standing_with_its_condition() -> None:
    """The falsifiable kinds are listed BEFORE `standing`, which carries its condition.

    ⚑⚑ ORDER, NOT JUST MEMBERSHIP: `standing` last, with its condition attached, is what makes
    choosing it a decision rather than the residue of a short list.
    """
    _, refusal = finding_kindspec.parse("nonsense-kind")
    assert refusal.index("selftest:<command>") < refusal.index("  standing")
    assert "LEGITIMATE ONLY" in refusal
    assert "measured FACT" in refusal
    assert "cannot notice a revert" in refusal


def test_both_command_spellings_parse_identically_to_their_builders() -> None:
    """A quoted and a comma-separated command agree; each verb picks its own builder."""
    quoted, _ = finding_kindspec.parse("selftest:python3 -m some.module")
    commas, _ = finding_kindspec.parse("selftest:python3,-m,some.module")
    refusing, _ = finding_kindspec.parse("refuses:python3 tool.py --bad")
    assert quoted is not None
    assert commas is not None
    assert refusing is not None
    assert quoted.cmd == ("python3", "-m", "some.module")
    assert quoted.cmd == commas.cmd
    assert quoted.builder == "_selftest"
    assert refusing.builder == "_refuses"


def test_an_empty_command_is_refused_naming_both_fixes() -> None:
    """An empty command is REFUSED rather than registered bare, naming quoting and commas.

    ⚑ THE MEASURED HAZARD: an unquoted space donates the command to the note, leaving the kind
    bare — which ran a tool with no arguments and exited 2 on its usage.
    """
    spec, refusal = finding_kindspec.parse("selftest:")
    assert spec is None
    assert "QUOTE it" in refusal
    assert "comma-separated" in refusal


def test_a_mode_kind_needs_all_three_parts() -> None:
    """A well-formed mode kind parses; a two-part one and an empty-flag one are refused."""
    good, _ = finding_kindspec.parse("mode:fix_notinscope.py:--summary")
    assert good is not None
    assert (good.tool, good.flag) == ("fix_notinscope.py", "--summary")
    short, why = finding_kindspec.parse("mode:onlytool")
    assert short is None
    assert "mode:TOOL:FLAG" in why
    assert finding_kindspec.parse("mode:tool:")[0] is None


def test_the_bare_kinds_parse_and_probed_is_the_one_rule() -> None:
    """Bare kinds carry no polarity; command kinds do; `mode:` is probed though it has no argv.

    ⚑ `probed` EXISTS SO A CALLER NEVER RE-TESTS THE KIND NAME.
    """
    standing, _ = finding_kindspec.parse("standing")
    unwitnessed, _ = finding_kindspec.parse("unwitnessed")
    probed, _ = finding_kindspec.parse("refuses:python3 tool.py")
    moded, _ = finding_kindspec.parse("mode:tool.py:--flag")
    assert standing is not None
    assert unwitnessed is not None
    assert probed is not None
    assert moded is not None
    assert standing.builder == "_standing"
    assert unwitnessed.builder == "_unwitnessed"
    assert not standing.probed
    assert probed.probed
    assert moded.probed
    assert not moded.cmd


def test_the_key_alphabet_is_a_contract_with_the_resolver() -> None:
    """Slug keys pass; an empty key, a colon and a space are refused, saying why."""
    assert not finding_kindspec.bad_key("gate-G63-the-mode-polarity-arm-is-built")
    assert not finding_kindspec.bad_key("tmi_F6")
    assert finding_kindspec.bad_key("")
    assert finding_kindspec.bad_key("gate:G1")
    assert "resolver" in finding_kindspec.bad_key("gate G1")
