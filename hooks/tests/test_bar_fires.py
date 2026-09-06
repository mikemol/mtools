# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The bar's own F-arms: each configured rule FIRES on the absence of the thing it means.

⚑⚑⚑ A CONFIGURED-BUT-INERT GATE IS THE EASY CASE. It fires on nothing and someone eventually
notices. AN ACTIVE GATE AIMED AT THE WRONG PREDICATE IS THE HARD CASE: it produces findings, it
passes review, and its greens are indistinguishable from correct ones. This repo and a peer were
MIRROR IMAGES of exactly that — one `notice-rgx` matched the SPDX line only, the other's default
matched `Copyright` only, so neither gated both and each party ran the arm its own config would
pass. Three separate grids were run over one rule and none carried a separator arm.

⚑⚑ SO THE ASSERTION IS PER PROPOSITION, NOT PER RULE. "CPY001 is enabled" was true in both repos
while both were half-blind. What must be asserted is that the rule fires on the absence of the
thing we mean — and a rule meaning four things needs four arms.

⚑⚑ AND EVERY F-ARM NEEDS ITS P-ARM. Without one, "every arm fires" is indistinguishable from a
checker that rejects everything, which is not a strict gate but a broken one that gets disabled
within a day.

⚑ THE CHECKER IS INVOKED AS THE GATE INVOKES IT — the distribution's own pinned binary against
the distribution's own config, on a file in a temp tree. Reading the config text would assert
INTENT; running the checker asserts EFFECT. A resolver, not a config file, decides which rules
exist: this repo's lock pinned one ruff while its venv ran another, so every arm had been measured
on a version the build would not install.
"""

from __future__ import annotations

import ast as pyast
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# ⚑ `Path` IS A RUNTIME IMPORT HERE, NOT ANNOTATION-ONLY. ruff's TC003 asked for it to move
# into a type-checking block; these module-level constants evaluate it at import time, so that
# move turns collection into a NameError. The rule was right about the common case and wrong
# about this file — which is why the finding was answered by reading the use, not by obeying the
# suggestion.
# ⚑⚑⚑ `.parent`, NOT `.resolve().parent` — AND THAT IS A SANDBOX ESCAPE, MEASURED. bazel stages
# runfiles as SYMLINKS back into the source tree, so `resolve()` follows them out of the sandbox
# and every read below then hit the LIVE WORKING COPY rather than the staged one. The probe that
# showed it: inside a hermetic action, `_DIST/.venv/bin/ruff` reported `is_file() == True` and
# resolved to `/home/mikemol/github/mtools/hooks/.venv/bin/ruff` — a developer venv that is not
# part of the repository at all, reached from a sandbox that is supposed to have staged inputs
# only. That is precisely the escape MODULE.bazel refuses for editable installs, in a test.
_DIST = Path(__file__).parent.parent


def _ruff_argv() -> list[str]:
    """Return the argv prefix that runs ruff, REFUSING when there is none.

    ⚑⚑⚑ THIS FILE ONCE READ `.venv/bin/ruff` UNCONDITIONALLY, so it passed only where a
    developer venv happened to exist. Measured from a fresh `git clone` with no venvs: 24 of 25
    hermetic targets passed and this one failed — the suite that exists to catch a gate aimed at
    the wrong thing, itself aimed at a path that is not part of the repository.

    ⚑⚑ `RUFF_BIN` NAMES A HASH-PINNED http_archive, NOT A pip DEPENDENCY. rules_python stages
    only `site-packages`, dropping the wheel's `bin/ruff`, so the installed package is a shim
    whose `find_ruff_bin()` searches for a binary that was never staged — `python -m ruff` inside
    a hermetic action raised and listed the paths it had tried. A pip requirement that cannot be
    EXECUTED is not a usable dependency for a test that runs the checker.

    ⚑ ABSENT EVERY SOURCE, THIS RAISES RATHER THAN SKIPPING. A skipped case and a passing one are
    indistinguishable in a summary line, and every arm below would then report green over a
    checker that was never run.

    Returns:
        The argv prefix to run ruff with.

    Raises:
        RuntimeError: when no ruff can be found by any route.

    """
    # ⚑⚑ `$(location ...)` YIELDS A PATH RELATIVE TO THE RUNFILES `_main` DIRECTORY, which is
    # `../+_repo_rules+ruff/ruff` for an external archive — it escapes `_main` by design.
    # MEASURED rather than guessed, after three cuts resolved it against the wrong base: this
    # file is staged at `<runfiles>/_main/hooks/tests/`, so `_DIST.parent` IS `_main` and the
    # declared path resolves against it. Passing the value raw produced a TypeError about
    # path-like args from a subprocess that never started.
    declared = os.environ.get("RUFF_BIN")
    if declared:
        candidate = (_DIST.parent / declared).resolve()
        if candidate.is_file():
            return [str(candidate)]
    local = _DIST / ".venv" / "bin" / "ruff"
    if local.is_file():
        return [str(local)]
    found = shutil.which("ruff")
    if found:
        return [found]
    msg = "no ruff available — refusing rather than reporting green over a checker that never ran"
    raise RuntimeError(msg)


_GOOD_HEADER = "# SPDX-License-Identifier: Apache-2.0\n# Copyright (c) 2026 Mike Mol\n"


def _ruff(rel: str, body: str, tmp: Path) -> str:
    """Run this distribution's ruff, with this distribution's config, over one written file.

    ⚑ `--no-cache` because a cache keyed on a path would answer about a previous body, and this
    function writes many bodies to few paths.
    """
    target = tmp / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    proc = subprocess.run(  # noqa: S603 — the checker is the subject of these cases
        [*_ruff_argv(), "check", "--no-cache", "--config", str(_DIST / "pyproject.toml"),
         "--output-format", "concise", str(target)],
        capture_output=True, text=True, check=False, cwd=tmp)
    return proc.stdout + proc.stderr


@pytest.fixture(scope="module")
def tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return a temp tree shaped like a distribution.

    ⚑ The shape matters: per-file-ignores resolve by PATH, so a probe written to `src/` and one
    written to `tests/` must sit under those names to be judged the way real files are.
    """
    return tmp_path_factory.mktemp("bar")


