# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-katas`: the host katas' subcommand names over the modules of this distribution (W878).

The grammar is the host `katas.py`'s, so a habit carries over:

    status | pulse | flush [--skip REPO ...] | probe REPO | archive REPO LETTER ... | precommit
    bazelize REPO [--hook] | tick begin | tick end [--note N] [--next S]
    commit REPO --waypoint W --subject S [--body B] [PATH ...]

A subcommand an mtools tool now does is not reimplemented: `wp`, `gate`, `typing`, `mypy`, `ship`
and `visit` print the exact command to run instead, and exit 2, so the old name leads to the new one
rather than to a silent difference. Every host value (the root, the skip list, the tool paths, the
holder) comes from the policy file (`policy`), never from a constant here.

⚑ PARSED BY HAND, NOT BY argparse: a `Namespace` attribute is `Any`, which this distribution's
strict mypy refuses, and the grammar is small enough that a typed reader is shorter than the casts.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.procrun.proc import capture

from mikemol.katas import fleet, hosttick, inbox, policy, pulse, scaffold, survey

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from typing import TextIO

EXIT_USAGE = 2
_POLICY_FLAG = "--policy"
_ARCHIVE_MINIMUM = 2  # a repo and at least one letter

DELEGATED = {
    "wp": "mikemol-paths-forward --state <repo>/.claude/paths-forward.json --add TITLE ... "
    "(it refuses a bundled title itself)",
    "gate": "mikemol-paths-forward --state <repo>/.claude/paths-forward.json "
    "--gate-red REASON --next STEP [--except REPAIRS ...] | --gate-green EVIDENCE",
    "typing": "mikemol-pycheck --refresh-ledger <repo>, then mikemol-debtplan plan | mint",
    "mypy": "mikemol-pycheck --check-file <path>  (the edit gate's own verdict)",
    "ship": "mikemol-pycheck --check-file <path>, mikemol-commit <repo> ..., "
    "then mikemol-pycheck --refresh-ledger <repo>",
    "visit": "nemik-inbound <repo>  (and the inbound-asks hook for the census)",
}
"""The host subcommands an mtools tool now does, with what to run instead."""


@dataclass(frozen=True)
class Context:
    """One invocation: the policy, the subcommand's own arguments, where to write, today's date."""

    policy: policy.Policy
    args: list[str]
    out: TextIO
    today: str

    def fleet(self, extra_skip: frozenset[str] = frozenset()) -> fleet.Fleet:
        """Build the fleet this invocation reads.

        Returns:
            the fleet over the policy's root, logs and skip list (plus any one-off skip).

        """
        return fleet.Fleet(self.policy.root, self.policy.logs, self.policy.skip_flush | extra_skip)

    def say(self, line: str) -> None:
        """Write one line."""
        self.out.write(line + "\n")


def _status(ctx: Context) -> int:
    """Print one row per workstream.

    Returns:
        0.

    """
    for row in fleet.status(ctx.fleet()):
        ctx.say(row)
    return 0


def _pulse(ctx: Context) -> int:
    """Print the fleet view.

    Returns:
        0.

    """
    for line in pulse.pulse(ctx.fleet(), ctx.policy.nemik, ctx.policy.standing_warnings):
        ctx.say(line)
    return 0


def _flush(ctx: Context) -> int:
    """Start a queue commit where one is due.

    Returns:
        0.

    """
    skip = frozenset(ctx.args[1:]) if ctx.args[:1] == ["--skip"] else frozenset()
    started = fleet.flush(ctx.fleet(), ctx.policy.commit_tool, skip)
    for repo in started:
        ctx.say(f"started: {repo}")
    ctx.say(f"{len(started)} commit(s) started" if started else "nothing to start (or all running)")
    return 0


def _probe(ctx: Context) -> int:
    """Run a repo's pre-commit hook detached, committing nothing.

    Returns:
        0 when the probe started, 1 with the reason when it did not, 2 without a repo.

    """
    if len(ctx.args) != 1:
        ctx.say("usage: probe REPO")
        return EXIT_USAGE
    host = ctx.fleet()
    refusal = fleet.probe(host, ctx.args[0])
    if refusal:
        ctx.say(refusal)
        return 1
    ctx.say(f"probe started for {ctx.args[0]}; log: {fleet.log_of(host, ctx.args[0], '.probe')}")
    return 0


def _archive(ctx: Context) -> int:
    """Move handled letters of a repo into its inbox archive.

    Returns:
        0, or 2 without a repo and a letter.

    """
    if len(ctx.args) < _ARCHIVE_MINIMUM:
        ctx.say("usage: archive REPO LETTER ...")
        return EXIT_USAGE
    repo, letters = ctx.args[0], ctx.args[1:]
    done = inbox.archive(ctx.policy.root / repo / "inbox", letters)
    for name in done.missing:
        ctx.say(f"not found: {name}")
    for name in done.clashing:
        ctx.say(f"already archived, left in place: {name}")
    ctx.say(f"{repo}: archived {done.moved} of {len(letters)}")
    return 0


