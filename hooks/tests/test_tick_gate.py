# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `tick_gate`: a tick prompt that cannot run is refused, any other prompt passes."""

from __future__ import annotations

import io
import json
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mikemol.hooks import entry, hook_argv, tick_gate
from mikemol.hooks.host_facts import GIB, REFUSE_FRACTION, Headroom, HostLock

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
TICK = "paths-forward tick (host session github-b3, /home/mikemol/github). Use the skill."
LIMIT = 100 * GIB
RATIO = 1.5
HEALTHY = Headroom(used=GIB, limit=LIMIT, ratio=RATIO)
CRAMPED = Headroom(used=90 * GIB, limit=LIMIT, ratio=RATIO)
AT_THE_LINE = Headroom(used=int(REFUSE_FRACTION * LIMIT), limit=LIMIT, ratio=RATIO)
JUST_UNDER = Headroom(used=int(REFUSE_FRACTION * LIMIT) - 1, limit=LIMIT, ratio=RATIO)
FREE = HostLock(holder=None, taken_at=None)
FRESH_LOCK = HostLock(holder="github-b3", taken_at="2026-10-06T11:58:00Z")
STALE_LOCK = HostLock(holder="github-b3", taken_at="2026-10-06T08:00:00Z")


def _queue(root: Path, doc: dict[str, object]) -> None:
    """Write `doc` as the queue under `root/.claude`."""
    (root / ".claude").mkdir(exist_ok=True)
    (root / ".claude" / "paths-forward.json").write_text(json.dumps(doc), encoding="utf-8")


def _no_read() -> Headroom | None:
    """Stand in for the zram reader on a path that must not read it.

    Raises:
        AssertionError: always, because the gate read a fact it should not have.

    """
    msg = "the gate read the zram fact for a prompt that is not a tick"
    raise AssertionError(msg)


def _healthy() -> Headroom | None:
    """Stand in for the zram reader on a healthy device.

    Returns:
        a device 1 GiB into a 100 GiB ceiling.

    """
    return HEALTHY


def _cramped() -> Headroom | None:
    """Stand in for the zram reader on a device 90 percent of the way to its ceiling.

    Returns:
        a device 90 GiB into a 100 GiB ceiling.

    """
    return CRAMPED


def _decision(kind: str, text: str) -> str:
    """Return the exact refusal line `run` prints.

    Returns:
        the JSON line, newline included.

    """
    refusal: dict[str, str] = {"decision": kind, "reason": text}
    return json.dumps(refusal) + "\n"


def test_only_a_prompt_that_begins_with_the_loop_text_is_a_tick() -> None:
    """Leading whitespace is ignored; a tick mentioned mid-sentence, or an empty prompt, is not."""
    assert tick_gate.is_tick(TICK)
    assert tick_gate.is_tick("   \n" + TICK)
    assert tick_gate.is_tick("[paths-forward tick] Invoke the paths-forward-loop skill")
    assert not tick_gate.is_tick("[[paths-forward tick]")
    assert not tick_gate.is_tick("[ paths-forward tick]")
    assert not tick_gate.is_tick("what does the paths-forward tick prompt do?")
    assert not tick_gate.is_tick("")


def test_a_device_at_the_refusal_line_refuses_and_one_just_under_does_not() -> None:
    """The threshold is inclusive: exactly REFUSE_FRACTION refuses, one byte under admits."""
    assert tick_gate.gate(AT_THE_LINE, FREE, NOW).reason is not None
    assert tick_gate.gate(JUST_UNDER, FREE, NOW).reason is None


def test_a_cramped_device_refuses_and_says_how_much_is_left() -> None:
    """The reason names the use, the ceiling, the room and the ratio, and adds no context."""
    verdict = tick_gate.gate(CRAMPED, FREE, NOW)
    assert verdict.context is None
    assert verdict.reason is not None
    assert "90%" in verdict.reason
    assert "100 GiB" in verdict.reason
    assert "about 15 GiB" in verdict.reason
    assert "1.50:1" in verdict.reason


def test_a_fresh_lock_skips_the_tick_naming_its_holder() -> None:
    """A tick already running (or just died) is skipped, saying who holds the lock since when."""
    verdict = tick_gate.gate(HEALTHY, FRESH_LOCK, NOW)
    assert verdict.context is None
    assert verdict.reason is not None
    assert "github-b3" in verdict.reason
    assert "2026-10-06T11:58:00Z" in verdict.reason


