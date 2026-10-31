# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The gate's bazel test stops at the first non-passing test, by bazel's own option (W2110).

⚑ THE CONTROLS: `--nokeep_going` alone does not stop on a failed test (it is the build option; a
failed test is not a failed action), the test option `--notest_keep_going` is on the same command
as the one that writes the build events, and there is exactly one such command in the gate.
"""

from pathlib import Path

_GATE = Path(__file__).parents[2] / ".githooks" / "pre-commit"
_VERB = "bazel test --nokeep_going"


def _command() -> list[str]:
    lines = _GATE.read_text(encoding="utf-8").splitlines()
    at = [i for i, line in enumerate(lines) if _VERB in line and not line.lstrip().startswith("#")]
    assert len(at) == 1
    return lines[at[0] : at[0] + 2]


def test_the_gates_bazel_test_carries_the_test_option_that_stops_at_the_first_failure() -> None:
    """`--notest_keep_going` is on the gate's one `bazel test` command, beside `--nokeep_going`."""
    first = _command()[0]
    assert "--notest_keep_going" in first
    assert "--nokeep_going" in first


def test_the_same_command_writes_the_build_events_the_first_failure_is_read_from() -> None:
    """The line after it names the build-event file: the stop and the reading are one command."""
    assert "--build_event_json_file" in " ".join(_command())
