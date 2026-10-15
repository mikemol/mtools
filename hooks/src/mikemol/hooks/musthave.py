# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The tracked list of fixes a pin must contain, and the verb that grows it (mtools:W1137).

    mikemol-repin --must-have SHA --dists D --reason R [--requires SHA ...] [--write]
    mikemol-repin --check-must-have [--mtools DIR]

A consumer that pins an mtools distribution at a commit that predates a fix is stale in a way a
par sha alone hides (luthen-observability:W968: a stale `repin_par.txt` hid pins older than
04d4f46). `repin/must_have.json` names the fixes that matter: a JSON list of objects with `sha` (a
full 40-hex commit), `dists` (the distributions the fix is in), `reason` (one line) and `requires`
(a list of full shas that must be in a pin before this one means anything). A reader decides a pin
is behind when `git merge-base --is-ancestor SHA PIN` fails for a fix that names the pin's dist.

⚑ THE FILE IS READ AT A COMMIT, NEVER FROM A WORKING TREE (the reader's rule): an uncommitted entry
never counts, so a fix's sha exists only after its commit and the entry is added in a LATER one.

⚑ A SHA THAT IS NOT A COMMIT IN HISTORY IS REFUSED, at add time and by the check: an entry naming
nothing would make every pin look behind a fix nobody can fetch. `git cat-file -e SHA^{commit}`
through the same process seam as the rest of `mikemol-repin`.

⚑ IDEMPOTENT ON SHA: adding a sha already present unions its `dists` and `requires` and takes the
new `reason`; it says `unchanged` when that changes nothing, so a rerun is a no-op.

CONSUMED BY: `mikemol-repin` and luthen-observability's repin census (W968).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.hooks import repin

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    type Runner = Callable[[Sequence[str], Path], tuple[int, str]]

Entry = dict[str, object]
FILE = Path("repin") / "must_have.json"
_ONE_LINE = re.compile(r"[^\r\n]+")


def _strings(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    items = cast("list[object]", value)
    return [str(i) for i in items] if all(isinstance(i, str) for i in items) else None


def _full(sha: str) -> bool:
    try:
        repin.check_sha(sha)
    except ValueError:
        return False
    return True


def _sha_of(entry: Entry) -> str:
    return str(entry.get("sha", ""))


def shape_problems(entries: Sequence[Entry]) -> list[str]:
    """Say what is wrong with the entries' shape, entry by entry.

    Returns:
        one message per problem; empty when every entry has a full sha, a non-empty dist list of
        strings, a one-line reason and a list of full shas in `requires`, and no sha repeats.

    """
    found: list[str] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        sha = entry.get("sha")
        if not isinstance(sha, str) or not _full(sha):
            found.append(f"entry {index}: sha must be a full 40-hex commit")
            continue
        where = sha[:12]
        if sha in seen:
            found.append(f"{where}: sha appears twice")
        seen.add(sha)
        if not _strings(entry.get("dists")):
            found.append(f"{where}: dists must be a non-empty list of strings")
        reason = entry.get("reason")
        if not isinstance(reason, str) or _ONE_LINE.fullmatch(reason) is None:
            found.append(f"{where}: reason must be one non-empty line")
        requires = _strings(entry.get("requires"))
        if requires is None or not all(_full(r) for r in requires):
            found.append(f"{where}: requires must be a list of full 40-hex commits")
    return found


def load(path: Path) -> list[Entry] | str:
    """Read the file, or say why it cannot be read.

    Returns:
        the entries (an absent file is an empty list), or the reason as a string.

    """
    if not path.is_file():
        return []
    try:
        raw = cast("object", json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        return f"cannot read {path}: {exc}"
    if not isinstance(raw, list) or not all(isinstance(e, dict) for e in cast("list[object]", raw)):
        return f"{path} is not a JSON list of objects"
    return cast("list[Entry]", raw)


def save(path: Path, entries: Sequence[Entry]) -> None:
    """Write the entries atomically, one object per sha in a stable order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(entries, key=_sha_of)
    scratch = path.with_name(path.name + ".tmp")
    scratch.write_text(json.dumps(ordered, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    scratch.replace(path)


def add(
    entries: Sequence[Entry], sha: str, dists: Sequence[str], reason: str, requires: Sequence[str]
) -> tuple[list[Entry], str]:
    """Add a fix, or merge it into the entry for the same sha.

    Returns:
        the new list and `added`, `updated` or `unchanged`.

    """
    merged = [dict(e) for e in entries]
    for entry in merged:
        if entry.get("sha") != sha:
            continue
        before = (
            sorted(_strings(entry.get("dists")) or []),
            sorted(_strings(entry.get("requires")) or []),
            entry.get("reason"),
        )
        after = (
            sorted(set(before[0]) | set(dists)),
            sorted(set(before[1]) | set(requires)),
            reason,
        )
        entry.update({"dists": after[0], "requires": after[1], "reason": reason})
        return merged, "unchanged" if after == before else "updated"
    fresh: Entry = {
        "sha": sha,
        "dists": sorted(set(dists)),
        "reason": reason,
        "requires": sorted(set(requires)),
    }
    return [*merged, fresh], "added"


def at_commit(commit: str, mtools: Path, runner: Runner) -> list[Entry] | str:
    """Read the fixes list as it stood at a commit, never from the working tree (W1138).

    ⚑ AN UNCOMMITTED ENTRY NEVER COUNTS: the list is read with `git show COMMIT:<file>`, so a pin
    is measured against fixes a consumer can actually fetch.

    ⚑ NO LIST AT THE COMMIT IS NOT AN EMPTY LIST: a par older than the file, or a checkout
    that cannot show it, gives a reason and so no measurement. Reading it as "no fixes
    required" would write a 0 (current) for every wheel against a list nobody could read.

    Returns:
        the entries, or the reason they cannot be read.

    """
    status, said = runner(["git", "show", f"{commit}:{FILE.as_posix()}"], mtools)
    if status != 0:
        return f"{FILE} cannot be read at {commit[:12]}: wheels are not measured"
    try:
        raw = cast("object", json.loads(said))
    except ValueError as exc:
        return f"{FILE} at {commit[:12]} is not JSON: {exc}"
    if not isinstance(raw, list) or not all(isinstance(e, dict) for e in cast("list[object]", raw)):
        return f"{FILE} at {commit[:12]} is not a JSON list of objects"
    return cast("list[Entry]", raw)


def missing_for(
    pin: str, dist: str, entries: Sequence[Entry], mtools: Path, runner: Runner
) -> tuple[str, ...] | None:
    """List the fixes a pin of a distribution does not contain, by commit ancestry.

    ⚑ ONLY FIXES THAT NAME THE DIST COUNT: a fence fix does not make a hooks-only pin behind.
    ⚑ A PIN GIT CANNOT RESOLVE IS NOT MEASURED, which is None and never "current": no claim is made
    about a commit that is not in this history.

    Returns:
        the shas of the fixes that are not ancestors of the pin (empty when it has them all), or
        None when the pin is not a commit in the mtools history.

    """
    if runner(["git", "cat-file", "-e", f"{pin}^{{commit}}"], mtools)[0] != 0:
        return None
    absent: list[str] = []
    for entry in entries:
        if dist not in (_strings(entry.get("dists")) or []):
            continue
        fix = _sha_of(entry)
        status, _said = runner(["git", "merge-base", "--is-ancestor", fix, pin], mtools)
        if status == 1:
            absent.append(fix)
        elif status != 0:
            return None
    return tuple(absent)


def history_problems(entries: Sequence[Entry], repo: Path, runner: Runner) -> list[str]:
    """Say which shas are not commits in the repository's history.

    Returns:
        one message per sha or required sha git cannot find as a commit; empty when all resolve.

    """
    named: dict[str, str] = {}
    for entry in entries:
        sha = _sha_of(entry)
        named.setdefault(sha, sha[:12])
        for needed in _strings(entry.get("requires")) or []:
            named.setdefault(needed, f"{sha[:12]} requires {needed[:12]}")
    found: list[str] = []
    for sha, label in named.items():
        status, _said = runner(["git", "cat-file", "-e", f"{sha}^{{commit}}"], repo)
        if status != 0:
            found.append(f"{label}: {sha} is not a commit in this history")
    return found
