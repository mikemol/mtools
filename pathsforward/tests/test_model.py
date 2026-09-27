# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the model: a malformed document is refused, a malformed symbol never crashes."""

from __future__ import annotations

import pytest

from mikemol.pathsforward.model import (
    MalformedStateError,
    State,
    describe_rank,
    foreign_symbol,
    is_reference,
    leverage,
    ordered,
    strlist,
    symbol_number,
    text,
    ticks,
    validate,
    weight,
    workable,
)

_SEVEN = 7
_THREE = 3
_FIFTY_FIVE = 55
_THREE_LEVERAGE = 3


def test_a_witnessed_ready_item_never_tops_the_queue() -> None:
    """A witnessed ready item sorts with blocked, below an unwitnessed ready one (W133)."""
    heavy: dict[str, object] = {"symbol": "W1", "status": "ready", "witness": "q", "weight": 9}
    plain: dict[str, object] = {"symbol": "W2", "status": "ready"}
    stuck: dict[str, object] = {"symbol": "W3", "status": "blocked"}
    order = [text(w, "symbol") for w in ordered([heavy, stuck, plain])]
    assert (order, workable(heavy), workable(plain)) == (["W2", "W1", "W3"], False, True)


def test_leverage_counts_enables_plus_in_degree_of_blocked_on() -> None:
    """A waypoint's leverage is its own `enables` count plus who names it in `blocked_on`."""
    w1: dict[str, object] = {"symbol": "W1", "blocked_on": ["W2"]}
    w2: dict[str, object] = {"symbol": "W2", "enables": ["nemik:W20"]}
    w3: dict[str, object] = {"symbol": "W3", "blocked_on": ["W2"]}
    waypoints = [w1, w2, w3]
    assert leverage(w2, waypoints) == _THREE_LEVERAGE


def test_leverage_is_zero_with_no_enables_or_blockers() -> None:
    """A waypoint nobody names and that names nothing itself scores zero."""
    w1: dict[str, object] = {"symbol": "W1"}
    assert leverage(w1, [w1]) == 0


def test_describe_rank_names_unblocks_and_enables() -> None:
    """A waypoint that unblocks another and enables a third names both, never overwriting."""
    w1: dict[str, object] = {"symbol": "W1", "blocked_on": ["W2"]}
    w2: dict[str, object] = {"symbol": "W2", "enables": ["nemik:W20"]}
    waypoints = [w1, w2]
    assert describe_rank(w2, waypoints) == "unblocks W1; enables nemik:W20"


def test_describe_rank_is_sweep_with_no_edges() -> None:
    """A waypoint with no `enables` and no one blocked on it reads as a sweep item."""
    w1: dict[str, object] = {"symbol": "W1"}
    reason = describe_rank(w1, [w1])
    assert reason == "sweep: enables nothing, unblocks nothing"


def test_ordered_ranks_higher_leverage_first_within_a_bucket() -> None:
    """Within one status bucket, the waypoint with more leverage sorts first, not file order."""
    low: dict[str, object] = {"symbol": "W1", "status": "ready"}
    high: dict[str, object] = {"symbol": "W2", "status": "ready", "enables": ["W3"]}
    assert [text(w, "symbol") for w in ordered([low, high])] == ["W2", "W1"]


def test_ordered_preserves_file_order_when_leverage_ties() -> None:
    """Zero-leverage waypoints in the same bucket keep their file order (stable sort)."""
    a: dict[str, object] = {"symbol": "W1", "status": "ready"}
    b: dict[str, object] = {"symbol": "W2", "status": "ready"}
    assert [text(w, "symbol") for w in ordered([a, b])] == ["W1", "W2"]


def test_a_foreign_symbol_parses_to_its_repo_and_number() -> None:
    """⚑⚑ `luthen-observability:W55` is another repo's W55, and never a local symbol."""
    sym = "luthen-observability:W55"
    assert (foreign_symbol(sym), symbol_number(sym), is_reference(sym)) == (
        ("luthen-observability", _FIFTY_FIVE),
        None,
        True,
    )


@pytest.mark.parametrize("bad", [":W5", "repo:", "repo:X5", "repo:W0", "a b:W5", "W5", 7, None])
def test_a_malformed_foreign_symbol_parses_to_none(bad: object) -> None:
    """An empty repo, a bad or zero number, a space, a plain local symbol or a non-string: None."""
    assert foreign_symbol(bad) is None


def _doc(**over: object) -> dict[str, object]:
    """Build a minimal valid document, with overrides.

    Returns:
        the document.

    """
    doc: dict[str, object] = {"counter": 1, "waypoints": [{"symbol": "W1"}], "residue": []}
    doc.update(over)
    return doc


def test_a_symbol_parses_to_its_number() -> None:
    """`W7` parses to 7."""
    assert symbol_number("W7") == _SEVEN


