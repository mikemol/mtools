# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Name the cards a landed commit carries since a time (mtools:W1377, github-8f).

⚑ A CARD IS ADVANCED WHEN A LANDED COMMIT CARRIES ITS SYMBOL, not when a queue edit stamped it:
`last_worked` is stamped on every update, so one bulk call that unblocked 130 cards read as 165
cards advanced by a tick that landed nothing of the kind. Every commit `mikemol-commit` writes ends
in a `Waypoint: W<n>` trailer, so the trailers of the commits since a time name what landed.

⚑ NO ANSWER IS NOT ZERO: with no git or an unreadable log the caller gets None and keeps the old
count, because a tick that could not look must not report that nothing landed.
CONSUMED BY: `closegate.judge`.
"""

import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

_TRAILER = re.compile(r"^Waypoint: (W[0-9]+)[ \t]*$", re.MULTILINE)
_GIT_TIMEOUT_S = 60
_RECORD_FIELDS = 3

Reader = Callable[[Path, str], str | None]


def trailer_cards(log: str) -> set[str]:
    """Read the symbols named by `Waypoint:` trailers in a log of commit messages.

    Returns:
        the distinct symbols.

    """
    return set(cast("list[str]", _TRAILER.findall(log)))


def read_log(root: Path, since: str) -> str | None:
    """Read the messages of the commits made since a time.

    Returns:
        the messages, or None when git is absent or refused.

    """
    git = shutil.which("git")
    if git is None:
        return None
    return _run([git, "-C", str(root), "log", f"--since={since}", "--format=%B"])


def _run_full(
    argv: list[str], env: dict[str, str] | None = None
) -> "subprocess.CompletedProcess[str] | None":
    # THE ONE PLACE THIS MODULE STARTS A CHILD (github-cb, b69): the finished process, or None when
    # it is absent or timed out. Callers read the exit code and both streams from this one run.
    try:
        return subprocess.run(
            argv,
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_S,
            env=env,
        )
    except Exception as caught:
        if not isinstance(caught, (OSError, subprocess.TimeoutExpired)):
            raise
        return None


def _run(argv: list[str], env: dict[str, str] | None = None) -> str | None:
    # The output of a child that exited 0, or None when it is absent, failed or timed out.
    done = _run_full(argv, env)
    return done.stdout if done is not None and done.returncode == 0 else None


Run = Callable[[list[str]], str | None]
_SHORT = 8


def _tip_lines(git: str, root: Path, before: str, tip: str, run: Run) -> list[str]:
    # What the move from the stored tip to this one means, as the lines a tick open prints.
    if not before:
        return [f"landings: first look, tip {tip[:_SHORT]}"]
    if before == tip:
        return ["landings: none since the last tick open"]
    base = run([git, "-C", str(root), "merge-base", before, tip])
    if base is None or base.strip() != before:
        rewrite = (
            f"landings: HISTORY REWRITE, the last tip {before[:_SHORT]} is not an ancestor of "
            f"{tip[:_SHORT]}"
        )
        return [rewrite]
    log = run([git, "-C", str(root), "log", "--oneline", f"{before}..{tip}"])
    span = f"{before[:_SHORT]}..{tip[:_SHORT]}"
    if log is None:
        return [f"landings: {span} (the log could not be read)"]
    shown = [f"  {line}" for line in log.splitlines()]
    return [f"landings since the last tick open ({span}):", *shown]


def landing_tips(root: Path, seen: Path, run: Run = _run) -> list[str]:
    """Say what landed on the branch since the previous tick open, and remember this tip (W2070).

    ⚑ THE PREVIOUS TIP IS THE BASELINE, so a tick reads its own landings off the history rather
    than from card stamps. A previous tip that is not an ancestor of this one is said as a history
    rewrite, never as an empty range. The tip is stored only where its directory already exists
    (`.git/mtools`), so a plain directory is not littered.

    Returns:
        the lines to print; empty when git is absent or cannot name the tip.

    """
    git = shutil.which("git")
    if git is None:
        return []
    named = run([git, "-C", str(root), "rev-parse", "HEAD"])
    if named is None or not named.strip():
        return []
    tip = named.strip()
    try:
        before = seen.read_text(encoding="utf-8").strip() if seen.is_file() else ""
    except OSError:
        before = ""
    lines = _tip_lines(git, root, before, tip, run)
    if seen.parent.is_dir():
        try:
            seen.write_text(f"{tip}\n", encoding="utf-8")
        except OSError:
            lines.append("landings: the tip could not be stored")
    return lines


def committed_text(root: Path, rel: str, run: Run = _run) -> str | None:
    """Read a file as HEAD holds it, not as the working tree has moved it since (W2267).

    Returns:
        the file's text at HEAD, or None when git is absent, the path is not in HEAD or git refuses.

    """
    git = shutil.which("git")
    if git is None:
        return None
    return run([git, "-C", str(root), "show", "--end-of-options", f"HEAD:{rel}"])


def read_commits(root: Path) -> str | None:
    """Read the last 500 commits as `sha US UTC-stamp US message RS` records (W1639).

    Returns:
        the text `reconcilecmd.parse_log` reads, or None when git is absent or refused.

    """
    git = shutil.which("git")
    if git is None:
        return None
    fmt = "--format=%H%x1f%cd%x1f%B%x1e"
    date = "--date=format-local:%Y-%m-%dT%H:%M:%SZ"
    env = {"TZ": "UTC", "PATH": "/usr/bin:/bin"}
    return _run([git, "-C", str(root), "log", "-n500", date, fmt], env)


def stamps_of(raw: str) -> dict[str, str]:
    """Read `read_commits` text into each card's newest landing stamp (W2170).

    ⚑ A RECORD IS `sha US stamp US message RS`, NEWEST FIRST: the first record that carries a card's
    `Waypoint:` trailer is its latest landing, so a later record for the same card never replaces
    it. The stamp is the commit's own date, which for a stack is its gate's start; an advance
    stamped after it is work done once the card's stack had gone to its gate.

    Returns:
        card symbol to the UTC stamp of the newest commit whose trailers name it.

    """
    found: dict[str, str] = {}
    for record in raw.split("\x1e"):
        parts = record.strip("\n").split("\x1f", 2)
        if len(parts) != _RECORD_FIELDS:
            continue
        for card in sorted(trailer_cards(parts[2])):
            found.setdefault(card, parts[1].strip())
    return found


def last_landings(root: Path) -> dict[str, str] | None:
    """Read each card's newest landing stamp from the repository's last 500 commits.

    Returns:
        the map, or None when git is absent or refused (no answer is not an empty history).

    """
    raw = read_commits(root)
    return None if raw is None else stamps_of(raw)


def landing_times(root: Path, count: int) -> list[float] | None:
    """Read the commit times of the last `count` commits, for the idle bound (W2047).

    Returns:
        the committer times in epoch seconds, newest first, or None when git is absent or refused:
        no answer is not an empty history.

    """
    git = shutil.which("git")
    if git is None:
        return None
    out = _run([git, "-C", str(root), "log", f"-n{count}", "--format=%ct"])
    if out is None:
        return None
    return [float(line) for line in out.split() if line.isdigit()]


def read_head_files(root: Path) -> frozenset[str] | None:
    """Name every file HEAD holds, relative to the root (W1717).

    Returns:
        the paths, or None when git is absent or refused: no answer is not an empty tree.

    """
    git = shutil.which("git")
    if git is None:
        return None
    listing = _run([git, "-C", str(root), "ls-tree", "-r", "--name-only", "HEAD"])
    return None if listing is None else frozenset(listing.splitlines())


def gate_tool(root: Path, beside: tuple[Path, ...], on_path: str | None) -> str | None:
    """Find `mikemol-commit`: beside the writer and its interpreter, then the repo's own, then PATH.

    ⚑ A FULL-PATH LAUNCH HAS NO .venv/bin ON PATH (luthen-observability:W1541, W1862): the writer
    and `mikemol-commit` are installed into one environment, so the directories of the writer
    script and of the interpreter running it are the sibling's home whatever PATH says.

    ⚑ PATH COMES LAST (W1898, github-8f 2026-10-27): the host's pinned writer reported 'reconcile:
    not run (is mikemol-commit on PATH?)' with the tool in the pinned bin beside it, and a PATH
    entry can as easily name another checkout's copy. PATH is only what is left when nothing the
    writer was installed with has it.

    Returns:
        the tool's path, or None when none of them has it.

    """
    for directory in beside:
        sibling = directory / "mikemol-commit"
        if sibling.is_file():
            return str(sibling)
    own = root / "hooks" / ".venv" / "bin" / "mikemol-commit"
    return str(own) if own.is_file() else on_path


def read_gate(root: Path) -> str | None:
    """Read the live-commit map as JSON from `mikemol-commit --in-gate --json` (W1587).

    Returns:
        the JSON text, or None when the tool is absent or refused.

    """
    return read_tool(find_gate_tool(root), root)[0]


def find_gate_tool(root: Path) -> str | None:
    """Find `mikemol-commit` for `root` the way `read_gate` does.

    Returns:
        the tool's path, or None when none of the places has it.

    """
    here = (Path(sys.argv[0]).absolute().parent, Path(sys.executable).parent)
    return gate_tool(root, here, shutil.which("mikemol-commit"))


def read_tool(tool: str | None, root: Path) -> tuple[str | None, str]:
    """Run `mikemol-commit --in-gate --json` for `root` ONCE and say what it answered and why.

    ⚑ A TOOL THAT RAN AND REFUSED IS NOT A TOOL THAT IS ABSENT (github:W59 R205 F1, W2180): a
    repository with no commit gate made the tool exit nonzero with 'git cannot name its
    directory', and the caller blamed PATH. Only a missing tool earns the PATH hint. ⚑ ONE RUN, NOT
    TWO (github-cb, b69): the JSON and the refusal line come from the same child.

    Returns:
        the JSON text and the empty string when the tool exited 0; None and the first non-empty
        stderr line when it exited nonzero; None and the empty string when there is no tool or it
        could not start.

    """
    if tool is None:
        return None, ""
    done = _run_full([tool, root.name, "--in-gate", "--json"])
    if done is None:
        return None, ""
    if done.returncode == 0:
        return done.stdout, ""
    return None, next((line.strip() for line in done.stderr.splitlines() if line.strip()), "")


def refusal_line(tool: str | None, root: Path) -> str:
    """Say why `mikemol-commit --in-gate` refused for `root`: the first line the tool itself wrote.

    Returns:
        the refusal line `read_tool` gives; the empty string when there is none.

    """
    return read_tool(tool, root)[1]


def _counter_of(text: str) -> int | None:
    # The queue document's TOP-LEVEL counter, or None when the text is not JSON, not an object, or
    # has no integer counter. Parsed, not searched: a waypoint field of the same name must not win.
    try:
        document: object = json.loads(text)
    except ValueError:
        return None
    if not isinstance(document, dict):
        return None
    value = cast("dict[str, object]", document).get("counter")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def queue_counters(root: Path, rel: str, count: int, run: Run = _run) -> list[int] | None:
    """Read the queue's `counter` as each of its last `count` commits held it (W2264).

    ⚑ THE CADENCE IS READ FROM GIT, NOT TYPED: the counters of the queue file at successive commits
    say how fast the queue moves between commits, which is what bounds how far a committed copy may
    trail the working one. A commit whose copy has no readable counter is skipped.

    Returns:
        the counters, newest commit first; None when git is absent or refuses the log.

    """
    git = shutil.which("git")
    if git is None:
        return None
    listing = run([git, "-C", str(root), "log", f"-n{count}", "--format=%H", "--", rel])
    if listing is None:
        return None
    found: list[int] = []
    for sha in listing.split():
        text = run([git, "-C", str(root), "show", "--end-of-options", f"{sha}:{rel}"])
        counter = None if text is None else _counter_of(text)
        if counter is not None:
            found.append(counter)
    return found


def landed_since(root: Path, since: str, reader: Reader = read_log) -> set[str] | None:
    """Name the cards a commit carries since `since`.

    Returns:
        the symbols, or None when `since` is empty or the log could not be read.

    """
    if not since:
        return None
    log = reader(root, since)
    return None if log is None else trailer_cards(log)
