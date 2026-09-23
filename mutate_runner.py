# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Mutate every def-site in a distribution's sources and report what its suite NOTICES.

⚑⚑⚑ THE QUESTION IS NOT *DOES THE SUITE PASS* BUT *WOULD IT NOTICE*. A green suite over code
nothing exercises is the defect this repository measures most, and no checker here answers it:
ruff and mypy read the sources, pytest reads its own assertions, and none of them can say whether
removing a function's body would change a verdict. This can, at def-site granularity.

⚑⚑ AND IT CATCHES ONE OF THE FOUR VACUITY SHAPES, WHICH `paperkit-82` ESTABLISHED AGAINST THEIR
OWN FRAMEWORK BEFORE I ASKED. Their phrasing, kept because it bounds the claim: *mutation testing
at this granularity tests whether your test EXERCISES code, not whether it MEASURES anything.*
Three of the four shapes are POPULATION defects — a set never populated, a set filtered empty by a
false premise — and no def-site mutation can express *return a differently ordered list*. This is
one instrument among several, and saying so is what keeps a green here from reading as coverage.

⚑ AST REWRITE INTO A TEMP TREE, NOT A CACHED BYTECODE ARTIFACT, AND THE COST WAS MEASURED BEFORE
THE ARCHITECTURE WAS CHOSEN. paperkit builds each mutant as a content-addressed `.pyc` because
their grid is 223 claims wide and the caching pays for the per-module build targets and declared
import DAG it requires. Measured here, per cell:

    ratchet  0.2s      hooks  0.4s      fence  0.5s      mdstruct  1.4s