# ────────────────────────── the header notice: four propositions, one rule ──────────────────────

def test_the_header_gate_passes_a_correct_notice(tree: Path) -> None:
    """The P-arm. Without it every arm below passes against a rule that rejects all input."""
    assert "CPY001" not in _ruff("src/probe_ok.py", _GOOD_HEADER + '"""D."""\n', tree)


@pytest.mark.parametrize(
    ("proposition", "header"),
    [
        ("the SPDX line is present",
         "# Copyright (c) 2026 Mike Mol\n"),
        ("the copyright line is present",
         "# SPDX-License-Identifier: Apache-2.0\n"),
        ("SPDX comes first",
         "# Copyright (c) 2026 Mike Mol\n# SPDX-License-Identifier: Apache-2.0\n"),
        ("the two lines are adjacent, blank line between",
         "# SPDX-License-Identifier: Apache-2.0\n\n# Copyright (c) 2026 Mike Mol\n"),
        ("the two lines are adjacent, comment between",
         "# SPDX-License-Identifier: Apache-2.0\n#\n# Copyright (c) 2026 Mike Mol\n"),
        ("the holder is this repo's",
         "# SPDX-License-Identifier: Apache-2.0\n# Copyright (c) 2026 Someone Else\n"),
    ],
)
def test_the_header_gate_fires_when_a_proposition_fails(
        proposition: str, header: str, tree: Path) -> None:
    """The gate fires when any one of the notice's propositions fails.

    ⚑ ONE ARM PER PROPOSITION. `notice-rgx` asserts presence, ORDER, ADJACENCY and HOLDER —
    four claims in one regex — and an earlier version of it silently accepted a blank line between
    the two notices while rejecting a `#` line between them. The tidier-looking file was the one
    that slipped through, so the gate was teaching the wrong habit rather than merely missing one.
    """
    out = _ruff("src/probe_bad.py", header + '"""D."""\n', tree)
    assert "CPY001" in out, f"gate did not fire on: {proposition}"


