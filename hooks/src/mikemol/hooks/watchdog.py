# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-watchdog`: exit when a session has gone quiet while it has work to do (W1474, W1476).

    mikemol-watchdog --state .claude/paths-forward.json [--writer PATH] [--poll-s S] [--phi-fire P]

Run it as a background task (`run_in_background`): the harness tells the session when a background
process exits, and that exit is the whole alarm. It reads the heartbeat the tools leave
(`hooks/heartbeat.py`, written by `mikemol-commit`, `mikemol-scratch` and the paths-forward writer),
and when the silence since the last beat passes the repo's own limit it asks the writer how many
ready cards are waiting. Cards waiting: it prints one line and exits with `EXIT_IDLE`. None: the
session is really blocked, the watchdog notes it and goes on watching.

⚑ THE LIMIT IS LEARNED AND BOUNDED (operator, 2026-10-17: "closer to a 5-10m cadence, with the cron
30m cadence as the fallback"). The suspicion model `phi(t) = t / (mean * ln 10)` picks the moment,
`phi_fire` being the level (1.0 is a silence that happens one time in ten), and the moment is held
inside `MIN_FIRE_S` to `MAX_FIRE_S`: a repo whose beats come every ten seconds is not woken after
twenty-three, and one with no history, or a long mean, is woken by twenty minutes at the latest.

⚑ THE WINDOW MOVED FROM 5-10 TO 10-20 MINUTES (operator, 2026-10-19, host session 695f3e0a line
86716, uuid 80e5bd9d: "let's take the watchdog from 10m to 20m, with the loop still at 30m"). The
floor moved with the ceiling to keep the window's shape (github-8f); the cron loop stays the
fallback at thirty minutes.

⚑ NO DEADLINE ON THE WATCH. The poll interval paces the reads and decides nothing. The only ends are
the alarm, and the parent going away: a watchdog that outlives its session is an orphan.

⚑ ITS OWN QUESTION IS NOT A BEAT. The ready count goes through the writer's `--ready-count`, which
does not beat (a beat is the SESSION's own action), so asking never resets the silence it measures.

CONSUMED BY: `--tick-open`, which prints the command to start it (W1476).
"""

import argparse
import contextlib
import math
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from mikemol.hooks import heartbeat
from mikemol.hooks.commit_span import binary, store_named
from mikemol.hooks.heartbeat import Beat
from mikemol.hooks.vlogdetach import spawn_detached

EXIT_IDLE = 8
EXIT_CANNOT_RUN = 7
MIN_FIRE_S = 600.0
MAX_FIRE_S = 1200.0
DEFAULT_PHI_FIRE = 1.0
DEFAULT_POLL_S = 20.0
ARMED_EVERY_POLLS = 3
ARMED_NAME = "mikemol.watchdog.armed"
ARMED_UP = "1"
ARMED_DOWN = "0"
DETACHED: Callable[[Sequence[str]], None] = spawn_detached
"""The sender of a sample the store does not wait for: a detached `mikemol-otlp metric`."""
SERVICE = "mikemol-watchdog"
_NS_PER_S = 1_000_000_000
_PROBE = 0

Seams = tuple[
    Callable[[], Beat | None],
    Callable[[], int | None],
    Callable[[], int],
    Callable[[float], None],
    Callable[[], bool],
]
"""(read the beat, count ready cards, now in ns, sleep, is the parent still alive)."""


def silence_limit_s(last: Beat, phi_fire: float) -> float:
    """Say how long a silence after `last` may run before the watchdog asks about work.

    Returns:
        the silence at which the suspicion reaches `phi_fire`, held between `MIN_FIRE_S` and
        `MAX_FIRE_S`; `MAX_FIRE_S` when too few gaps are recorded to learn a mean.

    """
    mean = heartbeat.mean_gap_s(last)
    if mean is None:
        return MAX_FIRE_S
    return min(max(phi_fire * mean * math.log(10), MIN_FIRE_S), MAX_FIRE_S)


def idle_line(waiting: int, last: Beat, now_ns: int, bound_s: float | None = None) -> str:
    """Spell the one line the alarm prints.

    ⚑ THE LINE GIVES THE REASON (luthen via github-8f, 2026-10-18, W1617): an exit 8 that said only
    that cards were waiting could not be told from one that fired on too little silence, so it also
    names the bound it crossed when it has one.

    Returns:
        `idle with N ready cards, last heartbeat Ts ago (tool)`, then `; bound Bs` when given.

    """
    ago = max(now_ns - last.at_ns, 0) // _NS_PER_S
    said = f"idle with {waiting} ready cards, last heartbeat {ago}s ago ({last.tool})"
    return said if bound_s is None else f"{said}; bound {bound_s:.0f}s"


def next_action(stackable: str, drafts: str) -> str:
    """Name one concrete thing to do now, from nemik-stackable's rows and its drafted manifests.

    ⚑ AN IDLE ALARM THAT ONLY RESTATES ITSELF IS A WASTED REMINDER (github-8f for the operator,
    2026-10-18, W1591): it carries its own content, the first stackable card and the first ready
    leaf with no manifest that a manifest can be drafted for.

    Returns:
        `next: stack W<n>; atomize W<m>`, either half left out when there is none, "" for neither.

    """
    rows = [ln.split() for ln in stackable.splitlines() if ln.startswith(("STACK", "WAITING"))]
    stack = next((row[1].rpartition(":")[2] for row in rows if row[0] == "STACK"), "")
    leaf = drafts.partition('"symbol": "')[2].partition('"')[0]
    parts = [f"stack {stack}" if stack else "", f"atomize {leaf}" if leaf else ""]
    named = "; ".join(part for part in parts if part)
    return f"next: {named}" if named else ""


def pidfile_of(git_dir: Path) -> Path:
    """Name the file a running watchdog leaves for its repo (W1556).

    Returns:
        `<git dir>/mtools/watchdog.pid`, beside the heartbeat.

    """
    return git_dir / "mtools" / "watchdog.pid"


def claim(git_dir: Path, pid: int) -> None:
    """Record that the watchdog with `pid` is watching this repo.

    ⚑ A PGREP IS NOT A READING OF THIS REPO (github-8f, 2026-10-18): a process list names every
    watchdog on the host, and the one that matters is the one pointed at this state file. The pid
    file is the repo's own record, checked with a signal-0 probe, so a stale file from a killed
    process reads as no watchdog.
    """
    target = pidfile_of(git_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{pid}\n", encoding="utf-8")


def release(git_dir: Path, pid: int) -> None:
    """Remove the pid file, but only if it still names `pid` (a newer watchdog may own it)."""
    target = pidfile_of(git_dir)
    with contextlib.suppress(OSError):
        if target.read_text(encoding="utf-8").strip() == str(pid):
            target.unlink()


def is_alive(pid: int) -> bool:
    """Probe a pid with signal zero.

    Returns:
        True when the process exists (even one this user may not signal), False when it does not.

    """
    try:
        os.kill(pid, _PROBE)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def running(git_dir: Path, alive: Callable[[int], bool] = is_alive) -> bool:
    """Say whether a live watchdog holds this repo's pid file.

    Returns:
        True when the file names a pid the probe finds; False when absent, unreadable or stale.

    """
    try:
        pid = int(pidfile_of(git_dir).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    return alive(pid)


def _nothing() -> None:
    # The default announcement: say nothing, for a caller with no store to tell.
    return None


def armed_publisher(
    env: Mapping[str, str],
    repo: str,
    spawn: Callable[[Sequence[str]], None] = spawn_detached,
    value: str = ARMED_UP,
) -> Callable[[], None]:
    """Build the call that tells the store whether a watchdog is armed for `repo` (W1518, W1558).

    ⚑ AN ARMED GAUGE THAT GOES STALE IS THE MONITOR (operator, 2026-10-17: is there a way to see
    whether the deadman switch is armed for the various sessions?): the watchdog sends
    `mikemol.watchdog.armed{repo}=1` every few polls while it runs, so when it dies the series stops
    and a freshness rule over it, with a recent heartbeat beside it, says a session is active
    and unwatched. The push is a detached `mikemol-otlp metric`, as the commit gauges are.

    ⚑ `value` IS `ARMED_UP` FROM THE WATCHDOG AND `ARMED_DOWN` FROM THE BEAT HOOK (W1558,
    github-8f 2026-10-18): a repo whose watchdog is gone sends no `armed=1`, and a freshness rule
    over a series that stopped cannot tell a dead watchdog from a repo that never had one. The hook
    that notices the absence sends the zero, so the series exists exactly when it matters.

    ⚑ BEST EFFORT, NEVER RAISING: no `mikemol-otlp`, no `MIKEMOL_ENDPOINTS` or a failed start means
    the number is not shipped and the watch goes on, exactly as the commit gauges behave.

    Returns:
        a function that sends one sample, or one that does nothing when there is nowhere to send.

    """
    program = binary(env)
    if program is None or not store_named(env):
        return _nothing
    argv = [program, "metric", "--service", SERVICE, "--namespace", repo]
    argv += ["--field", f"repo={repo}", "--name", ARMED_NAME, "--value", value]

    def publish() -> None:
        with contextlib.suppress(OSError):
            spawn(argv)

    return publish


def _no_hint() -> str:
    return ""


def watch(
    seams: Seams,
    phi_fire: float,
    poll_s: float,
    armed: Callable[[], None] = _nothing,
    hint: Callable[[], str] = _no_hint,
) -> int:
    """Watch until the silence passes the limit with work waiting, or the parent goes away.

    ⚑ NO HEARTBEAT FILE IS A BEAT AT THE WATCHDOG'S OWN START (github-8f, 2026-10-17). A repo whose
    tools are too old to beat has ready cards and no beat at all, which is the strongest stall
    signal there is; reading it as "never beaten, never fire" hid exactly the repos that need the
    alarm. So the silence is counted from the start, the alarm fires after the band with work
    waiting, and one line says no heartbeat source exists, so an old pin shows up instead of hiding.

    ⚑ A BEAT OLDER THAN THE START IS NOT A SILENCE TO FIRE ON (luthen via github-8f, 2026-10-18,
    W1564): the session started this watchdog, which is its own action, so the silence is counted
    from the start whenever the last beat predates it. Otherwise a stale file fires the first poll,
    the session restarts it, it fires again, and nothing watches in between.

    ⚑ THE ALARM CARRIES ITS OWN NEXT ACTION (W1591): after the idle line, `hint` supplies one line
    naming a stackable card and a leaf to atomize, when it has any.

    Returns:
        EXIT_IDLE after printing the idle line; 0 when the parent is gone.

    """
    read, ready, now_ns, sleep, alive = seams
    asked_about: int | None = None
    started = Beat("no heartbeat source", now_ns(), ())
    noted = False
    polls = 0
    while alive():
        if polls % ARMED_EVERY_POLLS == 0:
            armed()
        polls += 1
        last = read()
        if last is None:
            last = started
            if not noted:
                sys.stdout.write("mikemol-watchdog: no heartbeat file: counting from my start\n")
                noted = True
        elif last.at_ns < started.at_ns:
            last = started
        if last.at_ns != asked_about:
            silent_s = (now_ns() - last.at_ns) / _NS_PER_S
            bound_s = silence_limit_s(last, phi_fire)
            if silent_s >= bound_s:
                waiting = ready()
                if waiting:
                    sys.stdout.write(idle_line(waiting, last, now_ns(), bound_s) + "\n")
                    said = hint()
                    if said:
                        sys.stdout.write(said + "\n")
                    return EXIT_IDLE
                asked_about = last.at_ns
        sleep(poll_s)
    return 0


def ready_from(writer: str, state: Path) -> int | None:
    """Ask the writer how many ready cards the queue holds.

    The writer is the one place the count is defined, so this is a question to it, not a reading
    of the queue file.

    Returns:
        the count, or None when the writer cannot run or does not answer with a number.

    """
    try:
        done = subprocess.run(
            [writer, "--state", str(state), "--ready-count"],
            capture_output=True,
            text=True,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except OSError:
        return None
    said = done.stdout.strip()
    return int(said) if done.returncode == 0 and said.isdecimal() else None


STACKABLE_ENV = "MIKEMOL_NEMIK_STACKABLE"
STACKABLE_DEFAULT = Path("github") / "nemik" / ".venv" / "bin" / "nemik-stackable"


def hint_from(repo: str, env: Mapping[str, str]) -> str:
    """Ask nemik-stackable what to do next in `repo`; never raises.

    Returns:
        the line `next_action` builds, or "" when nemik-stackable is not there or does not answer.

    """
    tool = Path(env.get(STACKABLE_ENV) or Path.home() / STACKABLE_DEFAULT)
    if not os.access(tool, os.X_OK):
        return ""
    heard: list[str] = []
    for extra in ([], ["--propose", "--json"]):
        try:
            done = subprocess.run(
                [str(tool), repo, *extra],
                capture_output=True,
                text=True,
                check=False,
                stdin=subprocess.DEVNULL,
            )
        except OSError:
            return ""
        heard.append(done.stdout if done.returncode == 0 else "")
    return next_action(heard[0], heard[1])


def inside_call(git_dir: Path, now_ns: int) -> str:
    """Say when the silence is one tool call that started after the last beat and has not ended.

    ⚑ A DIAGNOSTIC, NOT A SUPPRESSION (github-8f, 2026-10-18, W1617): a session sitting inside one
    foreground call, a gate above all, is a stall by the operator's ruling of 2026-10-17, so the
    watchdog stays right to fire. The line only tells the session why, so it learns to run such a
    call in the background.

    Returns:
        the sentence, or "" when no call-start stamp is newer than the last beat.

    """
    call = heartbeat.read_call(git_dir)
    last = heartbeat.read(git_dir)
    if call is None or (last is not None and call.at_ns <= last.at_ns):
        return ""
    ran = max(now_ns - call.at_ns, 0) // _NS_PER_S
    return (
        f"the silence is inside one call: {call.tool} has run {ran}s; "
        "a gate in the foreground is a stall, so run it in the background and poll"
    )


HINT_NAME = "next-action"
"""The file beside the heartbeat that keeps the last next-action line the watchdog computed."""


def remember_hint(git_dir: Path, line: str) -> None:
    """Keep the next-action line for the beat hook's notice; a refusing file system is no error."""
    target = git_dir / "mtools" / HINT_NAME
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(line, encoding="utf-8")
    except OSError:
        return


def cached_hint(git_dir: Path) -> str:
    """Read the last next-action line the watchdog kept.

    ⚑ THE HOOK ASKS A FILE, NEVER nemik-stackable (W1565): a PostToolUse hook runs inside a tool
    call, and nemik-stackable measured more than a minute for a repo it did not know, so the notice
    reads what the watchdog computed when it last exited, where waiting costs the session nothing.

    Returns:
        the line, or "" when there is none or it cannot be read.

    """
    try:
        return (git_dir / "mtools" / HINT_NAME).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def exit_notes(git_dir: Path, repo: str, env: Mapping[str, str]) -> str:
    """Spell what follows the idle line: the file read, any call it sat in, the next action.

    Returns:
        `heartbeat read: <path>`, then a line when the silence was inside one call, then the next
        action `hint_from` names.

    """
    lines = [f"heartbeat read: {heartbeat.path_of(git_dir)}"]
    hint = hint_from(repo, env)
    remember_hint(git_dir, hint)
    lines.extend(line for line in (inside_call(git_dir, time.time_ns()), hint) if line)
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mikemol-watchdog")
    parser.add_argument("--state", required=True, help="the queue file the session works from")
    parser.add_argument("--writer", help="the paths-forward writer (default: the one on PATH)")
    parser.add_argument("--poll-s", type=float, default=DEFAULT_POLL_S)
    parser.add_argument("--phi-fire", type=float, default=DEFAULT_PHI_FIRE)
    return parser


def main(
    argv: Sequence[str] | None = None, spawn: Callable[[Sequence[str]], None] = DETACHED
) -> int:
    """Run the watchdog.

    ⚑ EVERY EXIT SAYS IT IS GONE (W1581, github-8f 2026-10-18, from luthen's alert rule): the
    watchdog sent `armed=1` while it lived and nothing on exit, so `last_over_time(armed[5m])` read
    a watchdog that had exited 8 a minute ago as armed, and an exit-and-restart cycle kept it
    looking armed all the time. The `finally` that removes the pid file now sends `armed=0` too, on
    exit 8, on a parent going away and on an exception alike. `spawn` is the sender, so a test
    records the samples and cannot reach the store.

    Returns:
        EXIT_IDLE when the session went quiet with work waiting, 0 when its parent went away,
        EXIT_CANNOT_RUN when no writer is found.

    """
    opts: dict[str, object] = vars(_parser().parse_args(sys.argv[1:] if argv is None else argv))
    named = opts.get("writer")
    writer = str(named) if named else shutil.which("mikemol-paths-forward")
    if writer is None:
        sys.stderr.write("mikemol-watchdog: no paths-forward writer found (use --writer)\n")
        return EXIT_CANNOT_RUN
    state = Path(str(opts["state"])).absolute()
    git_dir = state.parent.parent / ".git"
    parent = os.getppid()
    seams: Seams = (
        lambda: heartbeat.read(git_dir),
        lambda: ready_from(writer, state),
        time.time_ns,
        time.sleep,
        lambda: os.getppid() == parent,
    )
    repo = git_dir.parent.name
    announce = armed_publisher(os.environ, repo, spawn)
    gone = armed_publisher(os.environ, repo, spawn, ARMED_DOWN)
    claim(git_dir, os.getpid())
    try:
        poll = float(str(opts["poll_s"]))
        return watch(
            seams,
            float(str(opts["phi_fire"])),
            poll,
            announce,
            lambda: exit_notes(git_dir, repo, os.environ),
        )
    finally:
        release(git_dir, os.getpid())
        gone()


if __name__ == "__main__":
    raise SystemExit(main())
