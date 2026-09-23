# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Moving a baseline must not change it: a JSON baseline may differ from a revision ONLY at paths.

⚑⚑ THIS IS THE FILE-CONTENT TWIN OF `core.partition`'s MOVE. There, a relocated finding is a key
whose identity (everything but the path) survives while its path changes. Here the unit is a whole
JSON baseline document: a reorganisation may rewrite every `path` leaf in it, and nothing else. A
non-path leaf that changed alongside a remap is debt edited in under cover of a move.

Ported from gabion `src/gabion/tooling/repo/baseline_path_remap_guard.py`, and TIGHTENED where
the origin's predicate was unsound (mtools review, probes P2/P4/P5/P7):

    compare  : the JSON at `<rev>:<file>` (git) against the working-tree file
    pointer  : a TUPLE of segments (dict key or list index), rendered as an RFC 6901 JSON
               Pointer. ⚑ The origin joined keys with `.` unescaped, so a key literally named
               `x.path` read as a path leaf (P5).
    path leaf: the last segment is the dict key `path` AND the value is a string on BOTH sides.
               ⚑ A deleted `path` key (P2) or a string that became a container carrying a
               payload (P4) is a NON-path leaf; the origin passed both.
    collision: a list whose elements now share a `path` more often than at `rev` is refused —
               two entries collapsed onto one path is a duplicated identity, not a move (P7).
    exit     : CLEAN 0 every diff is path-only (or there is none), REFUSED 1 some non-path leaf
               differs or paths collide, UNREADABLE 2 a file could not be read or parsed.

⚑⚑ RESIDUE, NOT CAUGHT (P1): two entries SWAPPING paths passes. Each entry's non-path content is
unchanged at its own list index and only its `path` leaf moved, so the rule "any path rewrite is
allowed" admits it — yet the counts have changed OWNER (a's debt now reads as b's). Catching it
needs a notion of which path an identity may legitimately move to, which is `core.partition`'s
path-plausibility, not something this document-level guard can see. Recorded, not claimed.

⚑ RESIDUE, REFUSED (P6): a pure REORDER of list entries is refused, though no identity changed.
Lists compare by index, so each moved entry's `rule`/`count` differ at its new index. This errs
toward refusal (a false alarm, never a laundered change); admitting it would need entries matched
by identity rather than position. Pinned by a test so a change here is a deliberate one.

