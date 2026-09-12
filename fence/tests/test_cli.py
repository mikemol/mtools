# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The command line: argument contracts and the refusals, without running a payload."""

from __future__ import annotations

import json

import pytest

from mikemol.fence.cli import _Args, _report_ratchet, _sweep_payload, build_parser, main
from mikemol.fence.core import Caps, Result

USAGE_EXIT = 2
PIDS_UNDER_TEST = 64


class TestParser:
    """What the flags mean, checked against the narrowed `_Args` rather than the help text.

    ⚑ THROUGH `_Args`, NOT `parse_args`, because the raw `Namespace` types as `Any` — a test
    reading it would assert against untyped values and check nothing the type system can see.
    """

    def test_separator_is_stripped(self) -> None:
        """The `--` separator does not reach the payload."""
        assert _Args.parse(build_parser(), ["--", "true"]).cmd == ("true",)

    def test_caps_parse(self) -> None:
        """Cap flags land on their fields, with `--pids` typed as an int."""
        a = _Args.parse(build_parser(), ["--mem", "2G", "--pids", "64", "--", "true"])
        assert a.mem == "2G"
        assert a.pids == PIDS_UNDER_TEST

    def test_observe_defaults_off(self) -> None:
        """`--observe` is opt-in; its absence is not a cap."""
        assert not _Args.parse(build_parser(), ["--", "true"]).observe


class TestRefusals:
    """⚑ EVERY REFUSAL IS A `SystemExit(2)` FROM argparse, not a silent precedence rule."""

    def test_no_command_is_refused(self) -> None:
        """A fence with nothing to fence is a usage error, not an empty success."""
        with pytest.raises(SystemExit) as e:
            main([])
        assert e.value.code == USAGE_EXIT

    @pytest.mark.parametrize("extra", [
        ["--mem", "1G"],
        ["--swap", "0"],
        ["--pids", "8"],
        ["--io", "259:0 wbps=1048576"],
        ["--ratchet", "2G,1G"],
    ])
    def test_observe_refuses_to_combine_with_a_cap(self, extra: list[str]) -> None:
        """Refuse rather than resolve an incoherent instruction.

        ⚑ NOT A PRECEDENCE RULE. "observe" plus "cap this" has two bad resolutions: a fence that
        does not fence, or a run the caller believed was read-only that quietly kills its
        payload. Guessing between them is how either happens, so it refuses.
        """
        with pytest.raises(SystemExit) as e:
            main([*extra, "--observe", "--", "true"])
        assert e.value.code == USAGE_EXIT

    def test_observe_alone_is_accepted_by_the_parser(self) -> None:
        """The T-arm: `--observe` with no cap parses cleanly."""
        a = _Args.parse(build_parser(), ["--observe", "--", "true"])
        assert a.observe
        assert a.cmd == ("true",)


