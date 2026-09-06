# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The cases for `mikemol.hooks.checkers` — that config reaches an in-flight edit.

⚑⚑⚑ THE SUBJECT-IDENTITY CASES ARE WHY THIS FILE EXISTS. The hook checks a TEMPFILE, so without
`--stdin-filename` every path-keyed setting an adopting repo writes — `per-file-ignores`,
`exclude` — resolves against `tmpab12cd.py` and matches nothing. The gate and a direct `ruff
check` then disagree about the same file ALWAYS, silently, in the direction that manufactures
findings the author cannot act on. Nothing about that is visible in a passing run.

⚑⚑ AND `--pretty` IS PINNED FOR A MEASURED REASON, not for taste. Without it mypy cites a line
number in a file deleted microseconds later that never existed on disk — a citation with no
readable referent, guessed at six times on one file and wrong every time.
"""

from __future__ import annotations

from pathlib import Path

from mikemol.hooks import checkers

_TMP = Path("/tmp/tmpab12cd.py")  # noqa: S108 — a fixed literal, never created or opened
_REAL = "/home/someone/project/src/thing.py"
_VENV = Path("/home/someone/project/.venv/bin/python3")
_CFG = Path("/home/someone/project/pyproject.toml")

_CHECKER_COUNT = 2


def _argv_for(name: str, path: str = _REAL) -> list[str]:
    """Return one checker's argv, or fail the calling test if it is not registered.

    Returns:
        one checker's argv, or fail the calling test if it is not registered.

    """
    for got, argv, _stdin in checkers.checker_argv(_TMP, path, _VENV, _CFG):
        if got == name:
            return argv
    msg = f"no checker named {name!r} is registered"
    raise AssertionError(msg)


def test_both_checkers_are_registered() -> None:
    """Check the roster is exactly ruff then mypy.

    ⚑ ASSERTED SO A CHECKER CANNOT SILENTLY DROP OUT OF THE GATE. A hook that ran one of two
    would report clean on a file the missing one refuses — the same armed-and-checking-nothing
    shape the arming switch guards against, one layer in.
    """
    got = [name for name, _argv, _stdin in checkers.checker_argv(_TMP, _REAL, _VENV, _CFG)]
    assert got == ["ruff", "mypy"]
    assert len(got) == _CHECKER_COUNT


def test_ruff_is_told_the_authors_real_path() -> None:
    """Check the flag and the author's path travel together.

    ⚑⚑ THE DEFECT THIS PREVENTS IS SILENT. Without the pair adjacent, every path-keyed exemption
    in the adopting repo's config is inert against the temp copy.
    """
    argv = _argv_for("ruff")
    assert "--stdin-filename" in argv
    assert argv[argv.index("--stdin-filename") + 1] == _REAL


def test_ruff_falls_back_to_the_tempfile_when_no_path_is_known() -> None:
    """Check an unknown subject names the tempfile rather than an empty string.

    ⚑ AN EMPTY `--stdin-filename` IS NOT THE SAME AS NO SUBJECT: ruff would resolve config
    against `""`, which matches nothing and reads exactly like the defect above.
    """
    argv = _argv_for("ruff", path="")
    assert argv[argv.index("--stdin-filename") + 1] == str(_TMP)


def test_ruff_reads_stdin_and_mypy_does_not() -> None:
    """Check each checker declares how it takes the staged content.

    ⚑ THE THIRD TUPLE ELEMENT IS WHAT KEEPS THE CALLER FROM KNOWING WHICH IS WHICH. Getting it
    backwards hands ruff an unread path, or mypy content it never receives.
    """
    got = {name: stdin for name, _argv, stdin in checkers.checker_argv(_TMP, _REAL, _VENV, _CFG)}
    assert got == {"ruff": True, "mypy": False}


def test_mypy_is_given_the_tempfile_as_its_subject() -> None:
    """Check the staged copy is named, since mypy takes a real path."""
    assert str(_TMP) in _argv_for("mypy")


def test_mypy_renders_the_source_line() -> None:
    """Check `--pretty` is present.

    ⚑⚑ IT IS THE WHOLE DIFFERENCE between an actionable finding and a bare number pointing into
    a file that no longer exists.
    """
    assert "--pretty" in _argv_for("mypy")


def test_both_checkers_are_pointed_at_the_projects_config() -> None:
    """Check each checker resolves rules from the edited file's project.

    ⚑ THE CONFIG FOLLOWS THE EDITED FILE, and each checker spells the flag differently. A hook
    naming its OWN project would apply one repo's bar to another's code — invisible while a
    session edits one tree, wrong in both directions the moment it edits two.
    """
    ruff = _argv_for("ruff")
    mypy = _argv_for("mypy")
    assert ruff[ruff.index("--config") + 1] == str(_CFG)
    assert mypy[mypy.index("--config-file") + 1] == str(_CFG)


def test_both_checkers_run_under_the_projects_interpreter() -> None:
    """Check each argv invokes the project venv's python, not whatever is on PATH."""
    for name, argv, _stdin in checkers.checker_argv(_TMP, _REAL, _VENV, _CFG):
        assert argv[0] == str(_VENV), name
        assert argv[1] == "-m", name


def test_ruff_does_not_cache() -> None:
    """Check caching is off.

    ⚑ A CACHE KEYED ON A TEMPFILE PATH NEVER HITS AND NEVER EXPIRES. Each staged edit gets a
    fresh random name, so entries accumulate without ever serving a read — cost with no benefit,
    on a hook that runs at every edit.
    """
    assert "--no-cache" in _argv_for("ruff")
