# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A bazel shim's argv: add the build-event file to `test` and `build`, find the real bazel (W2109).

⚑ WHY A SHIM (paperkit:W547, measured 2026-10-28): mtools' own `.githooks/pre-commit` adds
`--build_event_json_file` itself, so its gate directory holds a live `.bep.json`; paperkit's hook
builds its own bazel command and its gate directory holds none, and no environment variable of
bazel's makes it write one. A one-file `bazel` placed first on the gate child's PATH sees every
bazel the repository's hook runs and adds the flag, with no edit to the repository's hook or its
`.bazelrc`. This module is the shim's pure part: what the argv becomes, and which bazel is the real
one.

⚑ THE FLAG GOES AFTER THE VERB, ONCE, AND ONLY ON `test` AND `build`: startup options come before
the verb and take their value in the `--name=value` form, so the first word that is not a `--flag`
is the verb. A first word that is not `test` or `build` (a `query`, `info`, `run`, a startup option
whose value was given as a separate word) leaves the argv alone: a missed BEP file is a smaller
harm than a changed command. A command that already names `--build_event_json_file` keeps its own.

⚑ THE REAL BAZEL IS THE FIRST `bazel` ON PATH THAT IS NOT THE SHIM'S OWN DIRECTORY: the shim must
never find itself, or every bazel call loops through it for ever.

CONSUMED BY: nothing yet (the shim script and `gateenv.child_env`).
"""

from collections.abc import Callable, Sequence
from pathlib import Path

FLAG = "--build_event_json_file"
VERBS = frozenset({"test", "build"})

Exists = Callable[[Path], bool]


def with_bep(args: Sequence[str], path: str) -> list[str]:
    """Add the build-event file to a `test` or `build` command, once.

    Returns:
        the argv with `--build_event_json_file=<path>` right after the verb; the argv unchanged
        for any other verb, for none, or when it already names the flag.

    """
    words = list(args)
    verb = next((i for i, word in enumerate(words) if not word.startswith("--")), None)
    if verb is None or words[verb] not in VERBS:
        return words
    if any(word == FLAG or word.startswith(f"{FLAG}=") for word in words):
        return words
    return [*words[: verb + 1], f"{FLAG}={path}", *words[verb + 1 :]]


def real_bazel(path_env: str, shim_dir: Path, exists: Exists) -> Path | None:
    """Find the first `bazel` on a PATH that is not in the shim's own directory.

    Returns:
        the path of that executable, or None when the PATH holds no other bazel.

    """
    for entry in path_env.split(":"):
        if not entry or Path(entry) == shim_dir:
            continue
        candidate = Path(entry) / "bazel"
        if exists(candidate):
            return candidate
    return None
