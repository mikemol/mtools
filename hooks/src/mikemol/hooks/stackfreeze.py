# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Freeze a stack at submit and carry it across the claim re-exec (W1447).

`stacksnap` freezes files; this is the part `mikemol-commit --stack` calls. At SUBMIT, before the
process queues for the lease, `at_submit` freezes every entry's files and writes them under the
repository's own ledger (`<git dir>/mtools/stack-<key>.snap`); the path rides the environment
through the re-exec. At RUN, `with_files` loads that file and puts the frozen files on the items,
so `stackland.build` places the submit-time bytes and never reads the working tree.

⚑ A MISSING OR UNUSABLE SNAPSHOT FALLS BACK TO FREEZING NOW, NEVER TO READING THE TREE LATE: a stack
that was not frozen at submit (an unlocked fallback, a ledger that could not be written, a snapshot
whose entry count no longer matches the stack file) is frozen when it runs. That is the old
behaviour's timing but still a frozen blob, and it is said where it matters by the caller.

⚑ THE SNAPSHOT FILE IS REMOVED WHEN THE RUN ENDS (`forget`): the blobs stay in git's object store,
unreachable, for `git gc` to take.

CONSUMED BY: `commit_kata.main` and `run_stack_mode`.
"""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path

from mikemol.hooks import stacksnap
from mikemol.hooks.isolated import EnvRunner
from mikemol.hooks.stackrun import Item, items_of

SNAP_ENV = "MIKEMOL_STACK_SNAPSHOT"


def at_submit(root: Path, stack_file: Path, ledger: Path | None, key: str, run: EnvRunner) -> str:
    """Freeze the stack's files now and record them in the ledger.

    Returns:
        the snapshot file's path, or the empty string when the stack file or the ledger cannot be
        used (the run then freezes when it runs).

    """
    items = items_of(stack_file)
    if isinstance(items, str) or ledger is None:
        return ""
    entries = [stacksnap.freeze(root, item.paths, run) for item in items]
    path = ledger / f"stack-{key}.snap"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        stacksnap.dump(path, entries)
        # ⚑ W1669: a copy of the entries beside the snapshot, so a lease holder can build this
        # stack's commits from the ledger alone and join it to its own run.
        path.with_suffix(".items.json").write_text(
            stack_file.read_text(encoding="utf-8"), encoding="utf-8"
        )
    except OSError:
        return ""
    return str(path)


def at_submit_paths(
    root: Path, paths: Sequence[str], ledger: Path | None, key: str, run: EnvRunner
) -> str:
    """Freeze a plain commit's files now and record them as a one-entry snapshot (W2120).

    Returns:
        the snapshot file's path, or the empty string when there is no ledger or it cannot be
        written (the commit then reads the tree when it runs, as it always did).

    """
    if ledger is None:
        return ""
    path = ledger / f"stack-{key}.snap"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        stacksnap.dump(path, [stacksnap.freeze(root, paths, run)])
    except OSError:
        return ""
    return str(path)


def plain_plan(env: Mapping[str, str]) -> list[list[str]]:
    """Plan the `update-index` calls that place a plain commit's submit-time files.

    Returns:
        the calls, or none when no snapshot was named, it is unreadable, or it is not one entry.

    """
    named = env.get(SNAP_ENV, "")
    loaded = stacksnap.load(Path(named)) if named else None
    return stacksnap.apply_argv(loaded[0]) if loaded is not None and len(loaded) == 1 else []


def with_files(items: list[Item], root: Path, env: Mapping[str, str], run: EnvRunner) -> list[Item]:
    """Put frozen files on the items: the submit-time snapshot if usable, else frozen now.

    Returns:
        the items, each carrying `files`.

    """
    named = env.get(SNAP_ENV, "")
    loaded = stacksnap.load(Path(named)) if named else None
    if loaded is None or len(loaded) != len(items):
        loaded = [stacksnap.freeze(root, item.paths, run) for item in items]
    return [replace(item, files=tuple(files)) for item, files in zip(items, loaded, strict=True)]


def forget(env: Mapping[str, str]) -> None:
    """Remove the snapshot file this run was given, if any; a vanished file is not an error."""
    named = env.get(SNAP_ENV, "")
    if named:
        Path(named).unlink(missing_ok=True)
        Path(named).with_suffix(".items.json").unlink(missing_ok=True)
