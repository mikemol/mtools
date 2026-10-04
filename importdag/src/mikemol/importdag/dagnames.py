# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Name every engine module importably, from the component partition.

Two namespaces describe an engine's modules: the path namespace that the component partition and
the import DAG record (`tests/boundaries_jobs.py`), and the name namespace that an `import` and a
build target use. Each consumer that wrote its own conversion between them eventually broke it, so
the question "what is this module's importable name" is answered here, once, as a question about
the partition.

This module is separate from the module that writes the generated DAG file on purpose: that
module owns an artifact and depends on an atomic writer, while this question needs no writer and
so inherits no such dependency.

The command line prints the importable names, or with `--verify` proves that each one imports in
a fresh interpreter:

    python3 -m mikemol.importdag.dagnames --engine DIR
    python3 -m mikemol.importdag.dagnames --engine DIR --skip tests
    python3 -m mikemol.importdag.dagnames --engine DIR --skip tests --verify

The name check, `unresolvable`, is importable by module path from a fresh interpreter. It runs
one child interpreter per name, and each child imports this very module by its package name, with
no change to `sys.path` made by code: the engine roots and this package's location reach the
child through its `PYTHONPATH` environment variable.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

PAIR = 2
"""An option and its value."""

CHILD_TIMEOUT = 120
"""Seconds a child interpreter may take to import one name."""

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
"""The directory holding the `mikemol` namespace this module was imported from."""

CHILD_PRELUDE = "import importlib; import mikemol.importdag.dagnames; "
"""Binds the first consumer module, as a consumer would, before the name under test."""


@dataclass
class Options:
    """What the command line asked for."""

    engine: Path = field(default_factory=lambda: Path("paperkit"))
    skip: tuple[str, ...] = ()
    pkg: str = ""
    verify: bool = False


def literal(path: Path, name: str) -> dict[str, list[str]]:
    """Read the one dict literal `name` is bound to in a .bzl file.

    The `literal_eval` result is narrowed here, at the seam, so callers see a concrete type.

    Returns:
        The mapping of string keys to string lists. Entries whose value is not a list are
        dropped, and a binding that is not a dict yields an empty mapping.

    """
    src = path.read_text(encoding="utf-8")
    i = src.index(name + " = ")
    val: object = ast.literal_eval(src[src.index("{", i) : src.index("\n}", i) + 2])
    if not isinstance(val, dict):
        return {}
    out: dict[str, list[str]] = {}
    for k, v in val.items():
        if isinstance(v, list):
            out[str(k)] = [str(x) for x in v]
    return out


def to_module(path: str, pkg: str = "") -> str:
    """Convert one engine-relative path to the name an `import` would use.

    A subpackage name must be qualified, because the bare one is ambiguous: an engine may hold a
    `tools/` subpackage while the repository root holds another `tools/`, and a bare
    `tools.bibstruct` then resolves to whichever directory a consumer happened to bind first. A
    name whose referent depends on load order is not a name; qualifying it with `pkg` makes it
    one. A top-level module keeps its bare name, which is the flat spelling the engine's modules
    use.

    Returns:
        The dotted name, qualified by `pkg` when `pkg` is given and the path is in a subpackage.

    """
    name = path.removesuffix(".py").replace("/", ".")
    return f"{pkg}.{name}" if pkg and "." in name else name


def module_names(eng: Path, skip: tuple[str, ...] = (), pkg: str = "") -> list[str]:
    """Name every engine module in the partition, omitting the components in `skip`.

    `skip` lets a caller state its filter (a consumer may exclude `tests`, whose modules are not
    engine entries) instead of re-deriving the list with its own comprehension. `pkg` qualifies
    the subpackage names against the engine's own package; see `to_module`.

    Returns:
        The sorted names, read from the `COMPONENTS` literal of `eng/components.bzl`.

    """
    comps = literal(eng / "components.bzl", "COMPONENTS")
    return sorted(to_module(f, pkg) for c, fs in comps.items() if c not in skip for f in fs)


def child_env(eng: Path) -> dict[str, str]:
    """Build the environment a name-check child runs under.

    Both roots go on `PYTHONPATH`, the engine directory and its parent, and so does the location
    of this package. A probe that imports only the name under test cannot see a collision
    between an engine subpackage and a same-named package at the repository root, so the child
    binds this module first, as the consumer does, and engine subpackage names must be qualified.
    Carrying the paths in the environment keeps every `sys.path` edit out of the child's code.

    Returns:
        The parent's environment with `PYTHONPATH` replaced by the three roots followed by
        whatever the parent already had.

    """
    roots = [str(eng), str(eng.parent), str(PACKAGE_ROOT)]
    inherited = os.environ.get("PYTHONPATH")
    if inherited:
        roots.append(inherited)
    return {**os.environ, "PYTHONPATH": os.pathsep.join(roots)}


def unresolvable(names: list[str], eng: Path, root: Path | None = None) -> list[tuple[str, str]]:
    """Report which of `names` do not import, by the route a consumer takes.

    The claim this module makes is that its names are importable, so it answers that itself rather
    than leaving each consumer to discover a bad name as a `ModuleNotFoundError` mid-suite. The
    route mirrors the consumer's: the engine on the path, imported by name. It runs in a
    subprocess, one per name, because importing the engine's modules has side effects and a
    failure part-way through must not poison the answer for the rest.

    Returns:
        A name and the last line of its child's output for each name that failed to import. The
        line is cut at 96 characters and empty when the child said nothing.

    """
    exe = sys.executable or "python3"
    env = child_env(eng)
    cwd = root if root is not None else eng.parent
    out: list[tuple[str, str]] = []
    for n in names:
        code = CHILD_PRELUDE + f"importlib.import_module({n!r})"
        r = subprocess.run(
            [exe, "-c", code],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=CHILD_TIMEOUT,
            check=False,
        )
        if r.returncode:
            tail = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip()]
            out.append((n, tail[-1][:96] if tail else ""))
    return out


def parse_args(argv: list[str]) -> Options:
    """Read the command line.

    An option other than `--verify` takes the next word as its value; the first word that is not
    a known option, and everything after it, is ignored.

    Returns:
        The options, with the defaults for any not given.

    """
    args = list(argv)
    opts = Options()
    if "--verify" in args:
        args.remove("--verify")
        opts.verify = True
    while len(args) >= PAIR:
        if args[0] == "--skip":
            opts.skip = tuple(args[1].split(","))
        elif args[0] == "--pkg":
            opts.pkg = args[1]
        elif args[0] == "--engine":
            opts.engine = Path(args[1])
        else:
            break
        args = args[PAIR:]
    return opts


def main(argv: list[str] | None = None) -> int:
    """Print the engine's importable module names, or verify that they all import.

    Returns:
        0 when names were printed or every name imported, 1 when any name failed to import.

    """
    opts = parse_args(sys.argv[1:] if argv is None else argv)
    eng = opts.engine.resolve()
    names = module_names(eng, skip=opts.skip, pkg=opts.pkg)
    if not opts.verify:
        for name in names:
            sys.stdout.write(name + "\n")
        return 0

    bad = unresolvable(names, eng)
    for n, why in bad:
        sys.stdout.write(f"  XX {n:<28} {why}\n")
    sys.stdout.write(f"\n{len(names) - len(bad)} of {len(names)} engine modules import by name\n")
    if bad:
        sys.stdout.write(
            "  a name here is a ModuleNotFoundError in every consumer that walks the partition.\n"
        )
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
