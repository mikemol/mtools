# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-new-dist NAME DESCRIPTION`: the shell around the pure core in `new_dist` (mtools:W945).

Reads the template distribution's files, writes the skeleton, applies the `MODULE.bazel` and
`INSTALL.md` edits, and runs `uv lock` in the new directory (the lock embeds the project name, so it
is generated rather than copied). ⚑ EVERYTHING IS CHECKED BEFORE ANYTHING IS WRITTEN: a bad name, an
existing directory, a missing template file or a failing edit refuses with the tree untouched.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from mikemol.hooks import new_dist

EXIT_REFUSED = 2
_OPERANDS = 2
_WITH_ROOT = 2


def scaffold(root: Path, name: str, description: str, *, lock: bool = True) -> list[str]:
    """Write a new distribution under `root`.

    Returns:
        the steps that remain for a human.

    Raises:
        ValueError: on a bad input, an existing directory or an unreadable template.

    """
    target = root / name
    if target.exists():
        msg = f"{target} already exists"
        raise ValueError(msg)
    source = root / new_dist.TEMPLATE
    try:
        template = {f: (source / f).read_text(encoding="utf-8") for f in new_dist.FILES}
        module = (root / "MODULE.bazel").read_text(encoding="utf-8")
        install = (root / "INSTALL.md").read_text(encoding="utf-8")
    except OSError as fault:
        msg = f"cannot read the template: {fault}"
        raise ValueError(msg) from fault
    files = new_dist.skeleton(name, description, template)
    module = new_dist.module_edit(module, name)
    install = new_dist.install_edit(install, name, description)
    for rel, text in files.items():
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (root / "MODULE.bazel").write_text(module, encoding="utf-8")
    (root / "INSTALL.md").write_text(install, encoding="utf-8")
    if lock:
        subprocess.run(["uv", "lock"], cwd=target, check=True)
    return [
        f"bazel build //{name}:.venv",
        f"uv venv + sync in {name}/ for the host tools",
        f"mikemol-gen-warrants --write {name.upper()} tests.test_smoke=smoke",
        f"mikemol-commit . --waypoint W<n> --subject 'add {name}' {name} MODULE.bazel INSTALL.md",
    ]


def main(argv: list[str] | None = None) -> int:
    """Scaffold a distribution; refuse by name and write nothing on a bad input.

    Returns:
        0 on success, 2 on a refusal.

    """
    rest = list(sys.argv[1:] if argv is None else argv)
    lock = "--no-lock" not in rest
    rest = [a for a in rest if a != "--no-lock"]
    root = Path.cwd()
    if len(rest) >= _WITH_ROOT and rest[0] == "--root":
        root = Path(rest[1])
        rest = rest[2:]
    if len(rest) != _OPERANDS:
        sys.stderr.write("usage: mikemol-new-dist [--root DIR] [--no-lock] NAME DESCRIPTION\n")
        return EXIT_REFUSED
    try:
        steps = scaffold(root, rest[0], rest[1], lock=lock)
    except ValueError as fault:
        sys.stderr.write(f"mikemol-new-dist: {fault}\n")
        return EXIT_REFUSED
    sys.stdout.write("scaffolded; remaining:\n" + "".join(f"  {s}\n" for s in steps))
    return 0
