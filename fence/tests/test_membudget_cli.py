# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-membudget`: bash's verbs and exit codes over `admit`, then one ledger shared with bash.

⚑ EVERY ARM USES A LEDGER UNDER `tmp_path`, named through `MEMBUDGET_FILE` in an explicit
environment — never the host's `~/.cache/membudget`, and the run ledger lands beside it. ⚑ `run`
READS A QUIET, INJECTED LOAD: the default `Host` reads the real loadavg, which hangs a waiter on a
busy box. ⚑ THE ADMISSION ARMS RUN UNFENCED (the `ledger` fixture swaps `core.run_once`); the cap's
own arms keep the real fence and skip, saying why, where the host has no delegated cgroup.

⚑⚑ THE LAST ARMS ARE THE CROSS-CLIENT ARM (`.claude/swarm/cross-client.md` §7): substrate's bash
`membudget`, copied beside the ledger so it can build or write nothing in substrate, runs against
the same file. Where that script is unreachable they SKIP and say why; they never pass over nothing.
Owners are SAME-USER processes — this one, and the bash client it spawns — because bash's
`kill -0` reads another user's live process as dead (G1), which is not the property under test.
"""

from __future__ import annotations

import math
import os
import shutil
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mikemol.fence import admit, core, membudget_cli
from mikemol.fence import ledger as run_ledger
from mikemol.fence.cgroup import FenceUnavailableError, parent_with_controllers

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

_TOTAL = 1000
_OTHER_TOTAL = 2000
_SMALL_TOTAL = 100
_DEFAULT_TOTAL = 777
_HELD = 300
_FITS = 400
_OVER_FREE = 800
_TINY = 10
_CHILD_CODE = 7
_QUIET = (0.0, 0.0, 0.0)
_BUSY = (1000.0, 1000.0, 1000.0)
_NPROC = 1
_LOCK_BOUND_S = "0.2"
_TIMEOUT_S = "5"
_MAXLOAD = "2.5"
_TINY_TIMEOUT_S = "0.001"
_WAIT_S = 20.0
_POLL_S = 0.05
_LABEL_DEFAULT_MB = "192"
_LABEL_CEILING_MB = "384"
_GUARD_DEFAULT_S = "600"
_GUARD_CEILING_S = "3600"

_EXIT_OK = 0
_EXIT_LOCK = 1
_EXIT_USAGE = 2
_EXIT_REFUSED = 3
_EXIT_LEDGER = 4
_EXIT_NOT_FOUND = 127
_SIGNAL_BASE = 128

# A cap's kill as the shell reports it: SIGKILL, 128 + 9.
_SIGKILLED = _SIGNAL_BASE + signal.SIGKILL

# The cap arms: a lease, a payload that touches far more than it, and one that touches far less.
_CAP_MB = 64
_HOG_OVER_MB = 256
_ROOM_MB = 256
_HOG_UNDER_MB = 16

# Bash's run ledger beside the budget (`_record_time`), and its label for an unlabelled run —
# spelled as bash spells them, so the arms are an oracle independent of the script under test.
_RUNS_NAME = "labels.tsv"
_UNLABELLED = "?"

# A pool above every `auto` lease here, so admission never refuses one.
_POOL_MB = 8192

# The autosize letter's three peaks, and the bucket of their max (188 → 256), not of the median.
_SEEDED_PEAKS = (40.0, 188.0, 90.0)
_SEEDED_LEASE = 256

# Bash's `AGDA_MB_DEFAULT` when unset, and an operator's own default.
_BASH_DEFAULT_MB = 192
_OWN_DEFAULT_MB = 100

# The origin's heavy module, bash's ceiling, a ceiling above it, and the bucket it then leases.
_BIG_PEAK = 600.0
_CEILING_MB = 384
_WIDE_CEILING_MB = 2048
_BIG_BUCKET = 1024

# A pid far above any `pid_max`, so its owner is dead on every host.
_DEAD_OWNER = "4194305:1"

# Substrate's bash client, as cross-client.md names it (B and L there).
_BASH_DIR = Path.home() / "github" / "substrate" / "scripts"
_BASH_FILES = ("membudget", "membudget-ledger")

# A child that reports its parent lease id, and whether that lease is in the ledger it runs under.
_PROBE = ("import os, pathlib, sys\n"
          "lid = os.environ['MEMBUDGET_PARENT']\n"
          "text = pathlib.Path(os.environ['MEMBUDGET_FILE']).read_text()\n"
          "pathlib.Path(sys.argv[1]).write_text(lid + ' ' + str(f'LEASE {lid} ' in text))\n"
          "sys.exit(int(sys.argv[2]))\n")

# A child that reports the MB of the lease it runs under, as the shared ledger records it.
_LEASE_PROBE = ("import os, pathlib, sys\n"
                "lid = os.environ['MEMBUDGET_PARENT']\n"
                "text = pathlib.Path(os.environ['MEMBUDGET_FILE']).read_text()\n"
                "for line in text.splitlines():\n"
                "    f = line.split()\n"
                "    if f[:2] == ['LEASE', lid]:\n"
                "        pathlib.Path(sys.argv[1]).write_text(f[2])\n")


def _quiet() -> tuple[float, float, float]:
    """Return an idle load average.

    Returns:
        zeros.

    """
    return _QUIET


def _busy() -> tuple[float, float, float]:
    """Return a load average far over any ceiling.

    Returns:
        a large load.

    """
    return _BUSY


def _default_total() -> int:
    """Return the injected default total.

    Returns:
        `_DEFAULT_TOTAL`.

    """
    return _DEFAULT_TOTAL


def _host(*, busy: bool = False) -> admit.Host:
    """Return a host with an injected load, one CPU, and a fixed default total.

    Returns:
        the host.

    """
    return admit.Host(loadavg=_busy if busy else _quiet, nproc=_NPROC,
                      default_total=_default_total)


def _env(ledger: Path, **extra: str) -> dict[str, str]:
    """Return a minimal environment naming `ledger`, plus `extra`.

    Returns:
        the environment.

    """
    return {"MEMBUDGET_FILE": str(ledger), "HOME": str(ledger.parent),
            "PATH": os.environ.get("PATH", ""), **extra}


def _ctx(ledger: Path, *, busy: bool = False, **extra: str) -> membudget_cli.Context:
    """Return a context over `ledger` with a quiet (or busy) injected host.

    Returns:
        the context.

    """
    return membudget_cli.Context(env=_env(ledger, **extra), host=_host(busy=busy))


def _write(ledger: Path, text: str) -> None:
    """Write ledger text."""
    ledger.write_text(text, encoding="utf-8")


def _me() -> str:
    """Return this process's owner string — a live, same-user owner.

    Returns:
        `pid:starttime`.

    """
    return admit.owner_of(os.getpid())


def _cli(argv: list[str], ctx: membudget_cli.Context) -> int:
    """Run the console script's `main`.

    Returns:
        its exit code.

    """
    return membudget_cli.main(argv, ctx)


def _ids(ledger: Path) -> tuple[int | None, list[str]]:
    """Return the ledger's total and its lease ids.

    Returns:
        (total, ids).

    """
    snap = admit.Store(ledger).read()
    return snap.total_mb, [lease.lease_id for lease in snap.leases]


def _unfenced(cmd: Sequence[str], caps: core.Caps | None = None,
              env: Mapping[str, str] | None = None) -> core.Result:
    """Run `cmd` in `env` with NO fence — `core.run_once`'s shape, for the admission arms.

    Returns:
        the result: the command's code as a shell reports it, and nothing measured.

    """
    try:
        pid = os.posix_spawnp(cmd[0], list(cmd), dict(env or {}))
    except FileNotFoundError:
        code = core.EXIT_NOT_FOUND
    else:
        code = os.waitstatus_to_exitcode(os.waitpid(pid, 0)[1])
        code = _SIGNAL_BASE - code if code < 0 else code
    return core.Result(cmd=tuple(cmd), caps=caps or core.Caps(), duration_s=0.0,
                       exit_code=code, memory_peak_bytes=None)


@pytest.fixture()
def ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return a ledger path under `tmp_path`, with no inherited parent lease and no real fence.

    ⚑ `core.run_once` IS REPLACED BY `_unfenced` HERE, so the admission arms run on a host with no
    delegated cgroup; the cap's own arms use `fenced_ledger`, which keeps the real fence.

    Returns:
        the path, not yet created.

    """
    monkeypatch.delenv(admit.ENV_PARENT, raising=False)
    monkeypatch.setattr(core, "run_once", _unfenced)
    return tmp_path / "budget.cotype"