def test_a_stale_lock_is_admitted_with_a_note_that_the_tick_takes_it_over() -> None:
    """A dead holder's lock does not refuse the tick; the context says it will be taken over."""
    verdict = tick_gate.gate(HEALTHY, STALE_LOCK, NOW)
    assert verdict.reason is None
    assert verdict.context is not None
    assert "stale tick lock from github-b3" in verdict.context
    assert "takes it over" in verdict.context


def test_a_healthy_free_host_is_admitted_with_both_facts_as_context() -> None:
    """The tick starts knowing the zram use, the ratio, and that the lock is free."""
    verdict = tick_gate.gate(HEALTHY, FREE, NOW)
    assert verdict.reason is None
    assert verdict.context == (
        "tick gate: zram1 1% of its 100 GiB ceiling, 1.50:1, about 148 GiB of data fits; "
        "tick lock free."
    )


def test_a_fact_that_cannot_be_read_is_named_not_checked_and_blocks_nothing() -> None:
    """Absent facts (None) are said so in the context, and the tick proceeds."""
    verdict = tick_gate.gate(None, None, NOW)
    assert verdict.reason is None
    assert verdict.context == (
        "tick gate: zram1 unreadable (not checked); tick lock unreadable (not checked)."
    )


def test_a_prompt_that_is_not_a_tick_passes_without_reading_any_fact(tmp_path: Path) -> None:
    """The facts are not read, and nothing is printed, for an ordinary prompt."""
    out = io.StringIO()
    payload: dict[str, object] = {"prompt": "please explain hooks", "cwd": str(tmp_path)}
    assert tick_gate.run(payload, _no_read, NOW, out) == 0
    assert not out.getvalue()


def test_a_cramped_device_blocks_a_tick_prompt_through_run(tmp_path: Path) -> None:
    """The refusal is printed as the block decision, and the exit code stays zero."""
    out = io.StringIO()
    payload: dict[str, object] = {"prompt": TICK, "cwd": str(tmp_path)}
    assert tick_gate.run(payload, _cramped, NOW, out) == 0
    reason = tick_gate.gate(CRAMPED, None, NOW).reason
    assert reason is not None
    assert out.getvalue() == _decision("block", reason)


def test_an_admitted_tick_prompt_prints_additional_context(tmp_path: Path) -> None:
    """A tick that may run gets the facts line as UserPromptSubmit additionalContext."""
    _queue(tmp_path, {"waypoints": []})
    out = io.StringIO()
    payload: dict[str, object] = {"prompt": TICK, "cwd": str(tmp_path)}
    assert tick_gate.run(payload, _healthy, NOW, out) == 0
    context = tick_gate.facts_line(HEALTHY, FREE)
    admitted: dict[str, dict[str, str]] = {
        "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}
    }
    assert out.getvalue() == json.dumps(admitted) + "\n"


def test_the_prompt_is_also_read_from_user_message(tmp_path: Path) -> None:
    """If the payload names its text `user_message`, the gate still recognises the tick."""
    out = io.StringIO()
    payload: dict[str, object] = {"user_message": TICK, "cwd": str(tmp_path)}
    assert tick_gate.run(payload, _cramped, NOW, out) == 0
    assert out.getvalue().startswith('{"decision": "block"')


def test_main_blocks_a_tick_with_a_fresh_lock_whatever_the_device_says(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Through main, with the real clock and the real zram reader, a fresh lock still blocks."""
    taken = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    _queue(tmp_path, {"lock": {"holder": "github-b3", "taken_at": taken}})
    stdin_payload: dict[str, str] = {"prompt": TICK, "cwd": str(tmp_path)}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(stdin_payload)))
    assert tick_gate.main() == 0
    assert capsys.readouterr().out.startswith('{"decision": "block"')


def test_main_passes_a_payload_that_is_not_json_and_says_so(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A gate that cannot read its input must not eat a prompt."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert tick_gate.main() == 0
    captured = capsys.readouterr()
    assert not captured.out
    assert "not JSON" in captured.err


def test_the_console_entry_refuses_an_argument_before_reading_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The argv contract: a hook takes no arguments, and the refusal names the program."""
    monkeypatch.setattr(sys, "argv", ["mikemol-hook-tick-gate", "--help"])
    assert entry.tick_gate_main() == hook_argv.EXIT_REFUSED
    assert "mikemol-hook-tick-gate" in capsys.readouterr().err