158 def-sites across four distributions is **under four minutes whole-tree**, and `-x` means a
KILLED cell stops at the first failing test — only SURVIVORS pay a full suite. That is the
opposite of the cost profile a caching layer is built for, so importing one would buy nothing and
cost the build-graph surgery paperkit named as its price.
"""

from __future__ import annotations

import ast
import concurrent.futures
import dataclasses
import fnmatch
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

# ⚑ THE SANDBOX STAGES ONLY WHAT IS DECLARED, so these are the trees a mutant must not carry into
# its copy. `.venv` in particular is a directory of pointers at host absolute paths — the property
# that makes it unfit as a bazel input makes it unfit to copy.
_NOT_SOURCE_PATTERNS = (".venv", "build", "*.egg-info", "__pycache__", ".*_cache", "bazel-*")


def _not_source(_directory: str, names: list[str]) -> set[str]:
    """Name the entries of one directory that a mutant's copy must leave behind.

    ⚑ WRITTEN OUT RATHER THAN `shutil.ignore_patterns(...)`, whose return type carries `Any` in
    its first parameter — a callable the root's strict mypy cannot admit as an expression.

    Returns:
        the subset of `names` matching any pattern in `_NOT_SOURCE_PATTERNS`.

    """
    return {n for n in names if any(fnmatch.fnmatch(n, p) for p in _NOT_SOURCE_PATTERNS)}


# The prefix every per-invocation git variable carries; none reaches a mutant's suite.
_GIT_PREFIX = "GIT_"


_ENUM_BASES = frozenset(
    {"enum.Enum", "Enum", "enum.StrEnum", "StrEnum", "enum.IntEnum", "IntEnum"},
)


@dataclasses.dataclass(frozen=True)
class Grid:
    """What every mutant of one distribution shares: its interpreter, its tree, its config."""

    py: pathlib.Path
    dist: pathlib.Path
    config: pathlib.Path


@dataclasses.dataclass(frozen=True)
class Mutant:
    """One def-site to mutate: the module it lives in, that module's source, the site's path."""

    rel: pathlib.Path
    source: str
    name: str


def launch(
    argv: list[str], cwd: pathlib.Path, env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    """Run one mutant's suite: argv only, no shell, output captured as text.

    ⚑ ONE SEAM FOR THE ONE SUBPROCESS, so a test replaces THIS rather than `subprocess.run` for the
    whole interpreter — which also replaced the git its own fixture needed.

    Returns:
        the completed process; its status is read by `verdict`, never raised.

    """
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False, env=env)


def _owned(tree: ast.Module) -> list[tuple[str, ast.FunctionDef, ast.ClassDef | None]]:
    """Walk the module in source order, naming each def by its QUALIFIED path.

    ⚑⚑⚑ A BARE NAME IS NOT AN ADDRESS, AND THE GRID WAS ADDRESSING BY ONE. Sites were reported as
    `<module>::<name>` and each mutant mutated the FIRST def carrying that name, so two `parse`s
    in one module were two rows over ONE mutation. Measured on ratchet: a Protocol stub `parse`
    that nothing calls came back SURVIVED three times, because every `parse` mutated the stub
    and the implementations were never touched — counted, and never measured.
    ⚑⚑ THE PATH FOLLOWS PYTHON'S OWN `__qualname__`: `Class.method`, `outer.<locals>.inner`.
    ⚑ AND A PATH CAN STILL REPEAT — a property getter and setter are both `C.x`, and so are the
    two arms of an `if TYPE_CHECKING:` — so the n-th repeat (n >= 2) carries `#n`. The first
    keeps the bare path, which is what leaves a module of unique names reported as before.

    Returns:
        `(qualified path, node, owning class or None)`, in source order.

    """
    found: list[tuple[str, ast.FunctionDef, ast.ClassDef | None]] = []
    seen: dict[str, int] = {}

    def visit(body: ast.AST, prefix: str, owner: ast.ClassDef | None) -> None:
        for child in ast.iter_child_nodes(body):
            if isinstance(child, ast.FunctionDef):
                path = f"{prefix}{child.name}"
                seen[path] = seen.get(path, 0) + 1
                label = path if seen[path] == 1 else f"{path}#{seen[path]}"
                found.append((label, child, owner))
                visit(child, f"{path}.<locals>.", None)
            elif isinstance(child, ast.AsyncFunctionDef | ast.Lambda):
                # ⚑ NOT A SITE (the operator never mutated these), but a def nested in one
                # still needs the path Python would give it.
                name = child.name if isinstance(child, ast.AsyncFunctionDef) else "<lambda>"
                visit(child, f"{prefix}{name}.<locals>.", None)
            elif isinstance(child, ast.ClassDef):
                visit(child, f"{prefix}{child.name}.", child)
            else:
                visit(child, prefix, owner)

    visit(tree, "", None)
    return found


def sites(tree: ast.Module) -> list[tuple[str, ast.FunctionDef]]:
    """List every function definition in a parsed module, in source order, by qualified path.

    Returns:
        `(qualified path, FunctionDef)` pairs, nested defs included; every path is distinct.

    """
    return [(path, node) for path, node, _owner in _owned(tree)]


def import_time_sites(tree: ast.Module) -> set[str]:
    """Name the def-sites this operator structurally cannot reach, DERIVED from the source.

    ⚑⚑⚑ FOUND BY THE ERRORED CATEGORY ON ITS FIRST REAL RUN, which is the category existing to
    do exactly this. `BaselineState.__init__` and `__str__` errored on ratchet: `BaselineState`
    subclasses `enum.Enum`, so its members are constructed WHEN THE CLASS BODY EXECUTES —
    mutating them raises during import and no test ever collects.

    ⚑⚑ SO IT IS A LIMIT OF THE OPERATOR, NOT A DEFECT IN THE SUITE, and the two are easy to
    confuse because both read as *the suite did not notice*. A silent skip would erase the
    distinction; an unexplained ERRORED would report a limit as a finding. Declaring it keeps
    both legible, and the arm below still counts these in ATTEMPTED.

    ⚑ THE PREDICATE IS STRUCTURAL RATHER THAN A NAME LIST. Matching `__init__` by name would
    also exclude every ordinary class's constructor, which IS reachable — over-declaring the
    limit to cover two real cases. Measured across the tree: 158 def-sites, exactly 2 in this
    class, both the ones ERRORED named. The derivation admits a new enum method for free.

    ⚑⚑ AND THE SET IS OF QUALIFIED PATHS, as `sites` now reports. It returned BARE names while
    this docstring promised `<Class>.<method>`, so an enum's `__str__` also skipped every other
    class's `__str__` in the same module — the same bare-name collision as the mutation itself.

    Returns:
        `"<Class>.<method>"` for every method of an `Enum` subclass in this module.

    """
    return {
        path for path, _node, owner in _owned(tree)
        if owner is not None and {ast.unparse(b) for b in owner.bases} & _ENUM_BASES
    }


def mutate(source: str, target: str) -> str:
    """Replace one def-site's body with a bare raise, leaving the rest of the module alone.

    ⚑ THE DOCSTRING IS KEPT so the mutant stays syntactically a function with a body. Replacing
    everything including the docstring would change two things under one label, and a mutant that
    alters more than its operator claims cannot support a conclusion about that operator.

    ⚑⚑ `target` IS A QUALIFIED PATH FROM `sites`, NOT A BARE NAME: a bare name picked the first
    same-named def, so every other one was reported and never mutated.

    Returns:
        the module source with `target` mutated.

    Raises:
        LookupError: when no def-site carries that path.

    """
    tree = ast.parse(source)
    for path, node in sites(tree):
        if path != target:
            continue
        keep = node.body[:1] if (
            isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ) else []
        raiser = ast.parse('raise AssertionError("mutant")').body
        node.body = [*keep, *raiser]
        return ast.unparse(ast.fix_missing_locations(tree))
    msg = f"no def-site at {target}"
    raise LookupError(msg)


def verdict(rc: int, stdout: str) -> str:
    """Sort one mutant run into `killed`, `survived` or `errored` — three outcomes, not two.

    ⚑⚑⚑ THE PREDECESSOR WAS `killed if rc else survived`, AND IT CREDITED THE SUITE FOR NOTICING
    THINGS IT NEVER RAN. A mutant that cannot import returns non-zero and was recorded as KILLED.
    Its `errored` list was bound, printed in the report, and never appended to — a POPULATION
    NEVER POPULATED, inside the instrument built to find exactly that.

    ⚑⚑ AND THE OBVIOUS REPAIR DOES NOT WORK, MEASURED, BECAUSE I ASSUMED IT WOULD. pytest's exit
    codes are documented as separating tests-failed (1) from internal error (3) and
    no-tests-collected (5), so keying on `rc` looked right. Across four shapes:

        unmutated control            rc=0   `151 passed`
        body -> raise (a real KILL)  rc=1   `1 failed`
        unparseable module           rc=1   `1 error`
        import-time raise            rc=1   `1 error`

    **All three non-zero cases return rc=1** — pytest reports a collection error as `1 error`
    rather than with a distinct code. THE EXIT STATUS CANNOT CARRY THIS DISTINCTION, and a repair
    keying on it would have been a second wrong answer wearing a measurement's clothes.

    ⚑ SO THE DISCRIMINATOR IS THE TERMINAL SUMMARY LINE. Weaker than an exit code and the one that
    exists — an honest `error` beats a confident `rc`.

    Returns:
        one of `"killed"`, `"survived"`, `"errored"`.

    """
    if rc == 0:
        return "survived"
    # ⚑⚑⚑ THE FIRST PREDICATE HERE WAS TOO BROAD AND ITS OWN CATEGORY CAUGHT IT. It read *any*
    # collection error as ERRORED, on a four-shape measurement where every error was an import
    # failure. Run against `fence`, three ordinary functions errored — and the traceback showed
    # the suite calling them AT COLLECTION TIME, through a module-level `_WHY = _unfenceable()`
    # guard that decides whether to skip. The suite's own code ran and REACHED the mutant.
    # ⚑⚑ SO THE DISTINCTION IS NOT *DID COLLECTION FINISH* BUT **WAS THE MUTANT REACHED**, which
    # is the question the whole grid asks. A mutant in the traceback was executed; the suite
    # noticed it, and where it noticed is not the measurement. That is a KILL.
    # ⚑ AND THE EXIT CODE WAS rc=2 HERE, a shape the original four-case measurement never
    # produced — a reminder that a predicate is only as wide as the corpus it was measured on.
    if "AssertionError: mutant" in stdout or "AssertionError('mutant')" in stdout:
        return "killed"
    # ⚑ THE LAST NON-EMPTY LINE IS pytest's SUMMARY under `-q`. Scanning the whole stdout would
    # also match the word `error` inside the traceback of a genuine FAILURE.
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    summary = lines[-1] if lines else ""
    # ⚑⚑ `failed` WINS OVER `error` WHEN BOTH APPEAR, and that case decides the predicate's shape:
    # `1 failed, 1 error` means the suite RAN and something failed, which is a kill. Without it,
    # `" error" in summary` alone would be sufficient and would misclassify.
    if " error" in summary and " failed" not in summary:
        return "errored"
    return "killed"


def _report_debug(proc: subprocess.CompletedProcess[str]) -> None:
    """Print what one mutant's suite said, for `--debug`."""
    tail = [ln for ln in proc.stdout.splitlines() if ln.strip()][-1:]
    reached = "AssertionError: mutant" in proc.stdout
    sys.stdout.write(f"      rc={proc.returncode} mutant_in_stdout={reached} "
                     f"summary={tail[0] if tail else '<none>'!r}\n")
    if proc.stderr.strip():
        sys.stdout.write(f"      stderr: {proc.stderr.strip().splitlines()[-1]}\n")
    # ⚑ WHEN THE MUTANT NEVER APPEARS, THE INTERESTING TEXT IS THE ERROR ITSELF — the
    # suite failed BEFORE reaching mutated code, so the summary line says nothing about
    # the mutation and everything about the environment.
    if not reached:
        for ln in proc.stdout.splitlines():
            if "Error" in ln or "error" in ln.lower():
                sys.stdout.write(f"      | {ln.strip()[:160]}\n")


