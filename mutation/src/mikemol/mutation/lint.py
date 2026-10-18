# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Check that every declared defect in a distribution's `mutants.regex` can be planted (W1533).

⚑ THE GRID'S OWN CODE, WITHOUT A SUITE: each line is read by `read_declarations` and planted by
`plant`, the two calls the mutation runner makes, so this cannot disagree with it about what is
well-formed. A wrong field count, a bare `%`, a module that is not a file, a rewrite that leaves
source that does not parse and a pattern that matches nothing in its scope are each named by their
line or label, in a second, where the grid names them after a 35-minute gate (W1176).
CONSUMED BY: the `mikemol-mutation-lint` console script, the edit hook and the preflight.
"""

import sys
from collections.abc import Sequence
from pathlib import Path

from mikemol.mutation.declarations import DECLARATION_FILE, plant, read_declarations


def problems(dist: Path) -> list[str]:
    """Name each declaration of a distribution that cannot be planted.

    Returns:
        one line per problem; empty when the file is absent, empty or sound.

    """
    path = dist / DECLARATION_FILE
    if not path.is_file():
        return []
    try:
        declared = read_declarations(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"{DECLARATION_FILE}: {exc}"]
    found: list[str] = []
    for item in declared:
        module = dist / item.module
        if not module.is_file():
            found.append(f"{item.label}: {item.module} is not a file")
            continue
        try:
            planted = plant(module.read_text(encoding="utf-8"), item.spec)
        except ValueError as exc:
            found.append(f"{item.label}: {exc}")
            continue
        if planted is None:
            found.append(f"{item.label}: the pattern matches nothing in its scope")
    return found


def main(argv: Sequence[str] | None = None) -> int:
    """Lint one distribution's declarations, naming each problem on stderr.

    Returns:
        0 when every declaration plants, 1 after naming those that do not, 2 on a usage error.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        sys.stderr.write("usage: mikemol-mutation-lint DIST\n")
        return 2
    found = problems(Path(args[0]))
    for line in found:
        sys.stderr.write(f"mutation-lint: {line}\n")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
