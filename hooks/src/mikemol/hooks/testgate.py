# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse a stack whose own tests fail in the sandbox, before it can queue (W2055).

⚑ THE GATE IS HOURS AND THE TEST IS SECONDS (2026-10-26: stack-w2039b waited about 110 minutes for
its turn and was refused in minutes because a new test shelled out to `git commit` in a sandbox with
no global identity; it had passed under pytest on a host that has one). The loop prompt already said
to run `bazel test //<pkg>:<touched target>`, and a prose rule can be skipped, so the submit path
does it: every test file a stack adds or changes becomes its bazel target, run over a snapshot of
the working tree with the cache the gate will read. A target that already passed costs nothing.

⚑ ONLY THE STACK'S OWN TESTS, NOT `//...`: the whole-tree run is the gate's work and the manual
presubmit's. A path outside `<dist>/tests/test_*.py` names no target here.
⚑ NO TOOL IS NOT A REFUSAL: with no `mikemol-snapshot` to find, nothing runs and nothing is refused,
as a missing store refuses nothing in `shardgate`. A failing target, or a build that fails, refuses.
⚑ THE REFUSAL NAMES THE COMMAND THAT REPRODUCES IT (W1663), and the output tail of the failure.

CONSUMED BY: `commit_kata.submit_problem`, beside the import, build-file and shard refusals.
"""

import os
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from mikemol.hooks.presubmit import DEFAULT_ROOT, ROOT_ENV, SNAPSHOT, SNAPSHOT_ENV, plan
from mikemol.hooks.stackrun import items_of
from mikemol.hooks.tool_path import find as find_tool

_TEST = re.compile(r"^(?P<dist>[^/.][^/]*)/tests/(?P<name>test_[^/]+)\.py$")
_TAIL = 25
SNAPSHOT_VOICE = "mikemol-snapshot:"
Run = Callable[[Sequence[str], Mapping[str, str], Path], tuple[int, str]]
Find = Callable[[Path, Mapping[str, str]], Path | None]


def targets_of(paths: Sequence[str]) -> list[str]:
    """Name the bazel test target of every test file among the paths.

    Returns:
        `//<dist>:<name>` for each `<dist>/tests/<name>.py` with a `test_` name, once, in order.

    """
    found: list[str] = []
    for path in paths:
        matched = _TEST.match(path)
        label = f"//{matched.group('dist')}:{matched.group('name')}" if matched else ""
        if label and label not in found:
            found.append(label)
    return found


def run_command(argv: Sequence[str], env: Mapping[str, str], cwd: Path) -> tuple[int, str]:
    """Run a command in a directory with extra environment, output and errors together.

    Returns:
        its exit code and what it printed.

    """
    done = subprocess.run(
        list(argv),
        env={**os.environ, **env},
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode, done.stdout + done.stderr


def _snapshot(root: Path, env: Mapping[str, str]) -> Path | None:
    return find_tool(SNAPSHOT, SNAPSHOT_ENV, root, env)


def refusal(
    root: Path,
    stack_file: Path,
    env: Mapping[str, str],
    run: Run = run_command,
    find: Find = _snapshot,
) -> str | None:
    """Run the stack's own test targets over a snapshot and judge the result.

    Returns:
        the failing run's last lines and the command that reproduces it; None when the stack names
        no test, no `mikemol-snapshot` is found, or every target passes.

    """
    items = items_of(stack_file)
    if isinstance(items, str):
        return None
    targets = targets_of([path for item in items for path in item.paths])
    snapshot = find(root, env)
    if not targets or snapshot is None:
        return None
    planned = plan(str(root), targets, env.get(ROOT_ENV, DEFAULT_ROOT), str(snapshot))
    status, out = run(planned.argv, planned.env, root)
    # ⚑ A SNAPSHOT THAT COULD NOT BE TAKEN IS NOT A FAILING TEST (found by this check's first real
    # run, 2026-10-26: `git add -A` died with 128 because an edit gate's scratch file vanished
    # mid-add, and the stack was refused for "its own tests fail"). The snapshot tool speaks first,
    # as `mikemol-snapshot: ...`; with no bazel run to judge, nothing is refused.
    if status == 0 or out.lstrip().startswith(SNAPSHOT_VOICE):
        return None
    tail = "\n".join(out.splitlines()[-_TAIL:])
    again = " ".join(("bazel", "test", *targets))
    return f"the stack's own tests fail in the sandbox (exit {status}):\n{tail}\nreproduce: {again}"
