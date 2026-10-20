# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The real tool runs behind `mikemol-pycheck --ratchet ROOT` (W1485).

`ruff_json` and `mypy_json` run each tool over the repo's trees with the repo's own house config
and return its JSON; `disk` reads a file or says it is absent. The comparison lives in
`pycheck_ratchet`, which takes these as seams.

⚑ A TOOL THAT FAILED IS NOT A TOOL THAT FOUND NOTHING. ruff and mypy both exit 0 when clean and 1
when they report findings; any other status (a crash, a bad config, the program missing) raises
`ToolFailedError` naming it, so the stage exits "nothing judged" and an empty output never reads as
an empty finding list.
"""

import sys
from pathlib import Path

from mikemol.hooks.pycheck_ratchet import Tools
from mikemol.hooks.runproc import run_process

TREES = ("src", "tests", "checks", "tools")
CLEAN_OR_FINDINGS = (0, 1)
RUFF_CONFIG = "ruff-house.toml"
MYPY_CONFIG = "mypy-house.ini"


class ToolFailedError(RuntimeError):
    """A tool exited with a status that is neither clean nor findings."""


def trees(root: Path) -> list[str]:
    """Name the trees under `root` that exist.

    Returns:
        their paths, in the fixed order of `TREES`.

    """
    return [str(root / tree) for tree in TREES if (root / tree).is_dir()]


def run_tool(tool: str, argv: list[str], root: Path) -> str:
    """Run one tool and refuse a status that is neither clean nor findings.

    Returns:
        the tool's standard output.

    Raises:
        ToolFailedError: when the exit status is not 0 or 1.

    """
    status, out = run_process(argv, root)
    if status not in CLEAN_OR_FINDINGS:
        message = f"{tool} exited {status}"
        raise ToolFailedError(message)
    return out


def ruff_json(root: Path) -> str:
    """Run ruff with the root's house config.

    Returns:
        ruff's JSON findings.

    """
    config = str(root / RUFF_CONFIG)
    argv = [sys.executable, "-m", "ruff", "check", "--config", config]
    return run_tool("ruff", [*argv, "--output-format", "json", "--no-cache", *trees(root)], root)


def mypy_json(root: Path) -> str:
    """Run mypy with the root's house config.

    Returns:
        mypy's findings, one JSON object a line.

    """
    config = str(root / MYPY_CONFIG)
    argv = [sys.executable, "-m", "mypy", "--config-file", config, "--output", "json"]
    return run_tool("mypy", [*argv, "--no-error-summary", "--no-incremental", *trees(root)], root)


def disk(path: Path) -> str | None:
    """Read a file.

    Returns:
        its text, or None when it is missing or unreadable.

    """
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def save(path: Path, text: str) -> None:
    """Write a baseline file."""
    path.write_text(text, encoding="utf-8")


def real() -> Tools:
    """Build the seams from the real tools and the disk.

    Returns:
        the `Tools` the console wiring passes to `ratchet`.

    """
    return Tools(ruff_json, mypy_json, disk)
