# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The labelled sample is random sentences plus the regex hits; the two files stay blind (W1966).

⚑ THE FIXTURE: a transcript of one assistant message with five sentences, one a regex hit; plus a
sidechain record, a user record and a sentence quoting a cross-session message, none of which may
enter the population.
"""

import io
import json
from pathlib import Path
from typing import cast

import pytest

from mikemol.transcriptstruct import sample
from mikemol.transcriptstruct.cli import main
from mikemol.transcriptstruct.records import parse_lines

_FIVE = "One. Two. I still need to attach the warrant, W1931. Four. Five."
_POOL = [sample.Sentence(i, f"u{i}", f"text {i}", None) for i in range(20)]
_HIT = sample.Sentence(99, "uh", "I still need to x.", "canonical")
_DRAW = 5
_USAGE = 2


def _object(line: str) -> dict[str, object]:
    return cast("dict[str, object]", json.loads(line))


def _assistant(text: str, *, side: bool = False) -> str:
    message: dict[str, object] = {"role": "assistant", "content": [{"type": "text", "text": text}]}
    envelope: dict[str, object] = {
        "type": "assistant",
        "uuid": "u1",
        "isSidechain": side,
        "message": message,
    }
    return json.dumps(envelope)


def test_the_population_is_the_assistant_sentences_the_extractor_sees() -> None:
    """Five sentences, one a hit; a sidechain, a quoted peer message and a user record are out."""
    user: dict[str, object] = {
        "type": "user",
        "uuid": "u0",
        "message": {"role": "user", "content": "Hello there."},
    }
    lines = [
        _assistant(_FIVE),
        _assistant("Side one.", side=True),
        _assistant("cross-session-message says I still need to."),
        json.dumps(user),
    ]
    found = sample.sentences(parse_lines(lines))
    wanted = ["One.", "Two.", "I still need to attach the warrant, W1931.", "Four.", "Five."]
    assert [s.text for s in found] == wanted
    assert [s.family for s in found] == [None, None, "canonical", None, None]


def test_the_draw_is_reproducible_from_the_seed_and_changes_with_it() -> None:
    """The same seed gives the same sample; another seed gives another."""
    first = sample.draw(_POOL, _DRAW, 1)
    assert first == sample.draw(_POOL, _DRAW, 1)
    assert first != sample.draw(_POOL, _DRAW, 2)
    assert {src for _item, src in first} == {sample.RANDOM}


def test_every_regex_hit_is_in_the_sample_once_and_tagged() -> None:
    """A hit is added whether or not the random draw took it, and never listed twice."""
    pool = [*_POOL, _HIT]
    for seed in range(_DRAW):
        chosen = sample.draw(pool, _DRAW, seed)
        assert [item for item, src in chosen if src == sample.REGEX] == [_HIT]
        assert [item for item, _src in chosen].count(_HIT) == 1


def test_the_blind_rows_carry_no_family_and_no_source() -> None:
    """What goes to the other labeller has the text and the place and nothing of this side's."""
    chosen = [(_HIT, sample.REGEX), (_POOL[0], sample.RANDOM)]
    rows = sample.blind(chosen)
    assert all(set(row) == {"id", "line", "uuid", "text"} for row in rows)
    assert "canonical" not in json.dumps(rows)
    own = sample.key(chosen)
    assert own[0] == {"id": 0, "source": sample.REGEX, "family": "canonical"}
    assert own[1] == {"id": 1, "source": sample.RANDOM, "family": ""}


def test_a_request_larger_than_the_pool_or_below_zero_does_not_fail() -> None:
    """Asking for more than there is gives everything; asking for none gives only the hits."""
    assert len(sample.draw(_POOL, 1000, 0)) == len(_POOL)
    assert sample.draw(_POOL, -3, 0) == []
    assert [item for item, _src in sample.draw([*_POOL, _HIT], 0, 0)] == [_HIT]


def test_the_mode_writes_blind_rows_to_stdout_and_labels_to_the_key(tmp_path: Path) -> None:
    """Stdout holds ids, places and text only; the key file holds source and family."""
    log = tmp_path / "abc.jsonl"
    log.write_text(_assistant(_FIVE) + "\n", encoding="utf-8")
    key = tmp_path / "key.jsonl"
    out = io.StringIO()
    args = [str(log), "--sample", "2", "--seed", "3", "--key", str(key)]
    assert main(args, out) == 0
    *rows, tally = out.getvalue().splitlines()
    assert tally.startswith("# ")
    parsed = [_object(row) for row in rows]
    assert all(set(row) == {"id", "line", "uuid", "text"} for row in parsed)
    labels = [_object(line) for line in key.read_text(encoding="utf-8").splitlines()]
    assert [label["id"] for label in labels] == [row["id"] for row in parsed]
    assert "canonical" in {label["family"] for label in labels}
    assert "canonical" not in "".join(rows)


def test_out_sends_the_blind_rows_to_a_file_and_leaves_stdout_to_the_tally(tmp_path: Path) -> None:
    """With `--out` the blind rows are in the file, the same rows stdout would have held."""
    log = tmp_path / "abc.jsonl"
    log.write_text(_assistant(_FIVE) + "\n", encoding="utf-8")
    plain, filed = io.StringIO(), io.StringIO()
    base = [str(log), "--sample", "2", "--seed", "3"]
    assert main([*base, "--key", str(tmp_path / "k1")], plain) == 0
    blind = tmp_path / "blind.jsonl"
    assert main([*base, "--key", str(tmp_path / "k2"), "--out", str(blind)], filed) == 0
    *rows, _tally = plain.getvalue().splitlines()
    assert blind.read_text(encoding="utf-8").splitlines() == rows
    assert filed.getvalue().startswith("# ")
    assert str(blind) in filed.getvalue()


def test_the_mode_without_a_key_stops_with_the_usage_code(tmp_path: Path) -> None:
    """The labels have nowhere to go but beside the blind rows, so it refuses."""
    log = tmp_path / "abc.jsonl"
    log.write_text(_assistant(_FIVE) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit) as stopped:
        main([str(log), "--sample", "2"], io.StringIO())
    assert stopped.value.code == _USAGE
