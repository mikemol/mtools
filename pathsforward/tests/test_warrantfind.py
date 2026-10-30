# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A card's evidence text yields the transcript citations a reader can check, and only those."""

from mikemol.pathsforward import warrantfind
from mikemol.pathsforward.warrantfind import Cite

_UUID = "53079d0f-ccac-4e25-b783-9f7b8912463c"
_OTHER = "0afcd13c-bc08-4eaf-bac5-6a29304b0faa"
_LINE = 109815
_LINE_TWO = 106208


def test_a_host_line_with_its_uuid_is_one_citation_carrying_all_three() -> None:
    """W1977's shape: 'host 695f3e0a line 109815, uuid <uuid>'."""
    text = f"Operator, host 695f3e0a line {_LINE}, uuid {_UUID}: a ruling"
    assert warrantfind.cites(text) == [Cite("695f3e0a", _UUID, _LINE)]


def test_two_citations_each_take_the_uuid_that_follows_them_and_not_the_next_ones() -> None:
    """The window of a citation ends where the next begins, so the uuids are not swapped."""
    text = (
        f"host 695f3e0a line {_LINE}, uuid {_UUID}; host 695f3e0a line {_LINE_TWO}, uuid {_OTHER}"
    )
    assert warrantfind.cites(text) == [
        Cite("695f3e0a", _UUID, _LINE),
        Cite("695f3e0a", _OTHER, _LINE_TWO),
    ]


def test_a_line_without_a_uuid_is_kept_and_a_bare_uuid_stands_alone() -> None:
    """Either can be checked, one by line and one by uuid; neither is dropped."""
    assert warrantfind.cites(f"host 695f3e0a line {_LINE}") == [Cite("695f3e0a", "", _LINE)]
    assert warrantfind.cites(f"the record {_UUID} said so") == [Cite("", _UUID, None)]
    stolen = f"host 695f3e0a line {_LINE}; host 695f3e0a line {_LINE_TWO}, uuid {_OTHER}"
    assert warrantfind.cites(stolen) == [
        Cite("695f3e0a", "", _LINE),
        Cite("695f3e0a", _OTHER, _LINE_TWO),
    ]


def test_a_card_that_cites_only_dates_is_unresolved_and_has_no_citation() -> None:
    """The measured majority: dates are not checkable. A text with no date claims nothing."""
    dated = "2026-10-26 the operator said to do it; also 2026-10-27"
    assert warrantfind.cites(dated) == []
    assert warrantfind.unresolved(dated)
    stamped = "2026-10-26T18:30:05Z: the operator said to do it (the writer's own stamp)"
    assert warrantfind.unresolved(stamped)
    assert not warrantfind.unresolved("no date and no citation at all")
    assert not warrantfind.unresolved(f"2026-10-26 host 695f3e0a line {_LINE}")
