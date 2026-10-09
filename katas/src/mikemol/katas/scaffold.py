# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Scaffold a repo's bazel files from host templates, and install its bazel pre-commit (W796, W876).

Ported from the host katas.py `bazelize`. Never overwrites: a file that exists is left alone and
named. `BUILD.bazel` is not scaffolded: its inputs are named files, never a glob or a directory
(operator 2026-10-06), so the repo's own list is the work and this cannot guess it.

⚑ The templates directory, the bazel version and the check that `//:precommit` passes are the
CALLER'S: this module writes files, it does not run bazel, so a hook is swapped only on the caller's
word that the target passed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

PLACEHOLDER = "@REPO@"
"""The word in a template that becomes the repo's name."""

SCAFFOLD = (("bazelrc", ".bazelrc"), ("MODULE.bazel", "MODULE.bazel"))
"""(template file, repo file) pairs; `.bazelversion` is written from the version, not a template."""

VERSION_FILE = ".bazelversion"


def render(templates: Path, template: str, repo: str) -> str:
    """Read a template with the repo's name filled in.

    Returns:
        the file text.

    """
    return (templates / template).read_text(encoding="utf-8").replace(PLACEHOLDER, repo)


def scaffold(root: Path, templates: Path, bazel_version: str) -> tuple[list[str], list[str]]:
    """Write each missing bazel file into `root`.

    Returns:
        the names written, and the names that already existed and were left alone.

    """
    wrote: list[str] = []
    left: list[str] = []
    wanted = [(template, name) for template, name in SCAFFOLD] + [("", VERSION_FILE)]
    for template, name in wanted:
        path = root / name
        if path.exists():
            left.append(name)
            continue
        text = f"{bazel_version}\n" if not template else render(templates, template, root.name)
        path.write_text(text, encoding="utf-8")
        wrote.append(name)
    return wrote, left


def install_hook(root: Path, templates: Path, *, target_passed: bool) -> str:
    """Swap `.githooks/pre-commit` for the bazel template, once the caller says //:precommit passed.

    Returns:
        '' when the hook was written; otherwise the reason it was not.

    """
    if not (root / "BUILD.bazel").exists():
        return f"{root.name}: no BUILD.bazel with //:precommit yet; write it first"
    if not target_passed:
        return f"{root.name}: //:precommit has not passed; hook NOT swapped"
    target = root / ".githooks" / "pre-commit"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(templates, "pre-commit", root.name), encoding="utf-8")
    return ""
