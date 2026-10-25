# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Judge a file that is NEW on disk under its real module name, so a mypy override applies (W1628).

The edit gate stages the edited bytes to a temp file and runs mypy on it. For a file that exists,
`--shadow-file` makes mypy read the staged bytes AS the real path, so its module name, its relative
imports and any `[[tool.mypy.overrides]]` keyed to that module all hold. For a file NOT YET ON DISK
there is nothing to shadow (mypy refuses `Cannot read file`), so the temp copy was judged under a
temp module name and an override for the real module could never apply (luthen-observability-d9).

⚑ THE FIX IS A MIRROR, MEASURED BEFORE IT WAS BUILT (2026-10-25, scratch packages with controls):
the staged bytes are written at the file's REAL relative path under a temp root and mypy runs from
that root with `MYPYPATH` naming the real project (and its `src`), so the module gets its real name
and the override applies, a module with no override is still judged (a planted type error still
fails), and its sibling imports resolve through MYPYPATH alone. Measured on a flat layout and on a
`src` layout whose parent is a PEP 420 namespace package.

⚑ AN `__init__.py` IS COPIED ONLY WHERE THE PROJECT HAS ONE. The namespace parent (`mikemol/`) has
none in this tree, and giving the mirror one would turn it into a regular package that shadows the
real namespace; measured both ways, the override applied either way, so the safe rule is to copy
the project's own shape and add nothing.

⚑ IT IS FOR A NEW FILE UNDER A CONFIG THAT HAS OVERRIDES, AND NOTHING ELSE. The house config carries
no `[[tool.mypy.overrides]]` (relief lives on the enumerable side), so for it the old path is
unchanged; this exists for the consumer whose config does.

CONSUMED BY: `pycheck.analyze` (W1628).
"""

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

_MARKERS = ("[[tool.mypy.overrides]]", "[mypy-")


@dataclass(frozen=True)
class Mirror:
    """A temp root holding the staged file at its real relative path, and how to point mypy."""

    root: Path
    subject: str
    mypy_path: str


def needed(path: str, config: Path) -> bool:
    """Say whether a file must be judged through a mirror.

    Returns:
        True for a file that does not exist yet under a config that has per-module overrides;
        False for an existing file or link, or a config with none or an unreadable one.

    """
    real = Path(path)
    if real.exists() or real.is_symlink():
        return False
    try:
        text = config.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return any(marker in text for marker in _MARKERS)


@contextmanager
def mirrored(path: str, content: str, config: Path) -> Iterator[Mirror | None]:
    """Stage `content` at `path`'s relative place under a temp root, removed on exit.

    Yields:
        the mirror; None when `path` is not under the config's directory.

    """
    base = config.parent.resolve()
    try:
        relative = Path(path).resolve().relative_to(base)
    except ValueError:
        yield None
        return
    with tempfile.TemporaryDirectory(prefix="mypy-mirror-") as raw:
        root = Path(raw)
        target = root / relative
        target.parent.mkdir(parents=True)
        target.write_text(content, encoding="utf-8")
        here = base
        for part in relative.parts[:-1]:
            here /= part
            if (here / "__init__.py").is_file():
                (root / here.relative_to(base) / "__init__.py").write_text("", encoding="utf-8")
        entries = [str(base)]
        if (base / "src").is_dir():
            entries.append(str(base / "src"))
        yield Mirror(root, relative.as_posix(), os.pathsep.join(entries))


@contextmanager
def judged(
    command: list[str], cwd: Path, path: str, content: str, config: Path | None
) -> Iterator[tuple[list[str], Path, str]]:
    """Say how to run mypy on `path`'s staged bytes: unchanged, or through a mirror.

    The subject is the LAST element of `command`, as `checkers.checker_argv` builds it. Through a
    mirror, that element becomes the real relative path, the command runs from the mirror's root,
    and `env` gives it MYPYPATH (the run has no environment argument).

    Yields:
        the command, the directory to run it in, and the mirror's subject whose appearances in the
        output stand for `path` (empty when there is no mirror).

    """
    if config is None or not needed(path, config):
        yield command, cwd, ""
        return
    with mirrored(path, content, config) as mirror:
        if mirror is None:
            yield command, cwd, ""
            return
        wrapped = ["env", f"MYPYPATH={mirror.mypy_path}", *command[:-1], mirror.subject]
        yield wrapped, mirror.root, mirror.subject
