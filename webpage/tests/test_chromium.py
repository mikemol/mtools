# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pinned chromium starts in the test sandbox and says the version that was pinned (W1819).

⚑ THIS IS THE MEASUREMENT BEFORE THE PROBES: nemik's three probes drive this browser, so whether a
bazel test sandbox can start it at all (its shared libraries, /dev/shm, the runfiles path) has to be
known first. The binary comes from `@chrome_headless_shell` as test data, and `CHROME_RLOCATION` is
set by the BUILD file, so outside bazel there is nothing to launch and the test says so.
"""

import os
import subprocess
from pathlib import Path

import pytest

_PINNED = "153.0.8010.12"


def _binary() -> Path | None:
    where = os.environ.get("CHROME_RLOCATION")
    runfiles = os.environ.get("RUNFILES_DIR") or os.environ.get("TEST_SRCDIR")
    if not where or not runfiles:
        return None
    return Path(runfiles) / where


def test_the_pinned_browser_starts_and_reports_the_pinned_version() -> None:
    """`chrome-headless-shell --version` names 153.0.8010.12, from the bazel archive."""
    binary = _binary()
    if binary is None:
        pytest.skip("not run under bazel: no CHROME_RLOCATION to launch")
    assert binary.is_file()
    done = subprocess.run([str(binary), "--version"], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    assert _PINNED in done.stdout