def test_the_header_gate_accepts_a_shebang_before_the_notice(tree: Path) -> None:
    """A shebang may precede the notice.

    ⚑ A `#!` that is not on line 1 stops being a shebang, so the notice follows it rather than
    preceding it. codemod_header.py depends on this and would otherwise be unadoptable here.
    """
    body = "#!/usr/bin/env python3\n" + _GOOD_HEADER + '"""D."""\n'
    assert "CPY001" not in _ruff("src/probe_shebang.py", body, tree)


def test_the_header_gate_accepts_a_later_year(tree: Path) -> None:
    r"""A later year passes.

    ⚑ The year is `\d{4}`, not a literal 2026. A copyright year is the year of AUTHORSHIP, so a
    file written in a later year carries a later year without a config change — and pinning the
    literal would make every January a silent, tree-wide false negative.
    """
    body = "# SPDX-License-Identifier: Apache-2.0\n# Copyright (c) 2031 Mike Mol\n" + '"""D."""\n'
    assert "CPY001" not in _ruff("src/probe_year.py", body, tree)


# ────────────────────────── the scoped exemptions: refused where the reason does not obtain ─────

def test_assert_is_refused_in_src(tree: Path) -> None:
    """`assert` is refused in src.

    ⚑ S101 is scoped to tests by PATH, and a scope is only meaningful if it has an outside.
    """
    body = _GOOD_HEADER + '"""D."""\n\n\ndef f() -> None:\n    """D."""\n    assert True\n'
    assert "S101" in _ruff("src/probe_assert.py", body, tree)


def test_assert_is_permitted_in_tests(tree: Path) -> None:
    """The P-arm for the scope. `assert` is the test idiom and `-O` never runs these."""
    body = _GOOD_HEADER + '"""D."""\n\n\ndef test_f() -> None:\n    """D."""\n    assert True\n'
    assert "S101" not in _ruff("tests/probe_assert.py", body, tree)


# ────────────────────────── declare-never-suppress, asserted as an effect ───────────────────────

def test_the_ignore_list_is_exactly_three_rules() -> None:
    """The ignore list holds exactly three rules.

    ⚑⚑ THE BAR IS THE MAX, SO IGNORES DO NOT ACCUMULATE. Three entries, each a checker-vs-checker
    conflict rather than a finding declined: D203/D213 are docstring-style pairs whose alternatives
    are mutually exclusive, and COM812 fights the formatter. A fourth entry appearing without this
    test failing is how a bar erodes — one exemption at a time, each defensible alone.

    ⚑ A peer carries a fourth (CPY001, deferred for want of a LICENSE). This repo has a LICENSE,
    which is that deferral's own stated exit condition, so it is not inherited.
    """
    text = (_DIST / "pyproject.toml").read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if ln.startswith("ignore = "))
    assert line == 'ignore = ["D203", "D213", "COM812"]'


def test_the_checker_that_runs_is_the_one_the_lock_pins() -> None:
    """The checker that runs is the one the lock pins.

    ⚑⚑ A RULE SET IS A PROPERTY OF THE RESOLVER, NOT OF THE CONFIG TEXT. This repo's lock pinned
    ruff 0.16.6 while its venv ran 0.16.5, so every arm above had been measured against a version
    the build would not install. The drift was benign and being UNMEASURED was not.
    """
    pinned = next(ln for ln in (_DIST / "requirements.txt").read_text(encoding="utf-8").splitlines()
                  if ln.startswith("ruff=="))
    proc = subprocess.run(  # noqa: S603 — the checker is the subject of this case
        [*_ruff_argv(), "--version"], capture_output=True, text=True, check=True)
    assert proc.stdout.split()[1] == pinned.split("==")[1].strip()