@pytest.fixture()
def fenced_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return a ledger path under `tmp_path`, with no inherited parent lease and the real fence.

    Returns:
        the path, not yet created.

    """
    monkeypatch.delenv(admit.ENV_PARENT, raising=False)
    return tmp_path / "budget.cotype"


# --- the pure half ---

def test_run_args_parse_size_label_and_command() -> None:
    """`run 300 job -- a b` reads 300, `job` and the command `a b`."""
    call = membudget_cli.RunArgs.parse(["300", "job", "--", "a", "b"])
    assert call == membudget_cli.RunArgs(_HELD, "job", ("a", "b"))


def test_run_label_is_optional() -> None:
    """`run 300 -- a` has an empty label; the control carries one."""
    assert not membudget_cli.RunArgs.parse(["300", "--", "a"]).label
    assert membudget_cli.RunArgs.parse(["300", "x", "--", "a"]).label == "x"


def test_env_maps_onto_waiting_and_the_lock() -> None:
    """NOBLOCK, TIMEOUT, MAXLOAD and LOCK_TIMEOUT land in Waiting and Store; unset is admit's."""
    env = {"MEMBUDGET_NOBLOCK": "1", "MEMBUDGET_TIMEOUT": _TIMEOUT_S,
           "MEMBUDGET_MAXLOAD": _MAXLOAD, "MEMBUDGET_LOCK_TIMEOUT": _LOCK_BOUND_S,
           "MEMBUDGET_FILE": "/x"}
    wait = membudget_cli.waiting_of(env)
    assert wait.noblock
    assert wait.timeout_s is not None
    assert math.isclose(wait.timeout_s, float(_TIMEOUT_S))
    assert math.isclose(wait.maxload, float(_MAXLOAD))
    assert math.isclose(membudget_cli.store_of(env).lock_timeout_s, float(_LOCK_BOUND_S))
    assert membudget_cli.waiting_of({}) == admit.Waiting()


def test_status_renders_as_bash_does() -> None:
    """Totals then one line per lease, top or under its parent; free counts top-level only."""
    snap = admit.Ledger(_TOTAL, (admit.Lease("a", _HELD, "1:2", 0, "-", "job"),
                                 admit.Lease("b", _FITS, "1:2", 0, "a", "kid")), 1)
    assert membudget_cli.render_status(snap) == (
        f"membudget: TOTAL={_TOTAL}MB top-level-leased={_HELD}MB "
        f"global-free={_TOTAL - _HELD}MB\n"
        f"  [a] {_HELD}MB pid=1:2 (top) job\n"
        f"  [b] {_FITS}MB pid=1:2 (under a) kid\n")


# --- usage ---

def test_an_unknown_verb_exits_2(ledger: Path) -> None:
    """An unknown verb and no verb exit 2; the control, `status`, exits 0."""
    assert _cli(["frob"], _ctx(ledger)) == _EXIT_USAGE
    assert _cli([], _ctx(ledger)) == _EXIT_USAGE
    assert _cli(["status"], _ctx(ledger)) == _EXIT_OK


