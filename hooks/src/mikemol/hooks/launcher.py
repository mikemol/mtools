# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Say when another repo commits through a bazel-bin launcher of a live mtools tree (W1743).

`bazel-bin/hooks/.venv` is a link farm into the working tree: an edited module follows at
once, and a NEW module has no link until `//hooks:.venv` is rebuilt, so a half-edited tree
broke every commit that ran through it (2026-10-19, and again 2026-10-21 when W1757 added
`bazelstop`). The sound entry for another repo is the hooks wheel installed at a sha in that
repo's own venv (INSTALL.md), which no edit in this tree can reach.

⚑ A NOTICE FIRST, A REFUSAL ONLY AFTER ADOPTION. Refusing at once would stop every repo still
using the bazel-bin path the moment this lands, and that path is live as it is written, so it
would be a lockout with no way to repair it from the repo that is locked out. The notice names
the repo and the exact line to run; the refusal is its own card, taken when each repo has the
pin.

⚑ THE LAUNCHER IS TOLD BY ITS PREFIX, not by who runs it: `sys.prefix` of a bazel venv lies
under `bazel-out` (the resolved cache path) or `bazel-bin` (the convenience link). mtools's own
commits are not noticed: a tree that holds `hooks/pyproject.toml` is the tree the launcher
follows.

CONSUMED BY: `commit_kata.resolve_root`, which runs it for every repository a commit names.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import TextIO

MARKERS = ("/bazel-out/", "/bazel-bin/")
TEST_ENV = "TEST_SRCDIR"
SPEC = "mikemol-hooks @ git+https://github.com/mikemol/mtools.git@<sha>#subdirectory=hooks"


def wheel_installed(prefix: str) -> bool:
    """Say whether a venv carries the hooks WHEEL (a `mikemol_hooks-*.dist-info`), not a link farm.

    ⚑ THE NOTICE READS WHAT THE VENV ACTUALLY IMPORTS (nemik-84, 2026-10-24). A bazel-bin
    launcher can be the vendored wheel from bazel's external repository (nemik's, dist-info
    `mikemol_hooks-0.1.0+57b9f2a`), which no edit in an mtools tree can reach, and the path alone
    said "live mtools tree" for it. The mtools tree's own launcher has no such dist-info: it is
    links into the working tree.

    Returns:
        True when the venv's site-packages holds a `mikemol_hooks` dist-info.

    """
    pattern = "lib/python*/site-packages/mikemol_hooks-*.dist-info"
    return any(Path(prefix).glob(pattern))


def notice(prefix: str, root: Path, env: Mapping[str, str]) -> str | None:
    """Judge whether a commit into `root` runs through a launcher it should not.

    Returns:
        the notice, or None when the launcher is not a bazel venv, carries the hooks wheel,
        `root` is the mtools tree or this runs inside a bazel test (a test's own commits are
        not a user's launcher).

    """
    if TEST_ENV in env or not any(marker in prefix for marker in MARKERS):
        return None
    if wheel_installed(prefix):
        return None
    if (root / "hooks" / "pyproject.toml").is_file():
        return None
    return (
        f"mikemol-commit: NOTICE, committing {root.name} through a bazel-bin launcher ({prefix}), "
        "a link farm into a live mtools tree: a module added there breaks this commit until "
        "//hooks:.venv is rebuilt (W1743). Install the pin in the repo's own venv instead:\n"
        f"  uv add '{SPEC}'  (one sha across every mtools spec; see INSTALL.md)"
    )


def announce(prefix: str, root: Path, env: Mapping[str, str], out: TextIO) -> None:
    """Write the notice, when there is one, to `out`."""
    said = notice(prefix, root, env)
    if said is not None:
        out.write(said + "\n")