@pytest.mark.parametrize("bad", ["Wx", "W0", "W07", "w7", "W", "W7b", 7, None])
def test_a_malformed_symbol_parses_to_none(bad: object) -> None:
    """A malformed symbol parses to None rather than raising (gabion crashed on `Wx`)."""
    assert symbol_number(bad) is None


def test_validate_accepts_a_minimal_document() -> None:
    """A minimal document validates, and its lists are the document's own."""
    doc = _doc()
    state = validate(doc)
    assert isinstance(state, State)
    state.waypoints.append({"symbol": "W2"})
    assert doc["waypoints"] is state.waypoints


def test_validate_creates_an_absent_residue() -> None:
    """An absent residue is created empty."""
    doc = _doc()
    del doc["residue"]
    assert validate(doc).residue == []


@pytest.mark.parametrize("raw", [[], "x", None])
def test_validate_refuses_a_non_object(raw: object) -> None:
    """A document that is not an object is refused."""
    with pytest.raises(MalformedStateError, match="not a JSON object"):
        validate(raw)


def test_validate_refuses_non_list_waypoints() -> None:
    """A `waypoints` that is not a list is refused (summit's `_waypoints`)."""
    with pytest.raises(MalformedStateError, match="`waypoints` is not a list"):
        validate(_doc(waypoints="not a list"))


def test_validate_refuses_a_non_object_record() -> None:
    """A record that is not an object is refused."""
    with pytest.raises(MalformedStateError, match=r"`residue\[0\]` is not an object"):
        validate(_doc(residue=["W3"]))


def test_validate_refuses_a_record_without_a_string_symbol() -> None:
    """A record whose symbol is not a string is refused."""
    with pytest.raises(MalformedStateError, match="no string `symbol`"):
        validate(_doc(waypoints=[{"symbol": 1}]))


@pytest.mark.parametrize("counter", [True, -1, "3", None])
def test_validate_refuses_a_bad_counter(counter: object) -> None:
    """A counter that is not a non-negative integer is refused; a bool is not an integer here."""
    with pytest.raises(MalformedStateError, match="`counter`"):
        validate(_doc(counter=counter))


def test_text_reads_absent_and_null_as_empty() -> None:
    """An absent or null field reads as the empty string, anything else as its str."""
    assert (text({}, "k"), text({"k": None}, "k"), text({"k": _THREE}, "k")) == ("", "", "3")


def test_strlist_reads_a_bare_string_as_one_element() -> None:
    """A bare string is one element, never an iterable of characters."""
    assert strlist({"on": "mikemol"}, "on") == ["mikemol"]


def test_strlist_reads_a_list_and_an_absence() -> None:
    """A list reads as its elements' strings, and an absence as []."""
    assert (strlist({"on": ["a", _THREE]}, "on"), strlist({}, "on")) == (["a", "3"], [])


def test_ticks_reads_only_an_integer() -> None:
    """ticks_blocked reads an int, and a bool or an absence as 0."""
    got = (ticks({"ticks_blocked": _THREE}), ticks({"ticks_blocked": True}), ticks({}))
    assert got == (_THREE, 0, 0)


def test_ordered_puts_a_heavier_weight_above_higher_leverage() -> None:
    """A stored weight outranks leverage inside a bucket: it is the judgment the graph lacks."""
    lever: dict[str, object] = {"symbol": "W1", "status": "ready", "enables": ["W3", "W4"]}
    heavy: dict[str, object] = {"symbol": "W2", "status": "ready", "weight": 1}
    assert [text(w, "symbol") for w in ordered([lever, heavy])] == ["W2", "W1"]


def test_a_weight_never_lifts_an_item_out_of_its_status_bucket() -> None:
    """A heavy blocked waypoint still sorts below a ready one: weight cannot make it workable."""
    ready: dict[str, object] = {"symbol": "W1", "status": "ready"}
    heavy: dict[str, object] = {"symbol": "W2", "status": "blocked", "weight": 99}
    assert [text(w, "symbol") for w in ordered([heavy, ready])] == ["W1", "W2"]


def test_an_unweighted_queue_keeps_its_order() -> None:
    """No weight anywhere reads as all zero: an unweighted repo's order is byte-for-byte today's."""
    waypoints: list[dict[str, object]] = [
        {"symbol": "W1", "status": "ready"},
        {"symbol": "W2", "status": "ready", "enables": ["W1"]},
        {"symbol": "W3", "status": "blocked"},
    ]
    zeroed = [{**w, "weight": 0} for w in waypoints]
    assert [text(w, "symbol") for w in ordered(waypoints)] == ["W2", "W1", "W3"]
    assert [text(w, "symbol") for w in ordered(zeroed)] == ["W2", "W1", "W3"]


@pytest.mark.parametrize("bad", ["3", 1.5, True, None])
def test_a_malformed_weight_sorts_as_zero(bad: object) -> None:
    """A string, float, bool or null weight reads as 0: check reports it, the sort never crashes."""
    assert weight({"symbol": "W1", "weight": bad}) == 0