@pytest.mark.parametrize("argv", [["run", "300", "true"], ["run", "300", "--"],
                                  ["run", "lots", "--", "true"], ["run", "300", "a b", "--", "x"],
                                  ["init", "0"], ["init", "--reset"], ["init", "1", "2"],
                                  ["status", "x"]])
def test_a_malformed_invocation_exits_2(ledger: Path, argv: list[str]) -> None:
    """No `--`, no command, a bad MB, a spaced label, or wrong operands exit 2 and write nothing."""
    assert _cli(argv, _ctx(ledger)) == _EXIT_USAGE
    assert not ledger.exists()


def test_a_bad_env_number_exits_2(ledger: Path) -> None:
    """A non-numeric MEMBUDGET_TIMEOUT exits 2; the control, a numeric one, runs."""
    bad = _ctx(ledger, MEMBUDGET_TIMEOUT="soon")
    assert _cli(["run", "1", "--", sys.executable, "-c", ""], bad) == _EXIT_USAGE
    good = _ctx(ledger, MEMBUDGET_TIMEOUT=_TIMEOUT_S)
    assert _cli(["run", "1", "--", sys.executable, "-c", ""], good) == _EXIT_OK


# --- init ---

def test_init_creates_the_total(ledger: Path) -> None:
    """`init 1000` on no file writes TOTAL_MB 1000."""
    assert _cli(["init", str(_TOTAL)], _ctx(ledger)) == _EXIT_OK
    assert _ids(ledger) == (_TOTAL, [])


def test_init_without_a_size_takes_the_default(ledger: Path) -> None:
    """`init` with no MB declares the host's default total."""
    assert _cli(["init"], _ctx(ledger)) == _EXIT_OK
    assert _ids(ledger) == (_DEFAULT_TOTAL, [])


