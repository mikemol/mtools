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
import signal
import subprocess
import sys
import tempfile

# ⚑⚑ THE FENCE SIBLING EDGE (mtools:W619, ruled A+B 2026-10-04). This runs under each
# distribution's own `.venv`, and only fence's carries `mikemol.fence`, so `mutate_check.sh` names
# the sibling's source root in `MUTATE_FENCE_SRC` (staged by each `:mutants` target's
# `//fence:fence` data) and it goes on THIS interpreter's path only; a suite receives the variable
# inert. `sys.path.extend` is the one statement an import may follow.
#
# ⚑⚑ THE MUTATION SIBLING EDGE (mtools:W629), THE SAME MECHANISM: the declared-defect path reads and
# plants through `mikemol.mutation.declarations`, its source root named in `MUTATE_MUTATION_SRC` and
# staged by each `:mutants` target's `//mutation:mutation` data. Standard library only, so it adds
# nothing to a distribution's own environment.
sys.path.extend(
    p
    for var in ("MUTATE_FENCE_SRC", "MUTATE_MUTATION_SRC")
    for p in os.environ.get(var, "").split(os.pathsep)
    if p
)

from mikemol.fence.git_env import clean_env
from mikemol.mutation.declarations import DECLARATION_FILE, Declared, plant, read_declarations

_FNV_OFFSET = 2166136261
_FNV_PRIME = 16777619
_FNV_MASK = 0xFFFFFFFF


def shard_spec(raw: str) -> tuple[int, int] | None:
    """Read `MUTATE_SHARD`, `i/N`: this run's share of the grid, none when unset.

    ⚑ A TARGET THAT TIMES OUT UNDER LOAD IS SPLIT, NOT GIVEN MORE TIME (operator 2026-10-10,
    mtools:W970). Each shard runs only the sites whose stable hash falls in its share.

    Returns:
        `(index, count)`, or None for the whole grid.

    Raises:
        ValueError: when `raw` is not `i/N` with `0 <= i < N`.

    """
    if not raw:
        return None
    index, _, count = raw.partition("/")
    if not (index.isdigit() and count.isdigit()) or int(count) < 1 or int(index) >= int(count):
        msg = f"MUTATE_SHARD must be i/N with 0 <= i < N, got {raw!r}"
        raise ValueError(msg)
    return int(index), int(count)


def in_shard(key: str, shard: tuple[int, int] | None) -> bool:
    """Say whether a site or declared defect belongs to this shard.

    ⚑ A HASH THAT IS THE SAME ON EVERY RUN AND EVERY HOST (FNV-1a over the key's bytes), not
    `hash()`, which is randomised per process: every key lands in exactly one of the N shards, so
    the union of the shards is the whole grid with no overlap.

    Returns:
        True for the whole grid, else whether the key's hash falls in this shard's share.

    """
    if shard is None:
        return True
    digest = _FNV_OFFSET
    for byte in key.encode():
        digest = ((digest ^ byte) * _FNV_PRIME) & _FNV_MASK
    return digest % shard[1] == shard[0]


