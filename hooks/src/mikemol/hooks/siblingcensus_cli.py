# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-siblings REPO [REPO ...]`: per repository, how many lines reach into another checkout.

The reading and the printing around `siblingcensus.reaches` (W1709): `git ls-files` names the
tracked files and each is read as text, so an untracked scratch file never counts.
"""

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from mikemol.hooks.siblingcensus import reaches

EXIT_USAGE = 2


def tracked_text(root: Path) -> dict[str, str]:
    """Read every tracked text file of a checkout.

    Returns:
        the path under `root` mapped to its text; a file that is not text or not a file is left out.

    """
    done = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True
    )
    out: dict[str, str] = {}
    for name in done.stdout.decode().split("\0"):
        path = root / name
        if not name or not path.is_file():
            continue
        try:
            out[name] = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
    return out


def main(argv: Sequence[str] | None = None) -> int:
    """Print, per repository given, how many lines reach into another checkout.

    Returns:
        0; EXIT_USAGE with no repository named.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        sys.stderr.write("usage: mikemol-siblings REPO [REPO ...]\n")
        return EXIT_USAGE
    for given in args:
        root = Path(given).resolve()
        found = reaches(root, tracked_text(root))
        files = len({r.file for r in found})
        sys.stdout.write(f"{root.name}: {len(found)} reach(es) in {files} file(s)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
