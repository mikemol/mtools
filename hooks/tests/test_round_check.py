# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A round that skips a ready published card while working an outside one is refused (W1942)."""

from __future__ import annotations

import json

from mikemol.hooks import round_check


def _row(repo: str, symbol: str, rank: str) -> str:
    row: dict[str, str] = {
        "repo": repo,
        "symbol": symbol,
        "rank": rank,
        "size": "2",
        "salience": "1",
        "n_source": "x",
    }
    return json.dumps(row)


_FILE = (
    '{"as_of": "2026-10-25T03:00:00Z", "rows": [\n'
    + _row("mtools", "W9", "2")
    + ",\n"
    + _row("nemik", "W5", "1")
    + ",\n"
    + _row("mtools", "W7", "1")
    + "\n]}\n"
)
_ROUND = ["W7", "W9"]


def test_a_repositorys_round_is_read_by_lines_in_rank_order() -> None:
    """Only this repository's rows, best rank first; the stamp and closing lines are not rows."""
    assert round_check.round_symbols(_FILE, "mtools") == _ROUND
    assert round_check.round_symbols(_FILE, "nemik") == ["W5"]
    assert round_check.round_symbols("", "mtools") == []
    assert round_check.round_symbols("not a round\n{bad\n", "mtools") == []


def test_the_one_line_document_luthens_egress_gate_writes_and_the_lines_form_read_alike() -> None:
    """A filtered file is rewritten as ONE line; nemik's writer is a head and row lines."""
    rows = [_row("mtools", "W9", "2"), _row("mtools", "W7", "1"), _row("nemik", "W5", "1")]
    one_line = f'{{"as_of": "2026-10-25T08:00:00Z", "rows": [{",".join(rows)}]}}'
    assert "\n" not in one_line
    assert round_check.round_symbols(one_line, "mtools") == _ROUND
    assert round_check.round_symbols(one_line, "nemik") == ["W5"]
    head = '{"as_of": "2026-10-25T08:00:00Z"}\n'
    lines = head + rows[0] + "\n" + rows[1] + "\n"
    assert round_check.round_symbols(lines, "mtools") == _ROUND


def test_a_fresh_card_worked_while_an_aged_round_card_is_passed_over_is_refused() -> None:
    """The depth-first pattern: W20 is worked, ready round cards W7 and W9 are skipped."""
    refused = round_check.composition(_ROUND, ready={"W7", "W9", "W20"}, working={"W20"})
    assert len(refused) == len(_ROUND)
    assert "W7 is in this repository's round and ready" in refused[0]
    assert "W20, which is not" in refused[0]
    assert "--update W7 --status working" in refused[0]


def test_the_round_worked_in_full_or_wholly_inside_is_admitted() -> None:
    """No card outside the round, or the whole ready round in the set: nothing is refused."""
    assert round_check.composition(_ROUND, {"W7", "W9"}, {"W7"}) == []
    assert round_check.composition(_ROUND, {"W7", "W9", "W20"}, {"W7", "W9", "W20"}) == []


def test_a_round_card_no_longer_ready_is_not_skipped_and_no_round_refuses_nothing() -> None:
    """A round card blocked or done since publication does not count; an empty round is silent."""
    assert round_check.composition(_ROUND, ready={"W9"}, working={"W9", "W20"}) == []
    assert round_check.composition([], ready={"W7"}, working={"W20"}) == []