def test_an_unknown_pytest_marker_is_an_error_rather_than_a_skip(tree: Path) -> None:
    """An unknown marker fails collection rather than skipping the case.

    ⚑ `--strict-markers` — a typo'd marker on a test must fail COLLECTION, not silently skip it.
    A skipped test and a passing one are indistinguishable in a summary line, which is the
    green-over-nothing shape this repo keeps finding one layer down.

    ⚑⚑ TWO EARLIER VERSIONS OF THIS ARM WERE AIMED AT THE WRONG PREDICATE, in the file whose
    whole subject is that failure. The first passed `-m nonexistent` and expected an error; `-m`
    DESELECTS an unknown expression and exits 5, saying nothing about strictness, because
    `--strict-markers` validates markers APPLIED TO TESTS. The second applied a marker but also
    passed `--strict-markers` ON THE COMMAND LINE — so it asserted that pytest's flag works, which
    nobody doubted, and stayed green when the flag was deleted from `addopts`. VERIFIED BY
    MUTATION: removing `--strict-markers` from the config must fail this case, and until the flag
    was dropped from the invocation it did not.
    """
    probe = tree / "marker_probe" / "test_probe.py"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text(
        "import pytest\n\n\n@pytest.mark.nonexistent_marker_probe\ndef test_x() -> None:\n"
        "    assert True\n", encoding="utf-8")
    proc = subprocess.run(  # noqa: S603 — pytest's own configuration is the subject
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "-c", str(_DIST / "pyproject.toml"), str(probe)],
        capture_output=True, text=True, check=False, cwd=_DIST)
    assert proc.returncode != 0
    assert "nonexistent_marker_probe" in proc.stdout + proc.stderr


def test_a_declared_pytest_marker_collects_cleanly(tree: Path) -> None:
    """The P-arm for strictness: a marker the config DECLARES must not trip it.

    ⚑⚑ AND IT PINS `-c` TO THIS DISTRIBUTION'S pyproject. The probe file lives in a temp tree, so
    pytest picks its rootdir from there and never reads the config under test — the arm would then
    assert strictness against pytest's DEFAULTS rather than against this repo's. Naming the config
    is what makes the subject of the case the thing it claims to be about.

    ⚑ It uses THIS distribution's marker. A first draft used a sibling's (`needs_pandoc`, which
    mdstruct declares and hooks does not) and the arm failed correctly -- the marker list is
    per-distribution, so a shared arm would have asserted a config neither repo has.
    """
    probe = tree / "marker_ok" / "test_probe.py"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text(
        "import pytest\n\n\n@pytest.mark.needs_shellcheck\ndef test_x() -> None:\n"
        "    assert True\n", encoding="utf-8")
    proc = subprocess.run(  # noqa: S603 — pytest's own configuration is the subject
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "-c", str(_DIST / "pyproject.toml"), str(probe)],
        capture_output=True, text=True, check=False, cwd=_DIST)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_mypy_path_pair_is_present_and_both_halves_are_set() -> None:
    """Both `mypy_path` and `explicit_package_bases` are set, or neither is.

    ⚑⚑ EITHER ONE ALONE LEAVES A WORKING-LOOKING CONFIG THAT CHECKS THE WRONG THING.
    `mypy_path` alone makes the source reachable under two names, so a module can be checked
    twice under different identities; `explicit_package_bases` alone does not make it
    reachable at all. The sibling distribution once had `mypy_path` without `src` and
    reported 14 errors, 13 of them `Any`, while its 90 tests passed — a green suite standing
    in for a checked one.

    ⚑ AND THE PAIR IS NOT TEMPORARY, WHICH ⟡mtools-drop-mypypath ASSERTED IT WAS. Measured
    against a fresh NON-EDITABLE install with both lines deleted, mypy passes cleanly — so
    the variable is the editable install, not bazel. Retiring it would mean a reinstall
    before any checker saw an edit. The ticket is closed won't-fix and this arm is what stops
    a future reader deleting the pair on the strength of the retired ticket's premise.
    """
    text = (_DIST / "pyproject.toml").read_text(encoding="utf-8")
    assert 'mypy_path = "src"' in text
    assert "explicit_package_bases = true" in text


