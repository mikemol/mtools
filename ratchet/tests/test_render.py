# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.ratchet.render`: substrate's `ratchet_render_selftest` arms, ported.

Plus the letter's two fixes: a gate that DECLARES its program gets the `--list` pointer (an
installed console script has no `.py` to infer from), and the mint message names no ambient
switch the package does not have.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from mikemol.ratchet import render

if TYPE_CHECKING:
    import pytest

# A label the renderer prints, never a file this suite creates or opens.
_BASELINE = "baselines/probe.baseline"
_PLAIN = render.Voice(label="probe", report=render.DEFAULT)


def _voice(report: render.Report) -> render.Voice:
    """Build a probe voice speaking with `report`.

    Returns:
        the voice.

    """
    return render.Voice(label="probe", report=report)


def _angled(key: str) -> str:
    """Wrap a key in angle brackets, a gate's own spelling.

    Returns:
        the rendered key.

    """
    return f"<{key}>"


def _blank(key: str) -> str:
    """Render nothing, so the fallback-to-key path runs.

    Returns:
        the empty string.

    """
    del key
    return ""


def _explodes(key: str) -> str:
    """Raise, so the totality wrapper runs.

    Raises:
        KeyError: always.

    """
    raise KeyError(key)


def test_a_bare_key_renders_as_itself() -> None:
    """The default renderer is the identity on keys."""
    assert render.renderer(_PLAIN)("some::key") == "some::key"


def test_a_custom_renderer_is_used() -> None:
    """A gate's own key renderer reaches the output."""
    assert render.renderer(_voice(render.Report(render=_angled)))("k") == "<k>"


def test_a_raising_renderer_falls_back_to_the_key() -> None:
    """A renderer that raises cannot crash paydown: THE TOTALITY ARM.

    ⚑⚑⚑ A paid-down key is absent from the current census by definition, so a renderer indexing
    that census raises exactly on the branch reporting PROGRESS.
    """
    assert render.renderer(_voice(render.Report(render=_explodes)))("gone::z.py") == "gone::z.py"


def test_an_empty_render_falls_back_to_the_key() -> None:
    """A renderer returning "" yields the key rather than a blank line."""
    assert render.renderer(_voice(render.Report(render=_blank)))("k") == "k"


def test_paydown_is_reported_when_keys_were_also_added() -> None:
    """Paydown renders with its sizes, independently of growth: THE 8,516 ARM.

    ⚑⚑⚑ substrate's ban ratchet once read BROKEN at 375 new while holding 8,516 paid down.
    """
    body = "\n".join(render.paid_lines({"a", "b"}, (10, 8), _PLAIN, verb="LOWERED", dry=False))
    assert "paid down" in body
    assert "10 -> 8" in body


def test_a_dry_run_says_nothing_was_recorded() -> None:
    """A preview is labelled as one: a preview that reads like a write hides what landed."""
    lines = render.paid_lines({"a"}, (2, 1), _PLAIN, verb="would lower", dry=True)
    assert "nothing recorded" in "\n".join(lines)


def test_no_paydown_renders_nothing() -> None:
    """An empty paydown set produces no lines rather than an empty header."""
    assert render.paid_lines(set(), (5, 5), _PLAIN, verb="held", dry=False) == []


def test_growth_refuses_and_says_so() -> None:
    """Added keys render as BROKEN, with the debt-only rule stated."""
    body = "\n".join(render.added_lines({"new::x"}, 0, _PLAIN))
    assert "BROKEN" in body
    assert "PAID DOWN, not grown" in body


def test_growth_names_the_paydown_it_blocks() -> None:
    """Blocked paydown is reported beside the refusal: THE INVISIBLE-PROGRESS ARM."""
    body = "\n".join(render.added_lines({"new::x"}, 20, _PLAIN))
    assert "20 genuine paydown" in body
    assert "CANNOT record while any NEW key is present" in body


def test_a_refuse_hint_reaches_the_reader() -> None:
    """A gate's own remedy text is printed with its refusal."""
    voice = _voice(render.Report(refuse_hint="fix it thus"))
    assert "fix it thus" in "\n".join(render.added_lines({"k"}, 0, voice))


def test_no_growth_renders_nothing() -> None:
    """An empty added set produces no lines."""
    assert render.added_lines(set(), 3, _PLAIN) == []


def test_a_move_is_its_own_line() -> None:
    """A relocation renders as neither paydown nor growth: THE RELABEL ARM."""
    body = "\n".join(render.moved_lines({("old::a", "new::a")}, _PLAIN))
    assert "RELOCATED" in body
    assert "not paydown, not growth" in body


