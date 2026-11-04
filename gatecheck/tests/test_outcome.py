# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The command outcome the gate tools' seams return, so tests need no subprocess types (W2265)."""

import pytest

from mikemol.gatecheck.outcome import CommandFailedError, Outcome

_FAILED = 3


def test_a_successful_outcome_passes_the_check_and_keeps_its_text() -> None:
    """The control: status zero is not refused, and the text fields default to empty."""
    done = Outcome(0, "out\n")
    done.check()
    assert done.stdout == "out\n"
    assert not done.stderr


def test_a_failed_outcome_is_refused_with_its_status_and_stderr() -> None:
    """Any non-zero status raises, carrying the status and what the command said."""
    with pytest.raises(CommandFailedError) as caught:
        Outcome(_FAILED, "", "boom\n").check()
    assert caught.value.returncode == _FAILED
    assert caught.value.stderr == "boom\n"
    assert str(caught.value) == f"command exited {_FAILED}"
