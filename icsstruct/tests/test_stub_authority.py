# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The stubs are checked against the libraries they claim to describe.

⚑⚑ A STUB IS AN UNCHECKED CLAIM UNTIL SOMETHING CHECKS IT. icsstruct's stubs replace icalendar's
`Any`-carrying annotations and supply the ones recurring-ical-events never shipped, so an upgrade
that moves either library's surface would otherwise go on type-checking against a fiction.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# ⚑ ABSOLUTE WITHOUT RESOLVING, as in //mdstruct:test_stub_authority: `resolve()` would follow
# bazel's runfiles symlinks out of the sandbox into the live working tree.
_DIST = (Path.cwd() / Path(__file__).parent.parent).absolute()
_ALLOWLIST = _DIST / "stubs" / "allowlist.txt"


def test_the_stubs_match_the_libraries_they_describe(tmp_path: Path) -> None:
    """Run stubtest over both stubs, with the curated allowlist.

    ⚑ cwd is a writable temporary directory because stubtest writes its cache relative to cwd and
    a sandbox stages the distribution read-only (measured in mdstruct). The parent environment is
    inherited so the staged mypy stays importable under bazel.
    """
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy.stubtest",
            "icalendar",
            "recurring_ical_events",
            "--ignore-missing-stub",
            "--allowlist",
            str(_ALLOWLIST),
            "--concise",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
        env={**os.environ, "MYPYPATH": str(_DIST / "stubs")},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_every_allowlist_entry_is_a_constructor() -> None:
    """Each allowed divergence is an `__init__` or `__new__`, never a called function.

    ⚑⚑ THIS IS WHAT KEEPS THE ALLOWLIST FROM BECOMING A SUPPRESSION LIST. icsstruct builds no
    Component and no CalendarQuery itself, so a constructor entry is surface the stubs decline to
    model. Any other entry would hide a real divergence in something icsstruct calls.
    """
    entries = [
        line.strip()
        for line in _ALLOWLIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert entries
    offenders = [e for e in entries if not e.endswith(("__init__", "__new__"))]
    assert offenders == [], f"non-constructor entries hide real divergence: {offenders}"
