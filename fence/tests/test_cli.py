# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The command line: argument contracts and the refusals, without running a payload."""

from __future__ import annotations

import pytest

from mikemol.fence.cli import _Args, build_parser, main

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