class TestSweepPayload:
    """The sweep's ANSWER must be in the machine-readable stream, not only in prose.

    ⚑⚑⚑ REPORTED BY `cassian-observability` FROM THE CONSUMING SIDE, and the route is the finding.
    They tracked OOM kills on their host for four ticks and reported a load incident, then read the
    enforced limits out of the KERNEL's own OOM dumps and recognised a clean descending ladder —
    1 GiB, 512, 256, 128, 64, 32, 16, 8, 4 — which is a `--ratchet` sweep doing exactly what it is
    designed to do. Their measurement of this tool's own voice: **zero** `BOUND BY` lines in 24h,
    against 34 journal lines mentioning "fence" that were all the kernel's records rather than ours.

    ⚑⚑ AND THE GAP IS NARROWER AND SHARPER THAN *the information is missing*. Per-rung `bound_by`
    was already in the payload; what was absent is the SYNTHESIS — which rung bound, the one thing
    a sweep exists to compute. A consumer received the ladder and had to re-derive the answer the
    tool had already rendered for humans. Measured before the repair: `--json --ratchet 64M,32M`
    emitted a bare array with no synthesis field anywhere.

    ⚑ THEIR OWN FRAMING IS THE JUSTIFICATION: *"the binding constraint is the answer a ratchet
    sweep exists to produce"*, and it was on a stream nobody collects. They explicitly offered
    that the gap might be theirs to close by capturing stderr — it is not; the payload is the right
    home, because a caller already parsing stdout should not need a second channel for the answer.
    """

    @staticmethod
    def _result(mem: str, *, bound: tuple[str, ...] = ()) -> Result:
        """One rung, built directly rather than by running a fence.

        Returns:
            A `Result` for cap `mem`, bound by `bound`. ⚑ NO CGROUP IS NEEDED to check what the
            payload SAYS about a set of results, and requiring one would make this arm unrunnable
            in the sandbox where the suite actually runs.

        """
        return Result(cmd=("true",), caps=Caps(mem=mem), duration_s=0.1,
                      exit_code=0, memory_peak_bytes=1, bound_by=bound)

    def test_the_binding_rung_is_named_in_the_payload(self) -> None:
        """⚑⚑⚑ THE ANSWER, AS A FIELD RATHER THAN AS PROSE.

        Without it a consumer scans the ladder for the last entry with a non-empty `bound_by` —
        re-deriving what the tool already computed and rendered for humans.
        """
        payload = _sweep_payload([self._result("64M"),
                                  self._result("8M", bound=("MEMORY, THROTTLED",))])
        assert payload["bound_at"] == "8M", (
            f"the sweep's answer is not in its payload; got {payload.get('bound_at')!r} — a "
            f"consumer must then re-derive the binding rung from the ladder"
        )
        assert payload["bound_by"] == ["MEMORY, THROTTLED"], (
            f"the binding rung is named but not WHY it bound; got {payload.get('bound_by')!r}"
        )
        assert payload["completed_within_all"] is False

    def test_nothing_binding_reports_null_rather_than_omitting_the_key(self) -> None:
        """⚑⚑ ABSENT AND NULL ARE DIFFERENT CLAIMS TO A PARSER.

        A missing key reads as *this tool does not report that*; a null reads as *it reports there
        was none*. The first sends a consumer looking for another source — which is exactly the
        trip `cassian-observability` made to the kernel's OOM dumps — and the second closes the
        question. This repository's absence-versus-unavailable distinction, at a JSON boundary.
        """
        payload = _sweep_payload([self._result("64M"), self._result("32M")])
        assert "bound_at" in payload, (
            "the key is absent when nothing bound, so a consumer cannot distinguish *no binding "
            "constraint* from *this tool does not report one*"
        )
        assert payload["bound_at"] is None
        assert payload["completed_within_all"] is True

    def test_every_rung_survives_beside_the_synthesis(self) -> None:
        """⚑ THE LADDER IS NOT REPLACED BY ITS SUMMARY, and this is the control.

        A payload carrying only the answer would be smaller and worse: the rungs are what let a
        reader check the synthesis rather than trust it, and `cassian-observability` reconstructed
        an entire sweep from rung-level evidence alone. Summarising IS the repair; summarising
        INSTEAD would be the truncation defect this tree has already measured in its own arms.
        """
        rungs = [self._result("64M"), self._result("32M"), self._result("8M", bound=("MEM",))]
        payload = _sweep_payload(rungs)
        got = payload["rungs"]
        assert isinstance(got, list), f"the rungs are not a list; payload was {payload!r}"
        # ⚑ NARROWED BY ASSERTION, NOT BY A SUPPRESSION. `ResultJSON` is `dict[str, object]`, so
        # indexing into a rung leaks through `disallow_any_expr` unless each hop is checked. A
        # `type: ignore` here would be this repository's first suppression, bought to save a line.
        caps: list[object] = []
        for rung in got:
            assert isinstance(rung, dict), f"a rung is not a mapping: {rung!r}"
            entry = rung["caps"]
            assert isinstance(entry, dict), f"a rung's caps are not a mapping: {entry!r}"
            caps.append(entry["mem"])
        assert caps == ["64M", "32M", "8M"], (
            f"the ladder did not survive into the payload beside its summary; got {caps!r}"
        )

    def test_the_payload_the_sweep_emits_is_the_one_with_the_answer(
            self, capsys: pytest.CaptureFixture[str]) -> None:
        """⚑⚑⚑ THE ARMS ABOVE TEST A FUNCTION; THIS ONE TESTS THAT IT IS CALLED.

        Measured, and it is why this arm exists: reverting the emit line to the bare array left all
        three arms above GREEN. They exercise `_sweep_payload` directly, so an unwired payload — the
        synthesis computed and then not shipped — passes every one of them. **That is the
        packager-is-not-a-user defect, in the arms written to close a wiring gap, on the same
        tick.**

        ⚑⚑ SO IT DRIVES THE REPORTER AND PARSES REAL STDOUT. The subject is what a consumer
        RECEIVES, and nothing short of reading the stream measures that: `cassian-observability`
        did not lack a function, they lacked a line on a stream they collect.

        ⚑ AND IT ASSERTS THE STREAM SPLIT TOO, because the payload landing on stderr would satisfy
        a looser check while breaking the contract this CLI states in `_note`: narration on stderr,
        machine-readable on stdout, so a caller piping stdout into a parser gets JSON and nothing
        else.
        """
        rc = _report_ratchet([self._result("64M"),
                              self._result("8M", bound=("MEMORY, THROTTLED",))], json_out=True)
        assert rc == 0, (
            "a completed sweep reports success even when a cap bound — the binding cap is the "
            "ANSWER, so a nonzero code would conflate it with a failure to measure"
        )
        captured = capsys.readouterr()
        # ⚑⚑ THE SHAPE IS CHECKED BEFORE IT IS INDEXED, because the defect this arm catches is a
        # payload that is a bare LIST. Indexing a list by a string name raises `TypeError` and the
        # reader gets a crash instead of the finding — measured on the F-arm, which reported
        # *list indices must be integers* rather than *the answer is not in the payload*.
        # ⚑ AND THE NARROWING IS ALSO WHAT KEEPS `json.loads`'s `Any` OUT of every read below it:
        # this distribution runs `disallow_any_expr`, so the boundary is the one place to state it.
        decoded: object = json.loads(captured.out)
        assert isinstance(decoded, dict), (
            f"the emitted payload is a bare {type(decoded).__name__}, so it carries the ladder and "
            f"not the sweep's answer — a consumer must re-derive the binding rung; got "
            f"{captured.out[:200]!r}"
        )
        payload: dict[str, object] = decoded
        assert payload["bound_at"] == "8M", (
            f"the EMITTED payload does not carry the sweep's answer — the synthesis exists but is "
            f"not what reaches stdout; got {captured.out!r}"
        )
        assert "bound_at" not in captured.err, (
            "the machine-readable payload leaked onto stderr, which breaks the stream split a "
            "caller relies on when piping stdout into a parser"
        )
