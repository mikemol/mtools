# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`python -m mikemol.pycodemod.cli_observe`: run a test command under the Observer (W1726).

    python -m mikemol.pycodemod.cli_observe --root PROJECT --out seen.json -- PYTEST_ARGS

⚑ IN THIS PROCESS, AND IN THE PROJECT'S OWN INTERPRETER: `sys.monitoring` sees only the interpreter
that registered its callbacks, so the tests cannot run as a child process, and they must run where
the project's dependencies are installed. So this is a module the project's python runs
(`mikemol-pycodemod` installed in the project's venv), not a mode of the `mikemol-pycodemod` script,
which would run the tests in pycodemod's own environment. pytest is imported here because it is the
project's own test runner, present wherever this runs.

⚑ WHAT RAN IS WHAT WAS OBSERVED: the document is written whatever pytest returned, and pytest's own
exit code is returned, so a red suite still leaves the types its passing tests showed.

⚑ THE KEYS ARE RELATIVE TO `--root`: `annotate` looks a file up by the path it was given, and an
absolute path from one checkout would never match another's. The document is the one `cli_annotate`
reads: `{"<file>::<qualified name>": {"params": {name: [type, ...]}, "returns": [type, ...]}}`.
"""

import json
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pytest

from mikemol.pycodemod.observed import Observer, Signature

SEPARATOR = "::"
EXIT_USAGE = 2
USAGE = "usage: python -m mikemol.pycodemod.cli_observe --root PROJECT --out FILE -- PYTEST_ARGS\n"
Run = Callable[[Sequence[str]], int]


def seen_document(observed: Mapping[str, Signature], root: Path) -> dict[str, dict[str, object]]:
    """Spell what was observed as the document `annotate --seen` reads.

    Returns:
        the signatures by `<file relative to root>::<qualified name>`; a file outside the root is
        left out, and each type set is sorted.

    """
    base = root.resolve()
    out: dict[str, dict[str, object]] = {}
    for key, signature in sorted(observed.items()):
        file, _, qual = key.partition(SEPARATOR)
        try:
            relative = Path(file).resolve().relative_to(base)
        except ValueError:
            continue
        out[f"{relative}{SEPARATOR}{qual}"] = {
            "params": {name: sorted(types) for name, types in signature.params.items()},
            "returns": sorted(signature.returns),
        }
    return out


def run_pytest(args: Sequence[str]) -> int:
    """Run pytest in this process.

    Returns:
        pytest's exit code.

    """
    return int(pytest.main(list(args)))


def observe_run(root: Path, out: Path, args: Sequence[str], run: Run = run_pytest) -> int:
    """Run `args` under an observer on `root` and write what it saw to `out`.

    Returns:
        the run's exit code; the file is written whatever it was.

    """
    with Observer(root) as watching:
        code = run(args)
    document = seen_document(watching.observed(), root)
    out.write_text(json.dumps(document, indent=1, sort_keys=True), encoding="utf-8")
    return code


def main(argv: Sequence[str] | None = None, run: Run = run_pytest) -> int:
    """Parse `--root`, `--out` and the arguments after `--`, then run and write.

    Returns:
        the run's exit code; EXIT_USAGE for a missing option or a root that is not a directory.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    split = args.index("--") if "--" in args else len(args)
    words, tail = args[:split], args[split + 1 :]
    options = dict(zip(words[0::2], words[1::2], strict=False))
    root, out = options.get("--root"), options.get("--out")
    if root is None or out is None or not Path(root).is_dir():
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    return observe_run(Path(root), Path(out), tail, run)


if __name__ == "__main__":
    sys.exit(main())
