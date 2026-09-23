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
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

# ⚑ THE SANDBOX STAGES ONLY WHAT IS DECLARED, so these are the trees a mutant must not carry into
# its copy. `.venv` in particular is a directory of pointers at host absolute paths — the property
# that makes it unfit as a bazel input makes it unfit to copy.
_NOT_SOURCE = shutil.ignore_patterns(
    ".venv", "build", "*.egg-info", "__pycache__", ".*_cache", "bazel-*",
)


def sites(tree: ast.Module) -> list[ast.FunctionDef]:
    """List every function definition in a parsed module, in source order.

    Returns:
        the `FunctionDef` nodes, nested ones included.

    """
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


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

    Returns:
        `"<Class>.<method>"` for every method of an `Enum` subclass in this module.

    """
    enum_bases = {"enum.Enum", "Enum", "enum.StrEnum", "StrEnum", "enum.IntEnum", "IntEnum"}
    excluded: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not ({ast.unparse(b) for b in node.bases} & enum_bases):
            continue
        excluded |= {i.name for i in node.body if isinstance(i, ast.FunctionDef)}
    return excluded


def mutate(source: str, target: str) -> str:
    """Replace one def-site's body with a bare raise, leaving the rest of the module alone.

    ⚑ THE DOCSTRING IS KEPT so the mutant stays syntactically a function with a body. Replacing
    everything including the docstring would change two things under one label, and a mutant that
    alters more than its operator claims cannot support a conclusion about that operator.

    Returns:
        the module source with `target` mutated.

    Raises:
        LookupError: when no def-site carries that name.

    """
    tree = ast.parse(source)
    for node in sites(tree):
        if node.name != target:
            continue
        keep = node.body[:1] if (
            isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ) else []
        raiser = ast.parse('raise AssertionError("mutant")').body
        node.body = [*keep, *raiser]
        return ast.unparse(ast.fix_missing_locations(tree))
    msg = f"no def-site named {target}"
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
    if 'AssertionError: mutant' in stdout or "AssertionError('mutant')" in stdout:
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


def run(py: pathlib.Path, dist: pathlib.Path, rel: pathlib.Path,
        source: str, name: str, config: pathlib.Path, *, debug: bool = False) -> str:
    """Build one mutant in a temp copy of the distribution and run its suite against it.

    Returns:
        this mutant's verdict.

    """
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "dist"
        shutil.copytree(dist, work, ignore=_NOT_SOURCE)
        (work / rel).write_text(mutate(source, name), encoding="utf-8")
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
        env = dict(os.environ)
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{work / 'src'}{os.pathsep}{existing}" if existing else str(work / "src")
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
        proc = subprocess.run(
            [str(py), "-m", "pytest", "-x", "-q", "--no-header",
             "-p", "no:cacheprovider", "-c", str(work / config.name), "tests"],
            cwd=work, capture_output=True, text=True, check=False, env=env,
        )
        if debug:
            tail = [ln for ln in proc.stdout.splitlines() if ln.strip()][-1:]
            marker = "AssertionError: mutant" in proc.stdout
            print(f"      rc={proc.returncode} mutant_in_stdout={marker} "
                  f"summary={tail[0] if tail else '<none>'!r}")
            if proc.stderr.strip():
                print(f"      stderr: {proc.stderr.strip().splitlines()[-1]}")
            # ⚑ WHEN THE MUTANT NEVER APPEARS, THE INTERESTING TEXT IS THE ERROR ITSELF — the
            # suite failed BEFORE reaching mutated code, so the summary line says nothing about
            # the mutation and everything about the environment.
            if not marker:
                for ln in proc.stdout.splitlines():
                    if "Error" in ln or "error" in ln.lower():
                        print(f"      | {ln.strip()[:160]}")
        return verdict(proc.returncode, proc.stdout)


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
    py = pathlib.Path(argv[1]).absolute()
    config = pathlib.Path(argv[2]).resolve()
    dist = config.parent
    modules = sorted((dist / "src").rglob("*.py"))

    attempted: list[str] = []
    killed: list[str] = []
    survived: list[str] = []
    errored: list[str] = []
    unreachable: list[str] = []
    jobs: list[tuple[str, pathlib.Path, str, str]] = []
    for mod in modules:
        source = mod.read_text(encoding="utf-8")
        tree = ast.parse(source)
        rel = mod.relative_to(dist)
        skip = import_time_sites(tree)
        for node in sites(tree):
            site = f"{rel}::{node.name}"
            attempted.append(site)
            # ⚑ COUNTED IN ATTEMPTED AND NOT RUN. Dropping it from `attempted` would make the
            # accounting balance by shrinking the denominator, which is the flattering direction
            # and the one this runner's predecessor took with ERRORED.
            if node.name in skip:
                unreachable.append(site)
                continue
            jobs.append((site, rel, source, node.name))

    # ⚑⚑ THE MUTANTS RUN CONCURRENTLY, BECAUSE SERIAL COST GREW PAST THE TARGET'S CEILING. Measured
    # 2026-09-23: adding `membudget_cli` (~30 def-sites) took //fence:mutants past 300s at a load of
    # ~33 — the grid, not the host, was the cost: one full `-x` suite per site, one after another.
    # Raising the ceiling was refused (a standing rule) and so was narrowing the grid. Each mutant
    # already builds in its OWN temp tree with its OWN `HOME`, so they share nothing to race on;
    # results are gathered in SITE ORDER, so the report is the serial report, byte for byte.
    # `MUTATE_JOBS` bounds the pool; `1` restores the serial run.
    workers = int(os.environ.get("MUTATE_JOBS", "") or (os.cpu_count() or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        verdicts = list(pool.map(
            lambda job: run(py, dist, job[1], job[2], job[3], config, debug=debug), jobs))
    for (site, _rel, _source, _name), got in zip(jobs, verdicts, strict=True):
        if debug:
            print(f"    {site} -> {got}")
        {"killed": killed, "survived": survived, "errored": errored}[got].append(site)

    # ⚑⚑ SURVIVORS ARE `attempted - killed - errored` BY CONSTRUCTION, ASSERTED RATHER THAN
    # ASSUMED. paperkit's fingerprint names only the KILLED sites, so a site absent from it either
    # survived or was never mutated and the record cannot say which — *absent ≠ surviving*. They
    # volunteered that as the half to build differently. Carrying ATTEMPTED is what makes the three
    # sets exhaustive; this check is what makes the carrying real rather than decorative.
    accounted = sorted(killed + survived + errored + unreachable)
    if accounted != sorted(attempted):
        missing = sorted(set(attempted) - set(accounted))
        print(f"mutate: {len(attempted)} attempted, {len(accounted)} accounted — "
              f"unclassified: {missing}", file=sys.stderr)
        return 1

    print(f"{dist.name}: ATTEMPTED {len(attempted)} def-site(s) in {len(modules)} module(s)")
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
        print(f"\n{label} ({len(group)}) — {gloss}:")
        for site in sorted(group):
            print(f"    {site}")

    if errored:
        print(f"\nmutate: {len(errored)} mutant(s) could not be RUN — the grid is incomplete and "
              f"a clean SURVIVED list would be a claim over a population that was never measured",
              file=sys.stderr)
        return 1
    if survived:
        print(f"\nmutate: {len(survived)} def-site(s) SURVIVED — mutating them changed no verdict, "
              f"so nothing in this distribution's suite exercises them", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
