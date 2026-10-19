# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse a stack at submit when a frozen BUILD or .bzl file names a source that is nowhere (W1603).

A stack freezes whole files at submit and gates the tip once, so a build file that lists a test
source the stack does not carry runs a full gate to fail on a file that was never there. luthen's
`unit_tests.bzl` declared `checks/hook_exec_test.py` with that file in no entry, ran the gate, and
"failed as I expected" (github-8f, 2026-10-18): the refusal belongs at submit, in seconds.

⚑ THE SAME RULE AS THE IMPORT CHECK (W1527): it can refuse only what is surely broken. A quoted
`.py` path with no wildcard, no label (`@repo//`, `//pkg:`) and no leading colon is a named source;
it counts as present when HEAD or any frozen file of this entry or an earlier one carries it under
EITHER of the two bases a build file can mean: beside itself, or from the repository root (a `.bzl`
macro's paths are relative to the package that calls it, which the file alone does not say).

⚑ THE BYTES ARE THE FROZEN BLOBS, as for the import check; a blob that cannot be read is skipped.

CONSUMED BY: `commit_kata.main`, at submit.
"""

import re
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath

from mikemol.hooks import stacksnap
from mikemol.hooks.isolated import EnvRunner
from mikemol.hooks.stackrun import items_of
from mikemol.hooks.stacksnap import Frozen

ReadBlob = Callable[[str], str | None]
InHead = Callable[[str], bool]
_QUOTED_PY = re.compile(r"""["']([A-Za-z0-9_][A-Za-z0-9_./-]*\.py)["']""")
_BUILD_NAMES = frozenset({"BUILD", "BUILD.bazel"})


def is_build_file(path: str) -> bool:
    """Say whether a path is a Bazel build file or a Starlark library.

    Returns:
        True for BUILD, BUILD.bazel and any `.bzl`.

    """
    name = PurePosixPath(path).name
    return name in _BUILD_NAMES or name.endswith(".bzl")


def named_sources(text: str) -> list[str]:
    """List the quoted `.py` paths a build file names, in order, once each.

    Returns:
        paths with no wildcard and no label syntax.

    """
    found: list[str] = []
    # ⚑ A PATH INSIDE glob(...) IS OPTIONAL, NEVER NAMED (found at the W1604 wiring, 2026-10-19:
    # buildtel's glob(["tests/conftest.py"], allow_empty = True) refused every stack carrying that
    # BUILD file): bazel takes a glob to match nothing, so what it lists is not a missing source.
    text = re.sub(r"\bglob\s*\([^)]*\)", "", text)
    for match in _QUOTED_PY.finditer(text):
        source = str(match.group(1))
        if source not in found:
            found.append(source)
    return found


def findings(
    entries: Sequence[tuple[str, Sequence[Frozen]]],
    read_blob: ReadBlob,
    in_head: InHead,
) -> list[str]:
    """Name every source a frozen build file lists that neither HEAD nor the stack carries.

    `entries` is each entry's waypoint with its frozen files, in landing order.

    Returns:
        one line per finding: the entry, the build file and the missing path.

    """
    present: set[str] = set()
    found: list[str] = []
    for waypoint, files in entries:
        present.update(frozen.path for frozen in files if frozen.blob)
        for frozen in files:
            if not frozen.blob or not is_build_file(frozen.path):
                continue
            text = read_blob(frozen.blob)
            if text is None:
                continue
            here = PurePosixPath(frozen.path).parent
            for source in named_sources(text):
                bases = {str(here / source), str(PurePosixPath(source))}
                if not any(path in present or in_head(path) for path in bases):
                    found.append(
                        f"{waypoint}: {frozen.path} names {source}, which neither HEAD nor this "
                        f"entry's or an earlier entry's files carry"
                    )
    return found


def refusal(root: Path, stack_file: Path, snap: str, run: EnvRunner) -> str | None:
    """Judge a submitted stack from its submit-time snapshot.

    Returns:
        the findings, one per line, or None when the stack is sound or cannot be judged (no
        snapshot, an unreadable stack file, a snapshot that no longer matches the stack).

    """
    items = items_of(stack_file)
    loaded = stacksnap.load(Path(snap)) if snap else None
    if isinstance(items, str) or loaded is None or len(loaded) != len(items):
        return None

    def read_blob(blob: str) -> str | None:
        done = run(["cat-file", "blob", blob], {}, root)
        return done.stdout if done.returncode == 0 else None

    def in_head(path: str) -> bool:
        return run(["cat-file", "-e", f"HEAD:{path}"], {}, root).returncode == 0

    entries = [(item.waypoint, files) for item, files in zip(items, loaded, strict=True)]
    found = findings(entries, read_blob, in_head)
    return "\n".join(found) if found else None