⚑ `write` REPLACES gabion's `--rewrite-path-only`, and is keyword-required for the reason
`core.write_baseline` gives: a mutation nobody asked for in the call is one nobody can find. It is
ALL-OR-NOTHING: every file is loaded and every projection verified before any file is written.
The write itself is two-phase: each output goes to a temp file in its target's own directory
(carrying the target's permission bits), and only once EVERY temp is written are they
`os.replace`d into place. Any failure while writing temps removes them all and exits UNREADABLE
with "nothing written".
⚑ RESIDUE, NOT CAUGHT (replace phase): `os.replace` is atomic PER FILE (same directory, so same
filesystem), but the sequence of replaces is not a transaction. If replace k fails (e.g. the
target was made read-only-immutable, or its directory vanished, between the phases), files
1..k-1 ARE rewritten and k.. are not; the remaining temps are removed, the run exits
UNREADABLE, and the error line names every file already replaced. A crash (power loss, SIGKILL)
mid-phase can likewise leave some files replaced and a stray `.<name>.*.tmp` beside a target.
A written file keeps the source's indent width (or compactness), key order, ASCII-ness and
trailing newline; other whitespace is re-rendered by `json.dumps`. A file with nothing to
discard is not rewritten at all.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Iterator

type Json = bool | int | float | str | list[Json] | dict[str, Json] | None
type Segment = str | int
type Pointer = tuple[Segment, ...]

CLEAN = 0
REFUSED = 1
UNREADABLE = 2
PATH_KEY = "path"


class Missing(Enum):
    """A side on which the leaf does not exist — never confusable with any JSON value."""

    MISSING = "<MISSING>"


type Side = Json | Missing


def render(pointer: Pointer) -> str:
    """Render a pointer as an RFC 6901 JSON Pointer (`~` and `/` escaped).

    Returns:
        the pointer text; the document root is the empty string.

    """
    return "".join("/" + str(seg).replace("~", "~0").replace("/", "~1") for seg in pointer)


@dataclass(frozen=True, slots=True)
class LeafDiff:
    """One leaf that differs between the revision and the working tree."""

    pointer: Pointer
    before: Side
    after: Side

    @property
    def is_path(self) -> bool:
        """Report whether this leaf is a path field, the only kind a remap may change."""
        return (bool(self.pointer) and self.pointer[-1] == PATH_KEY
                and isinstance(self.before, str) and isinstance(self.after, str))


def _dict_diffs(before: dict[str, Json], after: dict[str, Json],
                pointer: Pointer) -> Iterator[LeafDiff]:
    for key in sorted(set(before) | set(after)):
        here = (*pointer, key)
        if key not in before:
            yield LeafDiff(here, Missing.MISSING, after[key])
        elif key not in after:
            yield LeafDiff(here, before[key], Missing.MISSING)
        else:
            yield from leaf_diffs(before[key], after[key], here)


def _list_diffs(before: list[Json], after: list[Json], pointer: Pointer) -> Iterator[LeafDiff]:
    for idx in range(max(len(before), len(after))):
        here = (*pointer, idx)
        if idx >= len(before):
            yield LeafDiff(here, Missing.MISSING, after[idx])
        elif idx >= len(after):
            yield LeafDiff(here, before[idx], Missing.MISSING)
        else:
            yield from leaf_diffs(before[idx], after[idx], here)


def leaf_diffs(before: Json, after: Json, pointer: Pointer = ()) -> Iterator[LeafDiff]:
    """Yield every leaf at which `before` and `after` differ.

    ⚑ A TYPE CHANGE IS ONE LEAF, not a descent: a dict that became a list differs at its own
    pointer — and `1` → `1.0` or `1` → `true` is a type change, though Python calls them equal.

    Yields:
        each differing leaf, dict keys sorted, list indices in order.

    """
    if type(before) is not type(after):
        yield LeafDiff(pointer, before, after)
    elif isinstance(before, dict) and isinstance(after, dict):
        yield from _dict_diffs(before, after, pointer)
    elif isinstance(before, list) and isinstance(after, list):
        yield from _list_diffs(before, after, pointer)
    elif before != after:
        yield LeafDiff(pointer, before, after)


def _duplicate_paths(items: list[Json]) -> int:
    paths = [path for item in items
             if isinstance(item, dict) and isinstance(path := item.get(PATH_KEY), str)]
    return len(paths) - len(set(paths))


def path_collisions(before: Json, after: Json, pointer: Pointer = ()) -> Iterator[Pointer]:
    """Yield each list in which more elements share a `path` than did at the revision.

    Yields:
        the pointer of each list whose path duplicates grew.

    """
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) & set(after)):
            yield from path_collisions(before[key], after[key], (*pointer, key))
    elif isinstance(before, list) and isinstance(after, list):
        if _duplicate_paths(after) > _duplicate_paths(before):
            yield pointer
        for idx in range(min(len(before), len(after))):
            yield from path_collisions(before[idx], after[idx], (*pointer, idx))


def project_path_only(before: Json, after: Json) -> Json:
    """Return `before` with only `after`'s admissible path leaves applied.

    ⚑ ADDED AND REMOVED KEYS ARE UNDONE TOO: the result has exactly `before`'s shape, and a
    `path` is taken from `after` only where it is a string on both sides — so a payload hidden
    under a `path` key (P4) is discarded, not laundered.

    Returns:
        the path-only projection of `after` onto `before`.

    """
    if isinstance(before, dict) and isinstance(after, dict):
        out: dict[str, Json] = {}
        for key, val in before.items():
            if key not in after:
                out[key] = val
                continue
            new = after[key]
            if key == PATH_KEY and isinstance(val, str) and isinstance(new, str):
                out[key] = new
            else:
                out[key] = project_path_only(val, new)
        return out
    if isinstance(before, list) and isinstance(after, list):
        return [project_path_only(val, after[idx]) if idx < len(after) else val
                for idx, val in enumerate(before)]
    return before


def _load_rev(root: Path, rev: str, rel: str) -> Json:
    # ⚑ `--end-of-options`: without it a rev such as `--output=/x` is read by git as an OPTION.
    result = subprocess.run(
        ["git", "-C", str(root), "show", "--end-of-options", f"{rev}:{rel}"],
        capture_output=True, text=True, check=False)
    if result.returncode != 0:
        msg = f"unable to load {rev}:{rel}: {result.stderr.strip()}"
        raise ValueError(msg)
    return cast("Json", json.loads(result.stdout))