def _precommit(ctx: Context) -> int:
    """Print where each repo's pre-commit hook lives and whether it invokes bazel.

    Returns:
        0.

    """
    for row in survey.survey(ctx.fleet()):
        ctx.say(f"{row.repo:22s} {row.verdict:11s} {row.where}  {row.first_bazel_line}".rstrip())
    return 0


def _bazelize(ctx: Context) -> int:
    """Scaffold a repo's bazel files, or (--hook) swap its pre-commit once //:precommit passes.

    Returns:
        0 on success, 1 when the hook was not swapped, 2 without a repo.

    """
    if not ctx.args:
        ctx.say("usage: bazelize REPO [--hook]")
        return EXIT_USAGE
    root = ctx.policy.root / ctx.args[0]
    if ctx.args[1:] == ["--hook"]:
        passed = capture(("bazel", "test", "//:precommit", "--noshow_progress"), cwd=root)
        refusal = scaffold.install_hook(
            root, ctx.policy.templates, target_passed=passed.returncode == 0
        )
        ctx.say(refusal or f"{root.name}: .githooks/pre-commit now invokes bazel test //:precommit")
        return 1 if refusal else 0
    wrote, left = scaffold.scaffold(root, ctx.policy.templates, ctx.policy.bazel_version)
    for name in left:
        ctx.say(f"{root.name}: {name} exists, left alone")
    ctx.say(f"{root.name}: wrote {', '.join(wrote) or 'nothing'}; next: BUILD.bazel, then --hook")
    return 0


def _queue(ctx: Context) -> hosttick.HostQueue:
    """Build the host queue handle from the policy.

    Returns:
        the host queue.

    """
    p = ctx.policy
    return hosttick.HostQueue(p.pathsforward, p.host_state, p.holder, p.standing_waypoint)


def _flag_values(args: Sequence[str], flags: Sequence[str]) -> dict[str, str]:
    """Read `--flag VALUE` pairs from an argument list.

    Returns:
        each given flag mapped to the word after it.

    """
    return {flag: args[i + 1] for i, flag in enumerate(args[:-1]) if flag in flags}


def _tick(ctx: Context) -> int:
    """Begin a tick on the host queue, or end one.

    Returns:
        0, or 2 without `begin` or `end`.

    """
    word = ctx.args[:1]
    if word == ["begin"]:
        ctx.say(hosttick.begin(_queue(ctx)))
        return 0
    if word != ["end"]:
        ctx.say("usage: tick begin | tick end [--note N] [--next S]")
        return EXIT_USAGE
    given = _flag_values(ctx.args[1:], ("--note", "--next"))
    closing = hosttick.Closing(
        ctx.today, given.get("--note", ""), given.get("--next", ""), ctx.policy.job_file
    )
    host = ctx.fleet()
    for line in hosttick.end(
        _queue(ctx), closing, lambda: fleet.flush(host, ctx.policy.commit_tool)
    ):
        ctx.say(line)
    return 0


def _commit(ctx: Context) -> int:
    """Commit through `mikemol-commit`, passing the arguments on as they are.

    Returns:
        the commit's status.

    """
    done = capture((str(ctx.policy.commit_tool), *ctx.args))
    ctx.say((done.stdout + done.stderr).strip())
    return done.returncode


COMMANDS: dict[str, Callable[[Context], int]] = {
    "status": _status,
    "pulse": _pulse,
    "flush": _flush,
    "probe": _probe,
    "archive": _archive,
    "precommit": _precommit,
    "bazelize": _bazelize,
    "tick": _tick,
    "commit": _commit,
}
"""The subcommands this CLI runs itself."""


def main(
    argv: Sequence[str] | None = None,
    out: TextIO | None = None,
    env: Mapping[str, str] | None = None,
    today: str | None = None,
) -> int:
    """Run one subcommand.

    Returns:
        the subcommand's status; 2 for an unknown subcommand, a missing one, or a policy gap.

    """
    sink = sys.stdout if out is None else out
    environment = os.environ if env is None else env
    args = list(sys.argv[1:] if argv is None else argv)
    path = policy.default_path(environment, Path.home())
    if args[:1] == [_POLICY_FLAG] and len(args) > 1:
        path, args = Path(args[1]), args[2:]
    name = args[0] if args else ""
    if name in DELEGATED:
        sink.write(f"{name}: an mtools tool does this now: {DELEGATED[name]}\n")
        return EXIT_USAGE
    command = COMMANDS.get(name)
    if command is None:
        sink.write(f"usage: mikemol-katas [--policy FILE] {' | '.join([*COMMANDS, *DELEGATED])}\n")
        return EXIT_USAGE
    try:
        host_policy = policy.load(path)
    except policy.PolicyError as exc:
        sink.write(f"policy: {exc}\n")
        return EXIT_USAGE
    stamp = datetime.now(UTC).date().isoformat() if today is None else today
    return command(Context(host_policy, args[1:], sink, stamp))
