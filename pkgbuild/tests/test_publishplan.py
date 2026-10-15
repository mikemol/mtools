# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that the release plan carries the publish card's number into every step.

W1238. ⚑ THE NUMBER IS READ FROM THE QUEUE: without a card it is the counter plus one and the plan
says to mint first; with a card it is that card's, and a card the queue has not issued is refused.
⚑ THE CONTROLS: a sha that is not hex, an index that is neither, a missing counter and a dangling
`--card` each exit 2 and print nothing to standard output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pkgbuild import publishplan

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_USAGE = 2
_SHA = "0123456789abcdef0123456789abcdef01234567"


def _state(tmp_path: Path, counter: int = 1238) -> Path:
    path = tmp_path / "state.json"
    path.write_text(f'{{"counter": {counter}, "waypoints": []}}', encoding="utf-8")
    return path


def test_without_a_card_the_next_number_is_planned_and_minting_comes_first(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Counter 1238 gives version 0.0.1239 and a first step that mints the card."""
    assert publishplan.run([str(_state(tmp_path)), _SHA, "testpypi"]) == 0
    out = capsys.readouterr().out
    assert "release 0.0.1239 at" in out
    assert "MINT FIRST" in out
    assert "--add" in out
    assert f"release-check . {_SHA} out --version 0.0.1239" in out
    assert "gh workflow run publish.yml -f index=testpypi -f version=0.0.1239" in out
    assert f"git tag v0.0.1239 {_SHA}" in out


def test_with_an_issued_card_its_number_is_the_version_and_nothing_is_minted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W1240 under a counter of 1240 gives 0.0.1240 and no mint step."""
    assert publishplan.run([str(_state(tmp_path, 1240)), _SHA, "pypi", "--card", "W1240"]) == 0
    out = capsys.readouterr().out
    assert "release 0.0.1240 at" in out
    assert "MINT FIRST" not in out
    assert "publish card W1240 exists" in out
    assert "-f index=pypi -f version=0.0.1240" in out


def test_a_card_the_queue_has_not_issued_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W1500 is above the counter, so no plan is printed."""
    assert publishplan.run([str(_state(tmp_path)), _SHA, "pypi", "--card", "W1500"]) == _USAGE
    captured = capsys.readouterr()
    assert not captured.out
    assert "not issued" in captured.err


def test_a_bad_sha_index_state_or_card_flag_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The controls: nothing reaches standard output."""
    state = str(_state(tmp_path))
    assert publishplan.run([state, "not-a-sha", "pypi"]) == _USAGE
    assert publishplan.run([state, _SHA, "elsewhere"]) == _USAGE
    assert publishplan.run([state, _SHA, "pypi", "--card"]) == _USAGE
    assert publishplan.run([state, _SHA, "pypi", "--card", "1240"]) == _USAGE
    assert publishplan.run([str(tmp_path / "absent.json"), _SHA, "pypi"]) == _USAGE
    assert publishplan.run([]) == _USAGE
    assert not capsys.readouterr().out
