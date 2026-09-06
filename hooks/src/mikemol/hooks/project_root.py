# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Which project governs a file — the nearest `pyproject.toml` at or above it.

⚑⚑⚑ A CHECKER POINTED AT THE WRONG CONFIG IS A CHECKER THAT AGREES WITH YOU, AND THE HOOK WAS
POINTING AT ITS OWN. `pycheck_analyze` derives the project from the HOOK's location, so every
file it checks gets THIS repo's bar regardless of which repo the file lives in. Inside substrate
that is correct and invisible; the moment a second repo is edited in the same session it is
wrong in both directions at once — the foreign file is measured against rules it never adopted,
and the rules it DID adopt are never applied.

⚑⚑ MEASURED, NOT SUPPOSED (2026-08-31). Creating a PEP 420 namespace package in a sibling repo
was refused with `INP001: part of an implicit namespace package. Add an __init__.py` — a rule
that is correct under substrate's config and EXACTLY BACKWARDS for a namespace distribution,
where the absent `__init__.py` is the property the whole package rests on. The hook was
demanding the destruction of the thing being built.

⚑⚑ AND THE STAGING DIRECTORY MOVES WITH THE CONFIG, WHICH IS WHY THIS RETURNS A ROOT RATHER
THAN A FILE. ruff and mypy discover configuration by walking UP from the file they are handed,
so a tempfile staged in the wrong project inherits the wrong `pyproject.toml` even when one is
named explicitly — and the editable install that resolves a half-migrated module's sibling
imports is the one in THAT project's venv. Config, staging and interpreter are one decision.

⚑ THE WALK STOPS AT THE FILESYSTEM ROOT AND REPORTS NOTHING RATHER THAN GUESSING. A file under
no project at all is a real case (a scratch file in `/tmp`, a path the caller invented), and
answering it with some default project would apply a bar nobody chose — the same defect one
level out.

⚑⚑ AND `absolute()`, NEVER `resolve()`, MATCHING THE HOOK THIS SERVES. The hooks are themselves
SYMLINKED into other checkouts; a resolved path would walk up from substrate's tree and hand an
adopting repo substrate's config, which is the very defect this module exists to remove. That is
the opposite of the ruling for a tool locating its OWN home, where following the symlink is
required — two rules that look contradictory and are not, because they answer different
questions: *where do I live* versus *whose file is this*.
"""

from __future__ import annotations

from pathlib import Path

# The file whose presence declares a directory a project root.
MARKER = "pyproject.toml"


def project_for(path: str | Path) -> Path | None:
    """Return the nearest directory at or above `path` holding a `pyproject.toml`.

    ⚑ `absolute()` RATHER THAN `resolve()` — see the module note. The caller's path is taken as
    given: a file reached through a symlink belongs to the project it was reached THROUGH, which
    is what an adopting repo means by adopting.

    Returns:
        nearest directory at or above `path` holding a `pyproject.toml`.

    """
    start = Path(path).absolute()
    here = start if start.is_dir() else start.parent
    for candidate in (here, *here.parents):
        if (candidate / MARKER).is_file():
            return candidate
    return None


def config_for(path: str | Path) -> Path | None:
    """Return the `pyproject.toml` governing `path`, or None when it is under no project.

    Returns:
        `pyproject.toml` governing `path`, or None when it is under no project.

    """
    root = project_for(path)
    return (root / MARKER) if root is not None else None


def venv_python_for(path: str | Path) -> Path | None:
    """Return the interpreter of the project governing `path`, when it has one.

    ⚑ THE INTERPRETER IS PART OF THE SAME DECISION. A checker run from another project's venv
    resolves that project's installed packages, so a half-migrated module's sibling imports
    would resolve against the wrong editable install — silently, and in the direction that finds
    less. A project without a venv returns None so the caller can say so rather than falling
    back to whichever interpreter happens to be running.

    Returns:
        interpreter of the project governing `path`, when it has one.

    """
    root = project_for(path)
    if root is None:
        return None
    candidate = root / ".venv" / "bin" / "python3"
    return candidate if candidate.exists() else None
