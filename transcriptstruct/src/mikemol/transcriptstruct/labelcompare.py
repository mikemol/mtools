# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Compare two labellers' labels over a blind sample, per kind (W2052, W1966).

    python -m mikemol.transcriptstruct.labelcompare MINE THEIRS [--exclude IDS] [--kinds KIND ...]

MINE and THEIRS are JSON-lines files of `{"id": ..., "label": ...}`. The comparison is over the ids
both files carry, less any id in the exclude file (the sentences a classifier was fitted on), so a
held-out reading counts only rows nobody fitted to. For each kind asked about it prints how many
rows each side gave it, how many both did, MY recall (both over mine) and THEIR precision (both
over theirs), and the whole confusion.

⚑ A COUNT IS NOT A RATE WHEN n IS SMALL: every figure is printed as `k of n`, never as a bare
percentage, so a precision of 1 of 5 cannot read as a measurement of a rate.
⚑ A SIDE'S LABEL WORD NOT IN THE OTHER'S SET IS KEPT, NEVER FOLDED: amr-skills' fifth word `other`
has no counterpart in a four-word reading, and mapping it to `status` is the reader's choice, made
visible in the confusion rather than done here.

CONSUMED BY: the operator of a held-out reading; the figures W2052 reports to amr-skills.
"""

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

DEFAULT_KINDS = ("commitment", "announce")


def read_labels(text: str) -> dict[str, str]:
    """Read a JSON-lines label file.

    Returns:
        id (as text) to label; a line that is not an object with both keys is skipped.

    """
    found: dict[str, str] = {}
    for line in text.splitlines():
        try:
            row: object = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            fields = cast("dict[str, object]", row)
            if "id" in fields and "label" in fields:
                found[str(fields["id"])] = str(fields["label"])
    return found


def read_ids(text: str) -> set[str]:
    """Read a whitespace-separated id list.

    Returns:
        the ids.

    """
    return set(text.split())


def confusion(
    mine: Mapping[str, str], theirs: Mapping[str, str], exclude: set[str]
) -> Counter[tuple[str, str]]:
    """Count (mine, theirs) label pairs over the ids both sides carry, less the excluded.

    Returns:
        the pair counts.

    """
    shared = (set(mine) & set(theirs)) - exclude
    return Counter((mine[i], theirs[i]) for i in shared)


def kind_line(pairs: Mapping[tuple[str, str], int], kind: str) -> str:
    """Score one kind from the confusion.

    Returns:
        `kind: mine M, theirs T, both B; recall B of M, precision B of T`.

    """
    mine = sum(n for (a, _b), n in pairs.items() if a == kind)
    theirs = sum(n for (_a, b), n in pairs.items() if b == kind)
    both = pairs.get((kind, kind), 0)
    return (
        f"{kind}: mine {mine}, theirs {theirs}, both {both}; "
        f"recall {both} of {mine}, precision {both} of {theirs}"
    )


def render(pairs: Mapping[tuple[str, str], int], kinds: Sequence[str]) -> list[str]:
    """Spell the comparison as report lines.

    Returns:
        the row count, the confusion cells in label order, then one line per kind.

    """
    lines = [f"rows compared: {sum(pairs.values())}"]
    lines += [f"  mine={a:<11} theirs={b:<11} {n}" for (a, b), n in sorted(pairs.items())]
    lines += [kind_line(pairs, kind) for kind in kinds]
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    """Run the comparison.

    Returns:
        0 after the report; 2 when a file cannot be read.

    """
    parser = argparse.ArgumentParser(prog="mikemol-transcriptstruct-labelcompare")
    parser.add_argument("mine", type=Path, help="my labels (JSON lines of id and label)")
    parser.add_argument("theirs", type=Path, help="the other labeller's labels")
    parser.add_argument("--exclude", type=Path, default=None, help="ids to leave out")
    parser.add_argument("--kinds", nargs="+", default=DEFAULT_KINDS, help="kinds to score")
    opts: dict[str, object] = vars(parser.parse_args(list(sys.argv[1:] if argv is None else argv)))
    try:
        mine = read_labels(Path(str(opts["mine"])).read_text(encoding="utf-8"))
        theirs = read_labels(Path(str(opts["theirs"])).read_text(encoding="utf-8"))
        named = cast("Path | None", opts["exclude"])
        skip = read_ids(named.read_text(encoding="utf-8")) if named is not None else set()
    except OSError as fault:
        sys.stderr.write(f"labelcompare: {fault}\n")
        return 2
    kinds = [str(k) for k in cast("Sequence[object]", opts["kinds"])]
    sys.stdout.writelines(f"{line}\n" for line in render(confusion(mine, theirs, skip), kinds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