def test_init_never_overwrites_a_total(ledger: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A second `init 2000` leaves 1000 and says so; the control: the first init wrote 1000."""
    _cli(["init", str(_TOTAL)], _ctx(ledger))
    assert _ids(ledger) == (_TOTAL, [])
    assert _cli(["init", str(_OTHER_TOTAL)], _ctx(ledger)) == _EXIT_OK
    assert _ids(ledger) == (_TOTAL, [])
    assert "changes nothing" in capsys.readouterr().out


def test_reset_resizes_and_keeps_a_live_lease(ledger: Path) -> None:
    """`init --reset 2000` sets 2000 and keeps a live lease and bash's `#` header."""
    _write(ledger, f"# header\nTOTAL_MB {_TOTAL}\nLEASE a {_HELD} {_me()} 0 - job\n")
    assert _cli(["init", "--reset", str(_OTHER_TOTAL)], _ctx(ledger)) == _EXIT_OK
    assert _ids(ledger) == (_OTHER_TOTAL, ["a"])
    assert admit.Store(ledger).read().extra == ("# header",)


def test_reset_below_the_leased_warns(ledger: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A reset under the leased total warns over-subscribed; the control, above it, does not."""
    _write(ledger, f"TOTAL_MB {_TOTAL}\nLEASE a {_HELD} {_me()} 0 - job\n")
    _cli(["init", "--reset", str(_OTHER_TOTAL)], _ctx(ledger))
    assert "over-subscribed" not in capsys.readouterr().err
    _cli(["init", "--reset", str(_SMALL_TOTAL)], _ctx(ledger))
    assert "over-subscribed" in capsys.readouterr().err
    assert _ids(ledger) == (_SMALL_TOTAL, ["a"])


def test_reset_refuses_two_totals(ledger: Path) -> None:
    """A ledger with two TOTAL_MB lines exits 4 and is left byte-for-byte."""
    text = f"TOTAL_MB {_TOTAL}\nTOTAL_MB {_OTHER_TOTAL}\n"
    _write(ledger, text)
    assert _cli(["init", "--reset", str(_TOTAL)], _ctx(ledger)) == _EXIT_LEDGER
    assert ledger.read_text(encoding="utf-8") == text


# --- status ---

def test_status_reaps_a_dead_lease(ledger: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A dead owner's lease is dropped; the control, a live owner's, is listed."""
    _write(ledger, f"TOTAL_MB {_TOTAL}\nLEASE dead {_HELD} {_DEAD_OWNER} 0 - gone\n"
                   f"LEASE live {_FITS} {_me()} 0 - here\n")
    assert _cli(["status"], _ctx(ledger)) == _EXIT_OK
    out = capsys.readouterr().out
    assert "[live]" in out
    assert "[dead]" not in out


# --- run ---

def test_run_holds_its_lease_while_the_command_runs(ledger: Path, tmp_path: Path) -> None:
    """The child sees MEMBUDGET_PARENT naming a lease in the ledger; its code is returned."""
    seen = tmp_path / "seen"
    argv = ["run", str(_TINY), "job", "--", sys.executable, "-c", _PROBE, str(seen),
            str(_CHILD_CODE)]
    assert _cli(argv, _ctx(ledger)) == _CHILD_CODE
    lease_id, present = seen.read_text(encoding="utf-8").split(" ")
    assert lease_id
    assert present == "True"


def test_run_releases_its_lease(ledger: Path) -> None:
    """After `run` the ledger holds no lease, and the run created it with the default total."""
    assert _cli(["run", str(_TINY), "--", sys.executable, "-c", ""], _ctx(ledger)) == _EXIT_OK
    assert _ids(ledger) == (_DEFAULT_TOTAL, [])


def test_run_reports_a_signal_as_128_plus_it(ledger: Path) -> None:
    """A child killed by SIGTERM exits 143, as a shell reports it."""
    kill = "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"
    argv = ["run", "1", "--", sys.executable, "-c", kill]
    assert _cli(argv, _ctx(ledger)) == _SIGNAL_BASE + signal.SIGTERM


def test_run_of_a_missing_command_exits_127(ledger: Path) -> None:
    """A command that does not exist exits 127, and its lease is still released."""
    assert _cli(["run", "1", "--", str(ledger.parent / "nope")], _ctx(ledger)) == _EXIT_NOT_FOUND
    assert _ids(ledger) == (_DEFAULT_TOTAL, [])


def test_noblock_over_free_exits_3(ledger: Path) -> None:
    """With 300 of 1000 held, NOBLOCK 800 exits 3 without running; the control, 400, runs."""
    _write(ledger, f"TOTAL_MB {_TOTAL}\nLEASE a {_HELD} {_me()} 0 - job\n")
    marker = ledger.parent / "ran"
    touch = [sys.executable, "-c", f"open({str(marker)!r}, 'w')"]
    ctx = _ctx(ledger, MEMBUDGET_NOBLOCK="1")
    assert _cli(["run", str(_OVER_FREE), "--", *touch], ctx) == _EXIT_REFUSED
    assert not marker.exists()
    assert _cli(["run", str(_FITS), "--", *touch], ctx) == _EXIT_OK
    assert marker.exists()


def test_timeout_gives_up_with_3(ledger: Path) -> None:
    """A tiny MEMBUDGET_TIMEOUT over free gives up with 3; the control, a fit, runs."""
    _write(ledger, f"TOTAL_MB {_TOTAL}\nLEASE a {_HELD} {_me()} 0 - job\n")
    ctx = _ctx(ledger, MEMBUDGET_TIMEOUT=_TINY_TIMEOUT_S)
    assert _cli(["run", str(_OVER_FREE), "--", "true"], ctx) == _EXIT_REFUSED
    assert _cli(["run", str(_FITS), "--", "true"], ctx) == _EXIT_OK


def test_impossible_exits_3_and_no_total_exits_4(ledger: Path) -> None:
    """Over the total is 3; a file with no total is 4; the control, within the total, is 0."""
    _write(ledger, f"TOTAL_MB {_TOTAL}\n")
    assert _cli(["run", str(_OTHER_TOTAL), "--", "true"], _ctx(ledger)) == _EXIT_REFUSED
    assert _cli(["run", str(_HELD), "--", "true"], _ctx(ledger)) == _EXIT_OK
    _write(ledger, "# no total\n")
    assert _cli(["run", str(_HELD), "--", "true"], _ctx(ledger)) == _EXIT_LEDGER


def test_a_busy_load_holds_run_back(ledger: Path) -> None:
    """Under a busy injected load NOBLOCK exits 3; the control, MAXLOAD=0, runs."""
    _write(ledger, f"TOTAL_MB {_TOTAL}\n")
    busy = _ctx(ledger, busy=True, MEMBUDGET_NOBLOCK="1")
    assert _cli(["run", "1", "--", "true"], busy) == _EXIT_REFUSED
    off = _ctx(ledger, busy=True, MEMBUDGET_NOBLOCK="1", MEMBUDGET_MAXLOAD="0")
    assert _cli(["run", "1", "--", "true"], off) == _EXIT_OK


def test_a_held_lock_exits_1(ledger: Path) -> None:
    """With the lock held past MEMBUDGET_LOCK_TIMEOUT, `status` exits 1; released, it exits 0."""
    ctx = _ctx(ledger, MEMBUDGET_LOCK_TIMEOUT=_LOCK_BOUND_S)
    with admit.Store(ledger).locked():
        assert _cli(["status"], ctx) == _EXIT_LOCK
    assert _cli(["status"], ctx) == _EXIT_OK


# --- run caps its command at its lease (R1) ---

def _unfenceable() -> str:
    """Return why this host cannot fence, or the empty string when it can — as test_fence does.

    Returns:
        the reason, or "".

    """
    try:
        parent_with_controllers(["memory", "pids"])
    except FenceUnavailableError as e:
        return f"cannot fence here: {e}"
    return ""


_WHY = _unfenceable()
needs_cgroup = pytest.mark.skipif(bool(_WHY), reason=_WHY or "host can fence")


def _hog(mb: int) -> list[str]:
    """Return a command that really touches `mb` MB — a bytes product writes every page.

    Returns:
        the argv.

    """
    return [sys.executable, "-c", f"s = b'x' * ({mb} * 1024 * 1024)"]


@needs_cgroup
def test_run_kills_a_payload_over_its_lease(
        fenced_ledger: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A 256MB payload under a 64MB lease is killed by the cap: 137, and stderr says so."""
    argv = ["run", str(_CAP_MB), "hog", "--", *_hog(_HOG_OVER_MB)]
    assert _cli(argv, _ctx(fenced_ledger)) == _SIGKILLED
    assert f"OOM-killed at {_CAP_MB}MB [hog]" in capsys.readouterr().err
    assert _ids(fenced_ledger) == (_DEFAULT_TOTAL, [])


@needs_cgroup
def test_run_under_its_lease_completes(
        fenced_ledger: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The positive control: a 16MB payload under a 256MB lease completes with 0, unkilled."""
    argv = ["run", str(_ROOM_MB), "fits", "--", *_hog(_HOG_UNDER_MB)]
    assert _cli(argv, _ctx(fenced_ledger)) == _EXIT_OK
    assert "OOM-killed" not in capsys.readouterr().err


def test_run_without_a_fence_refuses_3(
        ledger: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With no cgroup `run` exits 3, never starts the command, and releases its lease."""
    def unavailable(*_args: object) -> core.Result:
        raise FenceUnavailableError(_WHY or "no delegated cgroup")

    monkeypatch.setattr(core, "run_once", unavailable)
    marker = ledger.parent / "ran"
    argv = ["run", str(_TINY), "--", sys.executable, "-c", f"open({str(marker)!r}, 'w')"]
    assert _cli(argv, _ctx(ledger)) == _EXIT_REFUSED
    assert not marker.exists()
    assert _ids(ledger) == (_DEFAULT_TOTAL, [])


def test_the_cap_is_the_lease_with_swap_forbidden(
        ledger: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`run 64` fences at memory 64M and swap 0 — `autosize.rung_caps`, restated nowhere."""
    seen: list[core.Caps] = []

    def recording(cmd: Sequence[str], caps: core.Caps | None = None,
                  env: Mapping[str, str] | None = None) -> core.Result:
        seen.append(caps or core.Caps())
        return _unfenced(cmd, caps, env)

    monkeypatch.setattr(core, "run_once", recording)
    assert _cli(["run", str(_CAP_MB), "--", "true"], _ctx(ledger)) == _EXIT_OK
    assert seen == [core.Caps(mem=f"{_CAP_MB}M", swap="0")]


# --- the run ledger, and `auto` sized from it (R2) ---

def _runs(ledger: Path) -> Path:
    """Return the run ledger bash would use beside `ledger`.

    Returns:
        `labels.tsv` in `ledger`'s directory.

    """
    return ledger.parent / _RUNS_NAME


def _seed(ledger: Path, label: str, *peaks: float) -> None:
    """Write one clean-run row per peak for `label` into the run ledger beside `ledger`."""
    rows = [run_ledger.Row(label, 1.0, peak, 0) for peak in peaks]
    _runs(ledger).write_text("".join(row.line() + "\n" for row in rows), encoding="utf-8")


def _leased(ledger: Path, label: str, **extra: str) -> tuple[int, str]:
    """Run `run auto LABEL` over a large pool; return its code and the lease MB its child saw.

    Returns:
        the exit code, and the MB (empty when the child never ran).

    """
    if not ledger.exists():
        _write(ledger, f"TOTAL_MB {_POOL_MB}\n")
    seen = ledger.parent / "leased"
    seen.unlink(missing_ok=True)
    argv = ["run", "auto", label, "--", sys.executable, "-c", _LEASE_PROBE, str(seen)]
    code = _cli(argv, membudget_cli.Context(env=_env(ledger, **extra), host=_host()))
    return code, seen.read_text(encoding="utf-8") if seen.exists() else ""


def test_auto_sizes_from_a_seeded_ledger(ledger: Path) -> None:
    """Peaks (40, 188, 90) for `job` lease 256 — the bucket of the max, from the run ledger."""
    _seed(ledger, "job", *_SEEDED_PEAKS)
    assert _leased(ledger, "job") == (_EXIT_OK, str(_SEEDED_LEASE))


def test_auto_with_no_history_takes_the_default(ledger: Path) -> None:
    """With no history `auto` leases bash's 192; the control, AGDA_MB_DEFAULT=100, leases 100."""
    assert _leased(ledger, "fresh") == (_EXIT_OK, str(_BASH_DEFAULT_MB))
    own = _leased(ledger, "fresh", AGDA_MB_DEFAULT=str(_OWN_DEFAULT_MB))
    assert own == (_EXIT_OK, str(_OWN_DEFAULT_MB))


def test_auto_passes_the_ceiling_and_it_clamps(
        ledger: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A 600MB peak leases 384 under AGDA_MB_MAX=384 and warns; under 2048 it leases 1024."""
    _seed(ledger, "heavy", _BIG_PEAK)
    clamped = _leased(ledger, "heavy", AGDA_MB_MAX=str(_CEILING_MB))
    assert clamped == (_EXIT_OK, str(_CEILING_MB))
    assert "BELOW the measured need" in capsys.readouterr().err
    wide = _leased(ledger, "heavy", AGDA_MB_MAX=str(_WIDE_CEILING_MB))
    assert wide == (_EXIT_OK, str(_BIG_BUCKET))
    assert "BELOW" not in capsys.readouterr().err


def test_auto_rejects_a_malformed_ceiling(ledger: Path) -> None:
    """AGDA_MB_MAX=lots is a usage error, 2; the control, an unset one, runs."""
    assert _leased(ledger, "x", AGDA_MB_MAX="lots") == (_EXIT_USAGE, "")
    assert _leased(ledger, "x")[0] == _EXIT_OK


def test_a_clean_run_is_recorded_and_a_failed_one_is_not(ledger: Path) -> None:
    """Exit 0 appends one row under its label; exit 1 appends none; unlabelled records as `?`."""
    ctx = _ctx(ledger)
    assert _cli(["run", "1", "rec", "--", "true"], ctx) == _EXIT_OK
    assert _cli(["run", "1", "rec", "--", "false"], ctx) != _EXIT_OK
    assert _cli(["run", "1", "--", "true"], ctx) == _EXIT_OK
    rows = run_ledger.parse(_runs(ledger).read_text(encoding="utf-8"))
    assert [row.label for row in rows] == ["rec", _UNLABELLED]


def test_the_run_ledger_honours_its_path_and_opt_out(ledger: Path, tmp_path: Path) -> None:
    """MEMBUDGET_LABEL_LEDGER moves the ledger; MEMBUDGET_NOLABELLEDGER=1 writes none at all."""
    moved = tmp_path / "elsewhere.tsv"
    assert _cli(["run", "1", "a", "--", "true"],
                _ctx(ledger, MEMBUDGET_LABEL_LEDGER=str(moved))) == _EXIT_OK
    assert [row.label for row in run_ledger.parse(moved.read_text(encoding="utf-8"))] == ["a"]
    assert _cli(["run", "1", "b", "--", "true"],
                _ctx(ledger, MEMBUDGET_NOLABELLEDGER="1")) == _EXIT_OK
    assert not _runs(ledger).exists()


# --- lease and deadline ---

def test_lease_and_deadline_answer_through_label_lease(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """With no history `lease` prints the default MB and `deadline` the default seconds."""
    runs = str(tmp_path / "labels.tsv")
    ctx = _ctx(tmp_path / "unused")
    assert _cli(["lease", runs, "x", _LABEL_DEFAULT_MB, _LABEL_CEILING_MB], ctx) == _EXIT_OK
    assert _cli(["deadline", runs, "x", _GUARD_DEFAULT_S, _GUARD_CEILING_S], ctx) == _EXIT_OK
    assert capsys.readouterr().out == f"{_LABEL_DEFAULT_MB}\n{_GUARD_DEFAULT_S}\n"
    assert _cli(["lease", runs], ctx) == _EXIT_USAGE


# --- retry-on-OOM (R3) and the per-module `.agda` key (R5), through the fence seam ---

# The climb: a start rung, the rung above it, a payload that needs the upper one, and one that
# needs more than any rung the ceiling allows.
_RUNG_LOW = 64
_RUNG_HIGH = 128
_NEEDS_HIGH = 100
_NEEDS_TOO_MUCH = 1024

# A peak the fake reports for a clean run, in KB, and the whole MB the ledger rounds it to.
_CLEAN_RSS_KB = 90 * 1024
_CLEAN_PEAK_MB = 90.0

# The cgroup verdict `autosize.killed_by_cap` reads as the cap's kill.
_CAP_KILL = ("MEMORY, KILLED (memory.events oom_kill=1 oom=1) — simulated",)

# A module's ledger, as bash's `_record_time` writes it beside the module; the peaks it holds for
# a heavy and a light module, and the light label peak a label-keyed lease would take instead.
_MODULE_LEDGER = ".agda-times.tsv"
_HEAVY_MODULE = "Heavy.agda"
_LIGHT_MODULE = "Light.agda"
_CORE_MODULE = "Heavy.agdai"
_LABEL_PEAK = 40.0


@dataclass
class _OomFence:
    """A fence that kills any rung below `need_mb` as the cap would, and records every call."""

    ledger: Path
    need_mb: int
    calls: list[tuple[int, int]]

    def __call__(self, cmd: Sequence[str], env: Mapping[str, str],
                 caps: core.Caps) -> core.Result:
        """Record (rung MB, live leases), then kill below `need_mb` or exit clean.

        Returns:
            the simulated result.

        """
        del env
        mb = int((caps.mem or "0M").removesuffix("M"))
        self.calls.append((mb, len(admit.Store(self.ledger).read().leases)))
        if mb < self.need_mb:
            return core.Result(cmd=tuple(cmd), caps=caps, duration_s=0.0,
                               exit_code=_SIGKILLED, memory_peak_bytes=None,
                               bound_by=_CAP_KILL)
        return core.Result(cmd=tuple(cmd), caps=caps, duration_s=1.0, exit_code=_EXIT_OK,
                           memory_peak_bytes=None, maxrss_kb=_CLEAN_RSS_KB)


def _oom_ctx(ledger: Path, need_mb: int, **extra: str) -> tuple[membudget_cli.Context, _OomFence]:
    """Return a quiet context over a large pool whose fence is an `_OomFence`, and that fence.

    Returns:
        the context and the fence.

    """
    if not ledger.exists():
        _write(ledger, f"TOTAL_MB {_POOL_MB}\n")
    fake = _OomFence(ledger, need_mb, [])
    return membudget_cli.Context(env=_env(ledger, **extra), host=_host(), fence=fake), fake


def test_retry_off_leaves_a_cap_kill_at_137(ledger: Path) -> None:
    """Without MEMBUDGET_RETRY_OOM a cap kill is 137 after one rung; the control, set, climbs."""
    argv = ["run", str(_RUNG_LOW), "job", "--", "agda"]
    ctx, fake = _oom_ctx(ledger, _NEEDS_HIGH)
    assert _cli(argv, ctx) == _SIGKILLED
    assert [mb for mb, _ in fake.calls] == [_RUNG_LOW]
    ctx, fake = _oom_ctx(ledger, _NEEDS_HIGH, MEMBUDGET_RETRY_OOM="1")
    assert _cli(argv, ctx) == _EXIT_OK


def test_retry_climbs_to_the_next_bucket_and_records_it(
        ledger: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A kill at 64 re-enters at 128, which exits 0, and only that clean rung is recorded."""
    ctx, fake = _oom_ctx(ledger, _NEEDS_HIGH, MEMBUDGET_RETRY_OOM="1")
    assert _cli(["run", str(_RUNG_LOW), "job", "--", "agda"], ctx) == _EXIT_OK
    assert [mb for mb, _ in fake.calls] == [_RUNG_LOW, _RUNG_HIGH]
    assert f"retrying at {_RUNG_HIGH}MB" in capsys.readouterr().err
    rows = run_ledger.parse(_runs(ledger).read_text(encoding="utf-8"))
    assert [(row.label, row.peak_mb) for row in rows] == [("job", _CLEAN_PEAK_MB)]


def test_retry_stops_at_the_ceiling_with_137(ledger: Path) -> None:
    """Under AGDA_MB_MAX=128 a payload needing 1024 is killed at 64 then 128, and exits 137."""
    ctx, fake = _oom_ctx(ledger, _NEEDS_TOO_MUCH, MEMBUDGET_RETRY_OOM="1",
                         AGDA_MB_DEFAULT=str(_RUNG_LOW), AGDA_MB_MAX=str(_RUNG_HIGH))
    assert _cli(["run", str(_RUNG_LOW), "job", "--", "agda"], ctx) == _SIGKILLED
    assert [mb for mb, _ in fake.calls] == [_RUNG_LOW, _RUNG_HIGH]
    assert not _runs(ledger).exists()


def test_retry_holds_one_lease_at_a_time(ledger: Path) -> None:
    """Every rung runs under exactly one live lease, and none is left after the climb."""
    ctx, fake = _oom_ctx(ledger, _NEEDS_TOO_MUCH, MEMBUDGET_RETRY_OOM="1",
                         AGDA_MB_MAX=str(_NEEDS_TOO_MUCH))
    assert _cli(["run", str(_RUNG_LOW), "job", "--", "agda"], ctx) == _EXIT_OK
    assert [live for _, live in fake.calls] == [1] * len(fake.calls)
    assert len(fake.calls) > 1
    assert _ids(ledger) == (_POOL_MB, [])


def _modules(tmp_path: Path) -> Path:
    """Write a module ledger, as bash writes it, holding a 600MB heavy and a 40MB light module.

    Returns:
        the directory the modules and their ledger live in.

    """
    src = tmp_path / "src"
    src.mkdir()
    (src / _MODULE_LEDGER).write_text(
        f"{_HEAVY_MODULE}\t12.0\t{_BIG_PEAK:g}\n{_LIGHT_MODULE}\t1.0\t{_LABEL_PEAK:g}\n",
        encoding="utf-8")
    return src


def test_auto_sizes_an_agda_compile_from_its_module(ledger: Path, tmp_path: Path) -> None:
    """`auto` on `Heavy.agda` leases the bucket of that module's 600MB, not its label's 40MB."""
    src = _modules(tmp_path)
    _seed(ledger, "agda", _LABEL_PEAK)
    argv = ["run", "auto", "agda", "--", "agda", "-c", str(src / _HEAVY_MODULE)]
    ctx, fake = _oom_ctx(ledger, 0, AGDA_MB_MAX=str(_WIDE_CEILING_MB))
    assert _cli(argv, ctx) == _EXIT_OK
    assert fake.calls == [(_BIG_BUCKET, 1)]


def test_a_clean_agda_run_records_to_its_module(ledger: Path, tmp_path: Path) -> None:
    """A clean `Light.agda` run appends a `Light.agda` row beside it, and none to the labels."""
    src = _modules(tmp_path)
    ctx, _ = _oom_ctx(ledger, 0)
    assert _cli(["run", "1", "agda", "--", "agda", str(src / _LIGHT_MODULE)], ctx) == _EXIT_OK
    rows = run_ledger.parse((src / _MODULE_LEDGER).read_text(encoding="utf-8"))
    assert [(row.label, row.peak_mb) for row in rows] == [(_LIGHT_MODULE, _CLEAN_PEAK_MB)]
    assert not _runs(ledger).exists()


def test_a_non_agda_command_keeps_the_label_path(ledger: Path, tmp_path: Path) -> None:
    """No module argument leases the label's bucket; a `.agdai` argument leases its module's."""
    src = _modules(tmp_path)
    (src / _MODULE_LEDGER).write_text(f"{_CORE_MODULE}\t12.0\t{_BIG_PEAK:g}\n", encoding="utf-8")
    _seed(ledger, "ingest", *_SEEDED_PEAKS)
    ctx, fake = _oom_ctx(ledger, 0, AGDA_MB_MAX=str(_WIDE_CEILING_MB))
    plain = ["run", "auto", "ingest", "--", "ingest", str(src / "notes.txt")]
    core_arg = ["run", "auto", "ingest", "--", "ingest", str(src / _CORE_MODULE)]
    assert _cli(plain, ctx) == _EXIT_OK
    assert _cli(core_arg, ctx) == _EXIT_OK
    assert [mb for mb, _ in fake.calls] == [_SEEDED_LEASE, _BIG_BUCKET]


# --- the cross-client arm: bash `membudget` on the same ledger ---

@dataclass(frozen=True, slots=True)
class _Bash:
    """Bash's client, copied under `tmp_path`, and the ledger it shares with this one."""

    home: Path
    ledger: Path

    def env(self, **extra: str) -> dict[str, str]:
        """Return bash's environment: the shared ledger, the stub backend, no load gate.

        Returns:
            the environment, with every inherited MEMBUDGET_* variable removed.

        """
        base = {key: value for key, value in os.environ.items()
                if not key.startswith("MEMBUDGET_")}
        return {**base, "PATH": f"{self.home}:{base.get('PATH', '')}",
                "MEMBUDGET_FILE": str(self.ledger), "MEMBUDGET_BACKEND": "systemd",
                "MEMBUDGET_NOLABELLEDGER": "1", "MEMBUDGET_MAXLOAD": "0", **extra}

    def start(self, args: Sequence[str], env: Mapping[str, str], out: Path) -> int:
        """Spawn bash's `membudget` in a process group of its own, stdout to `out`.

        ⚑ STDOUT IS SWAPPED AROUND THE SPAWN, NOT PASSED AS A FILE ACTION (typeshed types those as
        `Any`): the child inherits fd 1 as it stands at spawn, and this process's is restored.

        Returns:
            its pid.

        """
        argv = [str(self.home / "membudget"), *args]
        target = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        saved = os.dup(1)
        try:
            os.dup2(target, 1)
            return os.posix_spawn(argv[0], argv, dict(env), setpgroup=0)
        finally:
            os.dup2(saved, 1)
            os.close(saved)
            os.close(target)

    def run(self, args: Sequence[str], **extra: str) -> tuple[int, str]:
        """Run bash's `membudget` to completion, killing it past `_WAIT_S`.

        Returns:
            its exit code and its stdout.

        """
        out = self.ledger.with_name(f"out.{time.monotonic_ns()}")
        pid = self.start(args, self.env(**extra), out)
        deadline = time.monotonic() + _WAIT_S
        while True:
            done, status = os.waitpid(pid, os.WNOHANG)
            if done:
                return os.waitstatus_to_exitcode(status), out.read_text(encoding="utf-8")
            if time.monotonic() >= deadline:
                os.killpg(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
                pytest.fail(f"bash membudget {args} ran past {_WAIT_S}s")
            time.sleep(_POLL_S)


@pytest.fixture()
def bash(tmp_path: Path, ledger: Path) -> _Bash:
    """Copy bash's client and a stub `systemd-run` under `tmp_path`, or skip saying why.

    ⚑ COPIED, NOT RUN IN PLACE: bash resolves helpers beside itself and would build `sched-batch`
    there; a copy without that source builds nothing and writes nothing in substrate.

    Returns:
        the client.

    """
    missing = [name for name in _BASH_FILES if not (_BASH_DIR / name).is_file()]
    tools = [tool for tool in ("bash", "flock", "awk") if shutil.which(tool) is None]
    if missing or tools:
        pytest.skip(f"cross-client arm needs substrate's bash membudget in {_BASH_DIR} "
                    f"(missing: {missing}) and bash, flock, awk on PATH (missing: {tools})")
    home = tmp_path / "bash"
    home.mkdir()
    for name in _BASH_FILES:
        shutil.copy2(_BASH_DIR / name, home / name)
    stub = home / "systemd-run"
    stub.write_text("#!/bin/bash\n"
                    'while [ $# -gt 0 ]; do case "$1" in\n'
                    '  --setenv=*) export "${1#--setenv=}"; shift ;;\n'
                    "  -p) shift 2 ;; --*) shift ;; *) break ;;\n"
                    'esac; done\nexec "$@"\n', encoding="utf-8")
    stub.chmod(0o755)
    return _Bash(home, ledger)


def _await_label(ledger: Path, label: str) -> admit.Lease:
    """Poll the ledger until a lease with `label` appears, or fail after `_WAIT_S`.

    Returns:
        the lease.

    """
    deadline = time.monotonic() + _WAIT_S
    while time.monotonic() < deadline:
        found = [lease for lease in admit.Store(ledger).read().leases if lease.label == label]
        if found:
            return found[0]
        time.sleep(_POLL_S)
    pytest.fail(f"no lease labelled {label} appeared in {ledger}")


@pytest.fixture()
def bash_lease(bash: _Bash) -> Iterator[admit.Lease]:
    """Hold a bash `run 300 bashjob -- sleep` lease on a 1000 MB ledger; kill it afterwards.

    Yields:
        the bash-written lease, as this client parses it.

    """
    assert bash.run(["init", str(_TOTAL)])[0] == _EXIT_OK
    args = ["run", str(_HELD), "bashjob", "--", "sleep", str(int(_WAIT_S * 3))]
    pid = bash.start(args, bash.env(), bash.ledger.with_name("bashjob.out"))
    try:
        yield _await_label(bash.ledger, "bashjob")
    finally:
        os.killpg(pid, signal.SIGKILL)
        os.waitpid(pid, 0)


def test_cross_python_reads_bash_init(bash: _Bash) -> None:
    """Bash `init 1000` reads as 1000 here; a python reset to 2000 is what bash's status prints."""
    assert bash.run(["init", str(_TOTAL)])[0] == _EXIT_OK
    assert _ids(bash.ledger) == (_TOTAL, [])
    assert _cli(["init", "--reset", str(_OTHER_TOTAL)], _ctx(bash.ledger)) == _EXIT_OK
    assert f"TOTAL={_OTHER_TOTAL}MB" in bash.run(["status"])[1]


def test_cross_bash_honours_a_python_lease(bash: _Bash) -> None:
    """Under a live python 300 of 1000, bash NOBLOCK 800 exits 3; the control, bash 400, runs."""
    _cli(["init", str(_TOTAL)], _ctx(bash.ledger))
    with admit.admit(admit.Store(bash.ledger), admit.Request(_HELD, "pyjob"), host=_host()):
        code, status = bash.run(["status"])
        assert code == _EXIT_OK
        assert f"global-free={_TOTAL - _HELD}MB" in status
        assert "pyjob" in status
        over = bash.run(["run", str(_OVER_FREE), "over", "--", "true"], MEMBUDGET_NOBLOCK="1")
        assert over[0] == _EXIT_REFUSED
        fits = bash.run(["run", str(_FITS), "fits", "--", "true"], MEMBUDGET_NOBLOCK="1")
        assert fits[0] == _EXIT_OK


def test_cross_python_honours_a_bash_lease(ledger: Path, bash_lease: admit.Lease) -> None:
    """Under a live bash 300 of 1000, python NOBLOCK 800 exits 3; the control, 400, runs."""
    assert admit.alive(bash_lease.owner)
    ctx = _ctx(ledger, MEMBUDGET_NOBLOCK="1")
    assert _cli(["run", str(_OVER_FREE), "--", "true"], ctx) == _EXIT_REFUSED
    assert _cli(["run", str(_FITS), "--", "true"], ctx) == _EXIT_OK


def test_cross_python_reset_keeps_a_bash_lease(ledger: Path, bash_lease: admit.Lease) -> None:
    """A python `init --reset` under a live bash lease keeps that lease."""
    assert _cli(["init", "--reset", str(_OTHER_TOTAL)], _ctx(ledger)) == _EXIT_OK
    assert _ids(ledger) == (_OTHER_TOTAL, [bash_lease.lease_id])


def test_cross_bash_init_keeps_a_python_lease(bash: _Bash) -> None:
    """Bash `init 2000` over a python lease changes nothing; bash `--reset` resizes and keeps it."""
    _cli(["init", str(_TOTAL)], _ctx(bash.ledger))
    store = admit.Store(bash.ledger)
    with admit.admit(store, admit.Request(_HELD, "pyjob"), host=_host()) as lease:
        assert bash.run(["init", str(_OTHER_TOTAL)])[0] == _EXIT_OK
        assert _ids(bash.ledger) == (_TOTAL, [lease.lease_id])
        assert bash.run(["init", "--reset", str(_OTHER_TOTAL)])[0] == _EXIT_OK
        assert _ids(bash.ledger) == (_OTHER_TOTAL, [lease.lease_id])
