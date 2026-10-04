# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Census which witnesses reach the engine through a subprocess the closure cannot see.

The closure tool already follows one subprocess edge: a witness that names another claim's key
has that claim's cone staged too. What it does not follow is a witness that shells out to a
generator script, run as a subprocess, which does its own path setup and a flat import of an
engine module. A witness like that stages the roots for its own imports while the script it runs
needs more, and the script's first import dies once an engine module gains a dependency.

The census counts the population of that specific gap, and it counts it by asking the owner,
the closure tool, what roots each claim gets, rather than by searching for `subprocess`. A witness
is flagged when it names a sibling script that imports engine modules the claim's own declared
closure does not contain. That difference is the under-declaration, in modules, and it is what a
build stages too few of.

The closure tool is `mikemol.importdag.closure` in this distribution, run as a child interpreter
with `-m`. The tree is described by a `Tree`: the repository root, the engine directory, and
optionally a closure script that stands in for the module. The command line takes them as options,
and the defaults are the paperkit layout with the module as the closure tool.

    python3 -m mikemol.importdag.closure_census                 # every project with checks
    python3 -m mikemol.importdag.closure_census paper           # one project
    python3 -m mikemol.importdag.closure_census --root DIR --closure SCRIPT
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from mikemol.importdag import dagderive, dagnames

DISPATCH = ("CLAIMS", "CONCEPTS", "WITNESSES")
FIELDS = 2
PAIR = 2


@dataclass(frozen=True)
class Tree:
    """Where the census looks: the repository root, the engine, and the closure tool.

    A `closure` of None means this distribution's own module, run with `-m`. A path replaces it
    with a script run by path, which is how a test substitutes a fake and how a tree with its own
    closure script is described.
    """

    root: Path
    engine: Path
    closure: Path | None = None


@dataclass
class Gap:
    """One witness whose subprocess-reached script needs engine modules its closure omits."""

    claim: str
    script: str
    missing: list[str] = field(default_factory=list)


def default_tree(root: Path) -> Tree:
    """Describe a tree laid out like paperkit's.

    Returns:
        A `Tree` whose engine is `root/paperkit` and whose closure tool is this distribution's
        own `closure` module.

    """
    return Tree(root=root, engine=root / "paperkit")


def closure_command(tree: Tree) -> list[str]:
    """Build the argument vector that starts the closure tool, before its own options.

    Returns:
        The running interpreter with `-m mikemol.importdag.closure` when the tree names no
        script, else the interpreter and the script path.

    """
    exe = sys.executable or "python3"
    if tree.closure is None:
        return [exe, "-m", "mikemol.importdag.closure"]
    return [exe, str(tree.closure)]


def closure_env(tree: Tree) -> dict[str, str]:
    """Build the environment the closure child runs under, which is deliberately minimal.

    A script finds its sibling modules through the directory it sits in. The module needs this
    package's location instead, passed in the environment so that no code edits `sys.path`, with
    whatever the parent already had following it.

    Returns:
        `PYTHONPATH` and `PATH` only.

    """
    if tree.closure is not None:
        return {"PYTHONPATH": str(tree.closure.parent), "PATH": "/usr/bin:/bin"}
    roots = [str(dagnames.PACKAGE_ROOT)]
    inherited = os.environ.get("PYTHONPATH")
    if inherited:
        roots.append(inherited)
    return {"PYTHONPATH": os.pathsep.join(roots), "PATH": "/usr/bin:/bin"}


def engine_modules(tree: Tree) -> list[str]:
    """List the engine .py paths the closure tool resolves names against, from the partition.

    Returns:
        The sorted paths, each prefixed with the engine directory's name.

    """
    comps = dagnames.literal(tree.engine / "components.bzl", "COMPONENTS")
    return sorted(f"{tree.engine.name}/{f}" for fs in comps.values() for f in fs)


def declared(check: str, mods: list[str], tree: Tree) -> dict[str, set[str]]:
    """Ask the closure tool for each claim's declared import roots, as module stems.

    The owner is asked, not reimplemented. A census that re-derived the roots would be a second
    body of the closure tool's rules and would drift from them, and a consumer re-deriving what an
    owner already computes is the defect class being counted here.

    Returns:
        The stems of each claim's import roots, by claim key. Rows that name a read or a file
        rather than an import are skipped.

    """
    r = subprocess.run(
        [*closure_command(tree), "--check", check, *mods],
        cwd=tree.root,
        capture_output=True,
        text=True,
        check=False,
        env=closure_env(tree),
    )
    out: dict[str, set[str]] = {}
    for ln in r.stdout.splitlines():
        parts = ln.split("\t")
        if len(parts) < FIELDS or ":" in parts[1]:
            continue
        out.setdefault(parts[0], set()).add(Path(parts[1]).stem)
    return out


