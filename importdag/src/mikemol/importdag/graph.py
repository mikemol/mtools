# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One graph of a distribution, as a machine-readable file: import edges and declared reads (W1503).

    python3 -m mikemol.importdag.graph --dist DIR --package mikemol.hooks [--check | --write]

`DIR/graph.json` holds, for every module under `DIR/src/<package path>/` and every test under
`DIR/tests/`, the modules it imports and the other files it declares it reads. Three consumers want
the same facts: bazel's cache (what a target depends on), nemik's stack grouping (which cards
conflict, which chain, W643) and the gate's cost prediction (which tests a change reaches).

⚑ TWO EDGE KINDS, BECAUSE THE GAP IS DATA A MODULE READS WITHOUT IMPORTING (nemik W643 step 0:
161 of 161 import edges found, and the queue files, baselines and `shapes.ttl` not at all). Import
edges are DERIVED from the syntax tree; reads are DECLARED, in `DIR/reads.json`, and checked for
existence here. The strace footprint audit (W1504) is what holds a declaration to the truth.

⚑ ALL THREE SPELLINGS OF A PACKAGE IMPORT ARE EDGES: `import pkg.mod`, `from pkg import mod` and
`from pkg.mod import name`. `dagderive.imports` reads only the second and a name-in-module form of
the third, because the engine it was written for imported flat; this package's modules are written
`from mikemol.hooks.heartbeat import Beat`, and reading only the others would drop most edges.

⚑ A DECLARED READ THAT NAMES NO FILE IS REFUSED, not recorded: a graph with a dangling edge sends a
cone to a file that is not there.

The file is written with the sibling distribution's atomic write.
"""

import argparse
import ast
import json
import sys
from pathlib import Path

from mikemol.atomicwrite.durable import write_atomic

from mikemol.importdag import dagderive

SCHEMA = 1
GRAPH_FILE = "graph.json"
READS_FILE = "reads.json"
EXIT_STALE = 1

Entry = dict[str, list[str]]


def package_imports(text: str, names: set[str], package: str) -> set[str]:
    """Collect the package modules `text` imports, in any of the three spellings.

    Returns:
        the stems in `names` that `text` imports; a text that does not parse yields the empty set.

    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    found: set[str] = set()
    prefix = package + "."
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                head = alias.name[len(prefix) :].split(".")[0]
                if alias.name.startswith(prefix) and head in names:
                    found.add(head)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            mod = node.module or ""
            if mod == package:
                found |= {a.name for a in node.names if a.name in names}
            elif mod.startswith(prefix):
                head = mod[len(prefix) :].split(".")[0]
                if head in names:
                    found.add(head)
    return found


def module_paths(dist: Path, package: str) -> list[str]:
    """List a distribution's modules as dist-relative paths.

    Returns:
        every `.py` file under `src/<package path>/`, sorted, `__init__.py` included.

    """
    base = dist / "src" / Path(*package.split("."))
    return sorted(str(p.relative_to(dist)) for p in base.rglob("*.py") if p.is_file())


def test_paths(dist: Path) -> list[str]:
    """List a distribution's test modules as dist-relative paths.

    Returns:
        every `tests/test_*.py`, sorted.

    """
    return sorted(str(p.relative_to(dist)) for p in (dist / "tests").glob("test_*.py"))


def declared_reads(dist: Path, known: set[str]) -> dict[str, list[str]]:
    """Read `reads.json` and refuse a declaration that names a file that is not there.

    Returns:
        the reads per module or test path, each list sorted; empty when there is no file.

    Raises:
        ValueError: when a declared path, or the module it is declared for, does not exist.

    """
    source = dist / READS_FILE
    if not source.is_file():
        return {}
    raw: dict[str, list[str]] = json.loads(source.read_text(encoding="utf-8"))
    for owner, files in raw.items():
        if owner not in known:
            msg = f"{READS_FILE}: {owner} is no module or test of {dist.name}"
            raise ValueError(msg)
        missing = [f for f in files if not (dist / f).exists()]
        if missing:
            msg = f"{READS_FILE}: {owner} declares reads of files that are not there: {missing}"
            raise ValueError(msg)
    return {owner: sorted(set(files)) for owner, files in raw.items()}


def build(dist: Path, package: str) -> dict[str, object]:
    """Derive the graph of one distribution.

    Returns:
        the document `graph.json` holds: schema, package, and per-module and per-test entries.

    """
    modules = module_paths(dist, package)
    tests = test_paths(dist)
    index = dagderive.stem_index(modules)
    reads = declared_reads(dist, set(modules) | set(tests))

    def entry(path: str) -> Entry:
        text = (dist / path).read_text(encoding="utf-8")
        found = package_imports(text, set(index), package) - {Path(path).stem}
        return {"imports": sorted(index[stem] for stem in found), "reads": reads.get(path, [])}

    return {
        "schema": SCHEMA,
        "package": package,
        "modules": {path: entry(path) for path in modules},
        "tests": {path: entry(path) for path in tests},
    }


def render(doc: dict[str, object]) -> str:
    """Spell the graph file.

    Returns:
        indented JSON with sorted keys and a closing newline, so a regeneration is byte-stable.

    """
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write or check a distribution's `graph.json`.

    Returns:
        0 when the file is fresh or was regenerated, EXIT_STALE when `--check` finds it stale or
        absent.

    """
    parser = argparse.ArgumentParser(prog="graph")
    parser.add_argument("--dist", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    opts: dict[str, object] = vars(parser.parse_args(sys.argv[1:] if argv is None else argv))
    mode = "--write" if opts["write"] else "--check"
    dist = Path(str(opts["dist"]))
    want = render(build(dist, str(opts["package"])))
    target = dist / GRAPH_FILE
    have = target.read_text(encoding="utf-8") if target.is_file() else None
    if mode == "--check":
        if have != want:
            sys.stderr.write(f"graph --check: {dist.name}/{GRAPH_FILE} is STALE: run --write\n")
            return EXIT_STALE
        sys.stdout.write(f"graph --check: {GRAPH_FILE} is fresh\n")
        return 0
    if have != want:
        write_atomic(target, want)
    sys.stdout.write(f"graph --write: {dist.name}/{GRAPH_FILE} is fresh\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