def test_the_bazel_test_rule_runs_pytest_rather_than_the_module() -> None:
    """Every py_test names the pytest entry point as `main`, not the test module.

    ⚑⚑⚑ `main = <the test module>` RUNS THAT MODULE AS A SCRIPT. Import-time code executes,
    pytest never collects, and the process exits 0 — so every target reported GREEN OVER ZERO
    ASSERTIONS. Measured: a module whose only statement was `raise AssertionError` PASSED
    under bazel, across all 23 targets, for the life of the rule.

    ⚑⚑ IT IS ASSERTED HERE RATHER THAN LEFT TO THE SUITE BECAUSE THE SUITE CANNOT SEE IT. A
    broken runner reports success, so no witness inside it can fail — the defect is invisible
    from exactly the place one would look for it, and only a probe designed to fail could
    reveal it. This reads the BUILD files instead.
    """
    root = _DIST.parent
    for name in ("hooks", "mdstruct", "ratchet"):
        build = (root / name / "BUILD.bazel").read_text(encoding="utf-8")
        assert 'main = "//:pytest_main.py"' in build, name
        assert "main = src," not in build, name


def test_the_gates_own_shell_is_checked() -> None:
    """`.githooks/pre-commit` and the checker script are both in a shellcheck target.

    ⚑⚑⚑ THE SHELL THAT RUNS EVERY OTHER CHECK WAS ITSELF CHECKED BY NOTHING. It was clean
    only because its author ran shellcheck by hand after each edit — a convention held in one
    person's memory, guarding the file that guards everything else. Measured: `grep -n
    shellcheck .githooks/pre-commit` returned only a comment.

    ⚑⚑ AND THE CHECKER'S OWN SCRIPT IS IN THE SAME LIST. A gate that checks every shell file
    except itself leaves exactly the one nobody would think to look at, for the same reason
    nobody checked the hook. Both are asserted here rather than assumed from the BUILD file
    being present, because a `data` entry that is not also an `args` entry stages a file the
    checker never opens.

    ⚑⚑⚑ THE ASSERTION IS OVER THE FILESYSTEM, NOT OVER THE BUILD FILE'S TEXT, AND THE FIRST CUT
    WAS OVER THE TEXT. It held a seven-name list and grepped for `$(location //:<name>)` — so it
    verified the BUILD file's LISTING STYLE, not its coverage, and it broke the moment that list
    became a `glob()` while coverage went UP from 7 files to 11. ⚑⚑ Worse, it carried the same
    hand-written population as the thing it guarded: two copies of one list, drifting together,
    and the test could never have reported the two files (`domain_witness.sh`, `collect_check.sh`)
    that were missing from BOTH. A guard that enumerates the same way as its subject cannot
    detect an omission they share.
    """
    build = (_DIST.parent / "BUILD.bazel").read_text(encoding="utf-8")
    # ⚑⚑⚑ NO FILESYSTEM ENUMERATION HERE, AND THE SANDBOX IS WHY. A cut of this test globbed
    # `*.sh` and `.githooks/*` off disk to build the expected population: it PASSED locally and
    # FAILED hermetically with `FileNotFoundError: .../.githooks`, because inside the sandbox only
    # DECLARED inputs exist. That is the escape this target's own BUILD comment warns about —
    # these witnesses once "passed only by resolving OUT of the sandbox into the live tree" — and
    # declaring `.githooks` as data to make the read work would have re-opened the hole rather
    # than closed it.
    #
    # ⚑⚑ THE GLOB IS THE COVERAGE CLAIM, SO THE GLOB IS WHAT GETS ASSERTED. `glob()` covers every
    # matching file by construction and cannot drift as files are added — which the seven-name
    # list it replaced could and did, missing two. Asserting the mechanism is strictly stronger
    # than re-listing its outputs, and it needs no input the sandbox has not staged.
    assert 'glob(["*.sh", ".githooks/*"]' in build, (
        "the shellcheck target must glob its population, not enumerate it")
    assert '"@shellcheck//:bin"' in build, "the checker binary must be staged"


