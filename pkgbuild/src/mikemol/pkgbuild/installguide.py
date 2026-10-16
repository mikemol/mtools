# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Check INSTALL.md against the dists it lists: each dist, its name, its scripts, the count (W1146).

    mikemol-wheel install-guide ROOT [GUIDE]

INSTALL.md is the first thing someone installing mtools reads, and a hand-kept list of 34 dists
with their console scripts drifts: it said 31 while the tree had 34, and named none of three
dists. This reads each top-level `pyproject.toml` for the project name and `[project.scripts]` keys
and compares them with the guide's bullets, one JSON line per disagreement.

⚑ THE GUIDE IS READ, NOT RENDERED: a bullet starts with the directory and the distribution name in
backticks, continues on lines that start with two spaces, and names its scripts as the backticked
words after `Script:` or `Scripts:`; a library has none. The sentence "There are N of them" is
checked against the number of dists.

⚑ NOTHING IS WRITTEN: a disagreement is a finding for a person (or a later fix mode) to resolve,
because the one-line description is prose that no tool should invent.

CONSUMED BY: `mikemol-wheel install-guide`, the off-host installable-guide card (W1146).
"""

import json
import re
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import cast

USAGE = 2
ROOT_ONLY = 1
ROOT_AND_GUIDE = 2
BULLET = re.compile(r"^- `([^`]+)` \(`([^`]+)`\)")
COUNT = re.compile(r"There are (\d+) of them")
SCRIPTS = re.compile(r"Scripts?:(.*)", re.DOTALL)
TICKED = re.compile(r"`([^`]+)`")
Entry = tuple[str, tuple[str, ...]]


def _group(match: re.Match[str], number: int) -> str:
    return cast("str", match.group(number))


def listed(text: str) -> dict[str, Entry]:
    """Read the guide's bullets.

    Returns:
        for each listed directory, its distribution name and its scripts.

    """
    blocks: list[str] = []
    for line in text.splitlines():
        if BULLET.match(line):
            blocks.append(line)
        elif blocks and line.startswith("  ") and line.strip():
            blocks[-1] += " " + line.strip()
        elif not line.startswith("  "):
            blocks.append("")
    found: dict[str, Entry] = {}
    for block in blocks:
        head = BULLET.match(block)
        if head is None:
            continue
        said = SCRIPTS.search(block)
        words = [_group(m, 1) for m in TICKED.finditer(_group(said, 1))] if said else []
        found[_group(head, 1)] = (_group(head, 2), tuple(words))
    return found


def declared(root: Path) -> dict[str, Entry]:
    """Read each top-level dist's name and console scripts from its `pyproject.toml`.

    Returns:
        for each directory holding a `[project]` table, its name and sorted scripts.

    """
    found: dict[str, Entry] = {}
    for pyproject in sorted(root.glob("*/pyproject.toml")):
        if pyproject.parent.is_symlink():
            continue
        table = cast("dict[str, object]", tomllib.loads(pyproject.read_text(encoding="utf-8")))
        project = table.get("project")
        if not isinstance(project, dict):
            continue
        fields = cast("dict[str, object]", project)
        scripts = fields.get("scripts", {})
        keys = sorted(cast("dict[str, object]", scripts)) if isinstance(scripts, dict) else []
        found[pyproject.parent.name] = (str(fields.get("name", "")), tuple(keys))
    return found


def findings(text: str, root: Path) -> list[dict[str, object]]:
    """Compare the guide with the tree.

    Returns:
        one finding per disagreement: `kind`, the directory and the two sides.

    """
    said, real = listed(text), declared(root)
    out: list[dict[str, object]] = []
    out.extend({"kind": "not-listed", "dist": d} for d in sorted(real.keys() - said.keys()))
    out.extend({"kind": "listed-but-absent", "dist": d} for d in sorted(said.keys() - real.keys()))
    for name in sorted(said.keys() & real.keys()):
        (guide_name, guide_scripts), (real_name, real_scripts) = said[name], real[name]
        if guide_name != real_name:
            out.append({"kind": "name", "dist": name, "guide": guide_name, "tree": real_name})
        if tuple(sorted(guide_scripts)) != real_scripts:
            out.append(
                {
                    "kind": "scripts",
                    "dist": name,
                    "guide": sorted(guide_scripts),
                    "tree": list(real_scripts),
                }
            )
    count = COUNT.search(text)
    if count is None or int(_group(count, 1)) != len(real):
        said_count = _group(count, 1) if count else None
        out.append({"kind": "count", "guide": said_count, "tree": len(real)})
    return out


def run(args: Sequence[str]) -> int:
    """Run `ROOT [GUIDE]`: one JSON line per disagreement.

    Returns:
        0 when the guide matches the tree, 1 when it does not, 2 for a usage error.

    """
    if len(args) not in {ROOT_ONLY, ROOT_AND_GUIDE} or not Path(args[0]).is_dir():
        sys.stderr.write("usage: mikemol-wheel install-guide ROOT [GUIDE]\n")
        return USAGE
    root = Path(args[0])
    guide = Path(args[1]) if len(args) == ROOT_AND_GUIDE else root / "INSTALL.md"
    try:
        text = guide.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"install-guide: cannot read {guide}: {exc.strerror}\n")
        return USAGE
    found = findings(text, root)
    sys.stdout.writelines(json.dumps(f, sort_keys=True) + "\n" for f in found)
    return 1 if found else 0
