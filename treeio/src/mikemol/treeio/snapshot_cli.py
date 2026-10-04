# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The `mikemol-edit-snapshot` command line: list snapshots, find which holds a path, restore one.

Ported from the `__main__` half of paperkit's `tools/edit_snapshot.py`. The `--selftest` mode is
gone: the suite that mode ran is now this distribution's pytest suite.

    mikemol-edit-snapshot --list
    mikemol-edit-snapshot --holding <path-fragment>
    mikemol-edit-snapshot --from-snapshot=<sha> [paths] [--apply]

`--holding` is THE QUESTION A RECOVERY ACTUALLY ASKS, and `--list` could not answer it: `--list`
dumps the raw journal, which was measured at 207 KB with every path of every snapshot, so "which
snapshot holds MY file" meant grepping the output. That is reprocessing at the shell, and it is what
sent a person to a hand-assembled copy-and-checkout line instead of `--from-snapshot`: a printed
command is not a recovery path.

THE JOURNAL IS NEWEST-LAST AND THE LISTING WANTS NEWEST-FIRST. The first cut reversed only in the
print loop and then indexed the UNREVERSED list for the restore hint, so the hint named the OLDEST
snapshot while the reader was looking at the newest. A printed command that is subtly wrong is
worse than none, because it gets run. So the rows are reversed ONCE and one orientation is used
everywhere.

`--from-snapshot` is dry unless `--apply` is given, and says so. Its untracked entries are the MOST
RECENT pre-write copy, because the store is keyed by path and not by sha.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.treeio.layout import layout
from mikemol.treeio.restore import restore

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_FROM_SNAPSHOT = "--from-snapshot"
_SHOWN = 5  # how many matching paths one snapshot's row names before it summarizes
_JOURNAL_FIELDS = 4  # sha, label, path count and paths
_EXIT_USAGE = 2
_USAGE = (
    "usage: mikemol-edit-snapshot --list\n"
    "       mikemol-edit-snapshot --holding <path-fragment>\n"
    "       mikemol-edit-snapshot --from-snapshot=<sha> [paths] [--apply]\n"
)
_ABOUT = (
    "A recoverable-by-construction snapshot for any tool that rewrites tree files.\n"
    "It records how to get back and NEVER restores on its own.\n"
)


def _say(text: str) -> None:
    """Write one line to stdout."""
    sys.stdout.write(text + "\n")


def holding_rows(journal: Path, fragment: str) -> list[tuple[str, str, list[str]]]:
    """Find the snapshots whose journaled paths include `fragment`, newest first.

    Returns:
        One row per matching snapshot: its sha, its label and the matching paths.

    """
    rows: list[tuple[str, str, list[str]]] = []
    if journal.exists():
        for line in journal.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            fields = line.split("\t")
            if len(fields) < _JOURNAL_FIELDS:
                continue
            hit = [p for p in fields[3].split(",") if fragment in p]
            if hit:
                rows.append((fields[0], fields[1], hit))
    rows.reverse()
    return rows


def _show_holding(journal: Path, fragment: str) -> None:
    """Print the snapshots holding a path, newest first, and the command to restore the newest."""
    rows = holding_rows(journal, fragment)
    for sha, label, hit in rows:
        _say(f"{sha[:12]}  {label}")
        for path in hit[:_SHOWN]:
            _say(f"      {path}")
        if len(hit) > _SHOWN:
            _say(f"      … {len(hit) - _SHOWN} more matching path(s)")
    _say(f"{len(rows)} snapshot(s) hold a path matching {fragment!r} (newest first)")
    if rows:
        _say(f"   restore:  mikemol-edit-snapshot --from-snapshot={rows[0][0][:12]} <path> --apply")


def _show_restore(sha: str, args: Sequence[str]) -> None:
    """Restore, or report what would be restored, and say what the untracked half is."""
    paths = [a for a in args if not a.startswith("-")]
    apply = "--apply" in args
    rows = restore(sha, paths, apply=apply)
    for rel, how in rows:
        _say(f"{'RESTORED' if apply else 'would restore':<14} {how:<18} {rel}")
    n_tracked = sum(1 for _, how in rows if how == "tracked")
    n_untracked = sum(1 for _, how in rows if how.startswith("untracked"))
    _say(f"{len(rows)} path(s): {n_tracked} tracked, {n_untracked} untracked")
    if n_untracked:
        _say(
            "   ⚑ untracked entries are the MOST RECENT pre-write copy "
            "(the store is keyed by path, not by sha)"
        )
    if not apply:
        _say("\nDry run — pass --apply to execute.")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line.

    Returns:
        2 for `--holding` without a fragment, otherwise 0.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    journal = layout().journal
    if "--holding" in args:
        wanted = [a for a in args if not a.startswith("-")]
        if not wanted:
            _say("usage: mikemol-edit-snapshot --holding <path-fragment>")
            return _EXIT_USAGE
        _show_holding(journal, wanted[0])
        return 0
    if "--list" in args:
        if journal.exists():
            sys.stdout.write(journal.read_text(encoding="utf-8"))
        else:
            _say("no snapshots recorded")
        return 0
    sha = next((a.split("=", 1)[1] for a in args if a.startswith(_FROM_SNAPSHOT + "=")), None)
    if sha:
        _show_restore(sha, args)
        return 0
    sys.stdout.write(_ABOUT + _USAGE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
