# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-hooks-probe`: fire each gate hook with a payload it must deny, and fail unless it does.

An adopted guard can be silently inert: the launcher resolves its venv from the wrong place, the
console script was never installed, the hook is wired to a name that no longer exists. Every one of
those exits 0 and says nothing, and the harness reads that as ALLOW. The only proof a guard works is
to FIRE it with a command it must refuse and read the refusal (mtools:W898, gcalculus:W223).

⚑⚑ A ROW THAT CANNOT RUN IS A FAILURE, NEVER A SKIP. The test this replaces skipped when the console
script was not installed, which is the exact condition under which a guard is inert: it passed
precisely where it proved nothing. Here an absent launcher, a timeout, unreadable output and an
allow are all FAILs, each with its reason.

⚑ EVERY GATE IS FIRED TWICE, from the project root and from a foreign working directory. A launcher
that resolves anything from the cwd denies at the root and is inert everywhere the harness actually
runs it; the project is named by `CLAUDE_PROJECT_DIR`, never by the cwd.

⚑ THE LAUNCHER IS AN ARGV TEMPLATE, NEVER A SHELL: `{entry}` and `{project}` are substituted into a
`shlex`-split template, so an adopter points the probe at its own `tools/hook {entry}` and mtools at
`{project}/hooks/bin/{entry}`.

CONSUMED BY: the `mikemol-hooks-probe` console script.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks.payload import as_record, text_of

if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_LAUNCHER = "{project}/hooks/bin/{entry}"
USAGE = "usage: mikemol-hooks-probe [--project DIR] [--launcher TEMPLATE] [ENTRY ...]\n"
TIMEOUT_S = 60
DENY = "deny"
ARM = "STRUCT_HOOK_BLOCK"
"""The switch every gate honours (payload.SHARED_SWITCH): unarmed, a gate only advises on stderr."""
EXIT_FAILED = 1
EXIT_USAGE = 2
_VALUED = frozenset(("--project", "--launcher"))


@dataclass(frozen=True, slots=True)
class Row:
    """One gate and the Bash command it must refuse; `env` arms a hook that is off by default."""

    entry: str
    command: str
    env: tuple[tuple[str, str], ...] = ()


GATES: tuple[Row, ...] = (
    Row("mikemol-hook-no-verify", "git commit --no-verify -m x", (("NOVERIFY_HOOK_BLOCK", "1"),)),
    Row("mikemol-hook-no-chaining", "ls; ls"),
    Row("mikemol-hook-structural-query", "grep needle README.md"),
    Row("mikemol-hook-shellcheck", "true done"),
)
"""The gates and a command each must deny, in one place."""


@dataclass(frozen=True, slots=True)
class Verdict:
    """What one firing did: the decision read from stdout (None when none), and why it failed."""

    entry: str
    where: str
    decision: str | None
    why: str

    @property
    def ok(self) -> bool:
        """Whether the gate denied."""
        return self.decision == DENY

    def line(self) -> str:
        """Render the verdict as one report line.

        Returns:
            `OK entry@where: deny`, or `FAIL entry@where: why`.

        """
        if self.ok:
            return f"OK   {self.entry}@{self.where}: {DENY}"
        return f"FAIL {self.entry}@{self.where}: {self.why}"


@dataclass(slots=True)
class Options:
    """What the command line asked for."""

    project: Path = field(default_factory=Path.cwd)
    launcher: str = DEFAULT_LAUNCHER
    entries: list[str] = field(default_factory=list)


def parse(args: Sequence[str]) -> Options | None:
    """Read the command line.

    Returns:
        the options, or None for a flag that is unknown or lacks its value.

    """
    opts = Options()
    queue = list(args)
    while queue:
        word = queue.pop(0)
        if word in _VALUED and queue:
            value = queue.pop(0)
            if word == "--project":
                opts.project = Path(value).resolve()
            else:
                opts.launcher = value
        elif word.startswith("-"):
            return None
        else:
            opts.entries.append(word)
    return opts


def decision_of(stdout: str) -> str | None:
    """Read the permission decision a hook printed.

    Returns:
        the `permissionDecision` string, or None when stdout holds no decision.

    """
    try:
        parsed: object = json.loads(stdout)
    except ValueError:
        return None
    inner = as_record(as_record(parsed).get("hookSpecificOutput"))
    return text_of(inner.get("permissionDecision")) or None


def payload_of(row: Row) -> str:
    """Build the PreToolUse payload for a row.

    Returns:
        the JSON text the harness would send.

    """
    body: dict[str, object] = {"tool_name": "Bash", "tool_input": {"command": row.command}}
    return json.dumps(body)


def fire(row: Row, template: str, project: Path, cwd: Path, where: str) -> Verdict:
    """Run one launcher with the row's payload from `cwd` and read its decision.

    Returns:
        the verdict; a launcher that could not run, timed out or printed no decision is a failure.

    """
    argv = [part.format(entry=row.entry, project=str(project)) for part in shlex.split(template)]
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "CLAUDE_PROJECT_DIR": str(project),
        ARM: "1",
        **dict(row.env),
    }
    try:
        done = subprocess.run(
            argv,
            input=payload_of(row),
            capture_output=True,
            text=True,
            cwd=cwd,
            env=env,
            check=False,
            timeout=TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return Verdict(row.entry, where, None, f"could not run {argv[0]}: {exc}")
    decision = decision_of(done.stdout)
    if decision is None:
        return Verdict(row.entry, where, None, f"exit {done.returncode}, no decision printed")
    return Verdict(row.entry, where, decision, f"{decision}, not {DENY}")


def probe(rows: Sequence[Row], template: str, project: Path, foreign: Path) -> list[Verdict]:
    """Fire every row from the project root and from a foreign directory.

    Returns:
        two verdicts per row, root first.

    """
    return [
        fire(row, template, project, cwd, where)
        for row in rows
        for where, cwd in (("root", project), ("foreign", foreign))
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the probe: `mikemol-hooks-probe [--project DIR] [--launcher TEMPLATE] [ENTRY ...]`.

    Returns:
        0 when every row denied from both places, 1 when any failed, 2 for a usage error.

    """
    opts = parse(sys.argv[1:] if argv is None else argv)
    if opts is None:
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    known = {row.entry for row in GATES}
    unknown = sorted(set(opts.entries) - known)
    if unknown:
        sys.stderr.write(f"mikemol-hooks-probe: no such gate: {', '.join(unknown)}\n")
        return EXIT_USAGE
    rows = [row for row in GATES if not opts.entries or row.entry in opts.entries]
    with tempfile.TemporaryDirectory() as foreign:
        verdicts = probe(rows, opts.launcher, opts.project, Path(foreign))
    sys.stdout.write("".join(f"{v.line()}\n" for v in verdicts))
    return 0 if all(v.ok for v in verdicts) else EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