def run(grid: Grid, mutant: Mutant, *, debug: bool = False) -> str:
    """Build one mutant in a temp copy of the distribution and run its suite against it.

    Returns:
        this mutant's verdict.

    """
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "dist"
        shutil.copytree(grid.dist, work, ignore=_not_source)
        (work / mutant.rel).write_text(mutate(mutant.source, mutant.name), encoding="utf-8")
        # ⚑ THE SYNTHESIZED PACKAGE MARKERS GO, for the reason `mypy_check.sh` records: rules_python
        # writes an empty `__init__.py` at every runfiles level, including the `src/mikemol/` one
        # PEP 420 forbids here. Only the EMPTY ones — a hand-written package `__init__.py` has
        # content and is part of the distribution.
        for marker in work.rglob("__init__.py"):
            if marker.stat().st_size == 0:
                marker.unlink()
        # ⚑⚑⚑ `PATH` IS INHERITED, AND STRIPPING IT REPORTED A WHOLE DISTRIBUTION AS UNMEASURABLE.
        # A first cut pinned `PATH=/usr/bin:/bin` for hermeticity. MEASURED: all 64 of mdstruct's
        # def-sites came back ERRORED, because `pandoc` lives at `~/bin/pandoc` and its suite
        # shells out to it — so every mutant failed for a reason that had nothing to do with the
        # mutation. The predecessor probe carried the same strip, which is why the recorded
        # mdstruct figures only ever covered `cli.py`, the one module whose arms do not need it.
        # ⚑⚑ AND THE ERRORED CATEGORY IS WHAT MADE THAT VISIBLE RATHER THAN FLATTERING. Under the
        # old two-outcome verdict every one of those 64 would have been recorded as KILLED — a
        # distribution reported as fully covered by a grid that never ran a single test.
        # ⚑ THE HERMETIC ANSWER IS THE SANDBOX, NOT A PINNED `PATH`. Under bazel the tools are
        # declared inputs and `PATH` is the sandbox's; here the environment is the caller's, and
        # a probe that silently loses a host tool is worse than one that inherits it.
        # ⚑ THE TEMP `src` IS PREPENDED, NOT SUBSTITUTED, so the mutant wins over the installed
        # copy while every other resolution path stays intact — which is what makes the mutation
        # the only difference between this run and a clean one.
        # ⚑⚑ AN EARLIER COMMENT HERE CLAIMED THIS COMPOSITION WAS *THE* DEFECT BEHIND 64 ERRORED
        # MUTANTS. IT WAS NOT, and the claim is corrected rather than deleted because a refuted
        # cause left standing is read as an established one. Measured: `PYTHONPATH` set to the
        # temp tree alone, prepended, or absent made NO difference — all three produced the same
        # result. The cause was `.resolve()` on the interpreter (see `main`).
        # ⚑⚑⚑ EVERY `GIT_*` VARIABLE IS DROPPED, BECAUSE A MUTANT'S SUITE CAN WRITE INTO THE
        # CALLER'S REPOSITORY. Under a git hook `GIT_DIR` and `GIT_INDEX_FILE` name the REAL repo,
        # and a fixture that runs `git init; git commit` in its temp dir follows them there — `cwd=`
        # does not override an exported `GIT_DIR`. Measured 2026-09-23: nine junk commits,
        # since recovered.
        # ⚑ substrate's `git_env.clean_env()` rule, at the runner, so suites not yet written are
        # covered too. A suite reading git state finds the repository from its `cwd` as before.
        env = {k: v for k, v in os.environ.items() if not k.startswith(_GIT_PREFIX)}
        existing = env.get("PYTHONPATH", "")
        src = str(work / "src")
        env["PYTHONPATH"] = f"{src}{os.pathsep}{existing}" if existing else src
        env["HOME"] = tmp
        # ⚑ THE CONFIG IS THE TEMP TREE'S OWN COPY. Passing the REAL `pyproject.toml` sets pytest's
        # rootdir to the real distribution while `cwd` is the temp copy, so reported paths climb
        # out of the tree under measurement. Naming the copy keeps rootdir and cwd agreeing.
        # ⚑⚑ AN EARLIER COMMENT HERE ALSO CLAIMED TO BE *THE* DEFECT. IT WAS NOT EITHER — changing
        # it moved the error path from `../../../github/mtools/mdstruct/test_cli_flags.py` to
        # `tests/test_cli_flags.py` and the failure followed rather than disappearing. Correct on
        # its own merits, and not the cause. **Two comments in this file each announced themselves
        # as the defect and both were wrong**, which is why the real one below states what it
        # RULED OUT alongside what it found.
        # ⚑ `shutil.copytree` ALREADY BRINGS `pyproject.toml` ACROSS, so this names the copy
        # rather than adding a file: the fix is which path is passed, not what exists.
        proc = launch(
            [str(grid.py), "-m", "pytest", "-x", "-q", "--no-header",
             "-p", "no:cacheprovider", "-c", str(work / grid.config.name), "tests"],
            work, env,
        )
        if debug:
            _report_debug(proc)
        return verdict(proc.returncode, proc.stdout)