def dispatch_table(tree: ast.Module) -> dict[str, str]:
    """Read the witness module's claim-key to function-name registry.

    Returns:
        The function name registered under each key of a top-level dict bound to `CLAIMS`,
        `CONCEPTS` or `WITNESSES`. Only a string key with a plain name as its value counts.

    """
    out: dict[str, str] = {}
    for n in tree.body:
        if not (isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict)):
            continue
        if not any(isinstance(t, ast.Name) and t.id in DISPATCH for t in n.targets):
            continue
        for k, v in zip(n.value.keys, n.value.values, strict=False):
            if isinstance(k, ast.Constant) and isinstance(v, ast.Name):
                out[str(k.value)] = v.id
    return out


def scripts_named(fn: ast.AST, sibling: set[str]) -> set[str]:
    """Collect sibling script basenames a witness names as a string constant.

    Returns:
        The basename of each string constant under `fn` whose last path segment is in `sibling`.

    """
    return {
        n.value.rsplit("/", 1)[-1]
        for n in ast.walk(fn)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and n.value.rsplit("/", 1)[-1] in sibling
    }


def script_imports(path: Path, names: set[str]) -> set[str]:
    """Collect engine module stems a script imports, which are its own cone seed.

    Returns:
        The stems in `names` that `path` imports by `import` or flat from-import. A script that
        cannot be read or parsed yields the empty set.

    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    return dagderive.node_imports(tree, names)


def cone(seeds: set[str], mods: list[str], tree: Tree) -> set[str]:
    """Expand `seeds` to the transitive engine cone the build would have to stage.

    Returns:
        The stems reachable from `seeds` through the engine's import edges, and the seeds that
        name an engine module.

    """
    paths = [m[len(tree.engine.name) + 1 :] for m in mods]
    edges: dict[str, list[str]] = {}
    for m, i in dagderive.edges(tree.engine, paths):
        edges.setdefault(m, []).append(i)
    by_stem = {Path(p).stem: p for p in paths}
    seen: set[str] = set()
    for s in seeds:
        if s in by_stem:
            seen |= {Path(p).stem for p in dagderive.cone(by_stem[s], edges)}
    return seen


def witness_modules(project: Path) -> list[Path]:
    """List the project's witness modules: every `checks/*.py` a bib `cmd:` actually names.

    A name list would skip a project whose witness has another name, a scrape of the bib alone
    would skip a project that uses a verb and never names its script, and a fallback name list
    would skip the next spelling. The mapping is declared in each project's `paper.toml`, as a
    command template naming the script, so it is read from there, place by ownership, plus
    whatever a bib `cmd:` names directly. A project inventing a new spelling is covered by
    construction rather than by editing a list here.

    Returns:
        The sorted paths under `project/checks` named by a `.bib` or by `paper.toml`. A project
        with no `checks` directory yields the empty list.

    """
    checks = project / "checks"
    if not checks.is_dir():
        return []
    named: set[str] = set()
    for bib in sorted(project.glob("*.bib")):
        for tok in bib.read_text(encoding="utf-8").split():
            leaf = tok.strip("{},").rsplit("/", 1)[-1]
            if leaf.endswith(".py") and (checks / leaf).exists():
                named.add(leaf)
    toml = project / "paper.toml"
    if toml.exists():
        for tok in toml.read_text(encoding="utf-8").split():
            leaf = tok.strip("\"'{},").rsplit("/", 1)[-1]
            if leaf.endswith(".py") and (checks / leaf).exists():
                named.add(leaf)
    return sorted(checks / n for n in named)


def audit_witness(witness: Path, project: Path, mods: list[str], tree: Tree) -> list[Gap]:
    """Report each claim in one witness module naming a script it does not stage the cone for.

    A witness outside the repository is a legitimate input, which is what lets the census be
    tested on a synthetic project: the closure tool takes an absolute path for it, and a path
    under the root is passed relative.

    Returns:
        One `Gap` per claim and sibling script whose cone is not covered by the claim's declared
        closure, sorted by claim key and script.

    """
    checks = witness.parent
    sibling = {p.name for p in checks.glob("*.py") if p.name not in {witness.name, "__init__.py"}}
    if not sibling:
        return []

    names = {Path(m).stem for m in mods}
    rel = str(witness.relative_to(tree.root)) if witness.is_relative_to(tree.root) else str(witness)
    have = declared(rel, mods, tree)
    module = ast.parse(witness.read_text(encoding="utf-8"))
    funcs = {f.name: f for f in module.body if isinstance(f, ast.FunctionDef)}

    gaps: list[Gap] = []
    for key, fname in sorted(dispatch_table(module).items()):
        fn = funcs.get(fname)
        if fn is None:
            continue
        for script in sorted(scripts_named(fn, sibling)):
            seed = script_imports(checks / script, names)
            missing = sorted(cone(seed, mods, tree) - have.get(key, set()))
            if missing:
                where = f"{project.name}/checks/{script}"
                gaps.append(Gap(claim=key, script=where, missing=missing))
    return gaps


def audit(project: Path, mods: list[str], tree: Tree) -> list[Gap]:
    """Report every under-declared witness in a project, across all its witness modules.

    Returns:
        The gaps of every witness module of `project`.

    """
    return [g for w in witness_modules(project) for g in audit_witness(w, project, mods, tree)]


def projects_of(root: Path) -> list[Path]:
    """List every project directory under `root` that keeps witnesses in a `checks` directory.

    The root project is one of them, and a glob over subdirectories does not match it: a root
    project keeps its witnesses at `checks/`, not `name/checks/`, so the root is added when it
    has its own.

    Returns:
        The sorted project directories.

    """
    found = {p.parent for p in root.glob("*/checks") if p.is_dir()}
    if (root / "checks").is_dir():
        found.add(root)
    return sorted(found)


def parse_args(argv: list[str]) -> tuple[Tree, set[str]]:
    """Read the command line.

    Returns:
        The tree, from `--root` (default the current directory) and `--closure` (default this
        distribution's closure module), and the project labels named by the remaining words.

    """
    args = list(argv)
    root = Path.cwd()
    closure: Path | None = None
    wanted: set[str] = set()
    while args:
        if args[0] == "--root" and len(args) >= PAIR:
            root = Path(args[1]).resolve()
            args = args[PAIR:]
        elif args[0] == "--closure" and len(args) >= PAIR:
            closure = Path(args[1]).resolve()
            args = args[PAIR:]
        else:
            wanted.add(args[0])
            args = args[1:]
    tree = default_tree(root)
    if closure is not None:
        tree = Tree(root=tree.root, engine=tree.engine, closure=closure)
    return tree, wanted


def main(argv: list[str] | None = None) -> int:
    """Report every claim whose subprocess-reached script out-runs its declared closure.

    The report says what was examined, not only what was found: a count of findings over an
    unstated population is the shape that reports a project as clean without opening a file in it.

    Returns:
        1 when any witness is under-declared, else 0.

    """
    tree, wanted = parse_args(sys.argv[1:] if argv is None else argv)
    mods = engine_modules(tree)

    gaps: list[Gap] = []
    examined: list[str] = []
    skipped: list[str] = []
    for proj in projects_of(tree.root):
        label = "(root)" if proj == tree.root else proj.name
        if wanted and label not in wanted and proj.name not in wanted:
            continue
        mods_seen = witness_modules(proj)
        if not mods_seen:
            skipped.append(label)
            continue
        examined.extend(f"{label}/checks/{w.name}" for w in mods_seen)
        gaps.extend(audit(proj, mods, tree))

    out = sys.stdout
    for g in gaps:
        out.write(f"  GAP {g.claim}\n")
        out.write(f"      shells out to : {g.script}\n")
        out.write(f"      NOT staged    : {', '.join(g.missing)}\n")

    out.write(f"\nexamined {len(examined)} witness module(s):\n")
    for e in sorted(examined):
        out.write(f"    {e}\n")
    if skipped:
        out.write(f"  NO bib-named witness found in: {', '.join(sorted(skipped))}\n")
    out.write(f"\n{len(gaps)} under-declared witness(es)\n")
    if gaps:
        out.write(
            "  each stages a cone too small for the script it runs,\n"
            "  a ModuleNotFoundError waiting for a module to gain a dependency.\n"
        )
    return 1 if gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
