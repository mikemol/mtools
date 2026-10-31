# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W2201 (github:W92): a read-only census of ONE repository's config surfaces, as JSON.

    survey(repo)   # {"schema": 1, "repo": "mtools", "surfaces": [{...}, ...]}

For each surface (CLAUDE.md, skills, settings, hooks, the loop prompt, the standing set, memory,
local policy) the census names four things, in fixed keys so a fleet reader can aggregate without
parsing prose:

    declared       the repository-relative paths where the surface is written
    changed_by     what edits it
    loaded_by      what reads it into a session
    reviewed_by    what gates a change to it

⚑ THE CONTRACT IS THE KEYS (schema 1): `schema` (integer), `repo` (the directory name), `surfaces`
(a list, in the fixed order of SURFACES) of objects with `surface` (a string) and the four list
fields above, each a sorted list of strings. A new field is a new schema number, never a silent
addition, because nemik's aggregation (nemik:W1325) reads these names.

⚑ A REPOSITORY READS ONLY ITSELF (operator ruling: repos do not know siblings exist): the loop
prompt that lives in a parent directory, and the auto-memory directory under the user's home, are
outside this repository, so they are reported with an empty `declared` rather than looked up. The
fleet view across repositories is the aggregator's, over each repository's own output.

⚑ DERIVED, NOT ASSUMED: `declared` is what exists on disk; `reviewed_by` names the git hook or the
review file a change would meet, only when that file exists. `changed_by` and `loaded_by` are the
fixed names of the writers and readers this toolchain has, and a surface with none is an empty
list, which is a finding, not an omission.
"""

import json
from dataclasses import dataclass
from pathlib import Path

SCHEMA = 1
_REVIEW_FILES = {
    ".githooks/pre-commit": "git pre-commit gate",
    ".github/CODEOWNERS": "CODEOWNERS review",
    "CODEOWNERS": "CODEOWNERS review",
}


@dataclass(frozen=True)
class Surface:
    """One config surface: where it may be declared and who changes and loads it."""

    name: str
    globs: tuple[str, ...]
    changed_by: tuple[str, ...]
    loaded_by: tuple[str, ...]


_EDIT = ("edit tools",)
_CODE = ("claude-code",)
SURFACES = (
    Surface("claude_md", ("CLAUDE.md", ".claude/CLAUDE.md"), _EDIT, _CODE),
    Surface("skills", (".claude/skills/*/SKILL.md",), _EDIT, ("claude-code skill listing",)),
    Surface(
        "settings",
        (".claude/settings.json", ".claude/settings.local.json"),
        ("operator",),
        ("claude-code settings",),
    ),
    Surface("hooks", ("hooks/bin/*", ".claude/hooks/*"), _EDIT, ("claude-code settings",)),
    Surface("loop_prompt", (".claude/loop-prompt.md",), _EDIT, ("cron tick prompt",)),
    Surface(
        "standing",
        (".claude/paths-forward.json",),
        ("mikemol-paths-forward --standing-set",),
        ("mikemol-paths-forward --tick-open",),
    ),
    Surface("memory", (".claude/memory/*.md", "memory/*.md"), _EDIT, _CODE),
    Surface("policy", ("*.rego", "policy/**/*.rego", ".claude/**/*.rego"), _EDIT, ()),
)


def _found(repo: Path, surface: Surface) -> list[str]:
    paths = {
        p.relative_to(repo).as_posix()
        for pattern in surface.globs
        for p in repo.glob(pattern)
        if p.is_file() and not p.is_symlink()
    }
    return sorted(paths)


def _reviews(repo: Path) -> list[str]:
    return sorted({label for name, label in _REVIEW_FILES.items() if (repo / name).is_file()})


def survey(repo: Path) -> dict[str, object]:
    """Census one repository's config surfaces.

    Returns:
        `{"schema", "repo", "surfaces"}` with one object per surface in SURFACES order; a surface
        with nothing declared keeps its place with an empty `declared` and `reviewed_by`.

    """
    reviews = _reviews(repo)
    surfaces: list[object] = []
    for surface in SURFACES:
        declared = _found(repo, surface)
        row: dict[str, object] = {
            "surface": surface.name,
            "declared": declared,
            "changed_by": sorted(surface.changed_by),
            "loaded_by": sorted(surface.loaded_by),
            "reviewed_by": reviews if declared else [],
        }
        surfaces.append(row)
    return {"schema": SCHEMA, "repo": repo.name, "surfaces": surfaces}


def to_json(repo: Path) -> str:
    """Render a repository's census as stable JSON.

    Returns:
        the document, keys sorted, one trailing newline.

    """
    return json.dumps(survey(repo), indent=2, sort_keys=True) + "\n"