def _plan(dist: pathlib.Path, modules: list[pathlib.Path]) -> tuple[
    list[str], list[str], list[tuple[str, Mutant]],
]:
    """Enumerate every def-site, setting aside the ones this operator cannot reach.

    Returns:
        `(attempted, unreachable, jobs)` — every site, the import-time ones, and the rest as
        `(site, Mutant)` in source order.

    """
    attempted: list[str] = []
    unreachable: list[str] = []
    jobs: list[tuple[str, Mutant]] = []
    for mod in modules:
        source = mod.read_text(encoding="utf-8")
        tree = ast.parse(source)
        rel = mod.relative_to(dist)
        skip = import_time_sites(tree)
        for path, _node in sites(tree):
            site = f"{rel}::{path}"
            attempted.append(site)
            # ⚑ COUNTED IN ATTEMPTED AND NOT RUN. Dropping it from `attempted` would make the
            # accounting balance by shrinking the denominator, which is the flattering direction
            # and the one this runner's predecessor took with ERRORED.
            if path in skip:
                unreachable.append(site)
                continue
            jobs.append((site, Mutant(rel, source, path)))
    return attempted, unreachable, jobs


def main(argv: list[str]) -> int:
    """Run the grid over one distribution and report the three categories by name.

    Returns:
        0 when every site was accounted for and none survived, 1 otherwise.

    """
    # ⚑⚑⚑ A DEBUG MODE IN THE RUNNER, NOT A REPRODUCTION BESIDE IT. The previous tick built a
    # standalone probe that reconstructed `run()` by hand; it WORKED while the real path failed,
    # which made a wrong diagnosis believable. A reproduction that is not the code under test is a
    # second instrument, and this tree has measured that class four times.
    debug = "--debug" in argv
    # ⚑⚑⚑ THE INTERPRETER IS NOT RESOLVED, AND RESOLVING IT COST THREE TICKS. `.venv/bin/python`
    # is a SYMLINK to the mise interpreter, and a venv works precisely BECAUSE the interpreter is
    # invoked through its own `bin/` path — that is what sets `sys.prefix` and puts the venv's
    # `site-packages` on the path. `.resolve()` follows the symlink and hands back
    # `~/.local/share/mise/.../python3.13`, so every mutant ran under the BARE SYSTEM INTERPRETER
    # with no venv at all.
    # ⚑⚑ AND IT ONLY SHOWED ON ONE DISTRIBUTION, WHICH IS WHY IT SURVIVED SO LONG: `ratchet` and
    # `fence` declare `dependencies = []`, so their suites run fine under a bare interpreter.
    # `mdstruct` declares `panflute` and died instantly — `ModuleNotFoundError` in 0.04s, which
    # was the tell all along. **A failure that fast has not imported anything**, and the message
    # named the missing package rather than the missing venv.
    # ⚑ FIVE HYPOTHESES DIED BEFORE THIS ONE, every one about the ENVIRONMENT of the subprocess —
    # PATH, PYTHONPATH composition, the editable `.pth`, pytest's rootdir, site-packages staging.
    # The cause was the INTERPRETER argument, one line above where they were all looking. What
    # found it was printing the arguments `main()` actually passes into `run()`, after `run()`
    # was measured CORRECT when called directly with the same-looking values.
    # ⚑ ABSOLUTE BUT NOT RESOLVED. The subprocess runs with `cwd` set to the temp tree, so a
    # relative argument names nothing there — measured, `FileNotFoundError` on the first cell.
    # `absolute()` prepends the caller's cwd WITHOUT following symlinks, which is exactly the
    # distinction this line turns on.
    config = pathlib.Path(argv[2]).resolve()
    grid = Grid(py=pathlib.Path(argv[1]).absolute(), dist=config.parent, config=config)
    modules = sorted((grid.dist / "src").rglob("*.py"))
    attempted, unreachable, jobs = _plan(grid.dist, modules)
    groups: dict[str, list[str]] = {"killed": [], "survived": [], "errored": []}

    # ⚑⚑ THE MUTANTS RUN CONCURRENTLY, BECAUSE SERIAL COST GREW PAST THE TARGET'S CEILING. Measured
    # 2026-09-23: adding `membudget_cli` (~30 def-sites) took //fence:mutants past 300s at a load of
    # ~33 — the grid, not the host, was the cost: one full `-x` suite per site, one after another.
    # Raising the ceiling was refused (a standing rule) and so was narrowing the grid. Each mutant
    # already builds in its OWN temp tree with its OWN `HOME`, so they share nothing to race on;
    # results are gathered in SITE ORDER, so the report is the serial report, byte for byte.
    # `MUTATE_JOBS` bounds the pool; `1` restores the serial run.
    workers = int(os.environ.get("MUTATE_JOBS", "") or (os.cpu_count() or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(run, grid, mutant, debug=debug) for _site, mutant in jobs]
        verdicts = [f.result() for f in futures]
    for (site, _mutant), got in zip(jobs, verdicts, strict=True):
        if debug:
            sys.stdout.write(f"    {site} -> {got}\n")
        groups[got].append(site)
    return _account(grid.dist.name, len(modules), attempted, unreachable, groups)


def _account(name: str, module_count: int, attempted: list[str], unreachable: list[str],
             groups: dict[str, list[str]]) -> int:
    """Check that every site landed in exactly one category, then report all four by name.

    Returns:
        0 when every site was accounted for and none survived, 1 otherwise.

    """
    killed, survived, errored = groups["killed"], groups["survived"], groups["errored"]

    # ⚑⚑ SURVIVORS ARE `attempted - killed - errored` BY CONSTRUCTION, ASSERTED RATHER THAN
    # ASSUMED. paperkit's fingerprint names only the KILLED sites, so a site absent from it either
    # survived or was never mutated and the record cannot say which — *absent ≠ surviving*. They
    # volunteered that as the half to build differently. Carrying ATTEMPTED is what makes the three
    # sets exhaustive; this check is what makes the carrying real rather than decorative.
    accounted = sorted(killed + survived + errored + unreachable)
    if accounted != sorted(attempted):
        missing = sorted(set(attempted) - set(accounted))
        sys.stderr.write(f"mutate: {len(attempted)} attempted, {len(accounted)} accounted — "
                         f"unclassified: {missing}\n")
        return 1

    sys.stdout.write(
        f"{name}: ATTEMPTED {len(attempted)} def-site(s) in {module_count} module(s)\n")
    # ⚑⚑⚑ EVERY CATEGORY PRINTS EVEN WHEN EMPTY, AND THAT IS NOT COSMETIC. The predecessor hid
    # ERRORED behind `if errored:`, so a reader saw no heading and could not tell *none occurred*
    # from *the set is never populated* — and the defect lived in exactly that gap for as long as
    # the probe existed. An empty category NAMED is a measurement; an absent category is a silence.
    for label, group, gloss in (
        ("KILLED", killed, "the suite RAN and a test FAILED"),
        ("SURVIVED", survived, "the suite ran and noticed nothing"),
        ("ERRORED", errored, "the suite did NOT run, so it noticed nothing"),
        ("UNREACHABLE", unreachable,
         ("constructed at IMPORT time (an Enum member); this OPERATOR cannot reach them, "
          "which is a fact about `body -> raise` and not about the suite")),
    ):
        sys.stdout.write(f"\n{label} ({len(group)}) — {gloss}:\n")
        for site in sorted(group):
            sys.stdout.write(f"    {site}\n")

    if errored:
        sys.stderr.write(
            f"\nmutate: {len(errored)} mutant(s) could not be RUN — the grid is incomplete and "
            f"a clean SURVIVED list would be a claim over a population that was never measured\n")
        return 1
    if survived:
        sys.stderr.write(
            f"\nmutate: {len(survived)} def-site(s) SURVIVED — mutating them changed no verdict, "
            f"so nothing in this distribution's suite exercises them\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
