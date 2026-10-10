# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""No hook script pipes into `grep -q` under `pipefail`: that pipeline is a race (W926).

⚑ `printf "$x" | grep -q pat` under `set -o pipefail` exits 141 whenever grep quits on its first
match before the writer has finished: the writer dies of SIGPIPE and the pipeline reads as FAILED
though the pattern matched. In `.githooks/post-commit` it made the `elif` read a rejected push as
'abandoned' and failed `test_a_moved_remote_is_still_reported_as_moved` once in a green run
(measured 2026-10-09). The same shape sat twice in `pre-commit`. A here-string (`grep -q pat
<<<"$x"`) has no writer to kill.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent
_PIPE_INTO_QUIET_GREP = re.compile(r"\|\s*grep\s+-[A-Za-z]*q")
_HOOKS = (".githooks/pre-commit", ".githooks/post-commit", ".githooks/pre-push")


def racy_lines(text: str) -> list[str]:
    """Find the lines that pipe into a quiet grep, in a script that sets pipefail.

    Returns:
        those lines, comments excluded; none for a script without pipefail (no race there).

    """
    if "pipefail" not in text:
        return []
    return [
        line.strip()
        for line in text.splitlines()
        if not line.lstrip().startswith("#") and _PIPE_INTO_QUIET_GREP.search(line)
    ]


def test_the_detector_finds_the_race_and_spares_the_here_string() -> None:
    """The control: a planted racy line is found, the here-string form is not."""
    racy = 'set -o pipefail\nif printf "%s" "$x" | grep -qE "a"; then :; fi\n'
    safe = 'set -o pipefail\nif grep -qE "a" <<<"$x"; then :; fi\n'
    assert racy_lines(racy) == ['if printf "%s" "$x" | grep -qE "a"; then :; fi']
    assert not racy_lines(safe)


def test_a_script_without_pipefail_has_no_race() -> None:
    """Without pipefail the pipeline's status is grep's alone, so the pipe is harmless."""
    assert not racy_lines('printf "%s" "$x" | grep -q a\n')


def test_a_comment_naming_the_pattern_is_not_a_finding() -> None:
    """The explanation in a hook's own comment must not trip the detector."""
    assert not racy_lines("set -o pipefail\n# a `printf | grep -q` pipe is a race\n")


def test_the_continued_pipe_form_is_found() -> None:
    """A pipe that begins its own line after a backslash continuation is the form pre-commit had."""
    text = "set -o pipefail\ngit diff \\\n    | grep -qE 'p' || continue\n"
    assert racy_lines(text) == ["| grep -qE 'p' || continue"]


def test_the_shipped_hook_scripts_have_no_such_pipe() -> None:
    """The real scripts, as the gate sees them: none pipes into a quiet grep under pipefail."""
    found = {
        name: racy_lines((_ROOT / name).read_text(encoding="utf-8"))
        for name in _HOOKS
        if (_ROOT / name).is_file()
    }
    assert {name: lines for name, lines in found.items() if lines} == {}
    assert found, "none of the hook scripts was readable: the arm checked nothing"