def test_quiet_suppresses_a_move_but_not_a_refusal() -> None:
    """`--quiet` silences a relocation while growth still refuses: quiet is about success."""
    quiet = _voice(render.Report(quiet=True))
    assert render.moved_lines({("a", "b")}, quiet) == []
    assert render.added_lines({"k"}, 0, quiet)


def test_the_mint_message_names_the_route_not_the_bypass() -> None:
    """The no-baseline message routes to the commit path and names the bypass as one."""
    body = "\n".join(render.no_baseline_lines(7, _BASELINE, _PLAIN))
    assert "git commit" in body
    assert "BYPASSES" in body


def test_the_mint_message_names_no_switch_the_package_lacks() -> None:
    """The default bypass text names no `SUBSTRATE_RATCHET_WRITE`: the package has no such switch.

    ⚑⚑ The letter's §3.1: `core`'s `write` is a REQUIRED argument, so the old text described a
    mechanism that does not exist here.
    """
    body = "\n".join(render.no_baseline_lines(7, _BASELINE, _PLAIN))
    assert "SUBSTRATE_RATCHET_WRITE" not in body
    assert "write=True" in body


def test_a_caller_can_supply_its_own_bypass_text() -> None:
    """A caller that still has an env switch (substrate, until its gates move) names it itself."""
    voice = _voice(render.Report(mint_bypass="  Setting OUR_SWITCH=1 BYPASSES the gate."))
    body = "\n".join(render.no_baseline_lines(7, _BASELINE, voice))
    assert "OUR_SWITCH=1" in body
    assert render.MINT_BYPASS not in body


def test_the_frozen_line_names_its_listing_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """The at-baseline count points at the mode that enumerates it, for a `.py` script."""
    monkeypatch.setattr("sys.argv", ["some_gate.py"])
    line = render.frozen_line(12, _PLAIN)
    assert "--list" in line
    assert "some_gate.py" in line


def test_a_declared_console_script_gets_its_pointer(monkeypatch: pytest.MonkeyPatch) -> None:
    """A gate declaring its program gets the pointer, though its argv[0] has no `.py`.

    ⚑⚑ The letter's §3.2, RED ON HEAD: an installed console script (the point of packaging) has
    no `.py` suffix, so inference from argv alone silently dropped the hint.
    """
    monkeypatch.setattr("sys.argv", ["/venv/bin/mikemol-some-gate"])
    line = render.frozen_line(12, _voice(render.Report(prog="mikemol-some-gate")))
    assert "mikemol-some-gate --list" in line


def test_a_non_cli_caller_gets_no_pointer(monkeypatch: pytest.MonkeyPatch) -> None:
    """A caller with no declared program and no `.py` argv gets no pointer, not a wrong one.

    ⚑ A bare `argv[0]` cannot tell pytest from a console script, which is why a console-script
    gate declares `prog` rather than having it inferred.
    """
    monkeypatch.setattr("sys.argv", ["pytest"])
    assert not render.list_pointer(5, "entries")


def test_a_zero_count_gets_no_pointer() -> None:
    """An empty census does not offer to enumerate itself, even with a declared program."""
    assert not render.list_pointer(0, "entries", "mikemol-some-gate")


def test_a_roundtrip_failure_reports_both_directions() -> None:
    """A baseline that did not read back names lost AND spurious keys.

    ⚑⚑ A write succeeding is not a read agreeing.
    """
    body = "\n".join(render.roundtrip_failure({"a"}, {"b"}, (5, 5), _PLAIN))
    assert "DID NOT ROUND-TRIP" in body
    assert "1 lost" in body
    assert "1 spurious" in body


def test_a_recorded_baseline_states_the_read_back() -> None:
    """A verified mint reports what was read back, not only what was written."""
    assert "read back, verified" in render.recorded_line(9, 9, _BASELINE, _PLAIN)


def test_the_census_listing_carries_its_total() -> None:
    """An enumeration ends with its count: a list without one cannot be weighed."""
    lines = render.census_listing({"a", "b"}, _PLAIN)
    assert "2 entries in the current census" in lines[-1]


def test_a_summary_reaches_the_listing() -> None:
    """A gate's per-census breakdown is printed beside the total."""
    lines = render.census_listing({"a"}, _voice(render.Report(summary="3 of one kind")))
    assert "3 of one kind" in lines[-1]


def test_emit_writes_one_narrative_to_the_stream_given() -> None:
    """`emit` writes every line, in order, to one stream: stdout by default, or the one given."""
    stream = io.StringIO()
    render.emit(["first", "second"], stream)
    assert stream.getvalue() == "first\nsecond\n"