def read_declared(dist: pathlib.Path) -> list[Declared]:
    """Read the distribution's declared defect classes, none when it has no `mutants.regex`.

    Returns:
        the declarations in file order; empty when the file is absent.

    Raises:
        ValueError: when the file is malformed; the message names the file and the line.

    """
    path = dist / DECLARATION_FILE
    if not path.is_file():
        return []
    try:
        return read_declarations(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        msg = f"{DECLARATION_FILE}: {exc}"
        raise ValueError(msg) from exc


def run_declared(grid: Grid, declared: Declared, *, debug: bool = False) -> str:
    """Plant one declared defect in a temp copy and run the distribution's suite against it.

    ⚑⚑ FOUR OUTCOMES, NOT THREE: `killed` (the suite noticed), `survived` (it is blind to a defect
    the distribution named), `errored` (the suite did not run, or the declaration is bad: a module
    that is not there, a rewrite that no longer parses) and `unapplied` (the pattern matches
    nothing, so no defect was planted and no question was asked: a STALE declaration).

    Returns:
        the outcome.

    """
    path = grid.dist / declared.module
    if not path.is_file():
        return "errored"
    try:
        mutant = plant(path.read_text(encoding="utf-8"), declared.spec)
    except ValueError:
        return "errored"
    if mutant is None:
        return "unapplied"
    return _run_text(grid, pathlib.Path(declared.module), mutant, debug=debug)


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


# ⚑⚑ THE PER-MUTANT TIME LIMIT (W359), in seconds of WALL time. A mutant that turns a bounded wait
# into an unbounded one (a retry loop around the raised `AssertionError`) never ends its suite, and
# without a limit ONE such cell held the whole grid until bazel's own ceiling killed it — measured
# as //gmailstruct:mutants TIMEOUT 300s (W356), a grid that reported nothing about any site.
_DEFAULT_TIMEOUT_S = 60.0


def mutant_timeout() -> float:
    """Read the per-mutant wall-time limit from `MUTATE_TIMEOUT`, defaulting to 60s.

    Returns:
        the limit in seconds of wall time.

    """
    return float(os.environ.get("MUTATE_TIMEOUT", "") or _DEFAULT_TIMEOUT_S)


def launch(
    argv: list[str],
    cwd: pathlib.Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    """Run one mutant's suite: argv only, no shell, output captured as text, bounded in time.

    ⚑ ONE SEAM FOR THE ONE SUBPROCESS, so a test replaces THIS rather than `subprocess.run` for the
    whole interpreter — which also replaced the git its own fixture needed.

    ⚑⚑ THE SUITE RUNS IN ITS OWN SESSION AND THE WHOLE GROUP IS KILLED AT THE LIMIT. Killing only
    the direct child would leave any grandchild holding the output pipes, and the read would wait
    on it — the hang moved one level down rather than removed.

    Returns:
        the completed process; its status is read by `verdict`, never raised.

    Raises:
        subprocess.TimeoutExpired: when the suite outlives `mutant_timeout()`; the group is dead.

    """
    limit = mutant_timeout()
    with subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    ) as proc:
        try:
            out, err = proc.communicate(timeout=limit)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            raise
        return subprocess.CompletedProcess(argv, proc.returncode, out, err)


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
        path
        for path, _node, owner in _owned(tree)
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
        keep = (
            node.body[:1]
            if (
                isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            )
            else []
        )
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
    sys.stdout.write(
        f"      rc={proc.returncode} mutant_in_stdout={reached} "
        f"summary={tail[0] if tail else '<none>'!r}\n"
    )
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
    return _run_text(grid, mutant.rel, mutate(mutant.source, mutant.name), debug=debug)


def _run_text(grid: Grid, rel: pathlib.Path, text: str, *, debug: bool = False) -> str:
    """Write `text` over module `rel` in a temp copy of the distribution and run its suite there.

    ⚑ ONE PLACE FOR BOTH OPERATORS: a def-site mutant (`run`) and a declared regex defect
    (`run_declared`) differ only in the text they put on the module, so the isolation, the
    environment and the time limit below are written once and cannot drift apart.

    Returns:
        this mutant's verdict.

    """
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "dist"
        shutil.copytree(grid.dist, work, ignore=_not_source)
        (work / rel).write_text(text, encoding="utf-8")
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
        # ⚑ fence's `git_env.clean_env()` rule (W619: imported), at the runner, so suites not yet
        # written are covered too. A suite reading git state finds the repository from its `cwd`
        # as before.
        env = clean_env()
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
        # ⚑⚑ A SUITE THAT OUTLIVES THE LIMIT IS A KILL: it did not pass, and the only code that
        # differs from a clean run is the mutant, so the mutant is what it noticed.
        try:
            proc = _launch_suite(grid, work, env)
        except subprocess.TimeoutExpired:
            if debug:
                sys.stdout.write(f"      timed out after {mutant_timeout()}s\n")
            return "killed"
        if debug:
            _report_debug(proc)
        return verdict(proc.returncode, proc.stdout)


def _launch_suite(
    grid: Grid, work: pathlib.Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run the distribution's suite inside the mutant's temp tree.

    Returns:
        the completed suite process.

    """
    return launch(
        [
            str(grid.py),
            "-m",
            "pytest",
            "-x",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
            "-c",
            str(work / grid.config.name),
            "tests",
        ],
        work,
        env,
    )


def _plan(
    dist: pathlib.Path, modules: list[pathlib.Path]
) -> tuple[
    list[str],
    list[str],
    list[tuple[str, Mutant]],
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

    # ⚑⚑ A MALFORMED `mutants.regex` REFUSES THE WHOLE GRID, naming the line (W629), rather than
    # being read as "declared nothing". A MALFORMED `MUTATE_SHARD` REFUSES IT THE SAME WAY (W970).
    try:
        shard = shard_spec(os.environ.get("MUTATE_SHARD", ""))
        declared = [d for d in read_declared(grid.dist) if in_shard(d.label, shard)]
    except ValueError as exc:
        sys.stderr.write(f"mutate: {exc}\n")
        return 1
    attempted = [s for s in attempted if in_shard(s, shard)]
    unreachable = [s for s in unreachable if in_shard(s, shard)]
    jobs = [(site, mutant) for site, mutant in jobs if in_shard(site, shard)]
    verdicts, regex = _run_all(grid, [m for _site, m in jobs], declared, debug=debug)
    for (site, _mutant), got in zip(jobs, verdicts, strict=True):
        if debug:
            sys.stdout.write(f"    {site} -> {got}\n")
        groups[got].append(site)
    name = grid.dist.name if shard is None else f"{grid.dist.name} shard {shard[0]}/{shard[1]}"
    code = _account(name, len(modules), attempted, unreachable, groups)
    # ⚑ BOTH ARE COMPUTED BEFORE EITHER DECIDES THE EXIT: `code or _regex_section(...)` would skip
    # printing the declared-defect section whenever the def-site grid had already failed.
    regex_code = _regex_section(regex)
    return 1 if code or regex_code else 0


def _run_all(
    grid: Grid, mutants: list[Mutant], declared: list[Declared], *, debug: bool
) -> tuple[list[str], list[tuple[str, str]]]:
    """Run every def-site mutant and every declared defect in one pool, results in input order.

    ⚑⚑ THE DECLARED DEFECTS SHARE THE POOL (W629): a distribution that declares none pays nothing,
    and one that declares some pays one suite run each, concurrently with the def-sites.

    Returns:
        the def-site verdicts, and each declared defect's `(label, outcome)`.

    """
    # ⚑⚑ THE MUTANTS RUN CONCURRENTLY, BECAUSE SERIAL COST GREW PAST THE TARGET'S CEILING. Measured
    # 2026-09-23: adding `membudget_cli` (~30 def-sites) took //fence:mutants past 300s at a load of
    # ~33 — the grid, not the host, was the cost: one full `-x` suite per site, one after another.
    # Raising the ceiling was refused (a standing rule) and so was narrowing the grid. Each mutant
    # already builds in its OWN temp tree with its OWN `HOME`, so they share nothing to race on;
    # results are gathered in SITE ORDER, so the report is the serial report, byte for byte.
    # `MUTATE_JOBS` bounds the pool; `1` restores the serial run.
    workers = int(os.environ.get("MUTATE_JOBS", "") or (os.cpu_count() or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(run, grid, mutant, debug=debug) for mutant in mutants]
        planted = [pool.submit(run_declared, grid, d, debug=debug) for d in declared]
        verdicts = [f.result() for f in futures]
        regex = [(d.label, f.result()) for d, f in zip(declared, planted, strict=True)]
    return verdicts, regex


def _regex_section(results: list[tuple[str, str]]) -> int:
    """Print the declared-defect section and say what a declared defect that was not killed means.

    ⚑ AN EMPTY SECTION IS NAMED, as the four before it are: `none declared` is a measurement and an
    absent heading is a silence that cannot be told from a section that never ran.

    ⚑⚑ ONLY `killed` PASSES. `survived` is a suite blind to a defect the distribution named,
    `unapplied` a declaration the code has moved away from, and `errored` one that was never run.

    Returns:
        0 when every declared defect was killed (vacuously, when none are declared), else 1.

    """
    sys.stdout.write(
        f"\nREGEX ({len(results)}) — defects the distribution DECLARED in {DECLARATION_FILE}, "
        f"planted one at a time:\n"
    )
    if not results:
        sys.stdout.write("    none declared\n")
    for label, got in results:
        sys.stdout.write(f"    {label} -> {got}\n")
    bad = [label for label, got in results if got != "killed"]
    if bad:
        sys.stderr.write(
            f"\nmutate: {len(bad)} declared defect(s) NOT killed: a suite blind to a named defect "
            f"(survived), a stale declaration (unapplied) or one never run (errored)\n"
        )
    return 1 if bad else 0


def _account(
    name: str,
    module_count: int,
    attempted: list[str],
    unreachable: list[str],
    groups: dict[str, list[str]],
) -> int:
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
        sys.stderr.write(
            f"mutate: {len(attempted)} attempted, {len(accounted)} accounted — "
            f"unclassified: {missing}\n"
        )
        return 1

    sys.stdout.write(
        f"{name}: ATTEMPTED {len(attempted)} def-site(s) in {module_count} module(s)\n"
    )
    # ⚑⚑⚑ EVERY CATEGORY PRINTS EVEN WHEN EMPTY, AND THAT IS NOT COSMETIC. The predecessor hid
    # ERRORED behind `if errored:`, so a reader saw no heading and could not tell *none occurred*
    # from *the set is never populated* — and the defect lived in exactly that gap for as long as
    # the probe existed. An empty category NAMED is a measurement; an absent category is a silence.
    for label, group, gloss in (
        ("KILLED", killed, "the suite RAN and a test FAILED"),
        ("SURVIVED", survived, "the suite ran and noticed nothing"),
        ("ERRORED", errored, "the suite did NOT run, so it noticed nothing"),
        (
            "UNREACHABLE",
            unreachable,
            (
                "constructed at IMPORT time (an Enum member); this OPERATOR cannot reach them, "
                "which is a fact about `body -> raise` and not about the suite"
            ),
        ),
    ):
        sys.stdout.write(f"\n{label} ({len(group)}) — {gloss}:\n")
        for site in sorted(group):
            sys.stdout.write(f"    {site}\n")

    if errored:
        sys.stderr.write(
            f"\nmutate: {len(errored)} mutant(s) could not be RUN — the grid is incomplete and "
            f"a clean SURVIVED list would be a claim over a population that was never measured\n"
        )
        return 1
    if survived:
        sys.stderr.write(
            f"\nmutate: {len(survived)} def-site(s) SURVIVED — mutating them changed no verdict, "
            f"so nothing in this distribution's suite exercises them\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
