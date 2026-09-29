# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The whisperx stubs are checked against the whisperx they claim to describe.

⚑⚑ A STUB IS AN UNCHECKED CLAIM UNTIL SOMETHING CHECKS IT. whisperx ships no py.typed, so the
signatures in stubs/whisperx were transcribed from 3.8.6's source by hand (W268). This runs
stubtest against the real package from the `audiostruct_gpu` hub, so a whisperx upgrade that
moves a signature fails here, not at a GPU run.

⚑⚑ NO SKIP. If whisperx is not importable, stubtest fails and so does this test. A skip would
read green over a stub nothing checked (design note D5).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# ⚑ ABSOLUTE WITHOUT RESOLVING, as in //icsstruct:test_stub_authority: `resolve()` would follow
# bazel's runfiles symlinks out of the sandbox into the live working tree.
_DIST = (Path.cwd() / Path(__file__).parent.parent).absolute()
_ALLOWLIST = _DIST / "stubs" / "allowlist.txt"

# The submodules the stubs declare. The package itself is `(*args, **kwargs)` wrappers.
_MODULES = (
    "whisperx.audio",
    "whisperx.asr",
    "whisperx.alignment",
    "whisperx.diarize",
    "torch.cuda",
)


def test_the_stubs_match_whisperx(tmp_path: Path) -> None:
    """Run stubtest over the four submodule stubs, with the curated allowlist.

    ⚑ cwd is a writable temporary directory because stubtest writes its cache relative to cwd and
    a sandbox stages the distribution read-only (measured in mdstruct).
    """
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy.stubtest",
            *_MODULES,
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

    ⚑⚑ THIS KEEPS THE ALLOWLIST FROM BECOMING A SUPPRESSION LIST, as in icsstruct. Any other entry
    would hide a real divergence in something the stage factories call.
    """
    entries = [
        line.strip()
        for line in _ALLOWLIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    offenders = [e for e in entries if not e.endswith(("__init__", "__new__"))]
    assert offenders == [], f"non-constructor entries hide real divergence: {offenders}"