def test_no_witness_reads_a_developer_venv() -> None:
    """No test resolves a path into `.venv`, which is not part of the repository.

    ⚑⚑⚑ THIS FILE DID EXACTLY THAT, AND IT PASSED. It read `.venv/bin/ruff` and used
    `Path(__file__).resolve()`, which follows bazel's runfiles symlinks OUT of the sandbox and
    back into the live working tree — so a hermetic action was reading a developer venv that no
    clone contains. Measured two ways: a probe inside the sandbox reported
    `venv.is_file() == True` resolving to `/home/mikemol/github/mtools/hooks/.venv/bin/ruff`,
    and a fresh `git clone` with no venvs failed this one target out of 25.

    ⚑⚑ THAT IS THE EDITABLE-INSTALL ESCAPE MODULE.bazel REFUSES, REPRODUCED IN A TEST. A
    sandbox that can reach the source tree is not a sandbox, and a suite that passes only where
    its author's machine is set up a particular way says nothing about the repository.
    """
    # ⚑⚑ THE CHECK PARSES THE MODULE RATHER THAN GREPPING IT, and both weaker cuts are why. A
    # `.venv` under `tmp_path` is a FIXTURE building a fake tree — legitimate, and a substring
    # search flagged three of them. Stripping `#` comments then flagged this very docstring,
    # which DESCRIBES the defect. Only an AST walk distinguishes an expression from prose about
    # an expression, and a witness that cannot make that distinction cannot live in a file that
    # documents what it forbids.
    for dist in ("hooks", "mdstruct", "ratchet"):
        for module in sorted((_DIST.parent / dist).glob("tests/test_*.py")):
            tree = pyast.parse(module.read_text(encoding="utf-8"))
            for node in pyast.walk(tree):
                if not isinstance(node, pyast.Call):
                    continue
                func = node.func
                if not isinstance(func, pyast.Attribute) or func.attr != "resolve":
                    continue
                inner = func.value
                names = {n.id for n in pyast.walk(inner) if isinstance(n, pyast.Name)}
                assert "__file__" not in names, (
                    f"{dist}/{module.name}:{node.lineno} resolves out of the runfiles tree")


def test_the_hermetic_sandbox_is_a_default_not_a_config() -> None:
    """The sandbox flags are unconditional `build` lines, never `build:<config>`.

    ⚑⚑⚑ AN OPT-IN HERMETICITY FLAG IS NOT HERMETICITY. These flags are NOT in the action key —
    measured: a target run without them caches a green verdict, and the same target run WITH
    them reports `Executed 0 out of 1 test: 1 test passes`, the verdict crossing the boundary
    unexecuted. So a `--config` would be a regime a cache hit silently bypasses, and a flag
    that changes what an action can READ but not what it is KEYED on cannot be left to the
    caller.

    ⚑⚑ WHAT THEY BUY, MEASURED BY PROBE IN BOTH ARMS: without them a hermetic action reads
    `/home/mikemol/github/mtools/hooks/.venv/bin/ruff` and the whole source tree; with them
    neither exists. That is the escape the AST witness above catches BY PATTERN, closed here BY
    CONSTRUCTION — and the two are not substitutes.
    """
    rc = (_DIST.parent / ".bazelrc").read_text(encoding="utf-8")
    for flag in ("--experimental_use_hermetic_linux_sandbox",
                 "--sandbox_add_mount_pair=/usr"):
        assert f"build {flag}" in rc, f"{flag} is not an unconditional build flag"
        assert f"build:hermetic {flag}" not in rc, f"{flag} was made opt-in"
