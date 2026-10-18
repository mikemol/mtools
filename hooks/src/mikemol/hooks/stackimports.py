# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse a stack at submit when a frozen file imports a module only a later entry adds (W1527).

A stack freezes WHOLE files at submit and lands them in order, so a file frozen in entry 1 can
name a module that entry 3 introduces. The commit for entry 1 is then broken, and a stack frozen
from a working tree that carried a sibling stack's edit is broken at the tip. On 2026-10-18 the
W1520 gate failed that way after 35 minutes: `cli.py` imported `watchdogcmd`, which no commit yet
had, and 78 targets could not import it.

⚑ THE CHECK IS ABOUT ORDER, NOT ABOUT NAMES. A name imported from a package may be a module or a
class, and telling them apart needs the package's own `__init__`. So only one case is judged: a
candidate module FILE that this stack adds in a later entry and that HEAD does not have. A symbol
that is not a file, or a module that exists in HEAD or in this or an earlier entry, is never a
finding, so the check cannot refuse a sound stack.

⚑ THE IMPORTS ARE READ FROM THE FROZEN BYTES, NOT THE WORKING TREE: the submit-time blob is what
will land. Only imports of the file's own top-level package are read, from the `src` root its path
names; a path with no `src` directory above it is not judged. A blob that will not parse is
skipped (the gate says why).

CONSUMED BY: `commit_kata.main`, at submit.
"""

import ast
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath

from mikemol.hooks import stacksnap
from mikemol.hooks.isolated import EnvRunner
from mikemol.hooks.stackrun import items_of
from mikemol.hooks.stacksnap import Frozen

ReadBlob = Callable[[str], str | None]
InHead = Callable[[str], bool]
_SRC = "src"


def src_root(path: str) -> PurePosixPath | None:
    """Find the `src` directory a source file's path names.

    Returns:
        the path up to and including the first `src` component, or None when there is none.

    """
    parts = PurePosixPath(path).parts
    if _SRC not in parts:
        return None
    return PurePosixPath(*parts[: parts.index(_SRC) + 1])


def candidates(text: str, root: PurePosixPath, top: str) -> set[str]:
    """List the module files `text` could be importing from its own package, under `root`.

    Returns:
        paths of the form `<root>/<dotted path>.py` for each import whose module starts with `top`.

    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == top:
                    found.add(str(root / (alias.name.replace(".", "/") + ".py")))
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module.split(".")[0] != top:
                continue
            base = node.module.replace(".", "/")
            found.add(str(root / (base + ".py")))
            found.update(str(root / base / (alias.name + ".py")) for alias in node.names)
    return found


def findings(
    entries: Sequence[tuple[str, Sequence[Frozen]]],
    read_blob: ReadBlob,
    in_head: InHead,
) -> list[str]:
    """Name every import of a module that only a later entry of the stack adds.

    `entries` is each entry's waypoint with its frozen files, in landing order.

    Returns:
        one line per finding: the file, the module path, and the entry that adds it.

    """
    added: dict[str, int] = {}
    for place, (_wp, files) in enumerate(entries):
        for frozen in files:
            if frozen.blob and frozen.path.endswith(".py"):
                added.setdefault(frozen.path, place)
    found: list[str] = []
    for place, (waypoint, files) in enumerate(entries):
        for frozen in files:
            root = src_root(frozen.path)
            if root is None or not frozen.blob or not frozen.path.endswith(".py"):
                continue
            text = read_blob(frozen.blob)
            if text is None:
                continue
            top = PurePosixPath(frozen.path).relative_to(root).parts[0]
            for module in sorted(candidates(text, root, top)):
                later = added.get(module, -1) > place
                if later and not in_head(module):
                    found.append(
                        f"{waypoint}: {frozen.path} imports {module}, which no earlier entry or "
                        f"HEAD carries (entry {added[module] + 1} adds it)"
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
