# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the repin core, over pyproject text in the shapes the fleet really uses. W957.

⚑ THE REWRITE OF EVERY PIN IS THE POSITIVE CONTROL for the selection and the refusals: a rewrite
that touched nothing would pass "the vendored wheel is left alone" and "other dists are kept".
"""

from __future__ import annotations

import pytest

from mikemol.hooks import repin

_OLD = "03749d56d55741840da13d86533e7e8d698e3be8"
_NEW = "6868dd2e0b7f4a9c1d2e3f405162738495a6b7c8"
_REPO = "https://github.com/mikemol/mtools.git"
_PYPROJECT = (
    "dependencies = [\n"
    f'    "mikemol-pathsforward @ git+{_REPO}@{_OLD}#subdirectory=pathsforward",\n'
    f'    "mikemol-hooks @ git+{_REPO}@{_OLD}#subdirectory=hooks",\n'
    "]\n\n[tool.uv.sources]\n"
    f'mikemol-buildtel = {{ git = "{_REPO}", subdirectory = "buildtel", rev = "{_OLD}" }}\n'
    'mikemol-ledger = { path = "vendor/wheels/mikemol_ledger-0.1.0+gc3ca6d2-py3-none-any.whl" }\n'
)
_THREE = 3


def test_the_three_shapes_are_found_in_file_order() -> None:
    """The control: PEP 508, uv source and vendored wheel, each with dist, sha and form."""
    assert repin.find(_PYPROJECT) == (
        repin.Pin("pathsforward", _OLD, repin.PEP508),
        repin.Pin("hooks", _OLD, repin.PEP508),
        repin.Pin("buildtel", _OLD, repin.SOURCE),
        repin.Pin("ledger", "c3ca6d2", repin.WHEEL),
    )


def test_rewriting_all_moves_every_git_pin_and_leaves_the_wheel() -> None:
    """Three git pins change; the vendored wheel's name is untouched."""
    text, changed = repin.rewrite(_PYPROJECT, _NEW)
    assert sorted(changed) == ["buildtel", "hooks", "pathsforward"]
    assert text.count(_NEW) == _THREE
    assert _OLD not in text
    assert "gc3ca6d2" in text


def test_rewriting_selected_dists_keeps_the_others() -> None:
    """Only the named dist moves."""
    text, changed = repin.rewrite(_PYPROJECT, _NEW, frozenset({"hooks"}))
    assert changed == ("hooks",)
    assert text.count(_NEW) == 1
    assert text.count(_OLD) == _THREE - 1


def test_a_pin_already_at_the_target_is_not_reported_changed() -> None:
    """A second run changes nothing and says so."""
    once, _ = repin.rewrite(_PYPROJECT, _NEW)
    again, changed = repin.rewrite(once, _NEW)
    assert changed == ()
    assert again == once


@pytest.mark.parametrize("bad", ["", "main", _NEW[:7], _NEW.upper(), _NEW + "0"])
def test_a_target_that_is_not_a_full_commit_is_refused(bad: str) -> None:
    """A branch, a short sha or an uppercase one would write a pin that does not pin."""
    with pytest.raises(ValueError, match="40-character"):
        repin.rewrite(_PYPROJECT, bad)


def test_same_compares_an_abbreviated_pin_by_prefix() -> None:
    """`c3ca6d2` names the commit it abbreviates and no other."""
    assert repin.same("6868dd2", _NEW)
    assert repin.same(_NEW, _NEW)
    assert not repin.same(_OLD, _NEW)
    assert not repin.same("6868dd3", _NEW)


def test_text_without_pins_finds_none_and_is_unchanged() -> None:
    """A pyproject that does not use mtools is not touched."""
    text = '[project]\nname = "x"\ndependencies = ["requests"]\n'
    assert repin.find(text) == ()
    assert repin.rewrite(text, _NEW) == (text, ())
