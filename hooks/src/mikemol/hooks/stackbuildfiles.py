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

⚑ A BARE NAME IS PRESENT WHEREVER A FILE OF THAT NAME IS (W1886). The root `BUILD.bazel` lists
each atom's scripts as bare names in a loop (`("check_mutants", ["mutate_runner.py"])`), and the
files live in the atoms' directories, beside neither the build file nor the root. Read as a
path they made every stack that froze the root build file a refusal. A name with no slash
therefore also counts when HEAD or the stack holds a file of that basename anywhere; a name
with a directory is judged as before.

CONSUMED BY: `commit_kata.main`, at submit.
"""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from mikemol.hooks import stacksnap
from mikemol.hooks.isolated import EnvRunner
from mikemol.hooks.stackrun import items_of
from mikemol.hooks.stacksnap import Frozen

ReadBlob = Callable[[str], str | None]
InHead = Callable[[str], bool]
HeadNames = Callable[[], frozenset[str]]
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


@dataclass
class _Known:
    """What can explain a named source: the files the stack carries so far, and HEAD."""

    present: set[str]
    in_head: InHead
    head_names: HeadNames | None
    heads: list[frozenset[str]] = field(default_factory=list)

    def path(self, here: PurePosixPath, source: str) -> bool:
        """Say whether the source is a file beside the build file or from the root.

        Returns:
            True when either spelling is carried by the stack so far or by HEAD.

        """
        bases = {str(here / source), str(PurePosixPath(source))}
        return any(path in self.present or self.in_head(path) for path in bases)

    def name(self, source: str) -> bool:
        """Say whether a bare name is the basename of a file the stack or HEAD holds (W1886).

        Returns:
            False for a name with a directory, else whether any carried file has that basename.

        """
        if "/" in source:
            return False
        if any(PurePosixPath(path).name == source for path in self.present):
            return True
        if self.head_names is None:
            return False
        if not self.heads:
            self.heads.append(self.head_names())
        return source in self.heads[0]


def findings(
    entries: Sequence[tuple[str, Sequence[Frozen]]],
    read_blob: ReadBlob,
    in_head: InHead,
    head_names: HeadNames | None = None,
) -> list[str]:
    """Name every source a frozen build file lists that neither HEAD nor the stack carries.

    `entries` is each entry's waypoint with its frozen files, in landing order; `head_names`
    lists the basenames HEAD holds, asked only for a bare name nothing else explains.

    Returns:
        one line per finding: the entry, the build file and the missing path.

    """
    known = _Known(set(), in_head, head_names)
    found: list[str] = []
    for waypoint, files in entries:
        known.present.update(frozen.path for frozen in files if frozen.blob)
        for frozen in files:
            text = read_blob(frozen.blob) if frozen.blob and is_build_file(frozen.path) else None
            if text is None:
                continue
            here = PurePosixPath(frozen.path).parent
            found += [
                f"{waypoint}: {frozen.path} names {source}, which neither HEAD nor this "
                f"entry's or an earlier entry's files carry"
                for source in named_sources(text)
                if not (known.path(here, source) or known.name(source))
            ]
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

    def head_names() -> frozenset[str]:
        listing = run(["ls-tree", "-r", "--name-only", "HEAD"], {}, root)
        return frozenset(PurePosixPath(line).name for line in listing.stdout.splitlines())

    entries = [(item.waypoint, files) for item, files in zip(items, loaded, strict=True)]
    found = findings(entries, read_blob, in_head, head_names)
    return "\n".join(found) if found else None