def _render_like(doc: Json, source: str) -> str:
    """Serialise `doc` in the source's indent width, ASCII-ness and trailing newline.

    Returns:
        the JSON text.

    """
    lines = source.strip().splitlines()
    indent: int | str | None = None
    for line in lines[1:]:
        stripped = line.lstrip(" \t")
        if stripped != line:
            lead = line[: len(line) - len(stripped)]
            indent = lead if "\t" in lead else len(lead)
            break
    text = json.dumps(doc, indent=indent, ensure_ascii=source.isascii())
    return text + "\n" if source.endswith("\n") else text


@dataclass(frozen=True, slots=True)
class _Loaded:
    rel: str
    before: Json
    after: Json
    source: str


def _load(root: Path, rev: str, rel: str) -> _Loaded:
    before = _load_rev(root, rev, rel)
    source = (root / rel).read_text(encoding="utf-8")
    return _Loaded(rel, before, cast("Json", json.loads(source)), source)


def _verdict(item: _Loaded) -> tuple[bool, list[str]]:
    diffs = list(leaf_diffs(item.before, item.after))
    collisions = list(path_collisions(item.before, item.after))
    if not diffs and not collisions:
        return False, [f"{item.rel}: no changes"]
    non_path = [d for d in diffs if not d.is_path]
    lines = [f"{item.rel}: total_leaf_diffs={len(diffs)} non_path_leaf_diffs={len(non_path)}"]
    lines.extend(f"  ! {render(d.pointer) or '/'}" for d in non_path)
    lines.extend(f"  ! {render(p) or '/'}: path collision" for p in collisions)
    return bool(non_path or collisions), lines


def _discard(temps: list[tuple[Path, Path]]) -> None:
    for temp, _ in temps:
        temp.unlink(missing_ok=True)


def _stage(target: Path, text: str, temps: list[tuple[Path, Path]]) -> None:
    """Write `text` to a temp beside `target` with its mode; record it in `temps` at once."""
    fd, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    temp = Path(name)
    temps.append((temp, target))
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    temp.chmod(stat.S_IMODE(target.stat().st_mode))


def _write_all(root: Path, outputs: list[tuple[str, str]]) -> list[str]:
    """Write every output to a sibling temp, then replace them all into place.

    Returns:
        report lines on failure (empty on success).

    """
    temps: list[tuple[Path, Path]] = []
    for rel, text in outputs:
        try:
            _stage(root / rel, text, temps)
        except OSError as exc:
            _discard(temps)
            return [f"{rel}: error: {exc}", "nothing written"]
    for idx, (temp, target) in enumerate(temps):
        try:
            temp.replace(target)
        except OSError as exc:
            _discard(temps[idx:])
            done = ", ".join(outputs[j][0] for j in range(idx)) or "none"
            return [f"{outputs[idx][0]}: error: {exc}",
                    f"replace phase failed; already rewritten: {done}"]
    return []


def remap_guard(root: Path, files: list[str], *, rev: str = "HEAD",
                write: bool) -> tuple[int, list[str]]:
    """Refuse any baseline whose diff against `rev` touches a non-path leaf. Return (code, lines).

    With `write=True` each file's path-only projection is computed and verified FIRST; only if
    every file loads and every projection passes are the files written — so a failed write run
    leaves every file as the author left it, and a successful one exits CLEAN.

    Returns:
        (exit code, report lines): CLEAN, REFUSED or UNREADABLE.

    """
    loaded: list[_Loaded] = []
    for rel in files:
        try:
            loaded.append(_load(root, rev, rel))
        except (OSError, ValueError) as exc:  # JSONDecodeError, UnicodeDecodeError: ValueError
            return UNREADABLE, [f"{rel}: error: {exc}", "nothing written" if write else
                                "remap guard could not read every file"]
    if write:
        projected = [_Loaded(i.rel, i.before, project_path_only(i.before, i.after), i.source)
                     for i in loaded]
        verdicts = [_verdict(p) for p in projected]
        if any(bad for bad, _ in verdicts):
            lines = [line for _, report in verdicts for line in report]
            return REFUSED, [*lines, "path-only projection REFUSED; nothing written"]
        outputs = [(old.rel, _render_like(new.after, old.source))
                   for old, new in zip(loaded, projected, strict=True)
                   if any(leaf_diffs(new.after, old.after))]
        failure = _write_all(root, outputs)
        if failure:
            return UNREADABLE, failure
        lines = [f"{rel}: rewritten path-only" for rel, _ in outputs]
        loaded = projected
    else:
        lines = []
    violated = False
    for item in loaded:
        bad, report = _verdict(item)
        violated = violated or bad
        lines.extend(report)
    if violated:
        return REFUSED, [*lines, "non-path baseline changes REFUSED"]
    return CLEAN, [*lines, "all baseline diffs are path-only"]
