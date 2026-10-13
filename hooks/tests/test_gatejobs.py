# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-gate-jobs`: the commit gate's job count follows the host's free cores.

W1100. ⚑ THE IDLE HOST IS THE POSITIVE CONTROL: with no load the gate gets every core, exactly
today's behaviour, so the lower counts are the load's doing and the tool does not throttle a quiet
host. The load is read from a file the test writes; no real /proc is read.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from mikemol.hooks import gatejobs

if TYPE_CHECKING:
    from pathlib import Path

_CORES = 24
_IDLE = 0.5
_BUSY = 97.0
_HALF = 12.0
_USAGE = 2


def _load(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "loadavg"
    path.write_text(text, encoding="utf-8")
    return path


def _printed(tmp_path: Path, text: str) -> str:
    out = io.StringIO()
    assert gatejobs.main([], out, _CORES, _load(tmp_path, text)) == 0
    return out.getvalue()


def test_an_idle_host_gets_every_core() -> None:
    """The positive control: nothing running, the count is the core count."""
    assert gatejobs.jobs(_CORES, _IDLE) == _CORES


def test_the_count_is_the_free_cores_and_never_below_the_floor() -> None:
    """Half loaded gets about half; a host at load 97 on 24 cores is held to the floor, not zero."""
    assert gatejobs.jobs(_CORES, _HALF) == _CORES - int(_HALF)
    assert gatejobs.jobs(_CORES, _BUSY) == gatejobs.MIN_JOBS


def test_it_prints_one_flag_per_line_for_the_hook_to_read(tmp_path: Path) -> None:
    """Two flags, one per line, the same number in both."""
    text = _printed(tmp_path, "97.33 118.78 114.89 66/7877 172797\n")
    assert text == f"--jobs={gatejobs.MIN_JOBS}\n--local_test_jobs={gatejobs.MIN_JOBS}\n"


def test_an_unreadable_load_reads_as_an_idle_host(tmp_path: Path) -> None:
    """A missing file and a garbled one both fall back to today's behaviour: every core."""
    assert not gatejobs.load_of(tmp_path / "absent")
    assert not gatejobs.load_of(_load(tmp_path, "garbled\n"))
    assert gatejobs.jobs(_CORES, gatejobs.load_of(tmp_path / "absent")) == _CORES


def test_explain_states_the_cap_the_cores_and_the_load(tmp_path: Path) -> None:
    """Under load 97 on 24 cores the line says jobs=2, both readings, and that the floor held."""
    out = io.StringIO()
    assert gatejobs.main(["--explain"], out, _CORES, _load(tmp_path, "97.33 1 1\n")) == 0
    assert out.getvalue() == "gate jobs=2 cores=24 load1=97.33 floor=2 (held at the floor)\n"


def test_explain_does_not_claim_the_floor_on_an_idle_host(tmp_path: Path) -> None:
    """The control: at load 0.5 the cap is every core and the line carries no floor note."""
    out = io.StringIO()
    assert gatejobs.main(["--explain"], out, _CORES, _load(tmp_path, "0.5 1 1\n")) == 0
    assert out.getvalue() == "gate jobs=24 cores=24 load1=0.5 floor=2\n"


def test_an_argument_is_a_usage_error(tmp_path: Path) -> None:
    """The tool takes only --explain."""
    out = io.StringIO()
    assert gatejobs.main(["--jobs=3"], out, _CORES, _load(tmp_path, "1 1 1\n")) == _USAGE
    assert not out.getvalue()
