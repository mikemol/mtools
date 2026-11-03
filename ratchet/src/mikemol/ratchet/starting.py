# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The starting `ratchets.json` a repository can adopt, built from the census's own guesses (W1959).

    mikemol-ratchet declare REPO [--write]

github-8f's rule (2026-10-25) is that a gate must never guess from a file name, so the real fix for
a misread census is the owning repository DECLARING its ratchets (W1957). Writing that file by hand
for thirteen repositories is the friction that keeps them on the guess, so this prints the guess as
a declaration for the repository's own session to read, correct and commit.

⚑ IT OFFERS, IT DOES NOT DECIDE. Without `--write` it prints and writes nothing. With it, the file
is written only when there is none: an existing declaration is the repository's own word, and is
never overwritten, merged or extended here.

⚑ THE PROBABLE MISREADS ARE ALREADY OUT, BY THE CENSUS'S OWN EXCLUSIONS (W1956): resolutions maps,
configs named like baselines, scratch, tmp and session-export archives are not in the walk, so they
are not offered. A file the census could not READ is left out and named, because a declaration that
lists a broken baseline would pin the breakage.

⚑ THE DOCUMENT IS THE GUESS AND NOTHING MORE: path and kind, never a value, so the first census
after it is adopted reads the same files the guess did, now as declared rather than guessed.
"""

import json
from pathlib import Path

from mikemol.ratchet import declaration, fleetcensus, kinds


def document(repo: Path) -> tuple[str, list[str]]:
    """Build the starting declaration of one repository.

    Returns:
        the JSON text (path and kind per file, sorted by path, newline-terminated) and one note per
        file left out because it could not be read.

    Raises:
        declaration.DeclarationError: when the repository already declares its ratchets.

    """
    if declaration.read(repo) is not None:
        msg = (
            f"{declaration.NAME}: {repo.name} already declares its ratchets; it is not overwritten"
        )
        raise declaration.DeclarationError(msg)
    by_path: dict[str, fleetcensus.Row] = {
        row.ratchet: row for row in fleetcensus.census_repo(repo)
    }
    offered: list[dict[str, str]] = []
    notes: list[str] = []
    for path, row in sorted(by_path.items()):
        if row.kind not in kinds.KIND_NAMES:
            continue
        if row.value is None:
            notes.append(f"left out: {path} could not be read")
            continue
        offered.append({"path": path, "kind": row.kind})
    payload: dict[str, object] = {"ratchets": offered}
    return json.dumps(payload, indent=2) + "\n", notes


def write(repo: Path, text: str) -> Path:
    """Write the declaration where the census reads it, atomically, when there is none.

    Returns:
        the path written.

    Raises:
        declaration.DeclarationError: when one already exists, or a link is in its place.

    """
    target = repo / declaration.NAME
    if target.exists() or target.is_symlink():
        msg = f"{declaration.NAME}: {repo.name} already has one; it is not overwritten"
        raise declaration.DeclarationError(msg)
    staging = target.with_name(f"{target.name}.tmp")
    staging.write_text(text, encoding="utf-8")
    staging.replace(target)
    return target
