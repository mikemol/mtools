# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-membudget`: bash's verbs and exit codes over `admit`, then one ledger shared with bash.

⚑ EVERY ARM USES A LEDGER UNDER `tmp_path`, named through `MEMBUDGET_FILE` in an explicit
environment — never the host's `~/.cache/membudget`. ⚑ `run` READS A QUIET, INJECTED LOAD: the
default `Host` reads the real loadavg, which hangs a waiter on a busy box.

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

from mikemol.fence import admit, membudget_cli

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


@pytest.fixture()
def ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return a ledger path under `tmp_path`, with no inherited parent lease.

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
