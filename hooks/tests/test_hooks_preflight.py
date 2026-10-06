# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-hooks-preflight`: rebuild first, and a failed rebuild is not clean."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "bin" / "mikemol-hooks-preflight"
NOT_CHECKED = 3


def test_a_rebuild_that_cannot_run_is_not_checked_and_never_a_clean_exit(tmp_path: Path) -> None:
    """With no bazel on PATH the script exits 3 and says the venv did not build."""
    bash = shutil.which("bash") or "bash"
    done = subprocess.run(
        [bash, str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": str(tmp_path)},
    )
    assert done.returncode == NOT_CHECKED
    assert "did not build" in done.stderr
    assert "not checked" in done.stderr


def test_the_script_rebuilds_before_it_asks_for_the_verdict() -> None:
    """The rebuild line precedes the verdict line: a verdict before it would judge stale code."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert text.index("bazel build //hooks:.venv") < text.index("mikemol-pycheck")
    assert "--changed" in text
    assert text.index("mikemol-pycheck") < text.index('bazel test "${targets[@]}"')
    assert "//$top:all" in text
    assert "'^dist_checks()'" in text
    assert "diff --name-only HEAD" in text
    assert "ls-files --others" in text
